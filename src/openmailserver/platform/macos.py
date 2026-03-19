from __future__ import annotations

import getpass
from pathlib import Path

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


class MacOSAdapter(PlatformAdapter):
    name = "macos"

    def _sudo_guard(self) -> str:
        return """
relaunch_in_interactive_terminal() {
  local script_path script_dir script_name relaunch_command

  if ! command -v osascript >/dev/null 2>&1; then
    return 1
  fi

  script_dir="$(cd "$(dirname "$0")" && pwd)"
  script_name="$(basename "$0")"
  script_path="$script_dir/$script_name"

  relaunch_command='export OPENMAILSERVER_INTERACTIVE_RELAUNCHED=1'
  if [[ -n "${OPENMAILSERVER_RESUME_COMMAND:-}" ]]; then
    printf -v relaunch_command '%s OPENMAILSERVER_RESUME_COMMAND=%q' "$relaunch_command" "$OPENMAILSERVER_RESUME_COMMAND"
  fi
  printf -v relaunch_command '%s; %q' "$relaunch_command" "$script_path"
  relaunch_command+='; status=$?; if [[ $status -eq 0 && -n "${OPENMAILSERVER_RESUME_COMMAND:-}" ]]; then echo "Resuming Open Mailserver install..."; bash -lc "$OPENMAILSERVER_RESUME_COMMAND"; status=$?; fi; echo; if [[ $status -eq 0 ]]; then echo "Open Mailserver privileged step completed."; else echo "Open Mailserver privileged step failed with exit code $status."; fi; read -r -p "Press Enter to close this window..."; exit $status'

  osascript - "$relaunch_command" <<'APPLESCRIPT' >/dev/null
on run argv
  tell application "Terminal"
    activate
    do script (item 1 of argv)
  end tell
end run
APPLESCRIPT
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
    echo "Opened a new Terminal window for the required administrator step." >&2
    exit "${OPENMAILSERVER_HANDOFF_EXIT_CODE:-91}"
  fi

  echo "This step requires administrator privileges." >&2
  echo "Open the generated script in Terminal and enter your macOS password when prompted." >&2
  echo "Tip: run 'sudo -v' first, then rerun the generated script if Terminal could not be opened automatically." >&2
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
            "brew install curl python@3.11 postgresql@16 dovecot",
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
        python_bin = root / ".venv" / "bin" / "python"
        log_file = root / "logs" / "openmailserver-api.log"
        user_name = getpass.getuser()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ai.openmailserver.api</string>
  <key>UserName</key>
  <string>{user_name}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_bin}</string>
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
  <key>StandardOutPath</key>
  <string>{log_file}</string>
  <key>StandardErrorPath</key>
  <string>{log_file}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
"""

    def install_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
brew install curl python@3.11 postgresql@16 dovecot
brew services start postgresql@16
sudo launchctl load -w /System/Library/LaunchDaemons/org.postfix.master.plist || true
sudo mkdir -p /usr/local/etc/dovecot /usr/local/etc/postfix/sql
echo "Packages installed. Run the generated apply-config script next."
"""
        )

    def apply_config_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return self._script_with_sudo_guard(
            f"""RUNTIME_ROOT="{repo_root}/runtime"

require_sudo_access
sudo cp "$RUNTIME_ROOT/postfix/main.cf" /etc/postfix/main.cf
sudo mkdir -p /etc/postfix/sql
sudo cp "$RUNTIME_ROOT/postfix/sql/"*.cf /etc/postfix/sql/
sudo cp "$RUNTIME_ROOT/dovecot/dovecot.conf" /usr/local/etc/dovecot/dovecot.conf
sudo cp "$RUNTIME_ROOT/dovecot/dovecot-sql.conf.ext" /usr/local/etc/dovecot/dovecot-sql.conf.ext

sudo postfix reload || true
brew services restart dovecot || true
echo "Applied Postfix and Dovecot configuration on macOS."
"""
        )

    def install_api_service_script(self, context: dict[str, str]) -> str:
        repo_root = context["repo_root"]
        return self._script_with_sudo_guard(
            f"""RUNTIME_ROOT="{repo_root}/runtime"
PLIST_TARGET="/Library/LaunchDaemons/ai.openmailserver.api.plist"

require_sudo_access
sudo cp "$RUNTIME_ROOT/ai.openmailserver.api.plist" "$PLIST_TARGET"
sudo chown root:wheel "$PLIST_TARGET"
sudo launchctl bootout system/ai.openmailserver.api >/dev/null 2>&1 || true
sudo launchctl bootstrap system "$PLIST_TARGET"
sudo launchctl enable system/ai.openmailserver.api
sudo launchctl kickstart -k system/ai.openmailserver.api
"""
        )

    def start_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo launchctl print system/ai.openmailserver.api >/dev/null 2>&1 || \
  sudo launchctl bootstrap system /Library/LaunchDaemons/ai.openmailserver.api.plist
sudo launchctl enable system/ai.openmailserver.api
sudo launchctl kickstart -k system/ai.openmailserver.api
"""
        )

    def stop_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo launchctl bootout system/ai.openmailserver.api
"""
        )

    def restart_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo launchctl bootout system/ai.openmailserver.api >/dev/null 2>&1 || true
sudo launchctl bootstrap system /Library/LaunchDaemons/ai.openmailserver.api.plist
sudo launchctl enable system/ai.openmailserver.api
sudo launchctl kickstart -k system/ai.openmailserver.api
"""
        )

    def status_api_service_script(self, context: dict[str, str]) -> str:
        return self._script_with_sudo_guard(
            """require_sudo_access
sudo launchctl print system/ai.openmailserver.api
"""
        )
