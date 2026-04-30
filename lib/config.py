from __future__ import annotations

from dataclasses import dataclass


def _first_param(params: dict, *keys):
    for key in keys:
        if key in params and params.get(key) not in (None, ""):
            return params.get(key)
    return None


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
        requested_mode = str(
            _first_param(params, "connection_mode", "backend_mode") or ""
        ).strip().lower()
        dummy_mode = _normalize_bool(params.get("dummy_mode"), default=False)
        mode_aliases = {
            "fake": "fake",
            "simulated": "fake",
            "simulation": "fake",
            "screenlogic": "screenlogic",
            "live": "screenlogic",
        }
        backend_mode = mode_aliases.get(requested_mode, "")
        if backend_mode not in {"fake", "screenlogic"}:
            backend_mode = "fake" if dummy_mode or not params else "screenlogic"

        include_dummy_thermostat = _normalize_bool(
            _first_param(
                params,
                "show_dummy_thermostat",
                "include_dummy_thermostat",
            ),
            default=False,
        )
        poll_enabled = _normalize_bool(
            _first_param(params, "auto_refresh", "poll_enabled"),
            default=backend_mode == "fake",
        )
        include_solar_node = _normalize_bool(
            _first_param(params, "show_solar_heater", "include_solar_node"),
            default=True,
        )
        include_solar_thermostat_node = _normalize_bool(
            _first_param(
                params,
                "show_solar_thermostat",
                "include_solar_thermostat_node",
            ),
            default=True,
        )
        if backend_mode == "screenlogic":
            include_dummy_thermostat = False

        return cls(
            backend_mode=backend_mode,
            screenlogic_system_name=str(
                _first_param(
                    params,
                    "screenlogic_system_name",
                    "screenlogic_name",
                )
                or ""
            ).strip(),
            screenlogic_host=str(_first_param(params, "screenlogic_host") or "").strip(),
            screenlogic_port=_normalize_int(_first_param(params, "screenlogic_port"), 0),
            screenlogic_password=str(
                _first_param(params, "screenlogic_password")
                or ""
            ).strip(),
            control_enabled=_normalize_bool(
                _first_param(params, "allow_writes", "control_enabled"),
                default=False,
            ),
            poll_enabled=poll_enabled,
            poll_seconds=max(
                10,
                _normalize_int(
                    _first_param(params, "refresh_interval_seconds", "poll_seconds"),
                    60,
                ),
            ),
            include_dummy_thermostat=include_dummy_thermostat,
            include_solar_node=include_solar_node,
            include_solar_thermostat_node=include_solar_thermostat_node,
            feature_nodes_enabled=_normalize_bool(
                _first_param(params, "show_features", "feature_nodes_enabled"),
                default=True,
            ),
            feature_include=_normalize_csv(
                _first_param(params, "feature_include_list", "feature_include")
            ),
            feature_exclude=_normalize_csv(
                _first_param(params, "feature_exclude_list", "feature_exclude")
            ),
            min_command_seconds=max(
                5,
                _normalize_int(
                    _first_param(
                        params,
                        "command_interval_seconds",
                        "min_command_seconds",
                    ),
                    10,
                ),
            ),
        )
