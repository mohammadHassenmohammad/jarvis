import pytest
from backend.app.tools.system_tools import (
    get_system_time,
    get_system_status,
    open_app,
    open_folder,
    open_website,
    save_memory_tool
)
from backend.app.tools.registry import ToolRegistry

def test_get_system_time():
    res = get_system_time()
    assert res["success"] is True
    assert "current_time" in res
    assert "current_date" in res
    assert "The current time is" in res["message"]

def test_get_system_status():
    res = get_system_status()
    assert res["success"] is True
    assert "os" in res

def test_open_app_security_rejects_unauthorized():
    # Attempt to open something dangerous or unapproved
    res = open_app("malicious_virus.exe")
    assert res["success"] is False
    assert "not in the approved safety allowlist" in res["error"]

def test_open_folder_security_rejects_unauthorized():
    res = open_folder("system32")
    assert res["success"] is False
    assert "not in the approved allowlist" in res["error"]

def test_open_website_url_validation():
    # Dangerous file:// or invalid scheme
    res = open_website("file:///C:/Windows/System32")
    assert res["success"] is False or "https://" in res.get("message", "")

def test_tool_registry_definitions():
    defs = ToolRegistry.get_definitions()
    assert len(defs) >= 5
    names = [d["function"]["name"] for d in defs]
    assert "get_system_time" in names
    assert "open_app" in names
    assert "open_folder" in names
    assert "open_website" in names
    assert "save_memory" in names

def test_tool_registry_rejects_unknown():
    res = ToolRegistry.execute_tool("format_hard_drive", {})
    assert res["success"] is False
    assert "not recognized or allowed" in res["error"]
