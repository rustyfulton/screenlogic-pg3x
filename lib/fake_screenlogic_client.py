from __future__ import annotations

from lib.model import FeatureState, PoolState
from lib.screenlogic_client import ScreenLogicClient


class FakeScreenLogicClient(ScreenLogicClient):
    def __init__(self) -> None:
        self.state = PoolState()
        self._tick = 0
        self.features = {
            501: FeatureState(501, "Waterfall", False, function=0, interface=0),
            502: FeatureState(502, "Pool Light", False, function=1, interface=0, is_light=True),
            510: FeatureState(510, "Roof Solar Valve", True, function=0, interface=0),
        }

    def connect(self) -> bool:
        self.state.connected = True
        return True

    def get_state(self) -> PoolState:
        self.state.solar_mode = 1 if self.state.solar_enabled else 0
        self._tick += 1
        self.state.solar_active = (
            self.state.connected
            and self.state.pump_on
            and self.state.solar_enabled
            and self.state.pool_temp_f < self.state.solar_setpoint_f
        )

        if self.state.solar_active:
            if self._tick % 2 == 0:
                self.state.pool_temp_f += 1
        elif self.state.pump_on and self.state.heater_on:
            if self._tick % 2 == 0 and self.state.pool_temp_f < self.state.pool_setpoint_f:
                self.state.pool_temp_f += 1
        elif not self.state.pump_on and self._tick % 3 == 0 and self.state.pool_temp_f > 78:
            self.state.pool_temp_f -= 1

        return self.state

    def set_pump(self, enabled: bool) -> PoolState:
        self.state.pump_on = enabled
        return self.state

    def set_heater(self, enabled: bool) -> PoolState:
        self.state.heater_on = enabled
        return self.state

    def set_pool_setpoint(self, value: int) -> PoolState:
        self.state.pool_setpoint_f = max(40, min(104, int(value)))
        return self.state

    def set_solar_enabled(self, enabled: bool) -> PoolState:
        self.state.solar_enabled = enabled
        self.state.solar_mode = 1 if enabled else 0
        if not enabled:
            self.state.solar_active = False
        return self.state

    def set_solar_setpoint(self, value: int) -> PoolState:
        self.state.solar_setpoint_f = max(40, min(104, int(value)))
        return self.state

    def set_solar_cool_setpoint(self, value: int) -> PoolState:
        self.state.solar_cool_setpoint_f = max(40, min(104, int(value)))
        return self.state

    def set_solar_mode(self, value: int) -> PoolState:
        mode = int(value)
        self.state.solar_mode = mode
        self.state.solar_enabled = mode != 0
        if not self.state.solar_enabled:
            self.state.solar_active = False
        return self.state

    def set_solar_fan_mode(self, value: int) -> PoolState:
        self.state.solar_fan_mode = int(value)
        return self.state

    def get_features(self) -> tuple[FeatureState, ...]:
        return tuple(self.features.values())

    def set_feature(self, circuit_id: int, enabled: bool) -> PoolState:
        feature = self.features[int(circuit_id)]
        self.features[int(circuit_id)] = FeatureState(
            circuit_id=feature.circuit_id,
            name=feature.name,
            enabled=enabled,
            function=feature.function,
            interface=feature.interface,
            is_light=feature.is_light,
        )
        return self.state
