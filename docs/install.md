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
```

Linux:

```bash
./runtime/scripts/install-mail-stack-linux.sh
./runtime/scripts/apply-config-linux.sh
```

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
