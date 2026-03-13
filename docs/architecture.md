# Architecture

`openmailserver` is a control plane over a direct-mail runtime.

Core pieces:

- FastAPI app for HTTP endpoints
- Typer CLI for agent workflows
- Postgres for domains, mailboxes, aliases, API keys, outbound mail, and debug metadata
- Maildir for local mailbox inspection
- Postfix and Dovecot config templates for real mail delivery/storage integration

The app keeps the user-facing API stable while platform adapters handle native macOS and Linux differences.
