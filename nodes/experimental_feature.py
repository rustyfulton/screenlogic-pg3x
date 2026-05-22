import udi_interface

LOGGER = udi_interface.LOGGER


class ExperimentalFeatureNodeBase(udi_interface.Node):
    GENERIC_SWITCH_HINT = "0x01040200"
    NON_DIMMING_LIGHT_HINT = "0x01021000"
    DIMMER_LIGHT_HINT = "0x01020900"
    status_uom = 2
    on_value = 1
    off_value = 0
    hint = GENERIC_SWITCH_HINT

    def __init__(self, polyglot, primary, address, name, client, circuit_id):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.circuit_id = int(circuit_id)

    def refresh(self, command=None):
        LOGGER.info(
            "Refreshing experimental ScreenLogic feature circuit id=%s node=%s",
            self.circuit_id,
            self.address,
        )
        for feature in self.client.get_features():
            if feature.circuit_id == self.circuit_id:
                self.update_from_feature(feature)
                return
        LOGGER.warning(
            "Experimental ScreenLogic feature circuit id=%s was not present in the latest data",
            self.circuit_id,
        )

    def cmd_on(self, command):
        LOGGER.info(
            "Experimental ScreenLogic feature command: circuit id=%s on via %s",
            self.circuit_id,
            self.address,
        )
        self.client.set_feature(self.circuit_id, True)
        self.refresh()

    def cmd_off(self, command):
        LOGGER.info(
            "Experimental ScreenLogic feature command: circuit id=%s off via %s",
            self.circuit_id,
            self.address,
        )
        self.client.set_feature(self.circuit_id, False)
        self.refresh()

    def update_from_feature(self, feature):
        self.setDriver("ST", self.on_value if feature.enabled else self.off_value, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "DON": cmd_on,
        "DOF": cmd_off,
    }


class ExperimentalFeatureBoolSwitchNode(ExperimentalFeatureNodeBase):
    id = "fexp_bool_switch"
    drivers = [{"driver": "ST", "value": 0, "uom": 2}]
    hint = ExperimentalFeatureNodeBase.GENERIC_SWITCH_HINT
    status_uom = 2
    on_value = 1
    off_value = 0


class ExperimentalFeatureLevelSwitchNode(ExperimentalFeatureNodeBase):
    id = "fexp_level_switch"
    drivers = [{"driver": "ST", "value": 0, "uom": 51}]
    hint = ExperimentalFeatureNodeBase.GENERIC_SWITCH_HINT
    status_uom = 51
    on_value = 100
    off_value = 0


class ExperimentalFeatureBoolLightNode(ExperimentalFeatureNodeBase):
    id = "fexp_bool_light"
    drivers = [{"driver": "ST", "value": 0, "uom": 2}]
    hint = ExperimentalFeatureNodeBase.NON_DIMMING_LIGHT_HINT
    status_uom = 2
    on_value = 1
    off_value = 0


class ExperimentalFeatureLevelLightNode(ExperimentalFeatureNodeBase):
    id = "fexp_level_light"
    drivers = [{"driver": "ST", "value": 0, "uom": 51}]
    hint = ExperimentalFeatureNodeBase.DIMMER_LIGHT_HINT
    status_uom = 51
    on_value = 100
    off_value = 0
