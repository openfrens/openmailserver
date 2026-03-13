# openmailserver

`openmailserver` is an open-source, self-hostable mailserver control plane for agents.

It exposes:

- HTTP endpoints
- a CLI for agents
- generated mail-stack config for native macOS and Linux

It uses:

- FastAPI
- Typer
- Postgres
- Postfix
- Dovecot
- Maildir

V1 goal:

1. install `openmailserver`
2. create a mailbox
3. send mail
4. receive mail

## Supported Platforms

- native macOS on Mac mini
- Linux on servers, VPS hosts, and ARM devices such as Raspberry Pi

## Quickstart

Give the agent these instructions:

```text
Set up openmailserver in this repo.

1. Create a virtualenv and install the project in editable mode.
2. Run `openmailserver install`.
3. Run `openmailserver doctor`.
4. Run the generated platform scripts from `runtime/scripts/`.
   - On macOS use the `*-macos.sh` scripts.
   - On Linux use the `*-linux.sh` scripts.
5. Run `openmailserver plan-dns`.
6. Create a mailbox with `openmailserver create-mailbox`.
7. Run `openmailserver smoke-test`.
8. If anything fails, use `openmailserver doctor` and `openmailserver queue`.
```

Equivalent commands:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor
```

Then:

```bash
./runtime/scripts/install-mail-stack-macos.sh
./runtime/scripts/apply-config-macos.sh
```

Or on Linux:

```bash
./runtime/scripts/install-mail-stack-linux.sh
./runtime/scripts/apply-config-linux.sh
```

Then continue:

```bash
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test
```

## Main Commands

- `openmailserver preflight`
- `openmailserver install`
- `openmailserver plan-dns`
- `openmailserver doctor`
- `openmailserver create-mailbox <local-part> <domain>`
- `openmailserver smoke-test`
- `openmailserver queue`
- `openmailserver backup-create`
- `openmailserver backup-verify`
- `openmailserver restore <path>`

## Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

## License

MIT. See `LICENSE`.

## Docs

- `docs/install.md`
- `docs/api.md`
- `docs/operations.md`
- `docs/architecture.md`
- `docs/dns.md`
- `docs/security.md`
- `docs/platforms.md`
