from __future__ import annotations

from pathlib import Path

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


class LinuxAdapter(PlatformAdapter):
    name = "linux"

    def install_hint(self) -> list[str]:
        return [
            (
                "sudo apt-get update && sudo apt-get install -y "
                "python3 python3-venv python3-pip postfix dovecot-core "
                "dovecot-imapd dovecot-lmtpd postgresql"
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
        return f"""[Unit]
Description=Openmailserver API
After=network.target

[Service]
Type=simple
WorkingDirectory={root}
ExecStart=/usr/bin/env python3 -m uvicorn openmailserver.app:app --host 0.0.0.0 --port 8787
Restart=always

[Install]
WantedBy=multi-user.target
"""

    def install_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip postfix dovecot-core dovecot-imapd dovecot-lmtpd postgresql
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y python3 postgresql-server postfix dovecot
else
  echo "Unsupported package manager. Install python3, postfix, dovecot, and postgresql manually."
  exit 1
fi

sudo systemctl enable --now postgresql || true
sudo systemctl enable --now postfix || true
sudo systemctl enable --now dovecot || true
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
