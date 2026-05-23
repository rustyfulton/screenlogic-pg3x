import udi_interface

LOGGER = udi_interface.LOGGER


class PoolThermostatNode(udi_interface.Node):
    id = "ThermostatF"
    hint = "0x010C0100"
    drivers = [
        {"driver": "ST", "value": 82.0, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLISPC", "value": 88.0, "uom": 17},
        {"driver": "CLISPH", "value": 84.0, "uom": 17},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIFRS", "value": 0, "uom": 80},
        {"driver": "CLIFSO", "value": 0, "uom": 81},
        {"driver": "CLIHUM", "value": 50.0, "uom": 22},
        {"driver": "BATLVL", "value": 100, "uom": 51},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.cool_setpoint = 88
        self.mode = 1
        self.fan_mode = 0
        self.fan_override = 0
        self.humidity = 50.0
        self.battery_level = 100

    def _encode_temp(self, value):
        return round(float(value), 1)

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

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool thermostat command: set fan mode to %s", raw)
        try:
            self.fan_mode = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid pool thermostat fan payload=%s", raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_fan_override(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool thermostat command: set fan override to %s", raw)
        try:
            self.fan_override = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid pool thermostat fan override payload=%s", raw)
        self.update_from_state(self.client.get_state())

    def update_from_state(self, state):
        self.setDriver("ST", self._encode_temp(state.pool_temp_f), force=True)
        self.setDriver("CLISPH", self._encode_temp(state.pool_setpoint_f), force=True)
        self.setDriver("CLISPC", self._encode_temp(self.cool_setpoint), force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)
        self.setDriver("CLIFS", self.fan_mode, force=True)
        self.setDriver("CLIFRS", 1 if state.pump_on else 0, force=True)
        self.setDriver("CLIFSO", self.fan_override, force=True)
        self.setDriver("CLIHUM", self.humidity, force=True)
        self.setDriver("BATLVL", self.battery_level, force=True)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
        "CLIFSO": cmd_set_fan_override,
    }
