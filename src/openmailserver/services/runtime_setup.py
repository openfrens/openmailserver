from __future__ import annotations

import stat
from pathlib import Path

from openmailserver.config import Settings
from openmailserver.platform.base import PlatformAdapter


def template_context(settings: Settings, repo_root: Path | None = None) -> dict[str, str]:
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
        "repo_root": str((repo_root or Path.cwd()).resolve()),
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


def make_executable(path: Path) -> None:
    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_script(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    make_executable(path)
    return str(path)


def render_runtime_bundle(
    settings: Settings, adapter: PlatformAdapter, repo_root: Path
) -> dict[str, str]:
    context = template_context(settings, repo_root)
    runtime_root = settings.config_root
    postfix_root = runtime_root / "postfix"
    dovecot_root = runtime_root / "dovecot"
    scripts_root = runtime_root / "scripts"
    scripts_root.mkdir(parents=True, exist_ok=True)

    rendered_files = {
        "postfix_main_cf": str(
            render_file(
                repo_root / "config/postfix/main.cf.template",
                postfix_root / "main.cf",
                context,
            )
        ),
        "postfix_virtual_domains": str(
            render_file(
                repo_root / "config/postfix/sql/virtual_domains.cf",
                postfix_root / "sql/virtual_domains.cf",
                context,
            )
        ),
        "postfix_virtual_mailboxes": str(
            render_file(
                repo_root / "config/postfix/sql/virtual_mailboxes.cf",
                postfix_root / "sql/virtual_mailboxes.cf",
                context,
            )
        ),
        "postfix_virtual_aliases": str(
            render_file(
                repo_root / "config/postfix/sql/virtual_aliases.cf",
                postfix_root / "sql/virtual_aliases.cf",
                context,
            )
        ),
        "dovecot_conf": str(
            render_file(
                repo_root / "config/dovecot/dovecot.conf",
                dovecot_root / "dovecot.conf",
                context,
            )
        ),
        "dovecot_sql_conf": str(
            render_file(
                repo_root / "config/dovecot/dovecot-sql.conf.ext.template",
                dovecot_root / "dovecot-sql.conf.ext",
                context,
            )
        ),
    }

    script_specs = [
        (
            "install_script",
            scripts_root / f"install-mail-stack-{adapter.name}.sh",
            adapter.install_script(context),
        ),
        (
            "apply_config_script",
            scripts_root / f"apply-config-{adapter.name}.sh",
            adapter.apply_config_script(context),
        ),
        (
            "install_api_service_script",
            scripts_root / f"install-api-service-{adapter.name}.sh",
            adapter.install_api_service_script(context),
        ),
        (
            "start_api_service_script",
            scripts_root / f"start-api-service-{adapter.name}.sh",
            adapter.start_api_service_script(context),
        ),
        (
            "stop_api_service_script",
            scripts_root / f"stop-api-service-{adapter.name}.sh",
            adapter.stop_api_service_script(context),
        ),
        (
            "restart_api_service_script",
            scripts_root / f"restart-api-service-{adapter.name}.sh",
            adapter.restart_api_service_script(context),
        ),
        (
            "status_api_service_script",
            scripts_root / f"status-api-service-{adapter.name}.sh",
            adapter.status_api_service_script(context),
        ),
    ]
    for key, path, content in script_specs:
        rendered_files[key] = _write_script(path, content)

    return rendered_files
