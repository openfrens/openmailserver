from __future__ import annotations

from pathlib import Path

import pytest

from openmailserver.platform.base import PlatformAdapter, PlatformCheck


def test_platform_check_stores_named_fields():
    check = PlatformCheck(name="runtime", status="pass", details="configured")

    assert check.name == "runtime"
    assert check.status == "pass"
    assert check.details == "configured"


def test_platform_adapter_defaults_and_abstract_methods():
    adapter = PlatformAdapter()

    assert adapter.name == "unknown"
    assert adapter.install_hint() == []
    assert adapter.service_hint() == []
    assert adapter.platform_checks(Path("/tmp")) == []

    with pytest.raises(NotImplementedError):
        adapter.api_service_unit(Path("/tmp"))
    with pytest.raises(NotImplementedError):
        adapter.install_script({})
    with pytest.raises(NotImplementedError):
        adapter.apply_config_script({})
