# API

## Core Endpoints

- `GET /v1/domains`
- `POST /v1/domains/attach`
- `GET /v1/domains/{name}`
- `POST /v1/domains/{name}/verify`
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

## Domain Attach Example

```bash
curl -X POST http://127.0.0.1:8787/v1/domains/attach \
  -H "Content-Type: application/json" \
  -H "X-OpenMailserver-Key: <admin-api-key>" \
  -d '{
    "name": "example.net",
    "dns_mode": "external",
    "attach_source": "manual"
  }'
```

## Domain Verify Example

```bash
curl -X POST http://127.0.0.1:8787/v1/domains/example.net/verify \
  -H "Content-Type: application/json" \
  -H "X-OpenMailserver-Key: <admin-api-key>" \
  -d '{
    "confirmed_records": true
  }'
```

## Send Example

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
