import time

import udi_interface

LOGGER = udi_interface.LOGGER


DRIVERS_MAP = {
    "HwhF": [
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
    ]
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
    id = "HwhF"
    drivers = DRIVERS_MAP["HwhF"]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.heat_setpoint = 65
        self.cool_setpoint = 75
        self.mode = MODE_MAP["Cool"]
        self.fan_mode = FAN_MAP["Auto"]
        self.hold_status = 0
        subscribe = getattr(polyglot, "subscribe", None)
        start_evt = getattr(polyglot, "START", None)
        if callable(subscribe) and start_evt is not None:
            subscribe(start_evt, self.start, address)
        LOGGER.info(
            "Honeywell lab thermostat created address=%s primary=%s id=%s",
            self.address,
            self.primary,
            self.id,
        )

    def start(self):
        LOGGER.info(
            "Honeywell lab thermostat START event address=%s -- publishing initial state",
            self.address,
        )
        self.query({"reason": "start_event"})

    def query(self, command=None):
        LOGGER.info(
            "Honeywell lab thermostat QUERY address=%s command=%s -- likely path when Alexa/Portal asks for fresh GUI state",
            self.address,
            command,
        )
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

        LOGGER.info(
            "Honeywell lab thermostat snapshot address=%s temp=%s heat_sp=%s cool_sp=%s mode=%s fan_mode=%s running=%s humidity=%s hold=%s connected=%s",
            self.address,
            updates["ST"],
            updates["CLISPH"],
            updates["CLISPC"],
            updates["CLIMD"],
            updates["CLIFS"],
            updates["CLIHCS"],
            updates["CLIHUM"],
            updates["GV4"],
            updates["GV6"],
        )
        for key, value in updates.items():
            LOGGER.info(
                "Honeywell lab thermostat publish address=%s driver=%s value=%s",
                self.address,
                key,
                value,
            )
            self.setDriver(key, value, force=True)
        LOGGER.info(
            "Honeywell lab thermostat reportDrivers address=%s -- flushing complete state bundle",
            self.address,
        )
        self.reportDrivers()

    def refresh(self, command=None):
        LOGGER.info(
            "Honeywell lab thermostat REFRESH address=%s command=%s",
            self.address,
            command,
        )
        self.query(command)

    def cmdSetPF(self, command):
        driver = command.get("cmd")
        raw = command.get("value")
        LOGGER.info(
            "Honeywell lab thermostat command address=%s driver=%s raw=%s",
            self.address,
            driver,
            raw,
        )
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

        LOGGER.info(
            "Honeywell lab thermostat updated local state address=%s driver=%s value=%s",
            self.address,
            driver,
            value,
        )
        self.query(command)

    def cmdSetHoldStatus(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Honeywell lab thermostat hold command address=%s raw=%s",
            self.address,
            raw,
        )
        try:
            self.hold_status = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Honeywell lab hold payload %s", raw)
            return
        self.setDriver("GV4", self.hold_status, force=True)
        LOGGER.info(
            "Honeywell lab thermostat hold state updated address=%s hold=%s",
            self.address,
            self.hold_status,
        )
        self.reportDrivers()

    def cmdSetFS(self, command):
        raw = command.get("value")
        LOGGER.info(
            "Honeywell lab thermostat fan command address=%s raw=%s",
            self.address,
            raw,
        )
        try:
            self.fan_mode = int(raw)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid Honeywell lab fan payload %s", raw)
            return
        self.setDriver("CLIFS", self.fan_mode, force=True)
        LOGGER.info(
            "Honeywell lab thermostat fan state updated address=%s fan_mode=%s",
            self.address,
            self.fan_mode,
        )
        self.reportDrivers()

    commands = {
        "QUERY": query,
        "CLISPH": cmdSetPF,
        "CLISPC": cmdSetPF,
        "CLIMD": cmdSetPF,
        "GV4": cmdSetHoldStatus,
        "CLIFS": cmdSetFS,
    }
