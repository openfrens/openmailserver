from __future__ import annotations

import os
import stat
from pathlib import Path

from openmailserver.config import Settings
from openmailserver.platform.linux import LinuxAdapter
from openmailserver.services import runtime_setup


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        maildir_root=tmp_path / "data" / "maildir",
        attachment_root=tmp_path / "data" / "attachments",
        config_root=tmp_path / "runtime",
        log_file=tmp_path / "logs" / "openmailserver.log",
        database_url="postgresql+psycopg://test-user:test-pass@db.example.test:5433/openmailserver",
        database_superuser_password="super-secret",
        canonical_hostname="mail.example.test",
        primary_domain="example.test",
    )


def test_template_helpers_render_expected_values(tmp_path):
    settings = _settings(tmp_path)
    context = runtime_setup.template_context(settings)
    template = tmp_path / "template.txt"
    destination = tmp_path / "rendered.txt"

    rendered = runtime_setup.render_text(
        "host={{ canonical_hostname }} user={{ database_user }}",
        context,
    )

    assert context["database_host"] == "db.example.test"
    assert context["database_port"] == "5433"
    assert context["database_user"] == "test-user"
    assert rendered == "host=mail.example.test user=test-user"

    template.write_text("{{ value }}", encoding="utf-8")
    written = runtime_setup.render_file(template, destination, {"value": "rendered"})
    runtime_setup.make_executable(written)

    assert written.read_text(encoding="utf-8") == "rendered"
    assert written.stat().st_mode & stat.S_IXUSR


def test_render_runtime_bundle_creates_expected_files(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    repo_root = Path(__file__).resolve().parents[2]
    adapter = LinuxAdapter()
    monkeypatch.chdir(repo_root)

    rendered_files = runtime_setup.render_runtime_bundle(settings, adapter, repo_root)

    assert Path(rendered_files["postfix_main_cf"]).exists()
    assert Path(rendered_files["dovecot_sql_conf"]).exists()
    assert Path(rendered_files["install_script"]).exists()
    assert Path(rendered_files["apply_config_script"]).exists()
    assert Path(rendered_files["install_api_service_script"]).exists()
    assert Path(rendered_files["start_api_service_script"]).exists()
    assert Path(rendered_files["stop_api_service_script"]).exists()
    assert Path(rendered_files["restart_api_service_script"]).exists()
    assert Path(rendered_files["status_api_service_script"]).exists()
    assert os.access(rendered_files["install_script"], os.X_OK)
    assert os.access(rendered_files["apply_config_script"], os.X_OK)
    assert os.access(rendered_files["install_api_service_script"], os.X_OK)
    assert os.access(rendered_files["status_api_service_script"], os.X_OK)
