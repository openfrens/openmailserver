# Install

`openmailserver` is meant to be installed by an agent with minimal judgment.

## Recommended Flow

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor
```

The install step writes:

- runtime `Postfix` config
- runtime `Dovecot` config
- SQL lookup files
- platform setup scripts
- API service definition

## Apply Mail Stack Setup

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
immediately after setup.

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
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test
```

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
