# ScreenLogic Pool PG3x Node Server

This repository contains a PG3x node server for Universal Devices eisy/IoX.

Current capabilities:

- PG3x-style installable project structure
- controller, pool, solar heater, thermostat-style, and dynamic feature nodes
- fake backend for safe simulation
- live ScreenLogic backend through `screenlogicpy`
- discovered ScreenLogic circuit/feature nodes with on/off commands
- mode-based read-only or read/write behavior
- conservative command pacing to avoid rapid back-to-back ScreenLogic writes
- command-only live refresh mode through `mode=2`
- configurable fixed solar nodes for different equipment layouts

Preferred PG3x configuration now centers on a single `mode` parameter:
- `mode=0` simulated/fake mode
- `mode=1` live read-only mode with polling
- `mode=2` live read/write mode without polling
- `mode=3` live read/write mode with polling

Advanced overrides use `OPT_` prefixes, and debug-only settings use
`DEBUG_` prefixes.

For live PG3 operation, the recommended polling posture is:
- `shortPoll=180` for normal state refresh in polling modes
- `longPoll=6000` for infrequent topology and feature inventory refreshes

Notes:
- In polling modes, PG3 `shortPoll` is the real driver of automatic refresh
  timing.
- `OPT_refresh_interval_seconds` is a client-side minimum refresh floor and
  does not override PG3 `shortPoll`.

The live backend follows the same broad model as the Home Assistant integration:
connect to the local ScreenLogic adapter, discover configured bodies and
circuits, map heater/solar modes from ScreenLogic data, and expose switchable
circuits as feature nodes.
