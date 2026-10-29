import pytest
from backend.app.database.db import get_all_settings, set_setting

def test_voice_settings_defaults():
    settings = get_all_settings()
    assert "wake_word_enabled" in settings
    assert "vad_silence_timeout" in settings
    assert "voice_feedback" in settings
    assert "max_recording_duration" in settings
    assert "interrupt_on_wake" in settings

def test_voice_settings_mutation():
    set_setting("vad_silence_timeout", "1.6")
    set_setting("interrupt_on_wake", "true")
    set_setting("voice_feedback", "false")
    
    settings = get_all_settings()
    assert settings["vad_silence_timeout"] == "1.6"
    assert settings["interrupt_on_wake"] == "true"
    assert settings["voice_feedback"] == "false"
    
    # Reset back to standard defaults
    set_setting("vad_silence_timeout", "1.4")
    set_setting("voice_feedback", "true")
