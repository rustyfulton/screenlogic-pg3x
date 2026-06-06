#!/usr/bin/env python3

import json
import sys
import threading
from pathlib import Path

import udi_interface

from lib.config import NodeServerConfig
from lib.diagnostic_runner import DiagnosticSettings, ScreenLogicDiagnosticRunner
from lib.fake_screenlogic_client import FakeScreenLogicClient
from lib.screenlogicpy_client import ScreenLogicPyClient
from nodes.controller import ControllerNode

LOGGER = udi_interface.LOGGER
PARAM_CACHE_PATH = Path("custom_params_cache.json")

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

    def _make_controller(self):
        return ControllerNode(
            self.polyglot,
            "controller",
            "controller",
            "ScreenLogic Pool Controller",
            self.client,
            include_pool_node=self.config.include_pool_node,
            include_dummy_thermostat=self.config.include_dummy_thermostat,
            startup_refresh=self.config.startup_refresh,
            poll_enabled=self.config.poll_enabled,
            include_pool_heater_node=self.config.include_pool_heater_node,
            include_pool_thermostat_node=self.config.include_pool_thermostat_node,
            include_spa_thermostat_node=self.config.include_spa_thermostat_node,
            feature_nodes_enabled=self.config.feature_nodes_enabled,
            feature_include=self.config.feature_include,
            feature_exclude=self.config.feature_exclude,
            enable_fountain_experiments=self.config.enable_fountain_experiments,
            enable_pool_temp_experiments=self.config.enable_pool_temp_experiments,
            isolated_thermostat_lab_mode=self.config.isolated_thermostat_lab_mode,
        )

    def _remove_node_if_present(self, address):
        get_node = getattr(self.polyglot, "getNode", None)
        del_node = getattr(self.polyglot, "delNode", None)
        if not callable(get_node) or not callable(del_node):
            return
        node = get_node(address)
        if node is None:
            return
        LOGGER.info("Removing node during controller mode switch address=%s", address)
        try:
            del_node(address)
        except Exception:
            LOGGER.exception(
                "Unable to remove node %s during controller mode switch",
                address,
            )

    def _controller_matches_runtime_mode(self):
        if self.controller is None:
            return False
        return isinstance(self.controller, ControllerNode)

    def _recreate_controller_for_runtime_mode(self):
        LOGGER.info(
            "Recreating controller for runtime mode thermostat_lab_mode=%s",
            self.config.isolated_thermostat_lab_mode,
        )
        for address in (
            "controllera",
            "controller",
            "thermostat_1",
            "labtstata",
            "labtstat",
            "pool",
            "solar",
            "solartstat",
        ):
            self._remove_node_if_present(address)
        self.controller = self._make_controller()
        self.polyglot.addNode(self.controller)
        self.controller.start()

    def _load_cached_custom_params(self):
        if not PARAM_CACHE_PATH.exists():
            return {}
        try:
            with PARAM_CACHE_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                LOGGER.info(
                    "Loaded cached custom params from %s",
                    PARAM_CACHE_PATH.resolve(),
                )
                return data
            LOGGER.warning(
                "Ignoring cached custom params in %s because the payload is not a mapping",
                PARAM_CACHE_PATH.resolve(),
            )
        except Exception:
            LOGGER.exception("Unable to load cached custom params from disk")
        return {}

    def _save_cached_custom_params(self, params):
        if not isinstance(params, dict) or not params:
            return
        try:
            with PARAM_CACHE_PATH.open("w", encoding="utf-8") as handle:
                json.dump(params, handle, indent=2, sort_keys=True)
                handle.write("\n")
            LOGGER.info(
                "Saved custom params cache to %s",
                PARAM_CACHE_PATH.resolve(),
            )
        except Exception:
            LOGGER.exception("Unable to save cached custom params to disk")

    def poll_handler(self, polltype):
        if self.controller is None:
            return
        if "shortPoll" in polltype:
            LOGGER.info("Received PG3 shortPoll event")
            self.controller.shortPoll()
        elif "longPoll" in polltype:
            LOGGER.info("Received PG3 longPoll event")
            self.controller.longPoll()

    def stop_handler(self):
        LOGGER.info("Stopping ScreenLogic PG3x node server")
        if self.controller is not None:
            try:
                self.controller.setDriver("ST", 0, force=True)
            except Exception:
                LOGGER.exception("Unable to mark controller offline during stop")
        stop = getattr(self.polyglot, "stop", None)
        if callable(stop):
            stop()

    def parameter_handler(self, params):
        self.custom_params = params
        self._save_cached_custom_params(params)
        self.config = NodeServerConfig.from_params(params)
        LOGGER.info(
            "Received custom params; mode=%s backend=%s host=%s port=%s system_name=%s "
            "auto_refresh=%s show_pool_node=%s show_features=%s "
            "show_pool_heater=%s show_pool_thermostat=%s show_spa_thermostat=%s "
            "fountain_experiments=%s pool_temp_experiments=%s thermostat_lab_mode=%s read_only=%s",
            self.config.mode,
            self.config.backend_mode,
            self.config.screenlogic_host or "<none>",
            self.config.screenlogic_port or 0,
            self.config.screenlogic_system_name or "<none>",
            self.config.poll_enabled,
            self.config.include_pool_node,
            self.config.feature_nodes_enabled,
            self.config.include_pool_heater_node,
            self.config.include_pool_thermostat_node,
            self.config.include_spa_thermostat_node,
            self.config.enable_fountain_experiments,
            self.config.enable_pool_temp_experiments,
            self.config.isolated_thermostat_lab_mode,
            not self.config.control_enabled,
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
            if self.config.isolated_thermostat_lab_mode:
                LOGGER.info(
                    "Using fake ScreenLogic backend in isolated thermostat lab mode"
                )
            else:
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
            "(password_configured=%s read_only=%s poll_seconds=%s min_command_seconds=%s "
            "sync_after_write=%s)",
            host or "<none>",
            port or 0,
            system_name or "<none>",
            bool(password),
            not self.config.control_enabled,
            self.config.poll_seconds,
            self.config.min_command_seconds,
            self.config.sync_after_write,
        )
        return ScreenLogicPyClient(
            host=host,
            port=port,
            control_enabled=self.config.control_enabled,
            system_name=system_name,
            password=password,
            min_refresh_seconds=self.config.poll_seconds,
            min_command_seconds=self.config.min_command_seconds,
            sync_after_write=self.config.sync_after_write,
        )

    def _rebuild_client(self):
        LOGGER.info("Rebuilding backend client from latest custom parameters")
        self.client = self._build_client()
        if not self._controller_matches_runtime_mode():
            self._recreate_controller_for_runtime_mode()
        self.controller.set_client(
            self.client,
            include_pool_node=self.config.include_pool_node,
            include_dummy_thermostat=self.config.include_dummy_thermostat,
            startup_refresh=self.config.startup_refresh,
            poll_enabled=self.config.poll_enabled,
            include_pool_heater_node=self.config.include_pool_heater_node,
            include_pool_thermostat_node=self.config.include_pool_thermostat_node,
            include_spa_thermostat_node=self.config.include_spa_thermostat_node,
            feature_nodes_enabled=self.config.feature_nodes_enabled,
            feature_include=self.config.feature_include,
            feature_exclude=self.config.feature_exclude,
            enable_fountain_experiments=self.config.enable_fountain_experiments,
            enable_pool_temp_experiments=self.config.enable_pool_temp_experiments,
            isolated_thermostat_lab_mode=self.config.isolated_thermostat_lab_mode,
        )
        try:
            if self.config.startup_refresh:
                self.client.connect()
        except Exception:
            LOGGER.exception("Backend client connect failed during parameter refresh")
        self._update_equipment_notices()
        if self.config.startup_refresh:
            self.controller.refresh_children(refresh_topology=True)

    def _update_notices(self):
        if self.config.isolated_thermostat_lab_mode:
            self._clear_equipment_notices()
            self._remove_notice("screenlogic_target")
            self._remove_notice("backend_mode")
            self._add_notice(
                {
                    "backend_mode": (
                        "Isolated thermostat lab mode enabled. Exposing only the "
                        "self-primary fake thermostat for Alexa/Portal testing."
                    )
                }
            )
            self._add_notice(
                {
                    "screenlogic_runtime": (
                        "Runtime: "
                        f"mode={self.config.mode} "
                        "thermostat_lab_mode=True "
                        f"auto_refresh={self.config.poll_enabled} "
                        f"read_only={not self.config.control_enabled}"
                    )
                }
            )
            return

        if self.config.use_fake_backend:
            self._remove_notice("screenlogic_target")
            self._clear_equipment_notices()
            self._add_notice(
                {
                    "backend_mode": (
                        "Using fake backend. Set mode=1, 2, or 3 and provide "
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
                            "Live ScreenLogic mode selected but screenlogic_host or "
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
                    f"mode={self.config.mode} "
                    f"auto_refresh={self.config.poll_enabled} "
                    f"show_pool_node={self.config.include_pool_node} "
                    f"show_features={self.config.feature_nodes_enabled} "
                    f"show_pool_heater={self.config.include_pool_heater_node} "
                    f"show_pool_thermostat={self.config.include_pool_thermostat_node} "
                    f"show_spa_thermostat={self.config.include_spa_thermostat_node} "
                    f"fountain_experiments={self.config.enable_fountain_experiments} "
                    f"pool_temp_experiments={self.config.enable_pool_temp_experiments} "
                    f"thermostat_lab_mode={self.config.isolated_thermostat_lab_mode} "
                    f"read_only={not self.config.control_enabled}"
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
        if (
            self.client is None
            or self.config.use_fake_backend
            or self.config.isolated_thermostat_lab_mode
        ):
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
        spa_gate = "enabled" if self.config.include_spa_thermostat_node else "disabled"

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
                    f"intelliflo_pumps={profile.intelliflo_pump_count} lights={lights} "
                    f"spa_thermostat_gate={spa_gate}"
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
        self.polyglot.subscribe(self.polyglot.POLL, self.poll_handler)
        self.polyglot.subscribe(self.polyglot.STOP, self.stop_handler)
        self.polyglot.ready()
        self.polyglot.setCustomParamsDoc()
        self.polyglot.updateProfile()
        if not self.custom_params:
            cached_params = self._load_cached_custom_params()
            if cached_params:
                self.custom_params = cached_params
                self.config = NodeServerConfig.from_params(cached_params)
                LOGGER.info(
                    "Bootstrapping runtime config from cached custom params while waiting for PG3"
                )
        self.config = NodeServerConfig.from_params(self.custom_params)
        self._update_notices()
        self.client = self._build_client()
        self.controller = self._make_controller()
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
