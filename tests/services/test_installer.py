from __future__ import annotations

from pathlib import Path

from openmailserver.config import Settings
from openmailserver.database import init_database
from openmailserver.platform.base import PlatformAdapter
from openmailserver.services import installer


class FakeAdapter(PlatformAdapter):
    name = "linux"

    def install_hint(self) -> list[str]:
        return ["fake install hint"]

    def service_hint(self) -> list[str]:
        return ["fake service hint"]

    def api_service_unit(self, root: Path) -> str:
        return f"service for {root}"

    def install_script(self, context: dict[str, str]) -> str:
        return _phase_script("mail_stack_install")

    def apply_config_script(self, context: dict[str, str]) -> str:
        return _phase_script("apply_config")

    def install_api_service_script(self, context: dict[str, str]) -> str:
        return _phase_script("install_api_service")

    def start_api_service_script(self, context: dict[str, str]) -> str:
        return "#!/usr/bin/env bash\nexit 0\n"

    def stop_api_service_script(self, context: dict[str, str]) -> str:
        return "#!/usr/bin/env bash\nexit 0\n"

    def restart_api_service_script(self, context: dict[str, str]) -> str:
        return "#!/usr/bin/env bash\nexit 0\n"

    def status_api_service_script(self, context: dict[str, str]) -> str:
        return "#!/usr/bin/env bash\nexit 0\n"


def _phase_script(phase: str) -> str:
    env_name = f"OPENMAILSERVER_TEST_{phase.upper()}"
    return f"""#!/usr/bin/env bash
set -euo pipefail

mode="${{{env_name}:-success}}"
case "$mode" in
  success)
    echo "{phase} ok"
    ;;
  handoff)
    echo "{phase} handoff"
    exit "${{OPENMAILSERVER_HANDOFF_EXIT_CODE:-91}}"
    ;;
  fail)
    echo "{phase} failed" >&2
    exit 1
    ;;
esac
"""


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        maildir_root=tmp_path / "data" / "maildir",
        attachment_root=tmp_path / "data" / "attachments",
        config_root=tmp_path / "runtime",
        log_file=tmp_path / "logs" / "openmailserver.log",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'installer.sqlite3'}",
        fallback_database_url=f"sqlite+pysqlite:///{tmp_path / 'installer.sqlite3'}",
        canonical_hostname="mail.example.test",
        primary_domain="example.test",
        public_ip="127.0.0.1",
        transport_mode="maildir",
    )


def _render_runtime_bundle(settings: Settings, adapter: PlatformAdapter, _repo_root: Path) -> dict[str, str]:
    scripts_root = settings.config_root / "scripts"
    scripts_root.mkdir(parents=True, exist_ok=True)

    files = {
        "install_script": scripts_root / f"install-mail-stack-{adapter.name}.sh",
        "apply_config_script": scripts_root / f"apply-config-{adapter.name}.sh",
        "install_api_service_script": scripts_root / f"install-api-service-{adapter.name}.sh",
        "start_api_service_script": scripts_root / f"start-api-service-{adapter.name}.sh",
        "stop_api_service_script": scripts_root / f"stop-api-service-{adapter.name}.sh",
        "restart_api_service_script": scripts_root / f"restart-api-service-{adapter.name}.sh",
        "status_api_service_script": scripts_root / f"status-api-service-{adapter.name}.sh",
    }
    contents = {
        "install_script": adapter.install_script({}),
        "apply_config_script": adapter.apply_config_script({}),
        "install_api_service_script": adapter.install_api_service_script({}),
        "start_api_service_script": adapter.start_api_service_script({}),
        "stop_api_service_script": adapter.stop_api_service_script({}),
        "restart_api_service_script": adapter.restart_api_service_script({}),
        "status_api_service_script": adapter.status_api_service_script({}),
    }

    for key, path in files.items():
        path.write_text(contents[key], encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)

    config_root = settings.config_root
    (config_root / "postfix").mkdir(parents=True, exist_ok=True)
    (config_root / "dovecot").mkdir(parents=True, exist_ok=True)
    (config_root / "postfix" / "main.cf").write_text("main", encoding="utf-8")
    (config_root / "dovecot" / "dovecot.conf").write_text("dovecot", encoding="utf-8")
    (config_root / "dovecot" / "dovecot-sql.conf.ext").write_text("sql", encoding="utf-8")

    return {
        "postfix_main_cf": str(config_root / "postfix" / "main.cf"),
        "dovecot_conf": str(config_root / "dovecot" / "dovecot.conf"),
        "dovecot_sql_conf": str(config_root / "dovecot" / "dovecot-sql.conf.ext"),
        **{key: str(path) for key, path in files.items()},
    }


def test_run_install_generate_only_persists_prepare_state(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    settings = _settings(tmp_path)
    monkeypatch.setattr(installer, "render_runtime_bundle", _render_runtime_bundle)

    result = installer.run_install(settings, adapter, tmp_path, generate_only=True)

    assert result["status"] == "pending"
    assert result["runtime_files"]["install_script"].endswith("install-mail-stack-linux.sh")
    assert result["installer"]["current_phase"] == "mail_stack_install"
    assert result["installer"]["phases"][0]["status"] == "completed"
    assert Path(result["installer"]["state_file"]).exists()
    assert (tmp_path / ".env").exists()

    init_database(reset=True)


def test_run_install_resumes_after_handoff(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    settings = _settings(tmp_path)
    monkeypatch.setattr(installer, "render_runtime_bundle", _render_runtime_bundle)
    monkeypatch.setenv("OPENMAILSERVER_TEST_MAIL_STACK_INSTALL", "handoff")

    handoff = installer.run_install(settings, adapter, tmp_path)

    assert handoff["status"] == "handoff"
    assert handoff["installer"]["current_phase"] == "mail_stack_install"
    assert "automatic resume" in handoff["installer"]["next_action"]

    monkeypatch.setenv("OPENMAILSERVER_TEST_MAIL_STACK_INSTALL", "success")
    resumed = installer.run_install(
        settings,
        adapter,
        tmp_path,
        resume=True,
        completed_phase="mail_stack_install",
    )

    assert resumed["status"] == "ok"
    assert resumed["installer"]["current_phase"] is None
    assert all(phase["status"] == "completed" for phase in resumed["installer"]["phases"])
    assert resumed["installer"]["doctor"] is not None

    init_database(reset=True)


def test_run_install_reports_failed_phase(tmp_path, monkeypatch):
    adapter = FakeAdapter()
    settings = _settings(tmp_path)
    monkeypatch.setattr(installer, "render_runtime_bundle", _render_runtime_bundle)
    monkeypatch.setenv("OPENMAILSERVER_TEST_APPLY_CONFIG", "fail")

    result = installer.run_install(settings, adapter, tmp_path)

    assert result["status"] == "failed"
    assert result["installer"]["current_phase"] == "apply_config"
    assert "Fix the reported issue" in result["installer"]["next_action"]

    init_database(reset=True)
