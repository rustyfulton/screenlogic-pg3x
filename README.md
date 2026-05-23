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

## Alexa / ISY Portal Thermostat Enrollment

There is currently one annoying but important manual step if you want ISY Portal
to offer the pool solar thermostat as a thermostat for Amazon Echo / Alexa.

1. Install the plugin and configure it normally.
2. Confirm the thermostat is visible and working in native IoX / Admin Console
   usage first.
3. In ISY Portal, open:
   `Select Tool -> Connectivity -> Device Hint Editor`
4. Find the solar thermostat device. In practice this is the device ending with
   `n*_solartstat` (shown as the Solar Thermostat node).
5. Change its hint from:
   `0.0.0.0`
   to:
   `1.12.1.0`
6. Go back to:
   `Select Tool -> Connectivity -> Amazon Echo`
7. Add the device there. After the hint change, Portal should offer it as a
   thermostat instead of a switch.

If Portal or Alexa gets into a bad state, delete the device from Portal/Alexa,
reinstall the node server into a fresh slot number, and try again.

## Admin Console NLS Placeholders

If you see button or subtitle text like:

- `[NLS-10:ND-feature-NAME]`
- `[NLS-10:CMD-REFRESH-NAME]`

that means IoX is showing unresolved profile labels from the node server NLS
files. In practice, this usually means the updated profile has not been fully
reloaded yet. Reinstall/update the node server profile and let IoX reload it.
