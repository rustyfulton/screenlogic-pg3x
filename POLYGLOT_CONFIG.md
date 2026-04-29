# Configuration

This build supports a simulated backend and a live ScreenLogic backend through
`screenlogicpy`.

## Custom Parameters

- `backend_mode`
  - `fake` uses the built-in simulated pool backend.
  - `screenlogic` enables live ScreenLogic polling.
- `dummy_mode`
  - Legacy compatibility option. `true` maps to `backend_mode=fake`.
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
- `control_enabled`
  - `false` keeps the node server read-only.
  - `true` allows write commands such as feature on/off and heat mode changes.
- `poll_seconds`
  - Minimum live refresh interval. Defaults to `60`; values below `10` are
    raised to `10`.
- `min_command_seconds`
  - Minimum delay between write commands. Defaults to `10`; values below `5`
    are raised to `5`.
- `feature_nodes_enabled`
  - `true` creates a node for each discovered ScreenLogic circuit/feature.
- `feature_include`
  - Optional comma-separated circuit IDs or exact lower-case names to include.
    Leave blank to include all discovered circuits.
- `feature_exclude`
  - Optional comma-separated circuit IDs or exact lower-case names to suppress.
- `include_dummy_thermostat`
  - `true` keeps the standalone `Dummy Thermostat` node visible for profile
    experiments.

## Current Safety Defaults

- Live write commands are blocked unless `control_enabled=true`.
- Write commands are paced by `min_command_seconds`.
- Password values are not logged. Diagnostics report only password labels such
  as blank/configured length.
- The legacy hardcoded diagnostic runner is disabled by default.
