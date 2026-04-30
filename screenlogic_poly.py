#!/usr/bin/env python3

import sys
import threading

import udi_interface

from lib.config import NodeServerConfig
from lib.diagnostic_runner import DiagnosticSettings, ScreenLogicDiagnosticRunner
from lib.fake_screenlogic_client import FakeScreenLogicClient
from lib.screenlogicpy_client import ScreenLogicPyClient
from nodes.controller import ControllerNode

LOGGER = udi_interface.LOGGER

ENABLE_HARDCODED_DIAGNOSTICS = False
ENABLE_HARDCODED_RUNTIME_DEFAULTS = False
HARDCODED_DIAGNOSTIC_SETTINGS = DiagnosticSettings(
    host="",
    port=0,
    alt_port=7653,
    system_name="",
    password="",
    password_candidates=("",),
    pause_seconds=30,
)


class ScreenLogicNodeServer:
    def __init__(self):
        self.polyglot = udi_interface.Interface([])
        self.custom_params = {}
        self.config = NodeServerConfig()
        self.client = None
        self.controller = None
        self.diagnostic_thread = None

    def parameter_handler(self, params):
        self.custom_params = params
        self.config = NodeServerConfig.from_params(params)
        LOGGER.info(
            "Received custom params; connection_mode=%s host=%s port=%s system_name=%s "
            "auto_refresh=%s show_features=%s show_solar_heater=%s "
            "show_solar_thermostat=%s allow_writes=%s",
            self.config.backend_mode,
            self.config.screenlogic_host or "<none>",
            self.config.screenlogic_port or 0,
            self.config.screenlogic_system_name or "<none>",
            self.config.poll_enabled,
            self.config.feature_nodes_enabled,
            self.config.include_solar_node,
            self.config.include_solar_thermostat_node,
            self.config.control_enabled,
        )
        if ENABLE_HARDCODED_DIAGNOSTICS:
            LOGGER.info(
                "Hardcoded ScreenLogic diagnostics are enabled; ignoring custom params "
                "for the runtime backend and using the fake backend for PG3x nodes."
            )
            return
        self._update_notices()
        if self.controller is not None:
            self._rebuild_client()

    def _build_client(self):
        if ENABLE_HARDCODED_DIAGNOSTICS:
            LOGGER.info(
                "Using fake ScreenLogic backend for runtime nodes while hardcoded "
                "diagnostics run in the background"
            )
            return FakeScreenLogicClient()

        if self.config.use_fake_backend:
            LOGGER.info("Using fake ScreenLogic backend")
            return FakeScreenLogicClient()

        host = self.config.screenlogic_host
        port = self.config.screenlogic_port
        system_name = self.config.screenlogic_system_name
        password = self.config.screenlogic_password

        if ENABLE_HARDCODED_RUNTIME_DEFAULTS:
            host = host or HARDCODED_DIAGNOSTIC_SETTINGS.host
            port = port or HARDCODED_DIAGNOSTIC_SETTINGS.port
            system_name = system_name or HARDCODED_DIAGNOSTIC_SETTINGS.system_name

        LOGGER.info(
            "Using ScreenLogic backend target host=%s port=%s system_name=%s via screenlogicpy "
            "(password_configured=%s control_enabled=%s poll_seconds=%s min_command_seconds=%s)",
            host or "<none>",
            port or 0,
            system_name or "<none>",
            bool(password),
            self.config.control_enabled,
            self.config.poll_seconds,
            self.config.min_command_seconds,
        )
        return ScreenLogicPyClient(
            host=host,
            port=port,
            control_enabled=self.config.control_enabled,
            system_name=system_name,
            password=password,
            min_refresh_seconds=self.config.poll_seconds,
            min_command_seconds=self.config.min_command_seconds,
        )

    def _rebuild_client(self):
        LOGGER.info("Rebuilding backend client from latest custom parameters")
        self.client = self._build_client()
        self.controller.set_client(
            self.client,
            include_dummy_thermostat=self.config.include_dummy_thermostat,
            poll_enabled=self.config.poll_enabled,
            include_solar_node=self.config.include_solar_node,
            include_solar_thermostat_node=self.config.include_solar_thermostat_node,
            feature_nodes_enabled=self.config.feature_nodes_enabled,
            feature_include=self.config.feature_include,
            feature_exclude=self.config.feature_exclude,
        )
        try:
            self.client.connect()
        except Exception:
            LOGGER.exception("Backend client connect failed during parameter refresh")
        self._update_equipment_notices()
        self.controller.refresh_children()

    def _update_notices(self):
        if self.config.use_fake_backend:
            self._remove_notice("screenlogic_target")
            self._clear_equipment_notices()
            self._add_notice(
                {
                    "backend_mode": (
                        "Using fake backend. Set backend_mode=screenlogic and provide "
                        "screenlogic_host/screenlogic_port to begin live integration."
                    )
                }
            )
        else:
            self._remove_notice("backend_mode")
            if not self.config.screenlogic_host or not self.config.screenlogic_port:
                self._add_notice(
                    {
                        "screenlogic_target": (
                            "ScreenLogic backend selected but screenlogic_host or "
                            "screenlogic_port is missing."
                        )
                    }
                )
            else:
                self._remove_notice("screenlogic_target")
                self._update_equipment_notices()
        self._add_notice(
            {
                "screenlogic_runtime": (
                    "Runtime: "
                    f"auto_refresh={self.config.poll_enabled} "
                    f"show_features={self.config.feature_nodes_enabled} "
                    f"show_solar_heater={self.config.include_solar_node} "
                    f"show_solar_thermostat={self.config.include_solar_thermostat_node} "
                    f"allow_writes={self.config.control_enabled}"
                )
            }
        )

    def _remove_notice(self, key):
        remove_notice = getattr(self.polyglot, "removeNotice", None)
        if callable(remove_notice):
            remove_notice(key)

    def _add_notice(self, notice):
        add_notice = getattr(self.polyglot, "addNotice", None)
        if callable(add_notice):
            add_notice(notice)

    def _clear_equipment_notices(self):
        for key in (
            "screenlogic_profile",
            "screenlogic_capabilities",
            "screenlogic_features",
            "screenlogic_runtime",
        ):
            self._remove_notice(key)

    def _update_equipment_notices(self):
        if self.client is None or self.config.use_fake_backend:
            self._clear_equipment_notices()
            return

        profile = self.client.get_equipment_profile()
        if profile is None:
            self._clear_equipment_notices()
            return

        bodies = ", ".join(profile.body_names) if profile.body_names else "<none>"
        features = ", ".join(profile.feature_names[:6]) if profile.feature_names else "<none>"
        if len(profile.feature_names) > 6:
            features += f", +{len(profile.feature_names) - 6} more"
        lights = len(profile.light_names)

        self._add_notice(
            {
                "screenlogic_profile": (
                    "Detected ScreenLogic controller: "
                    f"firmware={profile.firmware or '<unknown>'} "
                    f"controller_type={profile.controller_type} "
                    f"hardware_type={profile.hardware_type} "
                    f"bodies={bodies}"
                )
            }
        )
        self._add_notice(
            {
                "screenlogic_capabilities": (
                    "Capabilities: "
                    f"solar={profile.has_solar} cooling={profile.has_cooling} "
                    f"chlorinator={profile.has_chlorinator} chemistry={profile.has_chemistry} "
                    f"hybrid_heater={profile.has_hybrid_heater} "
                    f"intelliflo_pumps={profile.intelliflo_pump_count} lights={lights}"
                )
            }
        )
        self._add_notice(
            {
                "screenlogic_features": (
                    f"Features/circuits ({len(profile.feature_names)} non-light): {features}"
                )
            }
        )

    def start(self):
        LOGGER.info("Starting ScreenLogic PG3x node server")
        self.polyglot.start()
        self.polyglot.subscribe(self.polyglot.CUSTOMPARAMS, self.parameter_handler)
        self.polyglot.ready()
        self.polyglot.setCustomParamsDoc()
        self.polyglot.updateProfile()
        self.config = NodeServerConfig.from_params(self.custom_params)
        self._update_notices()
        self.client = self._build_client()

        self.controller = ControllerNode(
            self.polyglot,
            "controller",
            "controller",
            "ScreenLogic Pool Controller",
            self.client,
            include_dummy_thermostat=self.config.include_dummy_thermostat,
            poll_enabled=self.config.poll_enabled,
            include_solar_node=self.config.include_solar_node,
            include_solar_thermostat_node=self.config.include_solar_thermostat_node,
            feature_nodes_enabled=self.config.feature_nodes_enabled,
            feature_include=self.config.feature_include,
            feature_exclude=self.config.feature_exclude,
        )
        self.polyglot.addNode(self.controller)
        self.controller.start()
        self._update_equipment_notices()
        self._start_diagnostics_if_enabled()
        self.polyglot.runForever()

    def _start_diagnostics_if_enabled(self):
        if not ENABLE_HARDCODED_DIAGNOSTICS:
            return

        LOGGER.info(
            "Starting hardcoded ScreenLogic diagnostic thread target=%s:%s system_name=%s",
            HARDCODED_DIAGNOSTIC_SETTINGS.host,
            HARDCODED_DIAGNOSTIC_SETTINGS.port,
            HARDCODED_DIAGNOSTIC_SETTINGS.system_name,
        )
        runner = ScreenLogicDiagnosticRunner(HARDCODED_DIAGNOSTIC_SETTINGS)
        self.diagnostic_thread = threading.Thread(
            target=runner.run_once,
            name="screenlogic_diagnostics",
            daemon=True,
        )
        self.diagnostic_thread.start()


if __name__ == "__main__":
    try:
        ScreenLogicNodeServer().start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
    except Exception:
        LOGGER.exception("ScreenLogic node server crashed during startup")
        raise
