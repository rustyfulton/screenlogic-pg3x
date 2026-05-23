import udi_interface

LOGGER = udi_interface.LOGGER


class EcobeeLabThermostatNode(udi_interface.Node):
    id = "EcobeeF"
    hint = "0x050b0100"
    drivers = [
        {"driver": "ST", "value": 74, "uom": 17},
        {"driver": "CLISPH", "value": 65, "uom": 17},
        {"driver": "CLISPC", "value": 74, "uom": 17},
        {"driver": "CLIMD", "value": 2, "uom": 67},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIHUM", "value": 50, "uom": 22},
        {"driver": "CLIHCS", "value": 2, "uom": 66},
        {"driver": "CLIFRS", "value": 1, "uom": 80},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.climd = 2

    def refresh(self, command=None):
        LOGGER.info("Refreshing Ecobee lab thermostat command=%s", command)
        state = self.client.get_state()
        temp = int(round(float(state.pool_temp_f)))
        heat_sp = int(round(float(state.pool_setpoint_f)))
        cool_sp = max(heat_sp, 74)
        hcs = 2 if state.heater_on else 0
        fan_state = 1 if state.pump_on else 0
        self.setDriver("ST", temp, force=True)
        self.setDriver("CLISPH", heat_sp, force=True)
        self.setDriver("CLISPC", cool_sp, force=True)
        self.setDriver("CLIMD", self.climd, force=True)
        self.setDriver("CLIFS", 0, force=True)
        self.setDriver("CLIHUM", 50, force=True)
        self.setDriver("CLIHCS", hcs, force=True)
        self.setDriver("CLIFRS", fan_state, force=True)

    def _set_int(self, attr_name, driver, command):
        raw = command.get("value")
        LOGGER.info("Ecobee lab command %s=%s", driver, raw)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Ecobee lab payload %s=%s", driver, raw)
            return
        setattr(self, attr_name, value)
        self.setDriver(driver, value, force=True)

    def cmd_set_pf(self, command):
        LOGGER.info("Ecobee lab setpoint/fan command=%s", command)
        self.refresh(command)

    def cmd_set_mode(self, command):
        self._set_int("climd", "CLIMD", command)

    def cmd_brt(self, command):
        self._adjust_active_setpoint(command, 1)

    def cmd_dim(self, command):
        self._adjust_active_setpoint(command, -1)

    def _adjust_active_setpoint(self, command, direction):
        raw = command.get("value")
        try:
            delta = int(raw) if raw not in (None, "") else 1
        except (TypeError, ValueError):
            delta = 1
        delta *= direction
        current_mode = int(self.getDriver("CLIMD"))
        if current_mode == 1:
            new_value = int(self.getDriver("CLISPH")) + delta
            self.setDriver("CLISPH", new_value, force=True)
        else:
            new_value = int(self.getDriver("CLISPC")) + delta
            self.setDriver("CLISPC", new_value, force=True)
        LOGGER.info("Ecobee lab %s adjusted setpoint by %s -> %s", command.get("cmd"), delta, new_value)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmd_set_pf,
        "CLISPC": cmd_set_pf,
        "CLIFS": cmd_set_pf,
        "CLIMD": cmd_set_mode,
        "BRT": cmd_brt,
        "DIM": cmd_dim,
    }
