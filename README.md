# Open Mailserver

`openmailserver` is an open-source, self-hostable mail server for agents. Run
your own mail infrastructure, provision inboxes on your own domain, and send and
receive mail through an HTTP API, a CLI, and a containerized `mox` runtime.

## Why Open Mailserver

- Self-host mail for agents instead of relying on shared SaaS inboxes.
- Generate inboxes and mailbox API keys for agent workflows and test environments.
- Send outbound mail from your own domain and read replies back through the API.
- Create local aliases like `sales@yourdomain.com` and sync them into the runtime.

## How It Works

Open Mailserver separates the mail control plane from the mail runtime:

- the API and CLI provision mailboxes, aliases, API keys, and operational state
- `mox` handles SMTP, IMAP, and direct-to-MX delivery
- `Postgres` stores control-plane data and outbound metadata
- Docker Compose runs the stack together as `api`, `postgres`, and `mox`

That gives you a self-hosted mail stack that agents can drive through API calls
or the CLI, while you keep the domain, runtime, and mailbox lifecycle under your
control.

## Quick Start

Prerequisites:

- `git`
- Python `3.11+` with `venv`
- Docker with Compose v2

Then run:

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

After the stack is up:

```bash
.venv/bin/openmailserver create-mailbox agent yourdomain.com
curl http://127.0.0.1:8787/health
.venv/bin/openmailserver smoke-test
.venv/bin/openmailserver plan-dns --public-ip <server-public-ip>
```

## Custom Port Binds

By default, the stack publishes the API and web interfaces on host ports
`8787`, `80`, and `443`. To change those binds, see
[the installation docs](docs/install.md#custom-port-binds) for the
supported reverse-proxy deployment flow.

Use a real domain from the start. Public internet delivery is not ready until
`MX`, `SPF`, `DKIM`, `DMARC`, reverse DNS, and reachable mail ports are in place.

For full install details, Linux/macOS notes, and troubleshooting, see
[`docs/install.md`](docs/install.md).

## Important Expectations

- Open Mailserver is built for direct-to-MX mail delivery.
- For public sending, prefer a Linux Docker host with direct access to ports
  `25`, `80`, and `443`.
- Reverse DNS / `PTR` is controlled by the provider that owns the server IP.
- A fresh domain or IP may still land in spam until sender reputation improves.

## VPS Provider Notes

- Tested on `Binary Lane`. Outbound mail may require disabling port blocking in
  mPanel first.
- `OVHcloud VPS` is commonly used for self-hosted mail and generally exposes
  port `25`, but may block spammy IPs at the network level.
- `Hetzner Cloud` can work, but new cloud servers often need support approval
  before outbound mail ports are opened.
- `UpCloud` can open outbound port `25` on request after account verification.
- `Exoscale` restricts SMTP by default and requires enabling access in the
  provider portal.
- `Akamai / Linode` may restrict outbound SMTP on newer accounts and can require
  a support request.

Provider policies change often. Before you deploy, verify outbound mail port
access, reverse DNS support, and abuse-policy fit for your use case.

## Documentation

- [`docs/README.md`](docs/README.md): docs index
- [`docs/install.md`](docs/install.md): install and first-run flow
- [`docs/api.md`](docs/api.md): mailbox provisioning, send, and read APIs
- [`docs/dns.md`](docs/dns.md): required DNS records
- [`docs/deliverability.md`](docs/deliverability.md): warmup and inbox placement
- [`docs/operations.md`](docs/operations.md): backups and troubleshooting
- [`docs/security.md`](docs/security.md): security defaults
- [`docs/architecture.md`](docs/architecture.md): high-level architecture

## Development

```bash
make install
make run
make lint
make test
```

## License

MIT. See `LICENSE`.
