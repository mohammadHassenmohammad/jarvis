"""
Regression tests for reliable Windows application launching.
Tests:
  1. "Open Notepad" and variants select the launcher intent.
  2. Correct application name and arguments reach backend.
  3. Successful launch produces truthful success result with PID.
  4. Launch failure produces truthful error message.
  5. Unknown or disallowed executables are rejected by allowlist.
  6. Existing allowlist and filesystem protections remain intact (no shell metacharacters).
  7. Calculator and Paint (mspaint) work reliably.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.tools.system_tools import open_app, resolve_app_executable
from backend.app.services.chat_service import chat_service
from backend.app.config import settings


def test_open_notepad_variants_detect_direct_intent():
    """Verify natural-language command variants correctly map to open_app with notepad."""
    variants = [
        "Open Notepad",
        "open notepad",
        "launch notepad",
        "start Notepad",
        "run notepad",
        "open the notepad",
        "can you please open notepad",
        "please launch notepad",
        "open notepad.exe",
    ]
    for cmd in variants:
        intent = chat_service.detect_direct_intent(cmd)
        assert intent is not None, f"Failed to detect intent for: '{cmd}'"
        tool_name, args = intent
        assert tool_name == "open_app", f"Expected open_app for '{cmd}', got {tool_name}"
        assert args.get("app_name") == "notepad", f"Expected notepad for '{cmd}', got {args.get('app_name')}"


def test_open_calculator_and_paint_detect_direct_intent():
    """Verify Calculator and Paint command variants map to normalized keys."""
    calc_intent = chat_service.detect_direct_intent("open calculator")
    assert calc_intent == ("open_app", {"app_name": "calc"})

    paint_intent = chat_service.detect_direct_intent("launch paint")
    assert paint_intent == ("open_app", {"app_name": "mspaint"})

    cmd_intent = chat_service.detect_direct_intent("start command prompt")
    assert cmd_intent == ("open_app", {"app_name": "cmd"})


def test_successful_launch_produces_truthful_result():
    """Verify successful launch produces structured success result distinguishing launched from visible."""
    mock_proc = MagicMock()
    mock_proc.pid = 98765

    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        result = open_app("notepad")

        assert result["success"] is True
        assert result["status"] == "launched"
        assert result["pid"] == 98765
        assert result["app"] == "notepad"
        assert "98765" in result["message"]
        assert "Process started; window visibility depends on Windows desktop session" in result["message"]
        mock_popen.assert_called_once()
        # Verify shell=False was enforced (no shell injection)
        _, kwargs = mock_popen.call_args
        assert kwargs.get("shell") is False


def test_launch_failure_produces_truthful_error():
    """Verify that execution failure produces a structured failure result without swallowing error."""
    with patch("subprocess.Popen", side_effect=OSError("Access is denied")):
        result = open_app("notepad")

        assert result["success"] is False
        assert result["status"] == "failed"
        assert "Access is denied" in result["error"]


def test_unknown_application_rejected_by_allowlist():
    """Verify unknown or unapproved executables are rejected."""
    result = open_app("malicious_app")
    assert result["success"] is False
    assert result["status"] == "rejected"
    assert "not in the approved safety allowlist" in result["error"]


def test_shell_injection_metacharacters_rejected():
    """Verify security policy strictly rejects any shell injection attempts."""
    dangerous_inputs = [
        "notepad; rm -rf /",
        "notepad & calc",
        "notepad | calc",
        "notepad`whoami`",
        "notepad$HOME",
        "notepad\ncalc",
    ]
    for dangerous in dangerous_inputs:
        result = open_app(dangerous)
        assert result["success"] is False
        assert result["status"] == "rejected"
        assert "Security policy violation" in result["error"]


def test_resolve_app_executable_prioritizes_system_paths():
    """Verify executable resolution resolves executable paths correctly."""
    with patch("shutil.which", return_value=r"C:\Windows\System32\notepad.exe"):
        resolved = resolve_app_executable("notepad.exe")
        assert resolved == r"C:\Windows\System32\notepad.exe"


def test_calculator_and_paint_allowed_and_launchable():
    """Verify Calculator and Paint launch with mock process."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with patch("subprocess.Popen", return_value=mock_proc):
        calc_res = open_app("calculator")
        assert calc_res["success"] is True
        assert calc_res["app"] == "calc"
        assert calc_res["pid"] == 12345

        paint_res = open_app("paint")
        assert paint_res["success"] is True
        assert paint_res["app"] == "mspaint"
        assert paint_res["pid"] == 12345
