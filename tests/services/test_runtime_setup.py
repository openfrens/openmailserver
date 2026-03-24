from __future__ import annotations

import os
from pathlib import Path

from openmailserver.config import Settings
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

    assert written.read_text(encoding="utf-8") == "rendered"
    assert context["quickstart_command"] == "openmailserver mox-quickstart"


def test_render_runtime_bundle_creates_expected_files(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    rendered_files = runtime_setup.render_runtime_bundle(settings, repo_root)

    assert Path(rendered_files["compose_file"]).exists()
    assert Path(rendered_files["dockerfile"]).exists()
    assert Path(rendered_files["mox_readme"]).exists()
    assert Path(rendered_files["mox_seed_env"]).exists()
    assert Path(rendered_files["mox_config_dir"]).exists()
    assert Path(rendered_files["mox_data_dir"]).exists()
    assert Path(rendered_files["mox_web_dir"]).exists()
    assert os.access(rendered_files["mox_config_dir"], os.W_OK)
    assert "quickstart" in rendered_files["quickstart_command"]
