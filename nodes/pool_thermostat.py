import udi_interface

LOGGER = udi_interface.LOGGER


class PoolThermostatNode(udi_interface.Node):
    id = "ThermostatF"
    hint = "0x010C0100"
    drivers = [
        {"driver": "ST", "value": 820, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLISPC", "value": 880, "uom": 17},
        {"driver": "CLISPH", "value": 840, "uom": 17},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.cool_setpoint = 88
        self.mode = 1

    def _encode_temp(self, value):
        return int(round(float(value) * 10))

    def refresh(self, command=None):
        LOGGER.info("Refreshing ScreenLogic pool thermostat state command=%s", command)
        self.update_from_state(self.client.get_state())

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool thermostat command: set heat setpoint to %s", raw)
        self.update_from_state(self.client.set_pool_setpoint(raw))

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool thermostat command: set cool setpoint to %s", raw)
        self.cool_setpoint = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool thermostat command: set mode to %s", raw)
        try:
            self.mode = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid pool thermostat mode payload=%s", raw)
        self.update_from_state(self.client.get_state())

    def update_from_state(self, state):
        self.setDriver("ST", self._encode_temp(state.pool_temp_f), force=True)
        self.setDriver("CLISPH", self._encode_temp(state.pool_setpoint_f), force=True)
        self.setDriver("CLISPC", self._encode_temp(self.cool_setpoint), force=True)
        self.setDriver("CLIMD", self.mode, force=True)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
    }
