# Domains

`openmailserver` now treats domains as attached lifecycle records instead of
implicitly creating them on first mailbox creation.

## Why

This keeps the OSS runtime focused on the part that matters today:
connecting a domain you already own, verifying DNS, and only allowing mailbox
creation once the instance is actually ready to send and receive mail.

## Primary Domain

The configured `OPENMAILSERVER_PRIMARY_DOMAIN` is bootstrapped automatically as
an attached, verified domain for the current instance.

That means the default setup flow still works:

```bash
.venv/bin/openmailserver install
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
```

## Additional Domains

Additional domains must be attached and verified first:

```bash
.venv/bin/openmailserver domains attach example.net --dns-mode external
.venv/bin/openmailserver domains verify example.net --confirm-records
.venv/bin/openmailserver create-mailbox agent example.net
```

## Bring Your Own Domain

The supported path right now is:

1. Use a domain you already own.
2. Attach it to the instance.
3. Apply the required DNS records.
4. Verify the domain.
5. Create mailboxes after the domain is ready.

`openmailserver` already supports this end-to-end through the CLI and API.

## Coming Soon

Buying a domain through an Open Mailserver-managed service is planned, but it
is not the current primary flow. For now, treat purchased-domain support as
coming soon and use your own domain for production setup.

## API And CLI

CLI:

- `openmailserver domains list`
- `openmailserver domains attach <domain>`
- `openmailserver domains status <domain>`
- `openmailserver domains verify <domain> --confirm-records`

API:

- `GET /v1/domains`
- `POST /v1/domains/attach`
- `GET /v1/domains/{name}`
- `POST /v1/domains/{name}/verify`
