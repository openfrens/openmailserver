# API

## Core Endpoints

- `POST /v1/mail/send`
- `GET /v1/outbound`
- `GET /v1/outbound/{id}`
- `POST /v1/mailboxes`
- `POST /v1/aliases`
- `GET /v1/mailboxes/{address}/messages`
- `GET /v1/messages/{id}?address=<mailbox>`

## Debug And Operations

- `GET /v1/queue`
- `GET /v1/debug/health`
- `GET /v1/debug/config`
- `GET /v1/debug/messages/{id}/trace`
- `GET /v1/debug/deliverability/report`
- `GET /v1/debug/logs`
- `POST /v1/backup`
- `POST /v1/restore/validate`

## Health Example

```bash
curl http://127.0.0.1:8787/health
```

## Mailbox Provisioning Example

Provision a mailbox with an admin-scoped API key:

```bash
curl -X POST http://127.0.0.1:8787/v1/mailboxes \
  -H "Content-Type: application/json" \
  -H "X-OpenMailserver-Key: <admin-api-key>" \
  -d '{
    "local_part": "agent",
    "domain": "yourdomain.com",
    "password": "choose-a-strong-password"
  }'
```

The response includes:

- `mailbox.email`: the hosted inbox address
- `password`: mailbox password for IMAP/SMTP login
- `api_key.key`: mailbox-scoped API key for send/read calls

## Send Example

Use the mailbox API key returned at provisioning time:

```bash
curl -X POST http://127.0.0.1:8787/v1/mail/send \
  -H "Content-Type: application/json" \
  -H "X-OpenMailserver-Key: <mailbox-api-key>" \
  -d '{
    "sender": "agent@example.com",
    "recipients": ["agent@example.com"],
    "subject": "hello",
    "text_body": "it works"
  }'
```

## Read Mail Example

List messages for a mailbox:

```bash
curl http://127.0.0.1:8787/v1/mailboxes/agent@yourdomain.com/messages \
  -H "X-OpenMailserver-Key: <mailbox-api-key>"
```

Fetch a specific message body:

```bash
curl "http://127.0.0.1:8787/v1/messages/<message-id>?address=agent@yourdomain.com" \
  -H "X-OpenMailserver-Key: <mailbox-api-key>"
```

## Credential Model

Mailbox provisioning returns two credential types:

- mailbox password: use with IMAP and SMTP submission clients
- mailbox API key: use with the Open Mailserver HTTP API for send/read operations

Standard client settings:

- IMAP host: your canonical mail hostname
- IMAP port: `993`
- SMTP submission host: your canonical mail hostname
- SMTP submission port: `465`
- username: full mailbox address
- password: mailbox password
