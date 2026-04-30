from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import udi_interface

from lib.model import EquipmentProfile, FeatureState, PoolState
from lib.screenlogic_client import ScreenLogicClient
from lib.screenlogic_protocol import build_local_login_payload

LOGGER = udi_interface.LOGGER

POST_WRITE_REFRESH_INITIAL_DELAY_SECONDS = 2
POST_WRITE_REFRESH_SECOND_DELAY_SECONDS = 5


@dataclass
class _CommandToken:
    event: threading.Event = field(default_factory=threading.Event)
    result: PoolState | None = None
    error: Exception | None = None


@dataclass
class _QueuedCommand:
    write_key: str
    description: str
    operation: Callable[[Any], Any]
    update_before: bool = False
    tokens: list[_CommandToken] = field(default_factory=list)


class ScreenLogicPyClient(ScreenLogicClient):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        system_name: str = "",
        password: str = "",
        control_enabled: bool = False,
        min_refresh_seconds: int = 30,
        min_command_seconds: int = 10,
        sync_after_write: bool = True,
    ) -> None:
        self.host = host
        self.port = port or 80
        self.system_name = system_name
        self.password = str(password or "").strip()
        self.control_enabled = control_enabled
        self.min_refresh_seconds = max(10, int(min_refresh_seconds or 30))
        self.min_command_seconds = max(5, int(min_command_seconds or 10))
        self.sync_after_write = bool(sync_after_write)
        self.state = PoolState(connected=False)
        self._lock = threading.Lock()
        self._last_data: dict[str, Any] = {}
        self._last_refresh_at = 0.0
        self._last_command_at = 0.0
        self._last_feature_config_summary: tuple[tuple[Any, ...], ...] = ()
        self._light_function_values: set[int] | None = None
        self._equipment_profile: EquipmentProfile | None = None
        self._command_condition = threading.Condition()
        self._command_queue: list[_QueuedCommand] = []
        self._command_worker = threading.Thread(
            target=self._command_worker_loop,
            name="screenlogic_command_queue",
            daemon=True,
        )
        self._command_worker.start()

    def connect(self) -> bool:
        with self._lock:
            self._refresh_state(force=True)
            return self.state.connected

    def get_state(self) -> PoolState:
        with self._lock:
            self._refresh_state()
            return self.state

    def get_features(self) -> tuple[FeatureState, ...]:
        with self._lock:
            self._refresh_state()
            return tuple(self._extract_features(self._last_data))

    def get_equipment_profile(self) -> EquipmentProfile | None:
        with self._lock:
            if not self._equipment_profile and self.host:
                self._refresh_state()
            return self._equipment_profile

    def set_feature(self, circuit_id: int, enabled: bool) -> PoolState:
        state_text = "on" if enabled else "off"
        return self._enqueue_write(
            write_key=f"feature:{int(circuit_id)}",
            description=f"set feature circuit {int(circuit_id)} {state_text}",
            operation=lambda gateway: gateway.async_set_circuit(
                int(circuit_id), 1 if enabled else 0
            ),
        )

    def set_pump(self, enabled: bool) -> PoolState:
        self._ensure_write_allowed()
        with self._lock:
            self._refresh_state()
            circuit_id = self._find_primary_pump_circuit_id(
                self._last_data.get("circuit", {})
            )
        if circuit_id is None:
            raise RuntimeError("Unable to identify the primary pool pump circuit.")
        return self.set_feature(circuit_id, enabled)

    def set_heater(self, enabled: bool) -> PoolState:
        return self._enqueue_write(
            write_key="body:0:heat_mode",
            description=f"set pool heater {'on' if enabled else 'off'}",
            operation=lambda gateway: gateway.async_set_heat_mode(
                0, 3 if enabled else 0
            ),
            update_before=True,
        )

    def set_pool_setpoint(self, value: int) -> PoolState:
        setpoint = int(value)
        return self._enqueue_write(
            write_key="body:0:heat_temp",
            description=f"set pool heat setpoint {setpoint}",
            operation=lambda gateway: gateway.async_set_heat_temp(0, setpoint),
            update_before=True,
        )

    def set_solar_enabled(self, enabled: bool) -> PoolState:
        return self.set_solar_mode(1 if enabled else 0)

    def set_solar_setpoint(self, value: int) -> PoolState:
        return self.set_pool_setpoint(value)

    def set_solar_cool_setpoint(self, value: int) -> PoolState:
        LOGGER.info(
            "ScreenLogic cool setpoint command received, but screenlogicpy exposes "
            "only heat setpoint writes for this body. Updating local driver only."
        )
        self.state.solar_cool_setpoint_f = int(value)
        return self.state

    def set_solar_mode(self, value: int) -> PoolState:
        mode = int(value)
        return self._enqueue_write(
            write_key="body:0:heat_mode",
            description=f"set pool heat mode {mode}",
            operation=lambda gateway: gateway.async_set_heat_mode(0, mode),
            update_before=True,
        )

    def set_solar_fan_mode(self, value: int) -> PoolState:
        LOGGER.info(
            "ScreenLogic fan mode command received, but ScreenLogic pool heat modes "
            "do not expose a fan command. Updating local driver only."
        )
        self.state.solar_fan_mode = int(value)
        return self.state

    def _refresh_state(self, *, force: bool = False) -> None:
        if not self.host:
            LOGGER.warning("ScreenLogic refresh skipped because no host is configured.")
            self.state.connected = False
            return

        now = time.monotonic()
        age = now - self._last_refresh_at
        if (
            not force
            and self.state.connected
            and self._last_data
            and age < self.min_refresh_seconds
        ):
            return

        try:
            self._last_data = asyncio.run(self._async_fetch_data())
            self._last_refresh_at = time.monotonic()
            self._apply_data_to_state(self._last_data)
            self.state.connected = True
            self._equipment_profile = self._build_equipment_profile(self._last_data)
            self._log_configuration_digest(self._last_data)
            self._log_state_digest(self._last_data)
        except Exception as exc:
            LOGGER.warning(
                "ScreenLogic refresh failed for %s:%s: %s",
                self.host,
                self.port,
                exc,
            )
            self.state.connected = False

    def _enqueue_write(
        self,
        *,
        write_key: str,
        description: str,
        operation: Callable[[Any], Any],
        update_before: bool = False,
    ) -> PoolState:
        self._ensure_write_allowed()
        token = _CommandToken()
        with self._command_condition:
            queued = self._find_queued_command(write_key)
            if queued is not None:
                queued.description = description
                queued.operation = operation
                queued.tokens.append(token)
                LOGGER.info(
                    "ScreenLogic command coalesced: key=%s latest=%s waiters=%s",
                    write_key,
                    description,
                    len(queued.tokens),
                )
            else:
                self._command_queue.append(
                    _QueuedCommand(
                        write_key=write_key,
                        description=description,
                        operation=operation,
                        update_before=update_before,
                        tokens=[token],
                    )
                )
                LOGGER.info(
                    "ScreenLogic command queued: key=%s description=%s queue_depth=%s",
                    write_key,
                    description,
                    len(self._command_queue),
                )
            self._command_condition.notify()

        token.event.wait()
        if token.error is not None:
            raise token.error
        assert token.result is not None
        return token.result

    async def _async_fetch_data(self) -> dict[str, Any]:
        return await self._async_with_gateway()

    async def _async_with_gateway(
        self,
        operation: Callable[[Any], Any] | None = None,
        *,
        update_before: bool = True,
        update_after: bool = True,
    ) -> dict[str, Any]:
        from screenlogicpy import ScreenLogicGateway
        import screenlogicpy.requests.login as login_module

        original_create_login_message = login_module.create_login_message
        patch_login = bool(self.password)
        if patch_login:
            login_module.create_login_message = lambda: build_local_login_payload(
                self.password
            )

        gateway = ScreenLogicGateway()
        try:
            connected = await gateway.async_connect(
                self.host,
                self.port,
                name=self.system_name,
            )
            if not connected:
                raise RuntimeError("ScreenLogic gateway login returned not connected.")

            if update_before:
                await gateway.async_update()
            if operation is not None:
                await operation(gateway)
                if update_after:
                    LOGGER.info(
                        "ScreenLogic post-write refresh: waiting %ss before first refresh",
                        POST_WRITE_REFRESH_INITIAL_DELAY_SECONDS,
                    )
                    await asyncio.sleep(POST_WRITE_REFRESH_INITIAL_DELAY_SECONDS)
                    await gateway.async_update()
                    LOGGER.info(
                        "ScreenLogic post-write refresh: waiting %ss before second refresh",
                        POST_WRITE_REFRESH_SECOND_DELAY_SECONDS,
                    )
                    await asyncio.sleep(POST_WRITE_REFRESH_SECOND_DELAY_SECONDS)
                    await gateway.async_update()
            return gateway.get_data()
        finally:
            if patch_login:
                login_module.create_login_message = original_create_login_message
            if gateway.is_connected:
                try:
                    await gateway.async_disconnect()
                except Exception as exc:  # pragma: no cover
                    LOGGER.debug("Ignoring ScreenLogic disconnect cleanup error: %s", exc)

    def _apply_data_to_state(self, data: dict[str, Any]) -> None:
        pool_body = data.get("body", {}).get(0, {})
        spa_body = data.get("body", {}).get(1, {})
        controller = data.get("controller", {})
        controller_sensor = controller.get("sensor", {})
        controller_equipment = controller.get("equipment", {})
        circuits = data.get("circuit", {})
        pumps = data.get("pump", {})

        pool_temp = self._nested_value(pool_body, "last_temperature")
        spa_temp = self._nested_value(spa_body, "last_temperature")
        heat_setpoint = self._nested_value(pool_body, "heat_setpoint")
        cool_setpoint = self._nested_value(pool_body, "cool_setpoint")
        heat_mode = self._nested_value(pool_body, "heat_mode")
        heat_state = self._nested_value(pool_body, "heat_state")
        air_temp = self._nested_value(controller_sensor, "air_temperature")
        equipment_flags = int(controller_equipment.get("flags", 0) or 0)

        if pool_temp is not None:
            self.state.pool_temp_f = int(pool_temp)
        if spa_temp is not None:
            self.state.spa_temp_f = int(spa_temp)
        if heat_setpoint is not None:
            self.state.pool_setpoint_f = int(heat_setpoint)
            self.state.solar_setpoint_f = int(heat_setpoint)
        if cool_setpoint is not None:
            self.state.solar_cool_setpoint_f = int(cool_setpoint)

        mapped_mode = self._map_heat_mode(int(heat_mode or 0), equipment_flags)
        self.state.solar_mode = mapped_mode
        self.state.solar_enabled = mapped_mode in (1, 2)
        self.state.heater_on = int(heat_state or 0) in (2, 3)
        self.state.solar_active = int(heat_state or 0) in (1, 3)
        self.state.pump_on = self._infer_pump_on(pumps, circuits)

        if air_temp is not None:
            LOGGER.info("ScreenLogic air temperature: %sF", air_temp)

    def _extract_features(self, data: dict[str, Any]) -> list[FeatureState]:
        features: list[FeatureState] = []
        circuits = data.get("circuit", {}) or {}
        for raw_circuit_id, circuit in sorted(
            circuits.items(), key=lambda item: int(item[0])
        ):
            circuit_id = int(raw_circuit_id)
            name = str(circuit.get("name") or f"Circuit {circuit_id}").strip()
            value = self._nested_value(circuit, "value")
            function = self._safe_int(circuit.get("function"))
            interface = self._safe_int(circuit.get("interface"))
            features.append(
                FeatureState(
                    circuit_id=circuit_id,
                    name=name,
                    enabled=bool(int(value or 0)),
                    function=function,
                    interface=interface,
                    is_light=self._is_light_function(function),
                )
            )
        return features

    def _build_equipment_profile(self, data: dict[str, Any]) -> EquipmentProfile:
        controller = data.get("controller", {})
        configuration = controller.get("configuration", {})
        equipment_flags = int(controller.get("equipment", {}).get("flags", 0) or 0)
        bodies = data.get("body", {}) or {}
        features = self._extract_features(data)
        body_names = tuple(self._body_name(index) for index in sorted(bodies.keys()))
        feature_names = tuple(feature.name for feature in features if not feature.is_light)
        light_names = tuple(feature.name for feature in features if feature.is_light)
        return EquipmentProfile(
            firmware=str(
                self._nested_value(data.get("adapter", {}).get("firmware", {}), "value")
                or ""
            ),
            controller_type=configuration.get("controller_type"),
            hardware_type=configuration.get("hardware_type"),
            equipment_flags=equipment_flags,
            body_names=body_names,
            feature_names=feature_names,
            light_names=light_names,
            has_solar=bool(equipment_flags & 0x1),
            has_cooling=bool(equipment_flags & 0x10000),
            has_chlorinator=bool(equipment_flags & 0x20),
            has_chemistry=bool(equipment_flags & 0x80),
            has_hybrid_heater=bool(equipment_flags & 0x20000),
            intelliflo_pump_count=self._count_intelliflo_flags(equipment_flags),
        )

    def _log_configuration_digest(self, data: dict[str, Any]) -> None:
        features = self._extract_features(data)
        summary = tuple(
            (
                feature.circuit_id,
                feature.name,
                feature.function,
                feature.interface,
                feature.is_light,
            )
            for feature in features
        )
        if summary == self._last_feature_config_summary:
            return

        self._last_feature_config_summary = summary
        profile = self._equipment_profile or self._build_equipment_profile(data)
        LOGGER.info(
            "ScreenLogic configuration: firmware=%s controller_type=%s hardware_type=%s "
            "equipment_flags=0x%X bodies=%s circuits=%s solar=%s cooling=%s "
            "chlorinator=%s chemistry=%s hybrid_heater=%s intelliflo_pumps=%s",
            profile.firmware or "<unknown>",
            profile.controller_type if profile.controller_type is not None else "<unknown>",
            profile.hardware_type if profile.hardware_type is not None else "<unknown>",
            profile.equipment_flags,
            len(profile.body_names),
            len(features),
            profile.has_solar,
            profile.has_cooling,
            profile.has_chlorinator,
            profile.has_chemistry,
            profile.has_hybrid_heater,
            profile.intelliflo_pump_count,
        )
        for feature in features:
            LOGGER.info(
                "ScreenLogic circuit discovered: id=%s name=%s state=%s function=%s "
                "interface=%s light=%s",
                feature.circuit_id,
                feature.name,
                "on" if feature.enabled else "off",
                feature.function if feature.function is not None else "<unknown>",
                feature.interface if feature.interface is not None else "<unknown>",
                feature.is_light,
            )

    def _log_state_digest(self, data: dict[str, Any]) -> None:
        pool_body = data.get("body", {}).get(0, {})
        heat_mode = self._nested_value(pool_body, "heat_mode")
        heat_state = self._nested_value(pool_body, "heat_state")
        active_features = [
            f"{feature.circuit_id}:{feature.name}"
            for feature in self._extract_features(data)
            if feature.enabled
        ]
        LOGGER.info(
            "ScreenLogic state: pool=%sF spa=%sF setpoint=%sF heat_mode=%s "
            "heat_state=%s pump=%s solar_enabled=%s solar_active=%s heater_on=%s "
            "active_features=%s",
            self.state.pool_temp_f,
            self.state.spa_temp_f,
            self.state.pool_setpoint_f,
            heat_mode if heat_mode is not None else "<unknown>",
            heat_state if heat_state is not None else "<unknown>",
            self.state.pump_on,
            self.state.solar_enabled,
            self.state.solar_active,
            self.state.heater_on,
            ", ".join(active_features) if active_features else "<none>",
        )

    def _wait_for_command_slot(self, description: str) -> None:
        if not self._last_command_at:
            return
        elapsed = time.monotonic() - self._last_command_at
        remaining = self.min_command_seconds - elapsed
        if remaining <= 0:
            return
        LOGGER.info(
            "ScreenLogic command pacing: waiting %.1fs before %s",
            remaining,
            description,
        )
        time.sleep(remaining)

    def _command_worker_loop(self) -> None:
        while True:
            with self._command_condition:
                while not self._command_queue:
                    self._command_condition.wait()
                command = self._command_queue.pop(0)

            result: PoolState | None = None
            error: Exception | None = None
            try:
                with self._lock:
                    self._wait_for_command_slot(command.description)
                    LOGGER.info("ScreenLogic command requested: %s", command.description)
                    self._last_data = asyncio.run(
                        self._async_with_gateway(
                            operation=command.operation,
                            update_before=command.update_before,
                            update_after=self.sync_after_write,
                        )
                    )
                    self._last_command_at = time.monotonic()
                    self._last_refresh_at = self._last_command_at
                    self._apply_data_to_state(self._last_data)
                    self._equipment_profile = self._build_equipment_profile(self._last_data)
                    self.state.connected = True
                    self._log_state_digest(self._last_data)
                    LOGGER.info("ScreenLogic command completed: %s", command.description)
                    result = self.state
            except Exception as exc:
                with self._lock:
                    self._last_command_at = time.monotonic()
                LOGGER.warning("ScreenLogic command failed: %s: %s", command.description, exc)
                error = exc

            for token in command.tokens:
                token.result = result
                token.error = error
                token.event.set()

    def _map_heat_mode(self, heat_mode: int, equipment_flags: int) -> int:
        has_solar = bool(equipment_flags & 0x1)
        if not has_solar:
            return 0 if heat_mode == 0 else min(heat_mode, 3)
        return min(heat_mode, 3)

    def _infer_pump_on(self, pumps: dict[str, Any], circuits: dict[str, Any]) -> bool:
        for pump in pumps.values():
            pump_state = self._nested_value(pump, "state")
            rpm_now = self._nested_value(pump, "rpm_now")
            watts_now = self._nested_value(pump, "watts_now")
            if any(int(value or 0) > 0 for value in (pump_state, rpm_now, watts_now)):
                return True

        for circuit in circuits.values():
            name = str(circuit.get("name", "")).strip().lower()
            circuit_value = int(self._nested_value(circuit, "value") or 0)
            if circuit_value and any(token in name for token in ("pool", "filter", "pump")):
                return True

        return False

    def _find_primary_pump_circuit_id(self, circuits: dict[str, Any]) -> int | None:
        for circuit_id, circuit in circuits.items():
            name = str(circuit.get("name", "")).strip().lower()
            if any(token in name for token in ("pool", "filter", "pump")):
                return int(circuit_id)
        return None

    def _nested_value(self, container: dict[str, Any], key: str) -> Any:
        value = container.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value

    def _safe_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _is_light_function(self, function: int | None) -> bool:
        if function is None:
            return False
        if self._light_function_values is None:
            self._light_function_values = self._load_light_function_values()
        return int(function) in self._light_function_values

    def _load_light_function_values(self) -> set[int]:
        try:
            from screenlogicpy.device_const.circuit import FUNCTION
        except Exception:
            return set()

        values: set[int] = set()
        for name in (
            "COLOR_WHEEL",
            "DIMMER",
            "INTELLIBRITE",
            "LIGHT",
            "MAGICSTREAM",
            "PHOTONGEN",
            "SAL_LIGHT",
            "SAM_LIGHT",
        ):
            enum_value = getattr(FUNCTION, name, None)
            if enum_value is not None:
                try:
                    values.add(int(enum_value))
                except (TypeError, ValueError):
                    values.add(int(enum_value.value))
        return values

    def _find_queued_command(self, write_key: str) -> _QueuedCommand | None:
        for queued in reversed(self._command_queue):
            if queued.write_key == write_key:
                return queued
        return None

    def _count_intelliflo_flags(self, equipment_flags: int) -> int:
        count = 0
        for bit in (0x100, 0x200, 0x400, 0x800):
            if equipment_flags & bit:
                count += 1
        return count

    def _body_name(self, index: Any) -> str:
        try:
            numeric = int(index)
        except (TypeError, ValueError):
            return f"Body {index}"
        return {0: "Pool", 1: "Spa"}.get(numeric, f"Body {numeric}")

    def _ensure_write_allowed(self) -> None:
        if not self.control_enabled:
            raise RuntimeError(
                "ScreenLogic write command blocked because control_enabled is false."
            )
