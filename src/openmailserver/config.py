from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPENMAILSERVER_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8787
    data_dir: Path = Path("./data")
    log_dir: Path = Path("./logs")
    database_url: str = "postgresql+psycopg://openmailserver:openmailserver@postgres:5432/openmailserver"
    fallback_database_url: str = "sqlite+pysqlite:///./data/openmailserver.sqlite3"
    database_superuser: str = "postgres"
    database_superuser_password: str | None = None
    maildir_root: Path = Path("./data/maildir")
    attachment_root: Path = Path("./data/attachments")
    config_root: Path = Path("./runtime")
    smtp_host: str = "mox"
    smtp_port: int = 25
    smtp_timeout_seconds: int = 15
    transport_mode: str = "smtp"
    canonical_hostname: str = "mail.example.com"
    primary_domain: str = "example.com"
    public_ip: str = "203.0.113.10"
    mox_image: str = "r.xmox.nl/mox:latest"
    api_key_header: str = "X-OpenMailserver-Key"
    log_file: Path = Path("./logs/openmailserver.log")
    admin_api_key: str | None = None
    backup_encryption_key: str | None = None
    max_sends_per_hour: int = 100
    max_messages_per_mailbox: int = 5000
    max_attachment_bytes: int = Field(default=25 * 1024 * 1024)
    debug_api_enabled: bool = True

    def ensure_directories(self) -> None:
        for path in [
            self.data_dir,
            self.log_dir,
            self.maildir_root,
            self.attachment_root,
            self.config_root,
            self.log_file.parent,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    @property
    def runtime_secret_path(self) -> Path:
        return self.config_root / "secrets.json"

    @property
    def mox_root(self) -> Path:
        return self.config_root / "mox"

    @property
    def mox_config_dir(self) -> Path:
        return self.mox_root / "config"

    @property
    def mox_data_dir(self) -> Path:
        return self.mox_root / "data"

    @property
    def mox_web_dir(self) -> Path:
        return self.mox_root / "web"

    @property
    def mox_readme_path(self) -> Path:
        return self.mox_root / "README.md"

    @property
    def mox_seed_path(self) -> Path:
        return self.mox_root / "quickstart.env"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def parsed_database_url(self):
        return urlparse(self.database_url.replace("+psycopg", ""))

    @property
    def database_host(self) -> str:
        return self.parsed_database_url.hostname or "127.0.0.1"

    @property
    def database_port(self) -> int:
        return self.parsed_database_url.port or 5432

    @property
    def database_name(self) -> str:
        return self.parsed_database_url.path.lstrip("/") or "openmailserver"

    @property
    def database_user(self) -> str:
        return self.parsed_database_url.username or "openmailserver"

    @property
    def database_password(self) -> str:
        return self.parsed_database_url.password or "openmailserver"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    return settings
