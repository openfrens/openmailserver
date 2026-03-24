# Contributing

Thanks for contributing to Open Mailserver.

## Project Expectations

- Keep the runtime container-first.
- Keep `mox` as the mail runtime unless an intentional architectural change is being proposed.
- Do not reintroduce host-level install scripts for `Postfix`, `Dovecot`, or other system mail daemons.
- Prefer changes that keep the CLI, API, and Docker deployment story aligned.

## Local Development

```bash
make install
make run
make lint
make test
```

If you prefer the direct Python workflow:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
uv run ruff check
uv run pytest
```

## Pull Requests

- Include tests for behavior changes whenever practical.
- Update docs when changing the install flow, runtime behavior, API, or operator-facing configuration.
- Keep the main `README.md` concise; move detailed setup and API material into `docs/`.
- Call out security-sensitive changes clearly, especially around mailbox auth, runtime secrets, backups, and debug endpoints.

## Issues

- Use GitHub issues for bugs, feature requests, and documentation gaps.
- For security vulnerabilities, follow the instructions in `SECURITY.md`.
