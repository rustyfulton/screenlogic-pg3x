from __future__ import annotations

from dataclasses import dataclass


def _normalize_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_int(value, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_csv(value) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    return tuple(
        item.strip().lower()
        for item in str(value).split(",")
        if item.strip()
    )


@dataclass
class NodeServerConfig:
    backend_mode: str = "fake"
    screenlogic_system_name: str = ""
    screenlogic_host: str = ""
    screenlogic_port: int = 0
    screenlogic_password: str = ""
    control_enabled: bool = False
    poll_enabled: bool = True
    poll_seconds: int = 60
    include_dummy_thermostat: bool = False
    include_solar_node: bool = True
    include_solar_thermostat_node: bool = True
    feature_nodes_enabled: bool = True
    feature_include: tuple[str, ...] = ()
    feature_exclude: tuple[str, ...] = ()
    min_command_seconds: int = 10

    @property
    def use_fake_backend(self) -> bool:
        return self.backend_mode == "fake"

    @classmethod
    def from_params(cls, params: dict) -> "NodeServerConfig":
        backend_mode = str(params.get("backend_mode", "")).strip().lower()
        dummy_mode = _normalize_bool(params.get("dummy_mode"), default=False)
        if backend_mode not in {"fake", "screenlogic"}:
            backend_mode = "fake" if dummy_mode or not params else "screenlogic"
        include_dummy_thermostat = _normalize_bool(
            params.get("include_dummy_thermostat"),
            default=False,
        )
        poll_enabled = _normalize_bool(
            params.get("poll_enabled"),
            default=backend_mode == "fake",
        )
        include_solar_node = _normalize_bool(
            params.get("include_solar_node"),
            default=True,
        )
        include_solar_thermostat_node = _normalize_bool(
            params.get("include_solar_thermostat_node"),
            default=True,
        )
        if backend_mode == "screenlogic":
            include_dummy_thermostat = False

        return cls(
            backend_mode=backend_mode,
            screenlogic_system_name=str(params.get("screenlogic_system_name", "")).strip(),
            screenlogic_host=str(params.get("screenlogic_host", "")).strip(),
            screenlogic_port=_normalize_int(params.get("screenlogic_port"), 0),
            screenlogic_password=str(params.get("screenlogic_password", "")).strip(),
            control_enabled=_normalize_bool(params.get("control_enabled"), default=False),
            poll_enabled=poll_enabled,
            poll_seconds=max(10, _normalize_int(params.get("poll_seconds"), 60)),
            include_dummy_thermostat=include_dummy_thermostat,
            include_solar_node=include_solar_node,
            include_solar_thermostat_node=include_solar_thermostat_node,
            feature_nodes_enabled=_normalize_bool(
                params.get("feature_nodes_enabled"),
                default=True,
            ),
            feature_include=_normalize_csv(params.get("feature_include")),
            feature_exclude=_normalize_csv(params.get("feature_exclude")),
            min_command_seconds=max(
                5,
                _normalize_int(params.get("min_command_seconds"), 10),
            ),
        )
