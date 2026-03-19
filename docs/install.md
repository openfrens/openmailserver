# Install

`openmailserver` is meant to be installed by an agent with minimal judgment.

## Recommended Flow

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
```

The install step now does the full agent-first setup flow:

- generates runtime `Postfix` and `Dovecot` config
- writes SQL lookup files and service definitions
- runs the generated platform install/apply/service scripts in order
- saves installer state under `runtime/install-state.json`
- runs the readiness checks that used to require a separate `doctor` call

If a privileged phase needs a real terminal for `sudo`, the installer will try to
open one automatically, finish the privileged script there, and resume the
remaining phases. If the machine cannot open a GUI terminal, rerun:

```bash
.venv/bin/openmailserver install --resume
```

The install step still writes:

- runtime `Postfix` config
- runtime `Dovecot` config
- SQL lookup files
- platform setup scripts
- API service definition

## Manual Fallback

macOS:

```bash
./runtime/scripts/install-mail-stack-macos.sh
./runtime/scripts/apply-config-macos.sh
./runtime/scripts/install-api-service-macos.sh
./runtime/scripts/status-api-service-macos.sh
```

Linux:

```bash
./runtime/scripts/install-mail-stack-linux.sh
./runtime/scripts/apply-config-linux.sh
./runtime/scripts/install-api-service-linux.sh
./runtime/scripts/status-api-service-linux.sh
```

On Ubuntu and Debian, the generated installer uses the distro-default
`python3`, `python3-venv`, and `python3-pip` packages rather than a hardcoded
minor version, and installs the Dovecot LMTP package needed by the generated
mail-delivery config.

The generated Linux installer also installs the PostgreSQL integration packages
used by the rendered `Postfix` and `Dovecot` configuration, and bootstraps the
default `openmailserver` database and role.

Both generated install scripts also install `curl` so the API can be tested
immediately after setup. Most users should not need to run these scripts
manually because `openmailserver install` now orchestrates them.

## API Service Management

The API can run as a background service using the generated scripts under
`runtime/scripts/`.

Useful scripts:

- `install-api-service-linux.sh` / `install-api-service-macos.sh`
- `start-api-service-linux.sh` / `start-api-service-macos.sh`
- `stop-api-service-linux.sh` / `stop-api-service-macos.sh`
- `restart-api-service-linux.sh` / `restart-api-service-macos.sh`
- `status-api-service-linux.sh` / `status-api-service-macos.sh`

## Continue

```bash
.venv/bin/openmailserver doctor
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver domains list
.venv/bin/openmailserver domains attach example.com --dns-mode external
.venv/bin/openmailserver domains verify example.com --confirm-records
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test
```

The configured `OPENMAILSERVER_PRIMARY_DOMAIN` is automatically attached to the
instance during install/startup so the default mailbox flow keeps working.

For additional domains you already own, attach and verify them first:

```bash
.venv/bin/openmailserver domains attach example.net --dns-mode external
.venv/bin/openmailserver domains verify example.net --confirm-records
.venv/bin/openmailserver create-mailbox agent example.net
```

Domain purchase through an Open Mailserver-managed service is planned, but it
is not the current setup path. Today the supported production flow is to use
your own domain and connect it to the instance.

## Important Configuration

Review `.env.example` and the generated `.env`.

Most important values:

- `OPENMAILSERVER_DATABASE_URL`
- `OPENMAILSERVER_MAILDIR_ROOT`
- `OPENMAILSERVER_CANONICAL_HOSTNAME`
- `OPENMAILSERVER_PRIMARY_DOMAIN`
- `OPENMAILSERVER_PUBLIC_IP`
- `OPENMAILSERVER_ADMIN_API_KEY`
- `OPENMAILSERVER_BACKUP_ENCRYPTION_KEY`
