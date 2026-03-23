# Architecture

`openmailserver` is a control plane over a direct-mail runtime.

Core pieces:

- FastAPI app for HTTP endpoints
- Typer CLI for agent workflows
- Postgres for domains, mailboxes, aliases, API keys, outbound mail, and debug metadata
- Maildir for local mailbox inspection
- `mox` as the containerized SMTP/IMAP runtime

The app keeps the user-facing API stable while Docker Compose manages the API,
database, and mail runtime as one deployable stack.
