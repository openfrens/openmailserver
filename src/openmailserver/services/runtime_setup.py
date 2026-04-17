from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from openmailserver.config import Settings


def template_context(settings: Settings) -> dict[str, str]:
    admin_address = settings.effective_mox_admin_address
    return {
        "canonical_hostname": settings.canonical_hostname,
        "primary_domain": settings.primary_domain,
        "maildir_root": str(settings.maildir_root.resolve()),
        "database_host": settings.database_host,
        "database_port": str(settings.database_port),
        "database_name": settings.database_name,
        "database_user": settings.database_user,
        "database_password": settings.database_password,
        "database_superuser": settings.database_superuser,
        "database_superuser_password": settings.database_superuser_password or "",
        "repo_root": str(Path.cwd()),
        "mox_image": settings.mox_image,
        "mox_binary": settings.mox_binary,
        "mox_admin_account": settings.mox_admin_account,
        "admin_address": admin_address,
        "quickstart_command": "openmailserver mox-quickstart",
    }


def render_text(template: str, context: dict[str, str]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
    return rendered


def render_file(source: Path, destination: Path, context: dict[str, str]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_text(encoding="utf-8")
    destination.write_text(render_text(content, context), encoding="utf-8")
    return destination


def render_runtime_bundle(settings: Settings, repo_root: Path) -> dict[str, str]:
    context = template_context(settings)
    settings.mox_config_dir.mkdir(parents=True, exist_ok=True)
    settings.mox_data_dir.mkdir(parents=True, exist_ok=True)
    settings.mox_web_dir.mkdir(parents=True, exist_ok=True)

    settings.mox_readme_path.write_text(
        render_text(
            dedent(
                """
            # Mox Runtime

            `openmailserver` now ships with a container-first runtime based on `mox`.

            ## Quickstart

            1. Review `.env` and confirm the install-time domain and hostname values
               for the real domain you want to host.
            2. Generate the `mox` config files:

               `{{ quickstart_command }}`

            3. Start the stack:

               `docker compose up -d`

            `mox` writes its runtime config into `runtime/mox/config/` and stores mail data
            under `runtime/mox/data/`.

            Validate the stack on the current machine while you complete DNS and
            mail-auth setup for public internet delivery.

            For public internet delivery, prefer a Linux Docker host and review the upstream
            deployment notes for DNS, TLS, and listener/networking expectations.
                """
            ),
            context,
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    settings.mox_seed_path.write_text(
        render_text(
            dedent(
                """
            OPENMAILSERVER_PRIMARY_DOMAIN={{ primary_domain }}
            OPENMAILSERVER_CANONICAL_HOSTNAME={{ canonical_hostname }}
            OPENMAILSERVER_MOX_IMAGE={{ mox_image }}
            OPENMAILSERVER_MOX_BINARY={{ mox_binary }}
            OPENMAILSERVER_MOX_ADMIN_ACCOUNT={{ mox_admin_account }}
            OPENMAILSERVER_MOX_ADMIN_ADDRESS={{ admin_address }}
            OPENMAILSERVER_MOX_QUICKSTART={{ quickstart_command }}
                """
            ),
            context,
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return {
        "compose_file": str(repo_root / "compose.yaml"),
        "dockerfile": str(repo_root / "Dockerfile"),
        "mox_readme": str(settings.mox_readme_path),
        "mox_seed_env": str(settings.mox_seed_path),
        "mox_config_dir": str(settings.mox_config_dir),
        "mox_data_dir": str(settings.mox_data_dir),
        "mox_web_dir": str(settings.mox_web_dir),
        "quickstart_command": context["quickstart_command"],
    }
