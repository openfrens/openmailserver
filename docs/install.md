# Install

Open Mailserver now has a container-first install path. The repository no longer
generates host-level `Postfix` or `Dovecot` install scripts.

The recommended onboarding flow is domain-first:

- configure the stack for the real domain you intend to use
- verify the API, CLI, and mailbox provisioning on the current machine
- complete DNS and mail-auth setup before expecting public internet mail to work

## Recommended Flow

Install these prerequisites first:

- `git`
- `python3` and `venv`
- Docker with Compose v2

Example install commands by platform:

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv docker.io docker-compose-v2
```

Fedora:

```bash
sudo dnf install -y git python3 python3-pip docker docker-compose-plugin
```

Arch Linux:

```bash
sudo pacman -Sy --needed git python python-pip docker docker-compose
```

macOS:

```bash
brew install git python
```

On macOS, install and start Docker Desktop separately so `docker compose` is
available. On Linux, if Docker is installed but your user cannot access the
daemon yet, either use `sudo docker compose ...` or add your user to the
`docker` group before continuing:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

If `python3 -m venv` reports that
`ensurepip` is unavailable, install the version-matched venv package for your
interpreter and rerun the command.

```bash
git clone https://github.com/openfrens/openmailserver
cd openmailserver
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver preflight
.venv/bin/openmailserver install --domain yourdomain.com --hostname mail.yourdomain.com
.venv/bin/openmailserver mox-quickstart
docker compose up -d
.venv/bin/openmailserver doctor
```

## Custom Port Binds

If another reverse proxy or web server already owns public `80` and `443` on the
same host, generate the stack config with loopback-only binds for the `mox` web
listeners and proxy the mail hostname to those loopback ports. If you also want
the Open Mailserver API published on a different host-side port or only on
loopback, add `--api-bind` too:

```bash
.venv/bin/openmailserver install \
  --domain yourdomain.com \
  --hostname mail.yourdomain.com \
  --api-bind 127.0.0.1:9787 \
  --mox-http-bind 127.0.0.1:8080 \
  --mox-https-bind 127.0.0.1:8443
```

The install step writes the provided domain and hostname into the generated
`.env`. Review the rest of the generated values before you continue.

The install step writes:

- `.env`
- `runtime/mox/config/`
- `runtime/mox/data/`
- `runtime/mox/web/`
- `runtime/mox/README.md`
- `runtime/mox/quickstart.env`

`openmailserver mox-quickstart` then creates a container-safe `mox.conf` and
`domains.conf` in `runtime/mox/config/`.

## Container Runtime

The checked-in `compose.yaml` is the primary deployment entry point and runs:

- `postgres`
- `api`
- `mox`

The checked-in `Dockerfile` builds the API image. The `mox` container uses the
official upstream image and persists runtime data under `runtime/mox/`. The API
image also includes the `mox` CLI so runtime provisioning can update hosted
domains and mailboxes automatically.

## Hosted Domains

Once quickstart is complete, creating mailboxes for additional domains will sync
those domains and accounts into the live `mox` runtime automatically.

- Mailboxes at hosted domains are provisioned automatically.
- Local aliases are provisioned automatically.
- External forwarding aliases are currently rejected because the `mox` alias
  runtime only supports local-account destinations.

## Machine Verification

```bash
.venv/bin/openmailserver create-mailbox agent yourdomain.com
curl http://127.0.0.1:8787/health
.venv/bin/openmailserver smoke-test
.venv/bin/openmailserver doctor
```

These checks confirm the stack is up on the current machine while DNS work is
still being completed.

`openmailserver create-mailbox` returns three important values:

- `mailbox.email`: the inbox address that can receive mail
- `password`: the mailbox password for IMAP and SMTP submission
- `api_key.key`: the mailbox-scoped HTTP API key for send/read endpoints

After mailbox creation, agents should validate both sending and reading.

Example send:

```bash
curl -X POST http://127.0.0.1:8787/v1/mail/send \
  -H "Content-Type: application/json" \
  -H "X-OpenMailserver-Key: <mailbox-api-key>" \
  -d '{
    "sender": "agent@yourdomain.com",
    "recipients": ["agent@yourdomain.com"],
    "subject": "hello",
    "text_body": "world"
  }'
```

Example list received messages:

```bash
curl http://127.0.0.1:8787/v1/mailboxes/agent@yourdomain.com/messages \
  -H "X-OpenMailserver-Key: <mailbox-api-key>"
```

Example fetch one message body:

```bash
curl "http://127.0.0.1:8787/v1/messages/<message-id>?address=agent@yourdomain.com" \
  -H "X-OpenMailserver-Key: <mailbox-api-key>"
```

If the user wants to use a standard mail client instead of the HTTP API, the
mailbox can also be accessed with:

- IMAP host: `OPENMAILSERVER_CANONICAL_HOSTNAME`
- IMAP port: `993`
- SMTP submission host: `OPENMAILSERVER_CANONICAL_HOSTNAME`
- SMTP submission port: `465`
- username: full mailbox address
- password: the mailbox password returned by mailbox creation

## Complete DNS And Mail Auth

Once the stack is running, use:

```bash
.venv/bin/openmailserver plan-dns --public-ip <server-public-ip>
```

That output is the DNS checklist for direct-to-MX delivery on the public
internet. At minimum, complete `MX`, `SPF`, `DKIM`, `DMARC`, and matching
reverse DNS before you treat the server as ready for real sending and receiving.

Important: reverse DNS / `PTR` is owned by the provider that owns the public IP.
It is usually not configured in Cloudflare or your normal DNS panel. If your VPS
provider does not let you change `PTR`, the stack can still run and receive mail,
but outbound deliverability will be limited.

After the infrastructure is correct, expect a warmup period for a new domain or IP.
See [`docs/deliverability.md`](deliverability.md) for a concise guide.

## Important Configuration

Review `.env.example` and the generated `.env`.

Most important values:

- `OPENMAILSERVER_DATABASE_URL`
- `OPENMAILSERVER_API_BIND`
- `OPENMAILSERVER_SMTP_HOST`
- `OPENMAILSERVER_CANONICAL_HOSTNAME`
- `OPENMAILSERVER_PRIMARY_DOMAIN`
- `OPENMAILSERVER_MOX_HTTP_BIND`
- `OPENMAILSERVER_MOX_HTTPS_BIND`
- `OPENMAILSERVER_MOX_ADMIN_ACCOUNT`
- `OPENMAILSERVER_MOX_ADMIN_ADDRESS`
- `OPENMAILSERVER_ADMIN_API_KEY`
- `OPENMAILSERVER_BACKUP_ENCRYPTION_KEY`
- `OPENMAILSERVER_MOX_IMAGE`

`openmailserver plan-dns` now takes the server IP explicitly with
`--public-ip`, so you do not need to set `OPENMAILSERVER_PUBLIC_IP` during
install just to generate the DNS plan.
