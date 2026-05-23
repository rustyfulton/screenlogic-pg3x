import udi_interface

LOGGER = udi_interface.LOGGER


class EcobeeLabThermostatNode(udi_interface.Node):
    id = "EcobeeF"
    hint = "0x010c0100"
    drivers = [
        {"driver": "ST", "value": 74, "uom": 17},
        {"driver": "CLISPH", "value": 65, "uom": 17},
        {"driver": "CLISPC", "value": 74, "uom": 17},
        {"driver": "CLIMD", "value": 2, "uom": 67},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIHUM", "value": 50, "uom": 22},
        {"driver": "CLIHCS", "value": 2, "uom": 25},
        {"driver": "CLIFRS", "value": 1, "uom": 80},
        {"driver": "GV1", "value": 45, "uom": 22},
        {"driver": "CLISMD", "value": 0, "uom": 25},
        {"driver": "GV4", "value": 0, "uom": 25},
        {"driver": "GV5", "value": 50, "uom": 22},
        {"driver": "GV6", "value": 0, "uom": 25},
        {"driver": "GV7", "value": 0, "uom": 25},
        {"driver": "GV8", "value": 1, "uom": 2},
        {"driver": "GV9", "value": 0, "uom": 25},
        {"driver": "GV17", "value": 0, "uom": 25},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.clismd = 0
        self.gv1 = 45
        self.gv4 = 0
        self.gv5 = 50
        self.gv6 = 0
        self.gv7 = 0
        self.gv8 = 1
        self.gv9 = 0
        self.gv17 = 0

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
        self.setDriver("CLIMD", 2, force=True)
        self.setDriver("CLIFS", 0, force=True)
        self.setDriver("CLIHUM", 50, force=True)
        self.setDriver("CLIHCS", hcs, force=True)
        self.setDriver("CLIFRS", fan_state, force=True)
        self.setDriver("GV1", self.gv1, force=True)
        self.setDriver("CLISMD", self.clismd, force=True)
        self.setDriver("GV4", self.gv4, force=True)
        self.setDriver("GV5", self.gv5, force=True)
        self.setDriver("GV6", self.gv6, force=True)
        self.setDriver("GV7", self.gv7, force=True)
        self.setDriver("GV8", self.gv8, force=True)
        self.setDriver("GV9", self.gv9, force=True)
        self.setDriver("GV17", self.gv17, force=True)

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
        self._set_int("clismd", "CLIMD", command)

    def cmd_set_schedule_mode(self, command):
        self._set_int("clismd", "CLISMD", command)

    def cmd_set_gv1(self, command):
        self._set_int("gv1", "GV1", command)

    def cmd_set_gv4(self, command):
        self._set_int("gv4", "GV4", command)

    def cmd_set_gv5(self, command):
        self._set_int("gv5", "GV5", command)

    def cmd_set_gv6(self, command):
        self._set_int("gv6", "GV6", command)

    def cmd_set_gv7(self, command):
        self._set_int("gv7", "GV7", command)

    def cmd_set_gv9(self, command):
        self._set_int("gv9", "GV9", command)

    def cmd_set_gv17(self, command):
        self._set_int("gv17", "GV17", command)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmd_set_pf,
        "CLISPC": cmd_set_pf,
        "CLIFS": cmd_set_pf,
        "CLIMD": cmd_set_mode,
        "CLISMD": cmd_set_schedule_mode,
        "GV1": cmd_set_gv1,
        "GV4": cmd_set_gv4,
        "GV5": cmd_set_gv5,
        "GV6": cmd_set_gv6,
        "GV7": cmd_set_gv7,
        "GV9": cmd_set_gv9,
        "GV17": cmd_set_gv17,
    }
