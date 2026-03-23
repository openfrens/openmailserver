# Install

`openmailserver` now has a container-first install path. The repository no longer
generates host-level `Postfix` or `Dovecot` install scripts.

## Recommended Flow

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
docker compose run --rm mox mox quickstart admin@example.com
docker compose up -d
.venv/bin/openmailserver doctor
```

The install step writes:

- `.env`
- `runtime/mox/config/`
- `runtime/mox/data/`
- `runtime/mox/web/`
- `runtime/mox/README.md`
- `runtime/mox/quickstart.env`

`mox quickstart` then creates the actual `mox.conf` and `domains.conf` files in
`runtime/mox/config/`.

## Container Runtime

The checked-in `compose.yaml` is the primary deployment entry point and runs:

- `postgres`
- `api`
- `mox`

The checked-in `Dockerfile` builds the API image. The `mox` container uses the
official upstream image and persists runtime data under `runtime/mox/`.

## Continue

```bash
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test
curl http://127.0.0.1:8787/health
```

## Important Configuration

Review `.env.example` and the generated `.env`.

Most important values:

- `OPENMAILSERVER_DATABASE_URL`
- `OPENMAILSERVER_SMTP_HOST`
- `OPENMAILSERVER_CANONICAL_HOSTNAME`
- `OPENMAILSERVER_PRIMARY_DOMAIN`
- `OPENMAILSERVER_PUBLIC_IP`
- `OPENMAILSERVER_ADMIN_API_KEY`
- `OPENMAILSERVER_BACKUP_ENCRYPTION_KEY`
- `OPENMAILSERVER_MOX_IMAGE`
