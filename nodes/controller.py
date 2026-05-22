import udi_interface

from nodes.experimental_pool_temp import (
    ExperimentalPoolTempDocCloneHintThermostatNode,
    ExperimentalPoolTempDocClonePracticalThermostatNode,
    ExperimentalPoolTempDocCloneThermostatNode,
    ExperimentalPoolTempFullCloneHintThermostatNode,
    ExperimentalPoolTempFullCloneThermostatNode,
    ExperimentalPoolTempPowerAlarmNode,
    ExperimentalPoolTempSensorNode,
    ExperimentalPoolTempStrictUdiThermostatNode,
    ExperimentalPoolTempTempSetpointNode,
    ExperimentalPoolTempTemperatureHintSensorNode,
    ExperimentalPoolTempTemperatureHintSetpointNode,
    ExperimentalPoolTempThermostatHintRONode,
    ExperimentalPoolTempThermostatHintRWNode,
    ExperimentalPoolTempThermostatReadOnlyNode,
    ExperimentalPoolTempThermostatReadWriteNode,
)
from nodes.feature import FeatureNode
from nodes.pool import PoolNode
from nodes.dummy_thermostat import DummyThermostatNode
from nodes.solar_heater import SolarHeaterNode
from nodes.solar_thermostat import SolarThermostatNode

LOGGER = udi_interface.LOGGER
EXPERIMENTAL_FEATURE_ADDRESSES = (
    "xfeat510a",
    "xfeat510b",
    "xfeat510c",
    "xfeat510d",
)


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
        include_pool_node=True,
        include_dummy_thermostat=True,
        startup_refresh=True,
        poll_enabled=True,
        include_solar_node=True,
        include_solar_thermostat_node=True,
        feature_nodes_enabled=True,
        feature_include=(),
        feature_exclude=(),
        enable_fountain_experiments=False,
        enable_pool_temp_experiments=False,
    ):
        super().__init__(polyglot, primary, address, name)
        self.client = client
        self.include_pool_node = include_pool_node
        self.include_dummy_thermostat = include_dummy_thermostat
        self.startup_refresh = startup_refresh
        self.poll_enabled = poll_enabled
        self.include_solar_node = include_solar_node
        self.include_solar_thermostat_node = include_solar_thermostat_node
        self.feature_nodes_enabled = feature_nodes_enabled
        self.feature_include = tuple(feature_include or ())
        self.feature_exclude = tuple(feature_exclude or ())
        self.enable_fountain_experiments = enable_fountain_experiments
        self.enable_pool_temp_experiments = enable_pool_temp_experiments
        self.pool_node = None
        self.solar_node = None
        self.solar_thermostat_node = None
        self.dummy_thermostat_node = None
        self.feature_nodes = {}
        self.experimental_pool_temp_nodes = {}
        self.experimental_pool_temp_main_nodes = {}
        self.experimental_pool_temp_alarm_nodes = {}

    def start(self):
        LOGGER.info("Starting controller node")
        self.setDriver("ST", 1, force=True)
        self.ensure_children()
        if self.startup_refresh:
            self.client.connect()
            self.refresh_children(refresh_topology=True)

    def ensure_children(self):
        if self.include_pool_node and self.pool_node is None:
            self.pool_node = PoolNode(
                self.poly,
                self.address,
                "pool",
                "Pool",
                self.client,
            )
            self.poly.addNode(self.pool_node)
        if self.include_solar_node and self.solar_node is None:
            self.solar_node = SolarHeaterNode(
                self.poly,
                self.address,
                "solar",
                "Solar Heater",
                self.client,
            )
            self.poly.addNode(self.solar_node)
        if self.include_solar_thermostat_node and self.solar_thermostat_node is None:
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
        include_pool_node=None,
        include_dummy_thermostat=None,
        startup_refresh=None,
        poll_enabled=None,
        include_solar_node=None,
        include_solar_thermostat_node=None,
        feature_nodes_enabled=None,
        feature_include=None,
        feature_exclude=None,
        enable_fountain_experiments=None,
        enable_pool_temp_experiments=None,
    ):
        self.client = client
        if include_pool_node is not None:
            self.include_pool_node = include_pool_node
        if include_dummy_thermostat is not None:
            self.include_dummy_thermostat = include_dummy_thermostat
        if startup_refresh is not None:
            self.startup_refresh = startup_refresh
        if poll_enabled is not None:
            self.poll_enabled = poll_enabled
        if include_solar_node is not None:
            self.include_solar_node = include_solar_node
        if include_solar_thermostat_node is not None:
            self.include_solar_thermostat_node = include_solar_thermostat_node
        if feature_nodes_enabled is not None:
            self.feature_nodes_enabled = feature_nodes_enabled
        if feature_include is not None:
            self.feature_include = tuple(feature_include or ())
        if feature_exclude is not None:
            self.feature_exclude = tuple(feature_exclude or ())
        if enable_fountain_experiments is not None:
            self.enable_fountain_experiments = enable_fountain_experiments
        if enable_pool_temp_experiments is not None:
            self.enable_pool_temp_experiments = enable_pool_temp_experiments

        if self.pool_node is not None:
            self.pool_node.client = client
        if self.solar_node is not None:
            self.solar_node.client = client
        if self.solar_thermostat_node is not None:
            self.solar_thermostat_node.client = client
        for node in self.feature_nodes.values():
            node.client = client
        for node in self.experimental_pool_temp_nodes.values():
            node.client = client
        for node in self.experimental_pool_temp_main_nodes.values():
            node.client = client
        for node in self.experimental_pool_temp_alarm_nodes.values():
            node.client = client
        self.ensure_children()

    def shortPoll(self):
        if not self.poll_enabled:
            return
        LOGGER.info("ScreenLogic shortPoll: refreshing operational state only")
        self.refresh_children(refresh_topology=False)

    def longPoll(self):
        LOGGER.info("ScreenLogic longPoll: refreshing topology and feature inventory")
        self.setDriver("ST", 1, force=True)
        self.refresh_topology()

    def refresh_children(self, *, refresh_topology=False):
        state = self.client.get_state()
        if self.pool_node is not None:
            self.pool_node.update_from_state(state)
        self._refresh_pool_temp_experiments(state, discover=refresh_topology)
        if self.solar_node is not None:
            self.solar_node.update_from_state(state)
        if self.solar_thermostat_node is not None:
            self.solar_thermostat_node.update_from_state(state)
        if self.dummy_thermostat_node is not None:
            self.dummy_thermostat_node.refresh()
        self.refresh_features(discover=refresh_topology)

    def refresh_topology(self):
        self.ensure_children()
        self.refresh_features(discover=True)

    def refresh_features(self, *, discover=False):
        self._cleanup_experimental_feature_nodes()
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
                if not discover:
                    continue
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
            elif discover:
                self._sync_feature_node_name(self.feature_nodes[address], feature)
            self.feature_nodes[address].update_from_feature(feature)

    def _feature_allowed(self, feature):
        name = str(feature.name).strip()
        lowered = name.lower()
        tokens = {
            str(feature.circuit_id).lower(),
            lowered,
        }
        if self._is_placeholder_feature(feature):
            return False
        if feature.function == 2:
            return False
        if self.feature_include and not any(token in self.feature_include for token in tokens):
            return False
        if self.feature_exclude and any(token in self.feature_exclude for token in tokens):
            return False
        return True

    def _feature_address(self, circuit_id):
        return f"f{int(circuit_id)}"

    def _is_placeholder_feature(self, feature):
        name = str(feature.name).strip().lower()
        if "[not used]" in name:
            return True
        if feature.function == 0 and feature.interface == 2 and name.startswith("feature "):
            return True
        return False

    def _sync_feature_node_name(self, node, feature):
        desired_name = f"{feature.name} ({feature.circuit_id})"
        if getattr(node, "name", None) == desired_name:
            return
        LOGGER.info(
            "Updating ScreenLogic feature node name address=%s old=%s new=%s",
            node.address,
            getattr(node, "name", "<unknown>"),
            desired_name,
        )
        node.name = desired_name
        rename = getattr(node, "setName", None)
        if callable(rename):
            try:
                rename(desired_name)
            except Exception:
                LOGGER.exception(
                    "Unable to push updated ScreenLogic feature node name for %s",
                    node.address,
                )

    def _cleanup_experimental_feature_nodes(self):
        get_node = getattr(self.poly, "getNode", None)
        del_node = getattr(self.poly, "delNode", None)
        if not callable(get_node) or not callable(del_node):
            return

        for address in EXPERIMENTAL_FEATURE_ADDRESSES:
            node = get_node(address)
            if node is None:
                continue
            LOGGER.info(
                "Removing retired experimental ScreenLogic feature node address=%s",
                address,
            )
            try:
                del_node(address)
            except Exception:
                LOGGER.exception(
                    "Unable to remove retired experimental ScreenLogic feature node %s",
                    address,
                )

    def _refresh_pool_temp_experiments(self, state, *, discover=False):
        if not self.enable_pool_temp_experiments:
            return

        variants = (
            ("xptempa", "Pool Temp EXP A Thermostat RW", ExperimentalPoolTempThermostatReadWriteNode),
            ("xptempb", "Pool Temp EXP B Thermostat RO", ExperimentalPoolTempThermostatReadOnlyNode),
            ("xptempc", "Pool Temp EXP C Temp Sensor", ExperimentalPoolTempSensorNode),
            ("xptempd", "Pool Temp EXP D Temp+Setpoint", ExperimentalPoolTempTempSetpointNode),
            ("xptempe", "Pool Temp EXP E Tstat Hint RW", ExperimentalPoolTempThermostatHintRWNode),
            ("xptempf", "Pool Temp EXP F Tstat Hint RO", ExperimentalPoolTempThermostatHintRONode),
            ("xptempg", "Pool Temp EXP G Temp Hint Sensor", ExperimentalPoolTempTemperatureHintSensorNode),
            ("xptemph", "Pool Temp EXP H Temp Hint Setpoint", ExperimentalPoolTempTemperatureHintSetpointNode),
            ("xptempi", "Pool Temp EXP I Strict UDI Tstat", ExperimentalPoolTempStrictUdiThermostatNode),
            ("xptempj", "Pool Temp EXP J Doc Clone", ExperimentalPoolTempDocCloneThermostatNode),
            ("xptempk", "Pool Temp EXP K Doc Clone Hint", ExperimentalPoolTempDocCloneHintThermostatNode),
            ("xptempl", "Pool Temp EXP L Doc Clone Practical", ExperimentalPoolTempDocClonePracticalThermostatNode),
        )

        for address, name, node_cls in variants:
            node = self.experimental_pool_temp_nodes.get(address)
            if node is None:
                if not discover:
                    continue
                LOGGER.info(
                    "Adding experimental pool temperature node address=%s class=%s",
                    address,
                    node_cls.__name__,
                )
                node = node_cls(
                    self.poly,
                    self.address,
                    address,
                    name,
                    self.client,
                )
                self.experimental_pool_temp_nodes[address] = node
                self.poly.addNode(node)
            node.update_from_state(state)

        main_variants = (
            ("xptempm", "Pool Temp EXP M Main Doc Clone", ExperimentalPoolTempDocCloneThermostatNode),
            ("xptempn", "Pool Temp EXP N Main Doc Clone Hint", ExperimentalPoolTempDocCloneHintThermostatNode),
            ("xptempo", "Pool Temp EXP O Main Solar-Style Hint", ExperimentalPoolTempThermostatHintRWNode),
            ("xptempp", "Pool Temp EXP P Main Strict UDI", ExperimentalPoolTempStrictUdiThermostatNode),
            ("xptempq", "Pool Temp EXP Q Main Full Clone", ExperimentalPoolTempFullCloneThermostatNode),
            ("xptempr", "Pool Temp EXP R Main Full Clone Hint", ExperimentalPoolTempFullCloneHintThermostatNode),
        )

        for address, name, node_cls in main_variants:
            node = self.experimental_pool_temp_main_nodes.get(address)
            if node is None:
                if not discover:
                    continue
                LOGGER.info(
                    "Adding experimental main pool temperature node address=%s class=%s",
                    address,
                    node_cls.__name__,
                )
                node = node_cls(
                    self.poly,
                    address,
                    address,
                    name,
                    self.client,
                )
                self.experimental_pool_temp_main_nodes[address] = node
                self.poly.addNode(node)
            node.update_from_state(state)

        family_variants = (
            ("xptemps", "Pool Temp EXP S Family Doc Hint", ExperimentalPoolTempDocCloneHintThermostatNode),
            ("xptempt", "Pool Temp EXP T Family Strict UDI", ExperimentalPoolTempStrictUdiThermostatNode),
            ("xptempu", "Pool Temp EXP U Family Full Hint", ExperimentalPoolTempFullCloneHintThermostatNode),
        )

        for address, name, node_cls in family_variants:
            node = self.experimental_pool_temp_main_nodes.get(address)
            if node is None:
                if not discover:
                    continue
                LOGGER.info(
                    "Adding experimental thermostat-family main node address=%s class=%s",
                    address,
                    node_cls.__name__,
                )
                node = node_cls(
                    self.poly,
                    address,
                    address,
                    name,
                    self.client,
                )
                self.experimental_pool_temp_main_nodes[address] = node
                self.poly.addNode(node)
            node.update_from_state(state)

            alarm_address = f"{address}a"
            alarm_name = f"{name} Power Alarm"
            alarm_node = self.experimental_pool_temp_alarm_nodes.get(alarm_address)
            if alarm_node is None:
                if not discover:
                    continue
                LOGGER.info(
                    "Adding experimental thermostat-family alarm node address=%s primary=%s",
                    alarm_address,
                    address,
                )
                alarm_node = ExperimentalPoolTempPowerAlarmNode(
                    self.poly,
                    address,
                    alarm_address,
                    alarm_name,
                    self.client,
                )
                self.experimental_pool_temp_alarm_nodes[alarm_address] = alarm_node
                self.poly.addNode(alarm_node)
            alarm_node.update_from_state(state)

    def discover(self, command=None):
        LOGGER.info("ScreenLogic discover invoked")
        self.refresh_topology()

    def query(self, command=None):
        self.refresh_children(refresh_topology=True)

    commands = {
        "DISCOVER": discover,
        "QUERY": query,
    }
