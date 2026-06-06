import time

import udi_interface

LOGGER = udi_interface.LOGGER


DRIVERS_MAP = {
    "ThermostatLabHwhF": [
        {"driver": "ST", "value": 70, "uom": 17},
        {"driver": "CLISPH", "value": 65, "uom": 17},
        {"driver": "CLISPC", "value": 75, "uom": 17},
        {"driver": "CLIMD", "value": 2, "uom": 67},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIHUM", "value": 50, "uom": 22},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFRS", "value": 0, "uom": 80},
        {"driver": "GV1", "value": 0, "uom": 25},
        {"driver": "GV2", "value": 1, "uom": 25},
        {"driver": "GV3", "value": 3, "uom": 25},
        {"driver": "GV4", "value": 0, "uom": 25},
        {"driver": "GV5", "value": 0, "uom": 2},
        {"driver": "GV6", "value": 1, "uom": 2},
        {"driver": "GV7", "value": 0, "uom": 110},
    ],
    "ThermostatF": [
        {"driver": "ST", "value": 70, "uom": 17},
        {"driver": "CLISPH", "value": 65, "uom": 17},
        {"driver": "CLISPC", "value": 75, "uom": 17},
        {"driver": "CLIMD", "value": 2, "uom": 67},
        {"driver": "CLIFS", "value": 0, "uom": 68},
        {"driver": "CLIHUM", "value": 50, "uom": 22},
        {"driver": "CLIHCS", "value": 0, "uom": 66},
        {"driver": "CLIFRS", "value": 0, "uom": 80},
        {"driver": "CLIFSO", "value": 0, "uom": 81},
        {"driver": "BATLVL", "value": 100, "uom": 51},
    ],
}

MODE_MAP = {
    "Off": 0,
    "Heat": 1,
    "Cool": 2,
    "Auto": 3,
}

FAN_MAP = {
    "Auto": 0,
    "On": 1,
    "Circulate": 6,
}

RUNNING_STATE_MAP = {
    "EquipmentOff": 0,
    "Heat": 1,
    "Cool": 2,
}


class HoneywellLabThermostatNode(udi_interface.Node):
    id = "ThermostatLabHwhF"
    hint = "0x010c0100"
    drivers = DRIVERS_MAP["ThermostatLabHwhF"]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.heat_setpoint = 65
        self.cool_setpoint = 75
        self.mode = MODE_MAP["Cool"]
        self.fan_mode = FAN_MAP["Auto"]
        self.hold_status = 0

    def refresh(self, command=None):
        LOGGER.info("Refreshing Honeywell lab thermostat command=%s", command)
        state = self.client.get_state()
        temp = int(round(float(state.pool_temp_f)))
        humidity = 50
        running_state = 0
        if state.heater_on:
            running_state = RUNNING_STATE_MAP["Heat"]
        elif state.pump_on and self.mode == MODE_MAP["Cool"]:
            running_state = RUNNING_STATE_MAP["Cool"]
        fan_state = 1 if state.pump_on else 0

        updates = {
            "ST": temp,
            "CLISPH": self.heat_setpoint,
            "CLISPC": self.cool_setpoint,
            "CLIMD": self.mode,
            "CLIFS": self.fan_mode,
            "CLIHUM": humidity,
            "CLIHCS": running_state,
            "CLIFRS": fan_state,
            "GV1": 0,  # Priority Type: Not Supported
            "GV2": 1,  # Schedule Status: Resume
            "GV3": 3,  # Current Schedule Mode: Home
            "GV4": self.hold_status,
            "GV5": 0,  # Vacation Hold: False
            "GV6": 1,  # Connected: True
            "GV7": int(time.time()),
        }

        for key, value in updates.items():
            self.setDriver(key, value, force=True)

    def cmdSetPF(self, command):
        driver = command.get("cmd")
        raw = command.get("value")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Honeywell lab payload %s=%s", driver, raw)
            return

        if driver == "CLISPH":
            self.heat_setpoint = value
        elif driver == "CLISPC":
            self.cool_setpoint = value
        elif driver == "CLIMD":
            self.mode = value

        self.refresh(command)

    def cmdSetHoldStatus(self, command):
        raw = command.get("value")
        try:
            self.hold_status = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Honeywell lab hold payload %s", raw)
            return
        self.setDriver("GV4", self.hold_status, force=True)

    def cmdSetFS(self, command):
        raw = command.get("value")
        try:
            self.fan_mode = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Honeywell lab fan payload %s", raw)
            return
        self.setDriver("CLIFS", self.fan_mode, force=True)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmdSetPF,
        "CLISPC": cmdSetPF,
        "CLIMD": cmdSetPF,
        "GV4": cmdSetHoldStatus,
        "CLIFS": cmdSetFS,
    }


class HoneywellPentairThermostatNode(HoneywellLabThermostatNode):
    id = "ThermostatF"
    hint = "0x010c0100"
    drivers = DRIVERS_MAP["ThermostatF"]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name, client)
        self.fan_override = 0
        self.battery_level = 100

    def refresh(self, command=None):
        LOGGER.info("Refreshing Honeywell Pentair thermostat command=%s", command)
        state = self.client.get_state()
        temp = int(round(float(state.pool_temp_f)))
        self.heat_setpoint = int(round(float(state.pool_setpoint_f)))
        humidity = 50
        running_state = 0
        if state.heater_on:
            running_state = RUNNING_STATE_MAP["Heat"]
        elif state.pump_on and self.mode == MODE_MAP["Cool"]:
            running_state = RUNNING_STATE_MAP["Cool"]
        fan_state = 1 if state.pump_on else 0

        updates = {
            "ST": temp,
            "CLISPH": self.heat_setpoint,
            "CLISPC": self.cool_setpoint,
            "CLIMD": self.mode,
            "CLIFS": self.fan_mode,
            "CLIHUM": humidity,
            "CLIHCS": running_state,
            "CLIFRS": fan_state,
            "CLIFSO": self.fan_override,
            "BATLVL": self.battery_level,
        }

        for key, value in updates.items():
            self.setDriver(key, value, force=True)

    def cmdSetPF(self, command):
        driver = command.get("cmd")
        raw = command.get("value")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning(
                "Ignoring invalid Honeywell Pentair payload %s=%s",
                driver,
                raw,
            )
            return

        if driver == "CLISPH":
            LOGGER.info(
                "Honeywell Pentair thermostat command: set real pool heat setpoint to %s",
                value,
            )
            state = self.client.set_pool_setpoint(value)
            self.heat_setpoint = int(round(float(state.pool_setpoint_f)))
            get_node = getattr(self.poly, "getNode", None)
            if callable(get_node):
                pool_node = get_node("pool")
                if pool_node is not None and hasattr(pool_node, "update_from_state"):
                    LOGGER.info(
                        "Honeywell Pentair thermostat command: syncing sibling Pool node after setpoint write"
                    )
                    pool_node.update_from_state(state)
            self.refresh(command)
            return

        if driver == "CLISPC":
            LOGGER.info(
                "Honeywell Pentair thermostat command: ignoring cool setpoint write %s for pool body",
                value,
            )
            self.cool_setpoint = value
        elif driver == "CLIMD":
            self.mode = value

        self.refresh(command)

    def cmdSetFanOverride(self, command):
        raw = command.get("value")
        try:
            self.fan_override = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning(
                "Ignoring invalid Honeywell Pentair fan override payload %s", raw
            )
            return
        self.setDriver("CLIFSO", self.fan_override, force=True)

    commands = {
        "QUERY": refresh,
        "CLISPH": cmdSetPF,
        "CLISPC": cmdSetPF,
        "CLIMD": cmdSetPF,
        "CLIFS": HoneywellLabThermostatNode.cmdSetFS,
        "CLIFSO": cmdSetFanOverride,
    }
