from __future__ import annotations

import socket

import udi_interface

from lib.model import PoolState
from lib.screenlogic_protocol import (
    CONNECT_BANNER,
    DISCOVERY_MESSAGE,
    DISCOVERY_PORT,
    PACKET_HEADER_SIZE,
    ChallengeInfo,
    HeatMode,
    LocalUnitConnection,
    MessageId,
    ScreenLogicPacket,
    VersionInfo,
    build_local_login_payload,
    decode_packet_header,
    encode_packet,
    parse_challenge_payload,
    parse_version_payload,
)
from lib.screenlogic_client import ScreenLogicClient
from lib.screenlogic_types import (
    ScreenLogicBodyState,
    ScreenLogicEquipmentFlags,
    ScreenLogicEquipmentState,
    ScreenLogicSnapshot,
)

LOGGER = udi_interface.LOGGER


class RealScreenLogicClient(ScreenLogicClient):
    def __init__(
        self,
        host: str,
        port: int,
        control_enabled: bool = False,
        system_name: str = "",
        password: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.control_enabled = control_enabled
        self.system_name = system_name
        self.password = password
        self.state = PoolState(connected=False)
        self.snapshot = ScreenLogicSnapshot()
        self.discovered_unit = None
        self.challenge = ChallengeInfo()
        self.version = VersionInfo()
        self.last_probe_packet = None
        self.login_response_code = None
        self.login_response_payload = b""

    def connect(self) -> bool:
        if self.host and self.port:
            self.discovered_unit = LocalUnitConnection(
                gateway_name=self.system_name or "Configured ScreenLogic Unit",
                address=self.host,
                port=self.port,
            )
        elif self.discovered_unit is None:
            self.discovered_unit = self._select_discovered_unit()

        self.state.connected = self._probe_local_connection()
        return self.state.connected

    def get_state(self) -> PoolState:
        self._refresh_state_from_snapshot()
        return self.state

    def discover_local_units(self) -> list[LocalUnitConnection]:
        units = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.0)
            sock.bind(("", 0))
            sock.sendto(DISCOVERY_MESSAGE, ("255.255.255.255", DISCOVERY_PORT))

            while True:
                try:
                    data, remote = sock.recvfrom(512)
                except socket.timeout:
                    break

                unit = self._parse_discovery_response(data, remote[0])
                if unit is not None:
                    units.append(unit)
        finally:
            sock.close()

        return units

    def apply_snapshot(self, snapshot: ScreenLogicSnapshot) -> PoolState:
        self.snapshot = snapshot
        self._refresh_state_from_snapshot()
        return self.state

    def apply_equipment_data(
        self,
        *,
        pool: ScreenLogicBodyState | None = None,
        spa: ScreenLogicBodyState | None = None,
        equipment_flags: ScreenLogicEquipmentFlags | None = None,
        equipment_state: ScreenLogicEquipmentState | None = None,
    ) -> PoolState:
        if pool is not None:
            self.snapshot.pool = pool
        if spa is not None:
            self.snapshot.spa = spa
        if equipment_flags is not None:
            self.snapshot.equipment_flags = equipment_flags
        if equipment_state is not None:
            self.snapshot.equipment_state = equipment_state
        self._refresh_state_from_snapshot()
        return self.state

    def set_pump(self, enabled: bool) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_heater(self, enabled: bool) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_pool_setpoint(self, value: int) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_solar_enabled(self, enabled: bool) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_solar_setpoint(self, value: int) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_solar_cool_setpoint(self, value: int) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_solar_mode(self, value: int) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def set_solar_fan_mode(self, value: int) -> PoolState:
        self._ensure_write_allowed()
        return self.state

    def _refresh_state_from_snapshot(self) -> None:
        pool = self.snapshot.pool
        spa = self.snapshot.spa
        flags = self.snapshot.equipment_flags
        equipment = self.snapshot.equipment_state

        self.state.pool_temp_f = pool.current_temp_f or self.state.pool_temp_f
        self.state.spa_temp_f = spa.current_temp_f or self.state.spa_temp_f
        self.state.pool_setpoint_f = pool.set_point_f or self.state.pool_setpoint_f
        self.state.solar_setpoint_f = pool.set_point_f or self.state.solar_setpoint_f
        self.state.solar_cool_setpoint_f = (
            pool.cool_set_point_f or self.state.solar_cool_setpoint_f
        )
        self.state.pump_on = equipment.pool_circuit_on or equipment.spa_circuit_on
        self.state.heater_on = equipment.pool_heater_on
        self.state.solar_active = equipment.solar_active
        self.state.solar_mode = self._map_heat_mode(pool.heat_mode, flags)
        self.state.solar_enabled = self.state.solar_mode != 0

    def _select_discovered_unit(self) -> LocalUnitConnection | None:
        units = self.discover_local_units()
        if not units:
            LOGGER.warning("ScreenLogic discovery did not find any local units.")
            return None

        if self.system_name:
            for unit in units:
                if unit.gateway_name.strip("\x00") == self.system_name:
                    return unit

        return units[0]

    def _probe_local_connection(self) -> bool:
        if self.discovered_unit is None:
            return False

        try:
            with socket.create_connection(
                (self.discovered_unit.address, self.discovered_unit.port),
                timeout=2.0,
            ) as sock:
                sock.settimeout(2.0)
                self._send_connect_banner(sock)
                self._request_challenge(sock)
                challenge_packet = self._read_packet(sock)
                if challenge_packet is not None:
                    self.last_probe_packet = challenge_packet
                    if challenge_packet.message_id == MessageId.CHALLENGE_RESPONSE:
                        self.challenge = parse_challenge_payload(challenge_packet.payload)
                login_packet = self._request_local_login(sock)
                if login_packet is None:
                    LOGGER.warning(
                        "ScreenLogic local login returned no response for %s:%s",
                        self.discovered_unit.address,
                        self.discovered_unit.port,
                    )
                    return False

                self.last_probe_packet = login_packet
                self.login_response_code = login_packet.message_id
                self.login_response_payload = login_packet.payload
                if login_packet.message_id == MessageId.ERROR_LOGIN_REJECTED:
                    LOGGER.warning(
                        "ScreenLogic local login rejected for %s:%s using password length=%s",
                        self.discovered_unit.address,
                        self.discovered_unit.port,
                        len((self.password or "").strip()),
                    )
                    return False

                if login_packet.message_id != MessageId.LOCAL_LOGIN_RESPONSE:
                    LOGGER.warning(
                        "ScreenLogic local login got unexpected response code %s for %s:%s",
                        login_packet.message_id,
                        self.discovered_unit.address,
                        self.discovered_unit.port,
                    )
                    return False

                self._request_version_probe(sock)
                LOGGER.info(
                    "ScreenLogic TCP probe succeeded for %s:%s (challenge=%s login_code=%s version=%s)",
                    self.discovered_unit.address,
                    self.discovered_unit.port,
                    self.challenge.challenge or "<none>",
                    self.login_response_code or "<none>",
                    self.version.version or "<unknown>",
                )
                return True
        except OSError as exc:
            LOGGER.warning(
                "ScreenLogic TCP probe failed for %s:%s: %s",
                self.discovered_unit.address,
                self.discovered_unit.port,
                exc,
            )
            return False
        except ValueError as exc:
            LOGGER.warning(
                "ScreenLogic TCP probe received malformed data from %s:%s: %s",
                self.discovered_unit.address,
                self.discovered_unit.port,
                exc,
            )
            return False

    def _parse_discovery_response(
        self,
        data: bytes,
        remote_address: str,
    ) -> LocalUnitConnection | None:
        if len(data) < 40:
            return None

        server_type = int.from_bytes(data[0:4], "little", signed=True)
        if server_type != 2:
            return None

        port = int.from_bytes(data[8:10], "little", signed=True)
        gateway_name = data[12:29].decode("utf-8", errors="ignore").rstrip("\x00")
        return LocalUnitConnection(
            gateway_name=gateway_name,
            address=remote_address,
            port=port,
        )

    def _map_heat_mode(
        self,
        heat_mode: int,
        flags: ScreenLogicEquipmentFlags,
    ) -> int:
        if not flags.pool_solar_present and not flags.pool_solar_heat_pump_present:
            return 0

        if heat_mode == HeatMode.OFF:
            return 0
        if heat_mode == HeatMode.SOLAR:
            return 1
        if heat_mode == HeatMode.SOLAR_PREFERRED:
            return 3
        if heat_mode == HeatMode.HEAT_PUMP:
            return 2
        return self.state.solar_mode

    def _ensure_write_allowed(self) -> None:
        if not self.control_enabled:
            raise RuntimeError(
                "ScreenLogic write command blocked because control_enabled is false."
            )

    def _send_connect_banner(self, sock: socket.socket) -> None:
        sock.sendall(CONNECT_BANNER)

    def _request_version_probe(self, sock: socket.socket) -> None:
        packet = encode_packet(4, MessageId.VERSION_REQUEST)
        sock.sendall(packet)
        try:
            response = self._read_packet(sock)
        except socket.timeout:
            response = None

        if response is not None and response.message_id == MessageId.VERSION_RESPONSE:
            self.version = parse_version_payload(response.payload)

    def _request_challenge(self, sock: socket.socket) -> None:
        packet = encode_packet(2, MessageId.CHALLENGE_REQUEST)
        sock.sendall(packet)

    def _request_local_login(self, sock: socket.socket) -> ScreenLogicPacket | None:
        payload = build_local_login_payload(self.password)
        packet = encode_packet(1, MessageId.LOCAL_LOGIN_REQUEST, payload)
        sock.sendall(packet)
        return self._read_packet(sock)

    def _read_packet(self, sock: socket.socket) -> ScreenLogicPacket | None:
        header = self._read_exact(sock, PACKET_HEADER_SIZE)
        if not header:
            return None

        sender_id, message_id, payload_length = decode_packet_header(header)
        payload = self._read_exact(sock, payload_length) if payload_length else b""
        return ScreenLogicPacket(
            sender_id=sender_id,
            message_id=message_id,
            payload=payload,
        )

    def _read_exact(self, sock: socket.socket, length: int) -> bytes:
        if length <= 0:
            return b""

        remaining = length
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                raise ValueError(
                    f"ScreenLogic connection closed while reading {length} bytes."
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
