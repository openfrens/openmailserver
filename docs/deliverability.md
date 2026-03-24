# Deliverability

Open Mailserver can help you run a technically correct self-hosted mail stack, but
good inbox placement is not instant. A fresh domain or fresh IP will often land in
spam at first, even when DNS and TLS are configured correctly.

## What This Means

- DNS correctness makes delivery possible.
- Reputation determines whether mail lands in inbox, spam, promotions, or gets throttled.
- New domains, new IPs, and sudden volume spikes are high-risk signals.

Treat direct-to-MX deliverability as something you earn over time, not something
the software can guarantee on day one.

## Before You Test Inbox Placement

Make sure all of the following are already true:

- `MX` points at the right canonical mail hostname
- `SPF`, `DKIM`, and `DMARC` are published and aligned
- reverse DNS / `PTR` matches the canonical mail hostname
- outbound port `25` is open on the VPS
- TLS works on the public hostname
- you are sending from a real mailbox on the hosted domain

If those basics are missing, fix them before spending time on warmup.

## Warmup Plan

For a new domain or IP, start with low volume and increase gradually.

Suggested approach:

1. Week 1: send a very small number of legitimate messages each day.
2. Week 2: increase volume slowly if messages are being accepted and engagement is healthy.
3. Week 3+: continue ramping only while complaint rates, bounce rates, and spam placement remain low.

Good warmup traffic usually looks like:

- real recipients
- expected messages
- normal reply behavior
- genuine opens, replies, and thread continuity

Bad warmup traffic usually looks like:

- cold blasts from a fresh domain
- large spikes in volume
- low-engagement recipients
- repetitive templates sent to many people at once

## Content Hygiene

Even with correct infrastructure, weak message quality hurts deliverability.

- Send mail people expect.
- Keep `From`, sender domain, and message intent consistent.
- Avoid misleading subjects, deceptive reply bait, or spammy formatting.
- Prefer plain, human-readable copy over heavy image-only or template-heavy mail.
- Make links and domains consistent with the sending domain.

## List Hygiene

- Send only to recipients who should receive the message.
- Remove hard bounces quickly.
- Stop repeated sends to inactive or invalid addresses.
- Do not keep retrying bad lists just because SMTP accepted some mail.

Fresh infrastructure plus poor list hygiene is one of the fastest ways to damage
reputation.

## Operational Guidance

- Start with one primary sending domain instead of many.
- Keep sending patterns stable.
- Avoid mixing product mail, cold outreach, and high-volume notification traffic on the same fresh domain.
- Watch mailbox provider behavior over time, not just SMTP acceptance.

If you need higher trust later, consider separating traffic types across domains or
subdomains.

## Testing

When validating deliverability, test more than one mailbox provider.

- Gmail
- Outlook / Microsoft 365
- iCloud
- Fastmail or another independent provider

Look for:

- inbox vs spam placement
- missing DKIM or SPF alignment warnings
- throttling or temporary rejects
- whether replies thread correctly

## What Open Mailserver Does And Does Not Solve

Open Mailserver helps with:

- self-hosting the mail infrastructure
- provisioning inboxes and aliases
- publishing the required DNS plan
- running a direct-to-MX runtime with API and CLI tooling

Open Mailserver does not automatically give you:

- domain reputation
- IP reputation
- inbox placement on a brand-new sender
- protection from poor list quality or aggressive sending patterns

## Practical Expectation

If you launch a brand-new self-hosted domain today, some providers will mark mail
as spam at first. That is normal. Get the DNS right, keep sending quality high,
warm up gradually, and judge progress over days and weeks, not a single test send.
