from __future__ import annotations

from pathlib import Path

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


class LinuxAdapter(PlatformAdapter):
    name = "linux"

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
        return f"""#!/usr/bin/env bash
set -euo pipefail

DB_NAME="{db_name}"
DB_USER="{db_user}"
DB_PASSWORD="{db_password}"

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

    def apply_config_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return f"""#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="{repo_root}/runtime"

if [[ ! -d /etc/postfix ]] || [[ ! -d /etc/dovecot ]]; then
  echo "Postfix or Dovecot config directories are missing."
  echo "Run runtime/scripts/install-mail-stack-linux.sh successfully before apply-config."
  exit 1
fi

sudo cp "$RUNTIME_ROOT/postfix/main.cf" /etc/postfix/main.cf
sudo mkdir -p /etc/postfix/sql
sudo cp "$RUNTIME_ROOT/postfix/sql/"*.cf /etc/postfix/sql/
sudo cp "$RUNTIME_ROOT/dovecot/dovecot.conf" /etc/dovecot/dovecot.conf
sudo cp "$RUNTIME_ROOT/dovecot/dovecot-sql.conf.ext" /etc/dovecot/dovecot-sql.conf.ext

sudo systemctl restart postfix || true
sudo systemctl restart dovecot || true
echo "Applied Postfix and Dovecot configuration on Linux."
"""

    def install_api_service_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return f"""#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="{repo_root}/runtime"

sudo cp "$RUNTIME_ROOT/openmailserver.service" /etc/systemd/system/openmailserver.service
sudo systemctl daemon-reload
sudo systemctl enable --now openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""

    def start_api_service_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

sudo systemctl start openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""

    def stop_api_service_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

sudo systemctl stop openmailserver.service
"""

    def restart_api_service_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

sudo systemctl restart openmailserver.service
sudo systemctl status openmailserver.service --no-pager -l || true
"""

    def status_api_service_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

sudo systemctl status openmailserver.service --no-pager -l
"""
