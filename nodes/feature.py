import udi_interface

LOGGER = udi_interface.LOGGER


class FeatureNode(udi_interface.Node):
    id = "feature"
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
    ]

    def __init__(self, polyglot, primary, address, name, client, circuit_id):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.circuit_id = int(circuit_id)

    def refresh(self, command=None):
        LOGGER.info("Refreshing ScreenLogic feature circuit id=%s", self.circuit_id)
        for feature in self.client.get_features():
            if feature.circuit_id == self.circuit_id:
                self.update_from_feature(feature)
                return
        LOGGER.warning(
            "ScreenLogic feature circuit id=%s was not present in the latest data",
            self.circuit_id,
        )

    def cmd_feature_on(self, command):
        LOGGER.info("ScreenLogic feature command: circuit id=%s on", self.circuit_id)
        self.client.set_feature(self.circuit_id, True)
        self.refresh()

    def cmd_feature_off(self, command):
        LOGGER.info("ScreenLogic feature command: circuit id=%s off", self.circuit_id)
        self.client.set_feature(self.circuit_id, False)
        self.refresh()

    def update_from_feature(self, feature):
        self.setDriver("ST", 1 if feature.enabled else 0, force=True)

    commands = {
        "QUERY": refresh,
        "REFRESH": refresh,
        "FEATURE_ON": cmd_feature_on,
        "FEATURE_OFF": cmd_feature_off,
    }
