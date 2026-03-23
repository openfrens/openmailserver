# Runtime Removal Matrix

This document tracks the legacy Postfix/Dovecot architecture that was removed and
what replaced it in the container-first design.

| Legacy surface | Previous role | New direction |
| --- | --- | --- |
| `config/postfix/` | Postfix templates and SQL maps | Removed. `mox` owns SMTP runtime config. |
| `config/dovecot/` | Dovecot IMAP/LMTP templates | Removed. `mox` owns IMAP runtime config. |
| `src/openmailserver/platform/linux.py` | Host package install and `systemd` wiring | Removed. Docker Compose is the deployment story. |
| `src/openmailserver/platform/macos.py` | Host package install and `launchctl` wiring | Removed. Docker Compose is the deployment story. |
| `src/openmailserver/platform/detect.py` | Platform branching for native installers | Removed. Runtime flow is container-native. |
| `src/openmailserver/services/runtime_setup.py` | Rendered Postfix/Dovecot files and shell scripts | Replaced with `mox` runtime directory preparation and quickstart guidance. |
| `runtime/scripts/*.sh` | Privileged setup and service-management shell scripts | Removed from the supported architecture. |
| `compose.yaml` | API + Postgres development helper | Replaced by a full stack with `postgres`, `api`, and `mox`. |
| `doctor` binary checks | Looked for `postconf` and `dovecot` | Now checks Docker, Docker Compose, runtime directories, and `mox` quickstart completion. |

## Notes

- The control plane still manages mailbox records, API keys, outbound metadata, and backups.
- The mail runtime is now expected to be created and operated through Docker.
- There is no backward-compatibility goal for the removed native-runtime path.
