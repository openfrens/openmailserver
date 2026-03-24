from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from openmailserver.config import Settings, get_settings
from openmailserver.models import Alias, Domain, Mailbox


class MoxSyncError(RuntimeError):
    pass


class MoxRuntimeNotReadyError(MoxSyncError):
    pass


class ExternalAliasNotSupportedError(MoxSyncError):
    pass


@dataclass(slots=True)
class MoxCommandResult:
    stdout: str
    stderr: str


CONTAINER_MOX_UID = "1000"
CONTAINER_MOX_CONF = "/app/runtime/mox/config/mox.conf"
ALREADY_EXISTS_MARKERS = ("already exists", "already present")


def runtime_account_name(local_part: str, domain: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{local_part}-{domain}".lower()).strip("-")
    return slug or "mailbox"


def _is_local_destination(db: Session, address: str) -> bool:
    mailbox = db.query(Mailbox).filter(Mailbox.email == address).first()
    return mailbox is not None


def split_address(address: str) -> tuple[str, str]:
    local_part, separator, domain = address.partition("@")
    if not separator or not local_part or not domain:
        raise MoxSyncError(f"Invalid email address: {address}")
    return local_part, domain


class MoxSyncService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _mox_conf_path(self) -> Path:
        return self.settings.mox_config_dir / "mox.conf"

    def _compose_root(self) -> Path:
        return self.settings.config_root.resolve().parent

    def _has_local_mox(self) -> bool:
        return shutil.which(self.settings.mox_binary) is not None

    def _has_compose_runtime(self) -> bool:
        return shutil.which("docker") is not None and (
            self._compose_root() / "compose.yaml"
        ).exists()

    def has_runtime_executor(self) -> bool:
        return self._has_local_mox() or self._has_compose_runtime()

    def _container_safe_mox_conf(self) -> None:
        config_path = self._mox_conf_path()
        if not config_path.exists():
            raise MoxRuntimeNotReadyError(
                "mox quickstart has not been completed. "
                "Run openmailserver install and initialize mox first."
            )

        lines = config_path.read_text(encoding="utf-8").splitlines()
        rewritten: list[str] = []
        in_public = False
        in_internal_http = False
        i = 0

        while i < len(lines):
            line = lines[i]

            if line == "User: root" or line.startswith("User: "):
                rewritten.append(f"User: {CONTAINER_MOX_UID}")
                i += 1
                continue

            if line == "\tpublic:":
                in_public = True
                rewritten.append(line)
                i += 1
                continue

            if in_public and line.startswith("\t") and not line.startswith("\t\t"):
                in_public = False

            if in_public and line == "\t\tIPs:":
                rewritten.extend(
                    [
                        line,
                        "\t\t\t- 0.0.0.0",
                        "\t\t\t- ::",
                    ]
                )
                i += 1
                while i < len(lines) and lines[i].startswith("\t\t\t- "):
                    i += 1
                continue

            if line in {
                "\t\tAccountHTTP:",
                "\t\tAdminHTTP:",
                "\t\tWebmailHTTP:",
                "\t\tWebAPIHTTP:",
            }:
                in_internal_http = True
                rewritten.append(line)
                i += 1
                continue

            if in_internal_http and line == "\t\t\tEnabled: true":
                rewritten.append("\t\t\tEnabled: false")
                i += 1
                in_internal_http = False
                continue

            if in_internal_http and not line.startswith("\t\t\t"):
                in_internal_http = False

            rewritten.append(line)
            i += 1

        config_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")

    def quickstart_runtime(self) -> MoxCommandResult:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "mox",
                self.settings.mox_binary,
                "quickstart",
                "-skipdial",
                "-hostname",
                self.settings.canonical_hostname,
                self.settings.effective_mox_admin_address,
                CONTAINER_MOX_UID,
            ],
            cwd=self._compose_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise MoxSyncError(
                (
                    "mox quickstart failed.\n"
                    f"{result.stdout}{result.stderr}"
                ).strip()
            )
        self._container_safe_mox_conf()
        return MoxCommandResult(stdout=result.stdout, stderr=result.stderr)

    def ensure_runtime_ready(self) -> None:
        if not self.has_runtime_executor():
            raise MoxRuntimeNotReadyError(
                f"{self.settings.mox_binary} is missing and no Docker Compose runtime "
                "is available. Install it in the runtime environment first or start "
                "the containerized stack."
            )
        if not self._mox_conf_path().exists():
            raise MoxRuntimeNotReadyError(
                "mox quickstart has not been completed. "
                "Run openmailserver install and initialize mox first."
            )

    def ensure_domain(self, domain: str) -> None:
        self.ensure_runtime_ready()
        self._run(
            [
                self.settings.mox_binary,
                "config",
                "domain",
                "add",
                domain,
                self.settings.mox_admin_account,
                self.settings.mox_admin_account,
            ],
            ignore_already_exists=True,
        )

    def provision_mailbox(self, mailbox: Mailbox, password: str) -> None:
        self.ensure_domain(mailbox.domain.name)
        self._run(
            [
                self.settings.mox_binary,
                "config",
                "account",
                "add",
                mailbox.runtime_account,
                mailbox.email,
            ],
            ignore_already_exists=True,
        )
        self.set_mailbox_password(mailbox, password)

    def set_mailbox_password(self, mailbox: Mailbox, password: str) -> None:
        self.ensure_runtime_ready()
        self._run(
            [self.settings.mox_binary, "setaccountpassword", mailbox.runtime_account],
            input_text=f"{password}\n{password}\n",
        )

    def provision_alias(self, db: Session, alias: Alias) -> None:
        destinations = [item.strip() for item in alias.destination.split(",") if item.strip()]
        if not destinations:
            raise MoxSyncError("Alias must have at least one destination")
        if any(not _is_local_destination(db, item) for item in destinations):
            raise ExternalAliasNotSupportedError(
                "External forwarding aliases are not supported by the current mox-backed runtime."
            )
        self.ensure_runtime_ready()
        _, domain = split_address(alias.source)
        self.ensure_domain(domain)
        self._run(
            [
                self.settings.mox_binary,
                "config",
                "alias",
                "add",
                alias.source,
                *destinations,
            ],
            ignore_already_exists=True,
        )
        self._run(
            [
                self.settings.mox_binary,
                "config",
                "alias",
                "update",
                alias.source,
                "-allowmsgfrom",
                "true",
            ]
        )

    def _run(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        ignore_already_exists: bool = False,
    ) -> MoxCommandResult:
        env = {**os.environ}
        cwd = self.settings.mox_root.resolve()
        runtime_command = command

        if self._has_local_mox():
            env["MOXCONF"] = str(self._mox_conf_path().resolve())
        else:
            runtime_command = [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"MOXCONF={CONTAINER_MOX_CONF}",
                "api",
                *command,
            ]
            cwd = self._compose_root()

        result = subprocess.run(
            runtime_command,
            cwd=cwd,
            env=env,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
        )
        combined_output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        ).lower()
        if result.returncode == 0 or (
            ignore_already_exists
            and any(marker in combined_output for marker in ALREADY_EXISTS_MARKERS)
        ):
            return MoxCommandResult(stdout=result.stdout, stderr=result.stderr)
        raise MoxSyncError(
            (
                f"mox command failed: {' '.join(runtime_command)}\n"
                f"{result.stdout}{result.stderr}"
            ).strip()
        )


def sync_mailbox_to_mox(db: Session, mailbox: Mailbox, password: str) -> None:
    MoxSyncService().provision_mailbox(mailbox, password)


def sync_alias_to_mox(db: Session, alias: Alias) -> None:
    MoxSyncService().provision_alias(db, alias)


def resolve_or_create_domain(db: Session, name: str) -> Domain:
    domain = db.query(Domain).filter(Domain.name == name).first()
    if domain:
        return domain
    domain = Domain(name=name)
    db.add(domain)
    db.flush()
    return domain


def mailbox_runtime_account(local_part: str, domain: str) -> str:
    return runtime_account_name(local_part, domain)


def set_mailbox_runtime_password(mailbox: Mailbox, password: str) -> None:
    MoxSyncService().set_mailbox_password(mailbox, password)
