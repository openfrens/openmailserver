from __future__ import annotations

from pathlib import Path

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


class MacOSAdapter(PlatformAdapter):
    name = "macos"

    def install_hint(self) -> list[str]:
        return [
            "brew install python@3.11 postgresql@16 dovecot",
            "Use the system postfix binary that ships with macOS.",
        ]

    def service_hint(self) -> list[str]:
        return [
            "brew services start postgresql@16",
            "sudo launchctl load -w /System/Library/LaunchDaemons/org.postfix.master.plist",
        ]

    def platform_checks(self, root: Path) -> list[PlatformCheck]:
        return [
            PlatformCheck("runtime", "pass", "Native macOS path selected."),
            PlatformCheck("service_manager", "pass", "launchd integration is available."),
            PlatformCheck("mail_stack", "warn", "Verify dovecot is installed through Homebrew."),
        ]

    def api_service_unit(self, root: Path) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ai.openmailserver.api</string>
  <key>ProgramArguments</key>
  <array>
    <string>python3</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>openmailserver.app:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>8787</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{root}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
"""

    def install_script(self, context: dict[str, str]) -> str:
        return """#!/usr/bin/env bash
set -euo pipefail

brew install python@3.11 postgresql@16 dovecot
brew services start postgresql@16
sudo launchctl load -w /System/Library/LaunchDaemons/org.postfix.master.plist || true
sudo mkdir -p /usr/local/etc/dovecot /usr/local/etc/postfix/sql
echo "Packages installed. Run the generated apply-config script next."
"""

    def apply_config_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return f"""#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="{repo_root}/runtime"

sudo cp "$RUNTIME_ROOT/postfix/main.cf" /etc/postfix/main.cf
sudo mkdir -p /etc/postfix/sql
sudo cp "$RUNTIME_ROOT/postfix/sql/"*.cf /etc/postfix/sql/
sudo cp "$RUNTIME_ROOT/dovecot/dovecot.conf" /usr/local/etc/dovecot/dovecot.conf
sudo cp "$RUNTIME_ROOT/dovecot/dovecot-sql.conf.ext" /usr/local/etc/dovecot/dovecot-sql.conf.ext

sudo postfix reload || true
brew services restart dovecot || true
echo "Applied Postfix and Dovecot configuration on macOS."
"""
