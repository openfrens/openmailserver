from __future__ import annotations

from pathlib import Path

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


class LinuxAdapter(PlatformAdapter):
    name = "linux"

    def _sudo_guard(self) -> str:
        return """
relaunch_in_interactive_terminal() {
  local script_path script_dir script_name relaunch_command

  script_dir="$(cd "$(dirname "$0")" && pwd)"
  script_name="$(basename "$0")"
  script_path="$script_dir/$script_name"

  relaunch_command='export OPENMAILSERVER_INTERACTIVE_RELAUNCHED=1'
  if [[ -n "${OPENMAILSERVER_RESUME_COMMAND:-}" ]]; then
    printf -v relaunch_command '%s OPENMAILSERVER_RESUME_COMMAND=%q' "$relaunch_command" "$OPENMAILSERVER_RESUME_COMMAND"
  fi
  printf -v relaunch_command '%s; %q' "$relaunch_command" "$script_path"
  relaunch_command+='; status=$?; if [[ $status -eq 0 && -n "${OPENMAILSERVER_RESUME_COMMAND:-}" ]]; then echo "Resuming Open Mailserver install..."; bash -lc "$OPENMAILSERVER_RESUME_COMMAND"; status=$?; fi; echo; if [[ $status -eq 0 ]]; then echo "Open Mailserver privileged step completed."; else echo "Open Mailserver privileged step failed with exit code $status."; fi; read -r -p "Press Enter to close this window..."; exit $status'

  if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash -lc "$relaunch_command" >/dev/null 2>&1 &
    return 0
  fi

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -lc "$relaunch_command" >/dev/null 2>&1 &
    return 0
  fi

  if command -v konsole >/dev/null 2>&1; then
    konsole -e bash -lc "$relaunch_command" >/dev/null 2>&1 &
    return 0
  fi

  if command -v xterm >/dev/null 2>&1; then
    xterm -e bash -lc "$relaunch_command" >/dev/null 2>&1 &
    return 0
  fi

  return 1
}

require_sudo_access() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    return 0
  fi

  if sudo -n true >/dev/null 2>&1; then
    return 0
  fi

  if [[ -n "${OPENMAILSERVER_INTERACTIVE_RELAUNCHED:-}" ]] || [[ -t 0 && -t 1 ]]; then
    echo "Requesting administrator privileges..." >&2
    sudo -v
    return 0
  fi

  if relaunch_in_interactive_terminal; then
    echo "Opened a new terminal window for the required administrator step." >&2
    exit "${OPENMAILSERVER_HANDOFF_EXIT_CODE:-91}"
  fi

  echo "This step requires administrator privileges." >&2
  echo "Open the generated script in a real terminal and enter your sudo password when prompted." >&2
  echo "Tip: run 'sudo -v' first, then rerun the generated script if no terminal could be opened automatically." >&2
  exit 1
}
"""

    def _script_with_sudo_guard(self, body: str) -> str:
        return f"""#!/usr/bin/env bash
set -euo pipefail

{self._sudo_guard()}

{body}
"""

    def install_hint(self) -> list[str]:
        return [
            (
                "sudo apt-get update && sudo apt-get install -y "
                "curl python3 python3-venv python3-pip postfix dovecot-core "
                "dovecot-imapd dovecot-lmtpd dovecot-pgsql postfix-pgsql postgresql"
            ),
            "For non-Debian systems, install equivalent postfix, dovecot, and postgres packages.",
        ]

    def service_hint(self) -> list[str]:
        return [
            "sudo systemctl enable --now postfix",
            "sudo systemctl enable --now dovecot",
            "sudo systemctl enable --now postgresql",
        ]

    def platform_checks(self, root: Path) -> list[PlatformCheck]:
        return [
            PlatformCheck("runtime", "pass", "Native Linux path selected."),
            PlatformCheck("service_manager", "pass", "systemd/service integration is available."),
            PlatformCheck("mail_stack", "pass", "Linux is the recommended direct-mail runtime."),
        ]

    def api_service_unit(self, root: Path) -> str:
        python_bin = root / ".venv" / "bin" / "python"
        log_file = root / "logs" / "openmailserver-api.log"
        return f"""[Unit]
Description=Openmailserver API
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory={root}
ExecStart={python_bin} -m uvicorn openmailserver.app:app --host 0.0.0.0 --port 8787
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:{log_file}
StandardError=append:{log_file}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
"""

    def install_script(self, context: dict[str, str]) -> str:
        db_name = context.get("database_name", "openmailserver")
        db_user = context.get("database_user", "openmailserver")
        db_password = context.get("database_password", "openmailserver")
        return self._script_with_sudo_guard(
            f"""DB_NAME="{db_name}"
DB_USER="{db_user}"
DB_PASSWORD="{db_password}"

require_sudo_access
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y curl python3 python3-venv python3-pip postfix dovecot-core dovecot-imapd dovecot-lmtpd dovecot-pgsql postfix-pgsql postgresql
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y curl python3 postgresql-server postfix postfix-pgsql dovecot dovecot-pgsql
else
  echo "Unsupported package manager. Install python3, postfix, dovecot, and postgresql manually."
  exit 1
fi

sudo systemctl enable --now postgresql || true
sudo systemctl enable --now postfix || true
sudo systemctl enable --now dovecot || true

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER \\"$DB_USER\\" WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE \\"$DB_NAME\\" OWNER \\"$DB_USER\\";"

echo "Packages installed. Run the generated apply-config script next."
"""
        )

    def apply_config_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return self._script_with_sudo_guard(
            f"""RUNTIME_ROOT="{repo_root}/runtime"

if [[ ! -d /etc/postfix ]] || [[ ! -d /etc/dovecot ]]; then
  echo "Postfix or Dovecot config directories are missing."
  echo "Run runtime/scripts/install-mail-stack-linux.sh successfully before apply-config."
  exit 1
fi

require_sudo_access
sudo cp "$RUNTIME_ROOT/postfix/main.cf" /etc/postfix/main.cf
sudo mkdir -p /etc/postfix/sql
sudo cp "$RUNTIME_ROOT/postfix/sql/"*.cf /etc/postfix/sql/
sudo cp "$RUNTIME_ROOT/dovecot/dovecot.conf" /etc/dovecot/dovecot.conf
sudo cp "$RUNTIME_ROOT/dovecot/dovecot-sql.conf.ext" /etc/dovecot/dovecot-sql.conf.ext

sudo systemctl restart postfix || true
sudo systemctl restart dovecot || true
echo "Applied Postfix and Dovecot configuration on Linux."
"""
        )

    def install_api_service_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return self._script_with_sudo_guard(
            f"""RUNTIME_ROOT="{repo_root}/runtime"

require_sudo_access
sudo cp "$RUNTIME_ROOT/openmailserver.service" /etc/systemd/system/openmailserver.service
sudo systemctl daemon-reload
sudo systemctl enable --now openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""
        )

    def start_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo systemctl start openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""
        )

    def stop_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo systemctl stop openmailserver.service
"""
        )

    def restart_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo systemctl restart openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""
        )

    def status_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo systemctl status openmailserver.service --no-pager -l
"""
        )
