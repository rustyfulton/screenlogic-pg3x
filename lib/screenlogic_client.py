from __future__ import annotations

from abc import ABC, abstractmethod

from lib.model import FeatureState, PoolState


class ScreenLogicClient(ABC):
    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_state(self) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_pump(self, enabled: bool) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_heater(self, enabled: bool) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_pool_setpoint(self, value: int) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_solar_enabled(self, enabled: bool) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_solar_setpoint(self, value: int) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_solar_cool_setpoint(self, value: int) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_solar_mode(self, value: int) -> PoolState:
        raise NotImplementedError

    @abstractmethod
    def set_solar_fan_mode(self, value: int) -> PoolState:
        raise NotImplementedError

    def get_features(self) -> tuple[FeatureState, ...]:
        return ()

    def set_feature(self, circuit_id: int, enabled: bool) -> PoolState:
        raise RuntimeError("This ScreenLogic backend does not support feature commands.")
