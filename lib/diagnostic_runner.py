from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass

import udi_interface

from lib.real_screenlogic_client import RealScreenLogicClient

LOGGER = udi_interface.LOGGER


@dataclass(frozen=True)
class DiagnosticSettings:
    host: str
    port: int
    system_name: str
    password: str = ""
    password_candidates: tuple[str, ...] = ("",)
    pause_seconds: int = 30
    alt_port: int = 7653
    cli_timeout_seconds: int = 20
    socket_timeout_seconds: int = 5


@dataclass(frozen=True)
class AttemptResult:
    name: str
    success: bool
    detail: str


class ScreenLogicDiagnosticRunner:
    def __init__(self, settings: DiagnosticSettings):
        self.settings = settings

    def run_once(self) -> list[AttemptResult]:
        attempts = []
        for password in self._candidate_passwords():
            label = self._password_label(password)
            attempts.append(
                (
                    f"raw_current_handshake_port80_password_{label}",
                    lambda password=password, label=label: self._attempt_raw_current_handshake_port80(
                        password=password,
                        name=f"raw_current_handshake_port80_password_{label}",
                    ),
                )
            )
            attempts.append(
                (
                    f"screenlogicpy_direct_json_port80_password_{label}",
                    lambda password=password, label=label: self._attempt_screenlogicpy_direct_json_port80_custom_password(
                        password=password,
                        name=f"screenlogicpy_direct_json_port80_password_{label}",
                    ),
                )
            )
        results: list[AttemptResult] = []

        LOGGER.info("=" * 80)
        LOGGER.info("Starting one-shot ScreenLogic diagnostic series")
        LOGGER.info(
            "Hardcoded target host=%s port=%s system_name=%s candidates=%s pause=%ss",
            self.settings.host,
            self.settings.port,
            self.settings.system_name,
            ", ".join(self._password_label(p) for p in self._candidate_passwords()),
            self.settings.pause_seconds,
        )
        LOGGER.info("=" * 80)

        for index, (name, attempt) in enumerate(attempts, start=1):
            LOGGER.info("-" * 80)
            LOGGER.info(
                "Diagnostic attempt %s/%s: %s",
                index,
                len(attempts),
                name,
            )
            LOGGER.info("-" * 80)
            started = time.time()
            try:
                result = attempt()
            except Exception as exc:
                result = AttemptResult(
                    name=name,
                    success=False,
                    detail=f"Unhandled exception: {type(exc).__name__}: {exc}",
                )
                LOGGER.exception("Diagnostic attempt %s raised an exception", name)

            elapsed = time.time() - started
            results.append(result)
            LOGGER.info(
                "Diagnostic result: name=%s success=%s elapsed=%.2fs detail=%s",
                result.name,
                result.success,
                elapsed,
                result.detail,
            )

            if index < len(attempts):
                LOGGER.info(
                    "Sleeping %s seconds before next diagnostic attempt",
                    self.settings.pause_seconds,
                )
                time.sleep(self.settings.pause_seconds)

        LOGGER.info("=" * 80)
        LOGGER.info("ScreenLogic diagnostic summary")
        for result in results:
            LOGGER.info(
                "Summary: name=%s success=%s detail=%s",
                result.name,
                result.success,
                result.detail,
            )
        LOGGER.info("=" * 80)
        return results

    def _attempt_raw_current_handshake_port80(self, *, password: str, name: str) -> AttemptResult:
        client = RealScreenLogicClient(
            host=self.settings.host,
            port=self.settings.port,
            control_enabled=False,
            system_name=self.settings.system_name,
            password=password,
        )
        success = client.connect()
        detail = (
            f"password={self._password_label(password)} "
            f"connected={success} "
            f"challenge={client.challenge.challenge or '<none>'} "
            f"login_code={client.login_response_code or '<none>'} "
            f"version={client.version.version or '<none>'}"
        )
        return AttemptResult(
            name=name,
            success=success,
            detail=detail,
        )

    def _attempt_screenlogicpy_direct_json_port80_custom_password(
        self,
        *,
        password: str,
        name: str,
    ) -> AttemptResult:
        return self._run_screenlogicpy_custom_password_script(
            name=name,
            password=password,
        )

    def _run_screenlogicpy_custom_password_script(
        self,
        *,
        name: str,
        password: str,
    ) -> AttemptResult:
        script = f"""
import asyncio
import json
import struct
import traceback

from screenlogicpy import ScreenLogicGateway
import screenlogicpy.requests.login as login_module
from screenlogicpy.requests.utility import encodeMessageString


def create_login_message():
    schema = 348
    connection_type = 0
    client_version = encodeMessageString("Android")
    pid = 2
    password = {password!r}
    passwd = encodeMessageString(password)
    fmt = f"<II{{len(client_version)}}s{{len(passwd)}}sxI"
    return struct.pack(fmt, schema, connection_type, client_version, passwd, pid)


login_module.create_login_message = create_login_message


async def main():
    gateway = ScreenLogicGateway()
    await gateway.async_connect(
        {self.settings.host!r},
        {self.settings.port},
        name={self.settings.system_name!r},
    )
    await gateway.async_update()
    print(json.dumps(gateway.get_data(), default=str))
    await gateway.async_disconnect()


try:
    asyncio.run(main())
except Exception as exc:
    print(f"{{type(exc).__name__}}: {{exc}}")
    traceback.print_exc()
    raise
""".strip()
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=self.settings.cli_timeout_seconds,
            check=False,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        stdout = self._sanitize_password(stdout, password)
        stderr = self._sanitize_password(stderr, password)
        detail = (
            f"returncode={result.returncode} "
            f"stdout={self._trim_output(stdout)} "
            f"stderr={self._trim_output(stderr)}"
        )
        return AttemptResult(
            name=name,
            success=result.returncode == 0,
            detail=f"password={self._password_label(password)} {detail}",
        )

    def _trim_output(self, output: str, limit: int = 500) -> str:
        if not output:
            return "<none>"
        compact = " ".join(output.split())
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "..."

    def _candidate_passwords(self) -> tuple[str, ...]:
        if self.settings.password_candidates:
            return tuple(self.settings.password_candidates)
        return (self.settings.password,)

    def _password_label(self, password: str) -> str:
        if password == "":
            return "blank"
        return f"configured_len_{len(password)}"

    def _sanitize_password(self, output: str, password: str) -> str:
        if not output or not password:
            return output
        return output.replace(password, "<password>")
