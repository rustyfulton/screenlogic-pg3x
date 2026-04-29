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


@dataclass(frozen=True)
class EquipmentProfile:
    firmware: str = ""
    controller_type: int | str | None = None
    hardware_type: int | str | None = None
    equipment_flags: int = 0
    body_names: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    light_names: tuple[str, ...] = ()
    has_solar: bool = False
    has_cooling: bool = False
    has_chlorinator: bool = False
    has_chemistry: bool = False
    has_hybrid_heater: bool = False
    intelliflo_pump_count: int = 0
