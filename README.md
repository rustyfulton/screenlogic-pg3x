# ScreenLogic Pool PG3x Node Server

This repository contains a PG3x node server for Universal Devices eisy/IoX.

Current capabilities:

- PG3x-style installable project structure
- controller, pool, solar heater, thermostat-style, and dynamic feature nodes
- fake backend for safe simulation
- live ScreenLogic backend through `screenlogicpy`
- discovered ScreenLogic circuit/feature nodes with on/off commands
- read-only default mode with opt-in writes through `control_enabled`
- conservative command pacing to avoid rapid back-to-back ScreenLogic writes
- command-only live refresh mode through `poll_enabled=false`
- configurable fixed solar nodes for different equipment layouts

The live backend follows the same broad model as the Home Assistant integration:
connect to the local ScreenLogic adapter, discover configured bodies and
circuits, map heater/solar modes from ScreenLogic data, and expose switchable
circuits as feature nodes.
