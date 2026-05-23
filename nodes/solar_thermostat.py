import udi_interface

LOGGER = udi_interface.LOGGER


class SolarThermostatNode(udi_interface.Node):
    id = "solartstat"
    MIN_SETPOINT_F = 45
    MAX_SETPOINT_F = 95
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 86, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFS", "value": 0, "uom": 68},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client

    def refresh(self, command=None):
        LOGGER.info("Refreshing ScreenLogic solar thermostat state")
        self.update_from_state(self.client.get_state())

    def _clamp_setpoint(self, value):
        try:
            numeric = int(round(float(value)))
        except (TypeError, ValueError):
            return self.MIN_SETPOINT_F
        return max(self.MIN_SETPOINT_F, min(self.MAX_SETPOINT_F, numeric))

    def _normalize_mode(self, value):
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 0
        return 1 if numeric == 1 else 0

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        clamped = self._clamp_setpoint(raw)
        LOGGER.info(
            "ScreenLogic solar thermostat command: set heat setpoint raw=%s clamped=%s",
            raw,
            clamped,
        )
        self.update_from_state(self.client.set_solar_setpoint(clamped))

    def cmd_set_mode(self, command):
        raw = command.get("value")
        normalized = self._normalize_mode(raw)
        LOGGER.info(
            "ScreenLogic solar thermostat command: set mode raw=%s normalized=%s",
            raw,
            normalized,
        )
        self.update_from_state(self.client.set_solar_mode(normalized))

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic solar thermostat command: set fan mode to %s", raw)
        self.update_from_state(self.client.set_solar_fan_mode(raw))

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", self._clamp_setpoint(state.solar_setpoint_f), force=True)
        self.setDriver("CLIMD", self._normalize_mode(state.solar_mode), force=True)
        self.setDriver("CLIHCS", 1 if state.solar_active else 0, force=True)
        self.setDriver("CLIFS", state.solar_fan_mode, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
    }
