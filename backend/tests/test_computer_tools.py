import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.tools.system_tools import (
    open_app,
    open_folder,
    search_folder,
    read_document,
    delete_file,
    terminate_app,
    get_system_time,
    get_system_status
)
from backend.app.tools.registry import ToolRegistry

client = TestClient(app)

# ==============================================================================
# 1. Windows Application Launching (Strict Allowlist, Anti-Shell Injection)
# ==============================================================================

def test_open_app_empty_rejected():
    res = open_app("")
    assert res["success"] is False
    assert "cannot be empty" in res["error"]


@pytest.mark.parametrize("malicious_cmd", [
    "notepad & calc",
    "calc | dir",
    "notepad; rm -rf /",
    "calc\nnotepad",
    "code `calc`",
    "notepad > file.txt",
    "notepad < input.txt",
    "notepad $ENV:PATH",
    "calc\0inject",
])
def test_open_app_shell_injection_rejected(malicious_cmd):
    res = open_app(malicious_cmd)
    assert res["success"] is False
    assert "Security policy violation" in res["error"]


def test_open_app_unapproved_rejected():
    res = open_app("malware.exe")
    assert res["success"] is False
    assert "not in the approved safety allowlist" in res["error"]


@patch("os.startfile", create=True)
def test_open_app_approved_apps(mock_startfile):
    # Test valid allowlisted apps and aliases
    for app_alias, expected_key in [
        ("notepad", "notepad"),
        ("calculator", "calc"),
        ("calc", "calc"),
        ("paint", "mspaint"),
        ("mspaint", "mspaint"),
        ("task manager", "taskmgr"),
        ("taskmgr", "taskmgr"),
        ("snipping tool", "snippingtool"),
        ("snippingtool", "snippingtool"),
        ("file explorer", "explorer"),
        ("explorer", "explorer"),
        ("code", "code"),
        ("visual studio code", "code"),
        ("character map", "charmap"),
        ("disk cleanup", "cleanmgr"),
    ]:
        res = open_app(app_alias)
        assert res["success"] is True, f"Failed for {app_alias}: {res}"
        assert "message" in res
        mock_startfile.assert_called()


# ==============================================================================
# 2. Approved Folder Access & Path Safety
# ==============================================================================

def test_open_folder_unapproved_rejected():
    for bad_folder in ["system32", "C:\\Windows", "../..", "/etc", "root"]:
        res = open_folder(bad_folder)
        assert res["success"] is False
        assert "not in the approved allowlist" in res["error"]


@patch("os.startfile", create=True)
def test_open_folder_approved(mock_startfile):
    for fld in ["desktop", "downloads", "documents", "pictures", "workspace"]:
        res = open_folder(fld)
        # Success if folder exists on host system or message is generated
        if res["success"]:
            mock_startfile.assert_called()
        else:
            assert "does not exist on disk" in res["error"]


# ==============================================================================
# 3. Approved Folder Search
# ==============================================================================

def test_search_folder_unapproved_rejected():
    res = search_folder(folder_name="random_unapproved_folder", query="test")
    assert res["success"] is False
    assert "not in the approved allowlist" in res["error"]


def test_search_folder_workspace_existing():
    # Workspace should find requirements.txt or python files
    res = search_folder(folder_name="workspace", query="requirements", extension=".txt")
    assert res["success"] is True
    assert res["folder"] == "workspace"
    assert "matches" in res
    assert isinstance(res["matches"], list)
    if res["count"] > 0:
        first = res["matches"][0]
        assert "filename" in first
        assert "relative_path" in first
        assert "size_kb" in first
        assert "extension" in first
        assert "modified" in first


def test_search_folder_extension_filter():
    res = search_folder(folder_name="workspace", query="", extension="py", max_results=5)
    assert res["success"] is True
    assert res["count"] <= 5
    for m in res["matches"]:
        assert m["extension"] == ".py"


def test_search_folder_no_matches():
    res = search_folder(folder_name="workspace", query="non_existent_super_unique_pattern_xyz_12345")
    assert res["success"] is True
    assert res["count"] == 0
    assert "No files matched" in res["message"]


# ==============================================================================
# 4. Selected Document Reading & Security Validation
# ==============================================================================

def test_read_document_unapproved_folder_rejected():
    res = read_document(folder_name="system32", file_path="config.txt")
    assert res["success"] is False
    assert "not in the approved allowlist" in res["error"]


def test_read_document_path_traversal_rejected():
    traversal_paths = [
        "../../Windows/System32/drivers/etc/hosts",
        "..\\..\\Windows\\win.ini",
        "....//....//boot.ini",
        "/Windows/System32/cmd.exe",
    ]
    for p in traversal_paths:
        res = read_document(folder_name="workspace", file_path=p)
        assert res["success"] is False
        assert "Path traversal detected" in res["error"] or "does not exist" in res["error"]


def test_read_document_forbidden_files_rejected():
    for f in [".env", ".env.local", "id_rsa", "server.pem", "private.key", "credentials.json"]:
        # Mock file existence inside workspace
        test_path = settings.ALLOWED_FOLDERS["workspace"] / f
        try:
            test_path.write_text("SECRET_DATA=123", encoding="utf-8")
            res = read_document(folder_name="workspace", file_path=f)
            assert res["success"] is False
            assert "restricted" in res["error"].lower() or "forbidden" in res["error"].lower()
        finally:
            if test_path.exists():
                test_path.unlink()


def test_read_document_restricted_extension_rejected():
    test_bin = settings.ALLOWED_FOLDERS["workspace"] / "test_binary.bin"
    try:
        test_bin.write_bytes(b"BINARY_CONTENT")
        res = read_document(folder_name="workspace", file_path="test_binary.bin")
        assert res["success"] is False
        assert "Unsupported or restricted file type" in res["error"]
    finally:
        if test_bin.exists():
            test_bin.unlink()


def test_read_document_valid_text():
    # Read backend requirements.txt
    req_path = "backend/requirements.txt"
    res = read_document(folder_name="workspace", file_path=req_path, max_chars=1000)
    assert res["success"] is True
    assert "content" in res
    assert "fastapi" in res["content"].lower() or "uvicorn" in res["content"].lower()
    assert res["filename"] == "requirements.txt"
    assert res["lines"] > 0


def test_read_document_truncation_limit():
    test_file = settings.ALLOWED_FOLDERS["workspace"] / "test_long_doc.txt"
    try:
        test_file.write_text("A" * 6000, encoding="utf-8")
        res = read_document(folder_name="workspace", file_path="test_long_doc.txt", max_chars=1000)
        assert res["success"] is True
        assert len(res["content"]) == 1000
        assert res["truncated"] is True
    finally:
        if test_file.exists():
            test_file.unlink()


# ==============================================================================
# 5. Sensitive Operation: Delete File (Explicit Confirmation Guard)
# ==============================================================================

def test_delete_file_requires_confirmation():
    test_file = settings.ALLOWED_FOLDERS["workspace"] / "temp_delete_test.txt"
    test_file.write_text("Temporary test file", encoding="utf-8")
    try:
        # 1. Unconfirmed attempt MUST NOT delete the file
        res = delete_file(folder_name="workspace", file_path="temp_delete_test.txt", confirmed=False)
        assert res["success"] is False
        assert res["status"] == "requires_confirmation"
        assert "Confirmation Required" in res["message"]
        assert test_file.exists(), "File was deleted without confirmation!"

        # 2. Confirmed attempt permanently deletes the file
        res_confirmed = delete_file(folder_name="workspace", file_path="temp_delete_test.txt", confirmed=True)
        assert res_confirmed["success"] is True
        assert res_confirmed["status"] == "completed"
        assert not test_file.exists(), "File should have been deleted after explicit confirmation"
    finally:
        if test_file.exists():
            test_file.unlink()


def test_delete_file_protected_file_rejected():
    res = delete_file(folder_name="workspace", file_path=".env", confirmed=True)
    assert res["success"] is False
    assert "protected" in res["error"].lower() or "does not exist" in res["error"]


def test_delete_file_traversal_rejected():
    res = delete_file(folder_name="workspace", file_path="../../test.txt", confirmed=True)
    assert res["success"] is False
    assert "Path traversal detected" in res["error"]


# ==============================================================================
# 6. Sensitive Operation: Terminate App (Explicit Confirmation Guard)
# ==============================================================================

def test_terminate_app_unapproved_rejected():
    res = terminate_app("malware_proc", confirmed=True)
    assert res["success"] is False
    assert "not in the approved allowlist" in res["error"]


def test_terminate_app_core_system_protected():
    res = terminate_app("explorer", confirmed=True)
    assert res["success"] is False
    assert "Terminating core system component" in res["error"]


def test_terminate_app_requires_confirmation():
    res = terminate_app("notepad", confirmed=False)
    assert res["success"] is False
    assert res["status"] == "requires_confirmation"
    assert "Confirmation Required" in res["message"]
    assert "terminate_app" == res["action"]


@patch("psutil.process_iter")
def test_terminate_app_confirmed_execution(mock_process_iter):
    mock_proc = MagicMock()
    mock_proc.info = {"name": "notepad.exe", "pid": 1234}
    mock_process_iter.return_value = [mock_proc]

    res = terminate_app("notepad", confirmed=True)
    assert res["success"] is True
    assert res["status"] == "completed"
    assert res["terminated_instances"] == 1
    mock_proc.terminate.assert_called_once()


# ==============================================================================
# 7. Tool Registry & Schema Validation
# ==============================================================================

def test_registry_contains_all_computer_tools():
    defs = ToolRegistry.get_definitions()
    tool_names = [d["function"]["name"] for d in defs]
    assert "search_folder" in tool_names
    assert "read_document" in tool_names
    assert "delete_file" in tool_names
    assert "terminate_app" in tool_names
    assert "open_app" in tool_names
    assert "open_folder" in tool_names


def test_registry_execute_tool():
    res = ToolRegistry.execute_tool("search_folder", {"folder_name": "workspace", "query": "requirements"})
    assert res["success"] is True


def test_registry_rejects_unregistered():
    res = ToolRegistry.execute_tool("bash_shell_exec", {"cmd": "whoami"})
    assert res["success"] is False
    assert "not recognized or allowed" in res["error"]


# ==============================================================================
# 8. FastAPI API Endpoints
# ==============================================================================

def test_api_list_tools():
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert "allowed_apps" in data
    assert "allowed_folders" in data
    assert "sensitive_tools" in data
    assert "allowed_document_extensions" in data
    assert "delete_file" in data["sensitive_tools"]
    assert "terminate_app" in data["sensitive_tools"]


def test_api_execute_tool():
    res = client.post("/api/tools/execute", json={
        "name": "search_folder",
        "arguments": {"folder_name": "workspace", "query": "README"}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["tool"] == "search_folder"
    assert data["result"]["success"] is True
