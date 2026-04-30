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
    mode: int = 0
    backend_mode: str = "fake"
    screenlogic_system_name: str = ""
    screenlogic_host: str = ""
    screenlogic_port: int = 0
    screenlogic_password: str = ""
    control_enabled: bool = False
    poll_enabled: bool = True
    poll_seconds: int = 60
    startup_refresh: bool = True
    sync_after_write: bool = True
    include_pool_node: bool = True
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
        mode_value = _first_param(params, "mode")
        parsed_mode = _normalize_int(mode_value, -1)
        dummy_mode = _normalize_bool(params.get("dummy_mode"), default=False)
        requested_connection_mode = str(
            _first_param(params, "connection_mode", "backend_mode") or ""
        ).strip().lower()

        if parsed_mode in (0, 1, 2, 3):
            mode = parsed_mode
        else:
            connection_aliases = {
                "0": 0,
                "fake": 0,
                "simulated": 0,
                "simulation": 0,
                "1": 1,
                "readonly": 1,
                "read_only": 1,
                "read-only": 1,
                "2": 2,
                "control": 2,
                "write": 2,
                "readwrite": 2,
                "read_write": 2,
                "read-write": 2,
                "live": 2,
                "screenlogic": 2,
                "3": 3,
                "control_polling": 3,
                "control+polling": 3,
                "readwrite_polling": 3,
                "read-write-polling": 3,
            }
            mode = connection_aliases.get(requested_connection_mode, -1)

        if mode not in (0, 1, 2, 3):
            if dummy_mode:
                mode = 0
            elif not params:
                mode = 0
            else:
                control_enabled_legacy = _normalize_bool(
                    _first_param(params, "allow_writes", "control_enabled"),
                    default=False,
                )
                poll_enabled_legacy = _normalize_bool(
                    _first_param(params, "auto_refresh", "poll_enabled"),
                    default=False,
                )
                if control_enabled_legacy:
                    mode = 3 if poll_enabled_legacy else 2
                else:
                    mode = 1 if poll_enabled_legacy else 1

        backend_mode = "fake" if mode == 0 else "screenlogic"
        control_enabled = mode in (2, 3)
        poll_enabled_default = mode in (0, 1, 3)
        startup_refresh_default = mode != 0

        include_dummy_thermostat = _normalize_bool(
            _first_param(
                params,
                "OPT_show_dummy_thermostat",
                "show_dummy_thermostat",
                "include_dummy_thermostat",
            ),
            default=False,
        )
        poll_enabled = _normalize_bool(
            _first_param(params, "auto_refresh", "poll_enabled"),
            default=poll_enabled_default,
        )
        startup_refresh = _normalize_bool(
            _first_param(params, "OPT_startup_refresh", "startup_refresh"),
            default=startup_refresh_default,
        )
        sync_after_write = _normalize_bool(
            _first_param(params, "OPT_sync_after_write", "sync_after_write"),
            default=True,
        )
        include_pool_node = _normalize_bool(
            _first_param(params, "OPT_show_pool_node", "show_pool_node"),
            default=True,
        )
        include_solar_node = _normalize_bool(
            _first_param(
                params,
                "OPT_show_solar_heater",
                "show_solar_heater",
                "include_solar_node",
            ),
            default=True,
        )
        include_solar_thermostat_node = _normalize_bool(
            _first_param(
                params,
                "OPT_show_solar_thermostat",
                "show_solar_thermostat",
                "include_solar_thermostat_node",
            ),
            default=True,
        )
        if backend_mode == "screenlogic":
            include_dummy_thermostat = False

        return cls(
            mode=mode,
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
            control_enabled=control_enabled,
            poll_enabled=poll_enabled,
            poll_seconds=max(
                10,
                _normalize_int(
                    _first_param(
                        params,
                        "OPT_refresh_interval_seconds",
                        "refresh_interval_seconds",
                        "poll_seconds",
                    ),
                    60,
                ),
            ),
            startup_refresh=startup_refresh,
            sync_after_write=sync_after_write,
            include_pool_node=include_pool_node,
            include_dummy_thermostat=include_dummy_thermostat,
            include_solar_node=include_solar_node,
            include_solar_thermostat_node=include_solar_thermostat_node,
            feature_nodes_enabled=_normalize_bool(
                _first_param(
                    params,
                    "OPT_show_features",
                    "show_features",
                    "feature_nodes_enabled",
                ),
                default=True,
            ),
            feature_include=_normalize_csv(
                _first_param(
                    params,
                    "OPT_include_circuits",
                    "feature_include_list",
                    "feature_include",
                )
            ),
            feature_exclude=_normalize_csv(
                _first_param(
                    params,
                    "OPT_exclude_circuits",
                    "feature_exclude_list",
                    "feature_exclude",
                )
            ),
            min_command_seconds=max(
                5,
                _normalize_int(
                    _first_param(
                        params,
                        "OPT_command_interval_seconds",
                        "command_interval_seconds",
                        "min_command_seconds",
                    ),
                    10,
                ),
            ),
        )
