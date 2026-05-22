import udi_interface

LOGGER = udi_interface.LOGGER


class DummyThermostatNode(udi_interface.Node):
    id = "dummytstat"
    drivers = [
        {"driver": "ST", "value": 72, "uom": 17},
        {"driver": "CLISPH", "value": 74, "uom": 17},
        {"driver": "CLISPC", "value": 78, "uom": 17},
        {"driver": "CLIMD", "value": 3, "uom": 67},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFS", "value": 0, "uom": 68},
    ]

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        self.current_temp = 72
        self.heat_setpoint = 74
        self.cool_setpoint = 78
        self.mode = 3
        self.hvac_state = 0
        self.fan_mode = 0
        self._tick = 0
        LOGGER.info(
            "Thermostat lab node created address=%s primary=%s name=%s",
            self.address,
            primary,
            name,
        )

    def _snapshot(self):
        return (
            f"temp={self.current_temp} heat_sp={self.heat_setpoint} "
            f"cool_sp={self.cool_setpoint} mode={self.mode} "
            f"hvac_state={self.hvac_state} fan_mode={self.fan_mode} tick={self._tick}"
        )

    def refresh(self, command=None):
        LOGGER.info(
            "Thermostat lab refresh address=%s command=%s before=%s",
            self.address,
            command,
            self._snapshot(),
        )
        self._tick += 1
        self._simulate()
        self._apply()
        LOGGER.info(
            "Thermostat lab refresh complete address=%s after=%s",
            self.address,
            self._snapshot(),
        )

    def cmd_set_heat_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Thermostat lab command CLISPH address=%s payload=%s before=%s",
            self.address,
            command,
            self._snapshot(),
        )
        self.heat_setpoint = max(40, min(104, int(raw)))
        self._simulate()
        self._apply()
        LOGGER.info(
            "Thermostat lab command CLISPH complete address=%s after=%s",
            self.address,
            self._snapshot(),
        )

    def cmd_set_cool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Thermostat lab command CLISPC address=%s payload=%s before=%s",
            self.address,
            command,
            self._snapshot(),
        )
        self.cool_setpoint = max(40, min(104, int(raw)))
        self._simulate()
        self._apply()
        LOGGER.info(
            "Thermostat lab command CLISPC complete address=%s after=%s",
            self.address,
            self._snapshot(),
        )

    def cmd_set_mode(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Thermostat lab command CLIMD address=%s payload=%s before=%s",
            self.address,
            command,
            self._snapshot(),
        )
        self.mode = int(raw)
        self._simulate()
        self._apply()
        LOGGER.info(
            "Thermostat lab command CLIMD complete address=%s after=%s",
            self.address,
            self._snapshot(),
        )

    def cmd_set_fan_mode(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Thermostat lab command CLIFS address=%s payload=%s before=%s",
            self.address,
            command,
            self._snapshot(),
        )
        self.fan_mode = int(raw)
        self._apply()
        LOGGER.info(
            "Thermostat lab command CLIFS complete address=%s after=%s",
            self.address,
            self._snapshot(),
        )

    def _simulate(self):
        if self.mode == 1:  # heat
            if self.current_temp < self.heat_setpoint:
                self.hvac_state = 1
                if self._tick % 2 == 0:
                    self.current_temp += 1
            else:
                self.hvac_state = 0
        elif self.mode == 2:  # cool
            if self.current_temp > self.cool_setpoint:
                self.hvac_state = 2
                if self._tick % 2 == 0:
                    self.current_temp -= 1
            else:
                self.hvac_state = 0
        elif self.mode == 3:  # auto
            if self.current_temp < self.heat_setpoint:
                self.hvac_state = 1
                if self._tick % 2 == 0:
                    self.current_temp += 1
            elif self.current_temp > self.cool_setpoint:
                self.hvac_state = 2
                if self._tick % 2 == 0:
                    self.current_temp -= 1
            else:
                self.hvac_state = 0
        else:  # off and anything else
            self.hvac_state = 0

    def _apply(self):
        self.setDriver("ST", self.current_temp, force=True)
        self.setDriver("CLISPH", self.heat_setpoint, force=True)
        self.setDriver("CLISPC", self.cool_setpoint, force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", self.hvac_state, force=True)
        self.setDriver("CLIFS", self.fan_mode, force=True)
        LOGGER.info(
            "Thermostat lab driver publish address=%s snapshot=%s",
            self.address,
            self._snapshot(),
        )

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "CLISPH": cmd_set_heat_setpoint,
        "CLISPC": cmd_set_cool_setpoint,
        "CLIMD": cmd_set_mode,
        "CLIFS": cmd_set_fan_mode,
    }
