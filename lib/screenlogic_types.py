from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScreenLogicBodyState:
    current_temp_f: int = 0
    set_point_f: int = 0
    cool_set_point_f: int = 0
    heat_mode: int = 0


@dataclass
class ScreenLogicEquipmentFlags:
    pool_solar_present: bool = False
    pool_solar_heat_pump_present: bool = False


@dataclass
class ScreenLogicEquipmentState:
    air_temp_f: int = 0
    pool_circuit_on: bool = False
    spa_circuit_on: bool = False
    pool_heater_on: bool = False
    solar_active: bool = False


@dataclass
class ScreenLogicSnapshot:
    pool: ScreenLogicBodyState = field(default_factory=ScreenLogicBodyState)
    spa: ScreenLogicBodyState = field(default_factory=ScreenLogicBodyState)
    equipment_flags: ScreenLogicEquipmentFlags = field(default_factory=ScreenLogicEquipmentFlags)
    equipment_state: ScreenLogicEquipmentState = field(default_factory=ScreenLogicEquipmentState)
