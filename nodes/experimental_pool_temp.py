import udi_interface

LOGGER = udi_interface.LOGGER


class ExperimentalPoolTempBaseNode(udi_interface.Node):
    hint = None

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        LOGGER.info(
            "Experimental pool temp node created address=%s primary=%s id=%s hint=%s",
            self.address,
            primary,
            getattr(self, "id", "<unknown>"),
            getattr(self, "hint", None),
        )

    def refresh(self, command=None):
        LOGGER.info(
            "Refreshing experimental pool temperature node address=%s command=%s",
            self.address,
            command,
        )
        state = self.client.get_state()
        self.update_from_state(state)

    def _log_snapshot(self, label, **values):
        joined = " ".join(f"{key}={value}" for key, value in values.items())
        LOGGER.info(
            "Experimental pool temp node %s address=%s %s",
            label,
            self.address,
            joined,
        )


class ExperimentalPoolTempPowerAlarmNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_pmalarm"
    drivers = [{"driver": "ALARM", "value": 1, "uom": 93}]

    def update_from_state(self, state):
        value = 1 if getattr(state, "pump_on", False) or getattr(state, "heater_on", False) else 2
        self.setDriver("ALARM", value, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
    }


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


class ExperimentalPoolTempStrictUdiThermostatNode(ExperimentalPoolTempBaseNode):
    hint = "0x05010000"
    id = "ptemp_tstat_udi"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
        {"driver": "CLISPC", "value": 88, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name, client)
        self.cool_setpoint = 88
        self.mode = 1

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental strict UDI thermostat: set heat setpoint to %s", raw)
        state = self.client.set_pool_setpoint(raw)
        self.update_from_state(state)

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental strict UDI thermostat: set cool setpoint to %s", raw)
        self.cool_setpoint = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental strict UDI thermostat: set mode to %s", raw)
        self.mode = int(raw)
        self.update_from_state(self.client.get_state())

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)
        self.setDriver("CLISPC", self.cool_setpoint, force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
    }


class ExperimentalPoolTempDocCloneThermostatNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_tstat_doc"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
        {"driver": "CLISPC", "value": 88, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name, client)
        self.cool_setpoint = 88
        self.mode = 1

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        self._log_snapshot(
            "command.CLISPH.before",
            payload=command,
            heat_sp=self.drivers[1]["value"],
            cool_sp=self.cool_setpoint,
            mode=self.mode,
        )
        state = self.client.set_pool_setpoint(raw)
        self.update_from_state(state)
        self._log_snapshot(
            "command.CLISPH.after",
            heat_sp=self.getDriver("CLISPH"),
            cool_sp=self.getDriver("CLISPC"),
            mode=self.getDriver("CLIMD"),
        )

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        self._log_snapshot(
            "command.CLISPC.before",
            payload=command,
            heat_sp=self.getDriver("CLISPH"),
            cool_sp=self.cool_setpoint,
            mode=self.mode,
        )
        self.cool_setpoint = int(raw)
        self.update_from_state(self.client.get_state())
        self._log_snapshot(
            "command.CLISPC.after",
            heat_sp=self.getDriver("CLISPH"),
            cool_sp=self.getDriver("CLISPC"),
            mode=self.getDriver("CLIMD"),
        )

    def cmd_set_mode(self, command):
        raw = command.get("value")
        self._log_snapshot(
            "command.CLIMD.before",
            payload=command,
            heat_sp=self.getDriver("CLISPH"),
            cool_sp=self.getDriver("CLISPC"),
            mode=self.mode,
        )
        self.mode = int(raw)
        self.update_from_state(self.client.get_state())
        self._log_snapshot(
            "command.CLIMD.after",
            heat_sp=self.getDriver("CLISPH"),
            cool_sp=self.getDriver("CLISPC"),
            mode=self.getDriver("CLIMD"),
        )

    def update_from_state(self, state):
        self.setDriver("ST", state.pool_temp_f, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)
        self.setDriver("CLISPC", self.cool_setpoint, force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)
        self._log_snapshot(
            "publish",
            temp=state.pool_temp_f,
            heat_sp=state.pool_setpoint_f,
            cool_sp=self.cool_setpoint,
            mode=self.mode,
            hcs=1 if state.heater_on else 0,
        )

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
    }


class ExperimentalPoolTempDocCloneHintThermostatNode(
    ExperimentalPoolTempDocCloneThermostatNode
):
    hint = "0x05010000"


class ExperimentalPoolTempDocClonePracticalThermostatNode(
    ExperimentalPoolTempDocCloneThermostatNode
):
    id = "ptemp_tstat_doc_plus"
    hint = "0x05010000"

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": ExperimentalPoolTempDocCloneThermostatNode.cmd_set_heat_setpoint,
        "CLISPC": ExperimentalPoolTempDocCloneThermostatNode.cmd_set_cool_setpoint,
        "CLIMD": ExperimentalPoolTempDocCloneThermostatNode.cmd_set_mode,
    }


class ExperimentalPoolTempFullCloneThermostatNode(ExperimentalPoolTempBaseNode):
    id = "ptemp_tstat_full"
    drivers = [
        {"driver": "ST", "value": 82, "uom": 17},
        {"driver": "CLITEMP", "value": 82, "uom": 17},
        {"driver": "CLISPH", "value": 84, "uom": 17},
        {"driver": "CLISPC", "value": 88, "uom": 17},
        {"driver": "CLIMD", "value": 1, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIHUM", "value": 51, "uom": 22},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIFRS", "value": 0, "uom": 80},
        {"driver": "CLIFSO", "value": 0, "uom": 81},
        {"driver": "BATLVL", "value": 100, "uom": 51},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name, client)
        self.cool_setpoint = 88
        self.mode = 1
        self.fan_mode = 0
        self.fan_override = 0
        self.humidity = 51.0
        self.battery_level = 100

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental full-clone thermostat: set heat setpoint to %s", raw)
        state = self.client.set_pool_setpoint(raw)
        self.update_from_state(state)

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental full-clone thermostat: set cool setpoint to %s", raw)
        self.cool_setpoint = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental full-clone thermostat: set mode to %s", raw)
        self.mode = int(raw)
        self.update_from_state(self.client.get_state())

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info("Experimental full-clone thermostat: set fan mode to %s", raw)
        self.fan_mode = int(raw)
        self.update_from_state(self.client.get_state())

    def update_from_state(self, state):
        current_temp = state.pool_temp_f
        hvac_state = 1 if state.heater_on else 0
        fan_run_state = 1 if state.pump_on else 0
        self.setDriver("ST", current_temp, force=True)
        self.setDriver("CLITEMP", current_temp, force=True)
        self.setDriver("CLISPH", state.pool_setpoint_f, force=True)
        self.setDriver("CLISPC", self.cool_setpoint, force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", hvac_state, force=True)
        self.setDriver("CLIHUM", self.humidity, force=True)
        self.setDriver("CLIFS", self.fan_mode, force=True)
        self.setDriver("CLIFRS", fan_run_state, force=True)
        self.setDriver("CLIFSO", self.fan_override, force=True)
        self.setDriver("BATLVL", self.battery_level, force=True)

    commands = {
        "QUERY": ExperimentalPoolTempBaseNode.refresh,
        "REFRESH": ExperimentalPoolTempBaseNode.refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
    }


class ExperimentalPoolTempFullCloneHintThermostatNode(
    ExperimentalPoolTempFullCloneThermostatNode
):
    hint = "0x05010000"
