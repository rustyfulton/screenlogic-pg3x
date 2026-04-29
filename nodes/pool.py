import udi_interface

LOGGER = udi_interface.LOGGER


class PoolNode(udi_interface.Node):
    id = "pool"
    drivers = [
        {"driver": "ST", "value": 1, "uom": 2},
        {"driver": "GV0", "value": 82, "uom": 17},
        {"driver": "GV1", "value": 99, "uom": 17},
        {"driver": "GV2", "value": 0, "uom": 25},
        {"driver": "GV3", "value": 0, "uom": 25},
        {"driver": "GV4", "value": 84, "uom": 17},
    ]

    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, primary, address, name)
        self.client = client

    def refresh(self, command=None):
        LOGGER.info("Refreshing ScreenLogic pool state")
        self.update_from_state(self.client.get_state())

    def cmd_pump_on(self, command):
        LOGGER.info("ScreenLogic pool command: pump on")
        self.update_from_state(self.client.set_pump(True))

    def cmd_pump_off(self, command):
        LOGGER.info("ScreenLogic pool command: pump off")
        self.update_from_state(self.client.set_pump(False))

    def cmd_heater_on(self, command):
        LOGGER.info("ScreenLogic pool command: heater on")
        self.update_from_state(self.client.set_heater(True))

    def cmd_heater_off(self, command):
        LOGGER.info("ScreenLogic pool command: heater off")
        self.update_from_state(self.client.set_heater(False))

    def cmd_set_pool_setpoint(self, command):
        raw = command.get("value")
        LOGGER.info("ScreenLogic pool command: set pool setpoint to %s", raw)
        self.update_from_state(self.client.set_pool_setpoint(raw))

    def update_from_state(self, state):
        self.setDriver("ST", 1 if state.connected else 0, force=True)
        self.setDriver("GV0", state.pool_temp_f, force=True)
        self.setDriver("GV1", state.spa_temp_f, force=True)
        self.setDriver("GV2", 1 if state.pump_on else 0, force=True)
        self.setDriver("GV3", 1 if state.heater_on else 0, force=True)
        self.setDriver("GV4", state.pool_setpoint_f, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "PUMP_ON": cmd_pump_on,
        "PUMP_OFF": cmd_pump_off,
        "HEATER_ON": cmd_heater_on,
        "HEATER_OFF": cmd_heater_off,
        "SET_POOL_SP": cmd_set_pool_setpoint,
    }
