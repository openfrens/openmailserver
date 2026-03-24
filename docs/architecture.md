# Architecture

Open Mailserver is a control plane over a self-hosted mail runtime. It keeps
mailbox provisioning and operator workflows in the application layer while `mox`
owns SMTP, IMAP, and direct-to-MX delivery.

## Core Pieces

- FastAPI app for HTTP endpoints
- Typer CLI for agent workflows
- Postgres for domains, mailboxes, aliases, API keys, outbound mail, and debug metadata
- Local Maildir copies for smoke tests and fallback reads
- `mox` as the containerized SMTP/IMAP runtime

## Runtime Shape

The default deployment is the checked-in `compose.yaml`, which runs:

- `api`
- `postgres`
- `mox`

The app keeps the user-facing API stable while Docker Compose manages the API,
database, and mail runtime as one deployable stack.

## Control Plane vs Runtime

Open Mailserver owns:

- mailbox records
- aliases
- mailbox-scoped API keys
- outbound metadata and delivery history
- operational checks, backups, and install flow

`mox` owns:

- SMTP listeners
- IMAP access
- mailbox login state
- direct-to-MX sending and receiving

## Provisioning Flow

At a high level:

1. The API or CLI creates mailbox and alias records in the control plane.
2. Open Mailserver syncs the relevant changes into `mox`.
3. `mox` becomes the authoritative live mail runtime for sending and receiving.
4. The API continues to provide agent-friendly mailbox, message, and operational access.

## Why Maildir Still Exists

Maildir is not the primary live runtime. It remains for local copies, smoke-test
artifacts, and safe fallback reads in the app layer.
