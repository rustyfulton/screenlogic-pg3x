import udi_interface

from nodes.experimental_pool_temp import (
    ExperimentalPoolTempDocCloneHintThermostatNode,
    ExperimentalPoolTempPowerAlarmNode,
)

LOGGER = udi_interface.LOGGER


class ThermostatLabControllerNode(ExperimentalPoolTempDocCloneHintThermostatNode):
    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, address, address, name, client)
        self.alarm_node = None

    def start(self):
        LOGGER.info("Starting thermostat lab controller node as root thermostat")
        if self.alarm_node is None:
            self.alarm_node = ExperimentalPoolTempPowerAlarmNode(
                self.poly,
                self.address,
                "controllera",
                "Thermostat Lab Power Alarm",
                self.client,
            )
            self.poly.addNode(self.alarm_node)
        self.refresh_children(refresh_topology=True)

    def set_client(self, client, **_kwargs):
        self.client = client
        if self.alarm_node is not None:
            self.alarm_node.client = client

    def shortPoll(self):
        LOGGER.info("Thermostat lab shortPoll: refreshing root thermostat")
        self.refresh_children(refresh_topology=False)

    def longPoll(self):
        LOGGER.info("Thermostat lab longPoll: refreshing root thermostat")
        self.refresh_children(refresh_topology=True)

    def refresh_children(self, *, refresh_topology=False):
        LOGGER.info(
            "Thermostat lab controller refresh refresh_topology=%s",
            refresh_topology,
        )
        self.refresh(
            {"reason": "thermostat_lab_root_refresh", "refresh_topology": refresh_topology}
        )
        if self.alarm_node is not None:
            self.alarm_node.refresh(
                {
                    "reason": "thermostat_lab_root_refresh",
                    "refresh_topology": refresh_topology,
                }
            )

    def refresh_topology(self):
        self.refresh_children(refresh_topology=True)

    def discover(self, command=None):
        LOGGER.info("Thermostat lab discover invoked command=%s", command)
        self.refresh_topology()

    def query(self, command=None):
        LOGGER.info("Thermostat lab query invoked command=%s", command)
        self.refresh_children(refresh_topology=True)

