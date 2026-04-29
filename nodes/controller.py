import udi_interface

from nodes.feature import FeatureNode
from nodes.pool import PoolNode
from nodes.dummy_thermostat import DummyThermostatNode
from nodes.solar_heater import SolarHeaterNode
from nodes.solar_thermostat import SolarThermostatNode

LOGGER = udi_interface.LOGGER


class ControllerNode(udi_interface.Node):
    id = "poolctl"
    drivers = [{"driver": "ST", "value": 1, "uom": 2}]

    def __init__(
        self,
        polyglot,
        primary,
        address,
        name,
        client,
        include_dummy_thermostat=True,
        feature_nodes_enabled=True,
        feature_include=(),
        feature_exclude=(),
    ):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.include_dummy_thermostat = include_dummy_thermostat
        self.feature_nodes_enabled = feature_nodes_enabled
        self.feature_include = tuple(feature_include or ())
        self.feature_exclude = tuple(feature_exclude or ())
        self.pool_node = None
        self.solar_node = None
        self.solar_thermostat_node = None
        self.dummy_thermostat_node = None
        self.feature_nodes = {}

    def start(self):
        LOGGER.info("Starting controller node")
        self.client.connect()
        self.setDriver("ST", 1, force=True)
        self.ensure_children()
        self.refresh_children()

    def ensure_children(self):
        if self.pool_node is None:
            self.pool_node = PoolNode(
                self.poly,
                self.address,
                "pool",
                "Pool",
                self.client,
            )
            self.poly.addNode(self.pool_node)
        if self.solar_node is None:
            self.solar_node = SolarHeaterNode(
                self.poly,
                self.address,
                "solar",
                "Solar Heater",
                self.client,
            )
            self.poly.addNode(self.solar_node)
        if self.solar_thermostat_node is None:
            self.solar_thermostat_node = SolarThermostatNode(
                self.poly,
                self.address,
                "solartstat",
                "Solar Thermostat",
                self.client,
            )
            self.poly.addNode(self.solar_thermostat_node)
        if self.include_dummy_thermostat and self.dummy_thermostat_node is None:
            self.dummy_thermostat_node = DummyThermostatNode(
                self.poly,
                self.address,
                "dummytstat",
                "Dummy Thermostat",
            )
            self.poly.addNode(self.dummy_thermostat_node)

    def set_client(
        self,
        client,
        include_dummy_thermostat=None,
        feature_nodes_enabled=None,
        feature_include=None,
        feature_exclude=None,
    ):
        self.client = client
        if include_dummy_thermostat is not None:
            self.include_dummy_thermostat = include_dummy_thermostat
        if feature_nodes_enabled is not None:
            self.feature_nodes_enabled = feature_nodes_enabled
        if feature_include is not None:
            self.feature_include = tuple(feature_include or ())
        if feature_exclude is not None:
            self.feature_exclude = tuple(feature_exclude or ())

        if self.pool_node is not None:
            self.pool_node.client = client
        if self.solar_node is not None:
            self.solar_node.client = client
        if self.solar_thermostat_node is not None:
            self.solar_thermostat_node.client = client
        for node in self.feature_nodes.values():
            node.client = client

    def shortPoll(self):
        self.refresh_children()

    def longPoll(self):
        self.setDriver("ST", 1, force=True)

    def refresh_children(self):
        state = self.client.get_state()
        if self.pool_node is not None:
            self.pool_node.update_from_state(state)
        if self.solar_node is not None:
            self.solar_node.update_from_state(state)
        if self.solar_thermostat_node is not None:
            self.solar_thermostat_node.update_from_state(state)
        if self.dummy_thermostat_node is not None:
            self.dummy_thermostat_node.refresh()
        self.refresh_features()

    def refresh_features(self):
        if not self.feature_nodes_enabled:
            return

        try:
            features = self.client.get_features()
        except Exception:
            LOGGER.exception("Unable to refresh ScreenLogic feature circuits")
            return

        for feature in features:
            if not self._feature_allowed(feature):
                continue
            address = self._feature_address(feature.circuit_id)
            if address not in self.feature_nodes:
                node_name = f"{feature.name} ({feature.circuit_id})"
                LOGGER.info(
                    "Adding ScreenLogic feature node address=%s id=%s name=%s "
                    "function=%s interface=%s light=%s",
                    address,
                    feature.circuit_id,
                    feature.name,
                    feature.function,
                    feature.interface,
                    feature.is_light,
                )
                node = FeatureNode(
                    self.poly,
                    self.address,
                    address,
                    node_name,
                    self.client,
                    feature.circuit_id,
                )
                self.feature_nodes[address] = node
                self.poly.addNode(node)
            self.feature_nodes[address].update_from_feature(feature)

    def _feature_allowed(self, feature):
        tokens = {
            str(feature.circuit_id).lower(),
            str(feature.name).strip().lower(),
        }
        if self.feature_include and not any(token in self.feature_include for token in tokens):
            return False
        if self.feature_exclude and any(token in self.feature_exclude for token in tokens):
            return False
        return True

    def _feature_address(self, circuit_id):
        return f"f{int(circuit_id)}"

    def discover(self, command=None):
        LOGGER.info("ScreenLogic discover invoked")
        self.ensure_children()
        self.refresh_features()

    def query(self, command=None):
        self.discover(command)
        self.refresh_children()

    commands = {
        "DISCOVER": discover,
        "QUERY": query,
    }
