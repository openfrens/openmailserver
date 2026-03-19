from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

from openmailserver.config import Settings
from openmailserver.database import create_all, init_database
from openmailserver.models import ApiKey
from openmailserver.platform.base import PlatformAdapter
from openmailserver.security import DEFAULT_ADMIN_SCOPES, generate_api_key
from openmailserver.services.debug_service import doctor_report
from openmailserver.services.domain_service import bootstrap_primary_domain
from openmailserver.services.runtime_setup import render_runtime_bundle

INSTALLER_STATE_VERSION = 1
HANDOFF_EXIT_CODE = 91
INSTALLER_PHASES = [
    "prepare",
    "mail_stack_install",
    "apply_config",
    "install_api_service",
    "verify",
]
SCRIPT_PHASE_KEYS = {
    "mail_stack_install": "install_script",
    "apply_config": "apply_config_script",
    "install_api_service": "install_api_service_script",
}


def installer_state_path(settings: Settings) -> Path:
    return settings.config_root / "install-state.json"


def _initial_phase_state() -> dict[str, dict[str, str | None]]:
    return {phase: {"status": "pending", "details": None} for phase in INSTALLER_PHASES}


def _default_state(adapter: PlatformAdapter) -> dict:
    return {
        "version": INSTALLER_STATE_VERSION,
        "platform": adapter.name,
        "status": "pending",
        "current_phase": "prepare",
        "phases": _initial_phase_state(),
        "artifacts": {},
        "doctor_report": None,
    }


def load_installer_state(settings: Settings, adapter: PlatformAdapter) -> dict:
    path = installer_state_path(settings)
    if not path.exists():
        return _default_state(adapter)

    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") != INSTALLER_STATE_VERSION or state.get("platform") != adapter.name:
        return _default_state(adapter)
    return state


def save_installer_state(settings: Settings, state: dict) -> Path:
    path = installer_state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _mark_phase(state: dict, phase: str, status: str, details: str | None = None) -> None:
    state["current_phase"] = phase
    state["phases"][phase]["status"] = status
    state["phases"][phase]["details"] = details
    incomplete = next(
        (
            phase_name
            for phase_name in INSTALLER_PHASES
            if state["phases"][phase_name]["status"] != "completed"
        ),
        None,
    )
    state["status"] = status if status in {"failed", "handoff"} else ("completed" if incomplete is None else "pending")
    state["current_phase"] = incomplete


def _phase_list(state: dict) -> list[dict[str, str | None]]:
    return [
        {
            "name": phase,
            "status": state["phases"][phase]["status"],
            "details": state["phases"][phase]["details"],
        }
        for phase in INSTALLER_PHASES
    ]


def _write_env(repo_root: Path, settings: Settings, admin_key: str, backup_key: str) -> Path:
    path = repo_root / ".env"
    content = f"""OPENMAILSERVER_ENV=development
OPENMAILSERVER_HOST={settings.host}
OPENMAILSERVER_PORT={settings.port}
OPENMAILSERVER_DATA_DIR={settings.data_dir}
OPENMAILSERVER_LOG_DIR={settings.log_dir}
OPENMAILSERVER_DATABASE_URL={settings.database_url}
OPENMAILSERVER_FALLBACK_DATABASE_URL={settings.fallback_database_url}
OPENMAILSERVER_DATABASE_SUPERUSER={settings.database_superuser}
OPENMAILSERVER_DATABASE_SUPERUSER_PASSWORD={settings.database_superuser_password or ""}
OPENMAILSERVER_MAILDIR_ROOT={settings.maildir_root}
OPENMAILSERVER_ATTACHMENT_ROOT={settings.attachment_root}
OPENMAILSERVER_CONFIG_ROOT={settings.config_root}
OPENMAILSERVER_SMTP_HOST={settings.smtp_host}
OPENMAILSERVER_SMTP_PORT={settings.smtp_port}
OPENMAILSERVER_SMTP_TIMEOUT_SECONDS={settings.smtp_timeout_seconds}
OPENMAILSERVER_TRANSPORT_MODE={settings.transport_mode}
OPENMAILSERVER_CANONICAL_HOSTNAME={settings.canonical_hostname}
OPENMAILSERVER_PRIMARY_DOMAIN={settings.primary_domain}
OPENMAILSERVER_PUBLIC_IP={settings.public_ip}
OPENMAILSERVER_API_KEY_HEADER={settings.api_key_header}
OPENMAILSERVER_LOG_FILE={settings.log_file}
OPENMAILSERVER_ADMIN_API_KEY={admin_key}
OPENMAILSERVER_BACKUP_ENCRYPTION_KEY={backup_key}
OPENMAILSERVER_MAX_SENDS_PER_HOUR={settings.max_sends_per_hour}
OPENMAILSERVER_MAX_MESSAGES_PER_MAILBOX={settings.max_messages_per_mailbox}
OPENMAILSERVER_MAX_ATTACHMENT_BYTES={settings.max_attachment_bytes}
OPENMAILSERVER_DEBUG_API_ENABLED={str(settings.debug_api_enabled).lower()}
"""
    path.write_text(content, encoding="utf-8")
    return path


def _bootstrap_admin_key(settings: Settings) -> str:
    _, session_factory = init_database(settings)
    session = session_factory()
    key = generate_api_key(prefix="admin")
    session.add(
        ApiKey(
            name="installer-admin",
            key_hash=key.hashed_key,
            scopes=list(DEFAULT_ADMIN_SCOPES),
        )
    )
    session.commit()
    session.close()
    return key.raw_key


def prepare_install_artifacts(settings: Settings, adapter: PlatformAdapter, repo_root: Path) -> dict[str, object]:
    settings.ensure_directories()
    init_database(settings, reset=True)
    create_all(settings)
    admin_key = settings.admin_api_key or _bootstrap_admin_key(settings)
    backup_key = settings.backup_encryption_key or Fernet.generate_key().decode("utf-8")

    _, session_factory = init_database(settings)
    session = session_factory()
    try:
        bootstrap_primary_domain(session)
        session.commit()
    finally:
        session.close()

    env_path = _write_env(repo_root, settings, admin_key, backup_key)
    service_definition = adapter.api_service_unit(repo_root)
    service_name = "openmailserver.service" if adapter.name == "linux" else "ai.openmailserver.api.plist"
    service_file = settings.config_root / service_name
    service_file.write_text(service_definition, encoding="utf-8")
    runtime_files = render_runtime_bundle(settings, adapter, repo_root)
    return {
        "env_file": str(env_path),
        "service_file": str(service_file),
        "runtime_files": runtime_files,
        "admin_api_key": admin_key,
    }


def _resume_command(repo_root: Path, completed_phase: str | None = None) -> str:
    command = "cd {repo} && {python} -m openmailserver.cli install --resume".format(
        repo=shlex.quote(str(repo_root)),
        python=shlex.quote(sys.executable),
    )
    if completed_phase is None:
        return command
    return f"{command} --completed-phase {shlex.quote(completed_phase)}"


def _mark_phase_and_save(
    settings: Settings,
    state: dict,
    phase: str,
    status: str,
    details: str | None = None,
) -> None:
    _mark_phase(state, phase, status, details)
    save_installer_state(settings, state)


def _run_script(
    repo_root: Path,
    script_path: Path,
    phase: str,
) -> tuple[str, str]:
    env = os.environ.copy()
    env["OPENMAILSERVER_HANDOFF_EXIT_CODE"] = str(HANDOFF_EXIT_CODE)
    env["OPENMAILSERVER_RESUME_COMMAND"] = _resume_command(repo_root, completed_phase=phase)
    process = subprocess.run(
        [str(script_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    output = "\n".join(part for part in [process.stdout.strip(), process.stderr.strip()] if part).strip()
    if process.returncode == 0:
        return "completed", output or f"{phase} completed."
    if process.returncode == HANDOFF_EXIT_CODE:
        return "handoff", output or f"{phase} moved to an interactive terminal."
    return "failed", output or f"{phase} failed with exit code {process.returncode}."


def _next_action(state: dict, repo_root: Path) -> str | None:
    resume_command = _resume_command(repo_root)
    if state["status"] == "handoff":
        return (
            "Complete the administrator step in the opened terminal window. "
            f"If automatic resume does not continue, run: {resume_command}"
        )
    if state["status"] == "failed":
        return f"Fix the reported issue and rerun: {resume_command}"
    if state["status"] == "pending":
        return f"Resume setup with: {resume_command}"
    return None


def _result_payload(
    settings: Settings,
    adapter: PlatformAdapter,
    state: dict,
    repo_root: Path,
    *,
    generate_only: bool = False,
) -> dict:
    artifacts = state.get("artifacts", {})
    return {
        "status": "ok" if state["status"] == "completed" else state["status"],
        "platform": adapter.name,
        "env_file": artifacts.get("env_file"),
        "service_file": artifacts.get("service_file"),
        "install_hint": adapter.install_hint(),
        "service_hint": adapter.service_hint(),
        "runtime_files": artifacts.get("runtime_files", {}),
        "admin_api_key": artifacts.get("admin_api_key"),
        "installer": {
            "state_file": str(installer_state_path(settings)),
            "status": state["status"],
            "current_phase": state.get("current_phase"),
            "phases": _phase_list(state),
            "next_action": _next_action(state, repo_root),
            "generate_only": generate_only,
            "doctor": state.get("doctor_report"),
        },
    }


def run_install(
    settings: Settings,
    adapter: PlatformAdapter,
    repo_root: Path,
    *,
    resume: bool = False,
    generate_only: bool = False,
    completed_phase: str | None = None,
) -> dict:
    state = load_installer_state(settings, adapter)

    if completed_phase:
        if completed_phase not in INSTALLER_PHASES:
            raise ValueError(f"Unknown installer phase: {completed_phase}")
        _mark_phase_and_save(
            settings,
            state,
            completed_phase,
            "completed",
            f"{completed_phase} completed in interactive terminal.",
        )

    if generate_only and state["phases"]["prepare"]["status"] == "completed":
        return _result_payload(settings, adapter, state, repo_root, generate_only=True)

    if state["status"] == "completed" and not generate_only and not resume and completed_phase is None:
        return _result_payload(settings, adapter, state, repo_root)

    for phase in INSTALLER_PHASES:
        if state["phases"][phase]["status"] == "completed":
            continue

        if phase == "prepare":
            artifacts = prepare_install_artifacts(settings, adapter, repo_root)
            state["artifacts"] = artifacts
            _mark_phase_and_save(
                settings,
                state,
                phase,
                "completed",
                "Generated local config, runtime files, and service definitions.",
            )
            if generate_only:
                return _result_payload(settings, adapter, state, repo_root, generate_only=True)
            continue

        if phase == "verify":
            state["doctor_report"] = doctor_report()
            _mark_phase_and_save(
                settings,
                state,
                phase,
                "completed",
                "Collected doctor readiness report.",
            )
            continue

        script_key = SCRIPT_PHASE_KEYS[phase]
        script_path = Path(state["artifacts"]["runtime_files"][script_key])
        status, details = _run_script(repo_root, script_path, phase)
        _mark_phase_and_save(settings, state, phase, status, details)
        if status != "completed":
            return _result_payload(settings, adapter, state, repo_root)

    return _result_payload(settings, adapter, state, repo_root, generate_only=generate_only)
