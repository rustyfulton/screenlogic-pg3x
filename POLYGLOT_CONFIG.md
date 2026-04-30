# Configuration

This build supports a simulated backend and a live ScreenLogic backend through
`screenlogicpy`.

## Preferred Custom Parameters

### Connection

- `connection_mode`
  - `simulated` uses the built-in test backend.
  - `live` enables the real local ScreenLogic adapter.
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

### Safety And Refresh

- `allow_writes`
  - `false` keeps the node server read-only.
  - `true` allows write commands such as feature on/off and heat mode changes.
- `auto_refresh`
  - `false` keeps the live ScreenLogic backend in command-only/manual-refresh mode.
  - `true` allows background polling at the configured refresh interval.
  - Defaults to `false` for live ScreenLogic and `true` for simulated mode.
- `refresh_interval_seconds`
  - Minimum live refresh interval. Defaults to `60`; values below `10` are
    raised to `10`.
- `command_interval_seconds`
  - Minimum delay between write commands. Defaults to `10`; values below `5`
    are raised to `5`.

### Node Visibility

- `show_features`
  - `true` creates a node for each discovered ScreenLogic circuit/feature.
- `show_solar_heater`
  - `true` keeps the fixed `Solar Heater` node visible.
- `show_solar_thermostat`
  - `true` keeps the fixed `Solar Thermostat` node visible.
- `show_dummy_thermostat`
  - `true` keeps the standalone `Dummy Thermostat` node visible for profile
    experiments. This is forced off in live mode.

### Feature Filtering

- `feature_include_list`
  - Optional comma-separated circuit IDs or exact lower-case names to include.
    Leave blank to include all discovered circuits.
- `feature_exclude_list`
  - Optional comma-separated circuit IDs or exact lower-case names to suppress.

## Legacy Compatible Names

These still work for backward compatibility:

- `backend_mode` -> `connection_mode`
  - `fake` maps to `simulated`
  - `screenlogic` maps to `live`
- `dummy_mode` -> legacy shortcut for simulated mode
- `control_enabled` -> `allow_writes`
- `poll_enabled` -> `auto_refresh`
- `poll_seconds` -> `refresh_interval_seconds`
- `min_command_seconds` -> `command_interval_seconds`
- `feature_nodes_enabled` -> `show_features`
- `include_solar_node` -> `show_solar_heater`
- `include_solar_thermostat_node` -> `show_solar_thermostat`
- `include_dummy_thermostat` -> `show_dummy_thermostat`
- `feature_include` -> `feature_include_list`
- `feature_exclude` -> `feature_exclude_list`
- `screenlogic_name` -> `screenlogic_system_name`

## Current Safety Defaults

- Live write commands are blocked unless `control_enabled=true`.
- Live background polling is disabled by default; use `QUERY`, `REFRESH`, or a
  write command to fetch fresh state unless `poll_enabled=true`.
- Write commands are paced by `min_command_seconds`.
- Password values are not logged. Diagnostics report only password labels such
  as blank/configured length.
- The legacy hardcoded diagnostic runner is disabled by default.
