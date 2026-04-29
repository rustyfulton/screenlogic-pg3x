import udi_interface

LOGGER = udi_interface.LOGGER


class SolarHeaterNode(udi_interface.Node):
    id = "solarhtr"
    drivers = [
        {"driver": "ST", "value": 1, "uom": 2},
        {"driver": "GV0", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 86, "uom": 17},
        {"driver": "GV2", "value": 1, "uom": 25},
        {"driver": "GV3", "value": 0, "uom": 25},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client

    def refresh(self, command=None):
        LOGGER.info("Refreshing ScreenLogic solar heater state")
        self.update_from_state(self.client.get_state())

    def cmd_solar_on(self, command):
        LOGGER.info("ScreenLogic solar command: solar auto enabled")
        self.update_from_state(self.client.set_solar_enabled(True))

    def cmd_solar_off(self, command):
        LOGGER.info("ScreenLogic solar command: solar off")
        self.update_from_state(self.client.set_solar_enabled(False))

    def cmd_set_solar_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic solar command: set solar setpoint to %s", raw)
        self.update_from_state(self.client.set_solar_setpoint(raw))

    def update_from_state(self, state):
        self.setDriver("ST", 1 if state.connected else 0, force=True)
        self.setDriver("GV0", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.solar_setpoint_f, force=True)
        self.setDriver("GV2", 1 if state.solar_enabled else 0, force=True)
        self.setDriver("GV3", 1 if state.solar_active else 0, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "SOLAR_ON": cmd_solar_on,
        "SOLAR_OFF": cmd_solar_off,
        "CLISPH": cmd_set_solar_setpoint,
        "SET_SOLAR_SP": cmd_set_solar_setpoint,
    }
