# DNS Setup

`openmailserver plan-dns --public-ip <server-public-ip>` prints the records
required for direct-to-MX delivery.

The expected flow is that you configure Open Mailserver for the real domain
first, then use this output to finish DNS before expecting internet mail to work
correctly.

Minimum records:

- `A` or `AAAA` for the canonical mail hostname
- `MX` for the primary domain
- `CNAME` for `autoconfig.<domain>` pointing at the canonical mail hostname
- `CNAME` for `mta-sts.<domain>` pointing at the canonical mail hostname
- `SPF`
- `DKIM`
- `DMARC`
- matching `PTR` from the server IP back to the canonical hostname

`SPF`, `DKIM`, and `DMARC` are baseline records for a secure and trustworthy
mail setup, not optional extras.

`PTR` is different from the other records above: it is controlled by the network
owner of the public IP, not by a normal DNS zone editor such as Cloudflare. If
your VPS provider does not expose reverse-DNS controls or will not set it for
you, direct-to-MX outbound deliverability will be weaker even if the rest of the
DNS records are correct.

Some VPS providers also block outbound port `25` by default. If outbound delivery
times out even after DNS is correct, check the provider control panel first and
make sure SMTP port blocking is disabled for the instance.

After DNS is correct, a brand-new domain or IP may still land in spam until sender
reputation improves. For concise warmup and deliverability guidance, see
[`docs/deliverability.md`](deliverability.md).
