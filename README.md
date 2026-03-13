# openmailserver

`openmailserver` is an open-source, self-hostable mailserver control plane for agents.

It gives you HTTP endpoints, a CLI, and generated mail-stack configuration for running your own mail server on native macOS or Linux.

Requires Python `3.11+`.

## For Your Agent

Paste this into your agent:

```text
Set up openmailserver from https://github.com/openfrens/openmailserver. Run all of the following in the repo.

python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor

Then run the generated platform scripts from `runtime/scripts/`.
- On macOS use the `*-macos.sh` scripts.
- On Linux use the `*-linux.sh` scripts.

Then continue with:
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test

If anything fails, use:
- `.venv/bin/openmailserver doctor`
- `.venv/bin/openmailserver queue`

Use `docs/install.md` for the full setup details.
```

## What It Includes

- HTTP endpoints for mailboxes, aliases, outbound mail, queue state, backups, and debugging
- a CLI designed for agent-driven setup and operations
- generated `Postfix` and `Dovecot` config
- `Postgres` for control-plane state and outbound metadata
- `Maildir` for local mailbox storage

## Quick Reference

```bash
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox <local-part> <domain>
.venv/bin/openmailserver smoke-test
```

## License

MIT. See `LICENSE`.

## Docs

- [`docs/install.md`](docs/install.md)
- [`docs/api.md`](docs/api.md)
- [`docs/operations.md`](docs/operations.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/dns.md`](docs/dns.md)
- [`docs/security.md`](docs/security.md)
- [`docs/platforms.md`](docs/platforms.md)
