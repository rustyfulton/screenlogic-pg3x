import udi_interface

from nodes.experimental_pool_temp import (
    ExperimentalPoolTempDocCloneHintThermostatNode,
)

LOGGER = udi_interface.LOGGER


class NativeThermostatLabRootNode(ExperimentalPoolTempDocCloneHintThermostatNode):
    id = "ThermostatF"
    hint = "0x010C0100"


class ThermostatLabChildNode(ExperimentalPoolTempDocCloneHintThermostatNode):
    id = "ThermostatF"
    hint = "0x010C0100"

    def _encode_temp(self, value):
        return round(float(value), 1)

    def update_from_state(self, state):
        self.setDriver("ST", self._encode_temp(state.pool_temp_f), force=True)
        self.setDriver("CLISPH", self._encode_temp(state.pool_setpoint_f), force=True)
        self.setDriver("CLISPC", self._encode_temp(self.cool_setpoint), force=True)
        self.setDriver("CLIMD", self.mode, force=True)
        self.setDriver("CLIHCS", 1 if state.heater_on else 0, force=True)
        self._log_snapshot(
            "publish",
            temp=state.pool_temp_f,
            heat_sp=state.pool_setpoint_f,
            cool_sp=self.cool_setpoint,
            mode=self.mode,
            hcs=1 if state.heater_on else 0,
        )


class ThermostatLabControllerNode(NativeThermostatLabRootNode):
    def __init__(self, polyglot, primary, address, name, client):
        super().__init__(polyglot, address, address, name, client)

    def start(self):
        LOGGER.info("Starting thermostat lab controller node as root thermostat")
        self._cleanup_stale_lab_nodes()
        self._ensure_name("Thermostat Lab")
        self.refresh_children(refresh_topology=True)

    def _cleanup_stale_lab_nodes(self):
        get_node = getattr(self.poly, "getNode", None)
        del_node = getattr(self.poly, "delNode", None)
        if not callable(get_node) or not callable(del_node):
            return
        for address in ("controllera", "labtstat", "labtstata"):
            node = get_node(address)
            if node is None:
                continue
            LOGGER.info(
                "Thermostat lab controller removing stale prior lab node address=%s",
                address,
            )
            try:
                del_node(address)
            except Exception:
                LOGGER.exception(
                    "Unable to remove stale thermostat lab node address=%s",
                    address,
                )

    def _ensure_name(self, desired_name):
        if getattr(self, "name", None) == desired_name:
            return
        LOGGER.info(
            "Thermostat lab controller renaming root node old=%s new=%s",
            getattr(self, "name", "<unknown>"),
            desired_name,
        )
        self.name = desired_name
        rename = getattr(self, "setName", None)
        if callable(rename):
            try:
                rename(desired_name)
            except Exception:
                LOGGER.exception(
                    "Unable to rename thermostat lab root node to %s",
                    desired_name,
                )

    def set_client(self, client, **_kwargs):
        self.client = client

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

    def refresh_topology(self):
        self.refresh_children(refresh_topology=True)

    def discover(self, command=None):
        LOGGER.info("Thermostat lab discover invoked command=%s", command)
        self.refresh_topology()

    def query(self, command=None):
        LOGGER.info("Thermostat lab query invoked command=%s", command)
        self.refresh_children(refresh_topology=True)
