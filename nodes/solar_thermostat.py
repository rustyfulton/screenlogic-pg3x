import udi_interface

LOGGER = udi_interface.LOGGER


class SolarThermostatNode(udi_interface.Node):
    id = "solartstat"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 86, "uom": 17},
        {"driver": "CLISPC", "value": 90, "uom": 17},
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

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic thermostat command: set heat setpoint to %s", raw)
        self.update_from_state(self.client.set_solar_setpoint(raw))

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic thermostat command: set mode to %s", raw)
        self.update_from_state(self.client.set_solar_mode(raw))

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic thermostat command: set cool setpoint to %s", raw)
        self.update_from_state(self.client.set_solar_cool_setpoint(raw))

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic thermostat command: set fan mode to %s", raw)
        self.update_from_state(self.client.set_solar_fan_mode(raw))

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.solar_setpoint_f, force=True)
        self.setDriver("CLISPC", state.solar_cool_setpoint_f, force=True)
        self.setDriver("CLIMD", state.solar_mode, force=True)
        self.setDriver("CLIHCS", 1 if state.solar_active else 0, force=True)
        self.setDriver("CLIFS", state.solar_fan_mode, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
    }
