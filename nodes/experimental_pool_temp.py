import udi_interface

LOGGER = udi_interface.LOGGER


class ExperimentalPoolTempBaseNode(udi_interface.Node):
    hint = None

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client

    def refresh(self, command=None):
        LOGGER.info("Refreshing experimental pool temperature node %s", self.address)
        self.update_from_state(self.client.get_state())


class ExperimentalPoolTempThermostatReadWriteNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_tstat_rw"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
        {"driver": "CLISPC", "value": 88, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFS", "value": 0, "uom": 68},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name, client)
        self.cool_setpoint = 88
        self.mode = 1
        self.fan_mode = 0

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental pool temp RW thermostat: set heat setpoint to %s", raw)
        state = self.client.set_pool_setpoint(raw)
        self.update_from_state(state)

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental pool temp RW thermostat: set cool setpoint to %s", raw)
        self.cool_setpoint = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental pool temp RW thermostat: set mode to %s", raw)
        self.mode = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental pool temp RW thermostat: set fan mode to %s", raw)
        self.fan_mode = int(raw)
        self.update_from_state(self.client.get_state())

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)
        self.setDriver("CLISPC", self.cool_setpoint, force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)
        self.setDriver("CLIFS", self.fan_mode, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
    }


class ExperimentalPoolTempThermostatReadOnlyNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_tstat_ro"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
        {"driver": "CLISPC", "value": 88, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFS", "value": 0, "uom": 68},
    ]

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)
        self.setDriver("CLISPC", state.pool_setpoint_f + 4, force=True)
        self.setDriver("CLIMD", 1, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)
        self.setDriver("CLIFS", 0, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
    }


class ExperimentalPoolTempSensorNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_sensor"
    drivers = [{"driver": "ST", "value": 82, "uom": 17}]

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
    }


class ExperimentalPoolTempTempSetpointNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_temp_sp"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
    ]

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental pool temp temp/setpoint node: set setpoint to %s", raw)
        state = self.client.set_pool_setpoint(raw)
        self.update_from_state(state)

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": cmd_set_heat_setpoint,
    }


class ExperimentalPoolTempThermostatHintRWNode(ExperimentalPoolTempThermostatReadWriteNode):
    hint = "0x05010000"


class ExperimentalPoolTempThermostatHintRONode(ExperimentalPoolTempThermostatReadOnlyNode):
    hint = "0x05010000"


class ExperimentalPoolTempTemperatureHintSensorNode(ExperimentalPoolTempSensorNode):
    hint = "0x05020000"


class ExperimentalPoolTempTemperatureHintSetpointNode(ExperimentalPoolTempTempSetpointNode):
    hint = "0x05020000"
