from dataclasses import dataclass


@dataclass
class PoolState:
    connected: bool = True
    pool_temp_f: int = 82
    spa_temp_f: int = 99
    pump_on: bool = False
    heater_on: bool = False
    pool_setpoint_f: int = 84
    solar_enabled: bool = True
    solar_active: bool = False
    solar_setpoint_f: int = 86
    solar_mode: int = 1
    solar_cool_setpoint_f: int = 90
    solar_fan_mode: int = 0


@dataclass(frozen=True)
class FeatureState:
    circuit_id: int
    name: str
    enabled: bool
    function: int | None = None
    interface: int | None = None
    is_light: bool = False
