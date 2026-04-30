# Configuration

This build supports a simulated backend and a live ScreenLogic backend through
`screenlogicpy`.

## Primary Parameters

### Connection

- `screenlogic_host`
  - Hostname or IP address for the Pentair ScreenLogic adapter.
- `screenlogic_port`
  - Port for the Pentair ScreenLogic adapter. Most local adapters use `80`.
- `screenlogic_system_name`
  - Optional Pentair system name in the style used by ScreenLogic, such as
    `Pentair: 00-00-00`.
- `screenlogic_password`
  - Optional ScreenLogic password. Leave blank for the normal local
    `screenlogicpy` login behavior.

### Runtime Mode

- `mode`
  - `0` = simulated/fake mode
  - `1` = live read-only mode with polling enabled
  - `2` = live read/write mode with polling disabled
  - `3` = live read/write mode with polling enabled

Recommended examples:

```text
mode=0
screenlogic_host=
screenlogic_port=80
screenlogic_system_name=
screenlogic_password=
```

```text
mode=1
screenlogic_host=192.168.1.99
screenlogic_port=80
screenlogic_system_name=Pentair: F1-11-11
screenlogic_password=
```

```text
mode=2
screenlogic_host=192.168.1.99
screenlogic_port=80
screenlogic_system_name=Pentair: F1-11-11
screenlogic_password=
```

```text
mode=3
screenlogic_host=192.168.1.99
screenlogic_port=80
screenlogic_system_name=Pentair: F1-11-11
screenlogic_password=
```

## Optional Parameters

These are advanced overrides. The node server should run fine without them.

### Refresh And Command Timing

- `OPT_refresh_interval_seconds`
  - Poll interval used by polling modes (`mode=1` and `mode=3`).
  - Default is `60`.
- `OPT_command_interval_seconds`
  - Minimum spacing between write commands.
  - Default is `10`.
  - This exists mainly for advanced tuning; the built-in default is intended to
    be safe for most ScreenLogic adapters.
- `OPT_startup_refresh`
  - `true` performs an initial live refresh during startup.
  - Default is `true` for live modes and `false` for simulated mode.
- `OPT_sync_after_write`
  - `true` refreshes state after write commands.
  - Default is `true`.

### Node Visibility

- `OPT_show_pool_node`
  - `true` keeps the main `Pool` node visible.
  - Default is `true`.
- `OPT_show_features`
  - `true` creates nodes for discovered ScreenLogic circuits/features.
  - Default is `true`.
- `OPT_show_solar_heater`
  - `true` keeps the fixed `Solar Heater` node visible.
  - Default is `true`.
- `OPT_show_solar_thermostat`
  - `true` keeps the fixed `Solar Thermostat` node visible.
  - Default is `true`.
- `OPT_show_dummy_thermostat`
  - `true` keeps the standalone `Dummy Thermostat` node visible for profile
    experiments.
  - Forced off in live modes.

### Feature Filtering

- `OPT_include_circuits`
  - Optional comma-separated circuit IDs or exact lower-case names to include.
  - Leave blank to include all discovered circuits.
- `OPT_exclude_circuits`
  - Optional comma-separated circuit IDs or exact lower-case names to suppress.

## Debug Parameters

These are intended for QA and troubleshooting.

- `DEBUG_log_level`
- `DEBUG_log_discovery_summary`
- `DEBUG_log_command_queue`
- `DEBUG_log_state_summary`

Current builds may not use every debug flag yet, but these names are reserved
for the debug-only configuration surface.

## Current Safety Defaults

- `mode=2` is the safest full-control mode because it disables background
  polling while still allowing writes.
- Polling is enabled by default only in `mode=1` and `mode=3`.
- Write commands are paced by an internal default of `10` seconds unless
  `OPT_command_interval_seconds` overrides it.
- Password values are not logged.
- The legacy hardcoded diagnostic runner is disabled by default.

## Legacy Compatible Names

The parser still accepts older names for backward compatibility while the new
configuration model rolls out:

- `connection_mode`
- `backend_mode`
- `dummy_mode`
- `allow_writes`
- `control_enabled`
- `auto_refresh`
- `poll_enabled`
- `refresh_interval_seconds`
- `poll_seconds`
- `command_interval_seconds`
- `min_command_seconds`
- `show_features`
- `feature_nodes_enabled`
- `show_solar_heater`
- `include_solar_node`
- `show_solar_thermostat`
- `include_solar_thermostat_node`
- `show_dummy_thermostat`
- `include_dummy_thermostat`
- `feature_include_list`
- `feature_include`
- `feature_exclude_list`
- `feature_exclude`
