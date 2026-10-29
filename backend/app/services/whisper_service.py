import io
import os
import re
import tempfile
import av

# PyAV 14+ compatibility patch for faster-whisper (removes deprecated metadata_errors kwarg)
_orig_av_open = av.open
def _safe_av_open(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _orig_av_open(*args, **kwargs)
av.open = _safe_av_open

from faster_whisper import WhisperModel

WHISPER_SYSTEM_PROMPT = (
    "J.A.R.V.I.S., Sir, Fayaz, Md Fayaz, Mohammed Fayaz, Fowzia, ChatGPT, OpenAI, Tony Stark, Stark Industries, "
    "Python, YouTube, GitHub, VS Code, PowerShell, Ollama, weather, system, voice mode, start, stop, listen."
)

PHANTOM_ARTIFACTS = [
    re.compile(r"\[.*?\]", re.IGNORECASE),
    re.compile(r"\(.*?\)", re.IGNORECASE),
    re.compile(r"thank you for watching.*", re.IGNORECASE),
    re.compile(r"please subscribe.*", re.IGNORECASE),
    re.compile(r"subtitles by.*", re.IGNORECASE),
    re.compile(r"you're watching.*", re.IGNORECASE),
]

PHONETIC_CORRECTIONS = [
    # User and family name acoustic grasping corrections
    (re.compile(r"\b(md|mohammed|mohd)?\s*(fiaz|faiaz|fayas|fayaas|fire us|fire as|phiyaz|faiyaz|fayoz|fayez)\b", re.IGNORECASE), "Fayaz"),
    (re.compile(r"\b(fauzia|fouzia|fauziya|fawzia|fawziya|fauza|fauja|phauzia)\b", re.IGNORECASE), "Fowzia"),
    
    # AI and STT corrections
    (re.compile(r"\b(chat\s*gpt|charge\s*gpt|chat\s*jpt|chat\s*gbt|chatgpt)\b", re.IGNORECASE), "ChatGPT"),
    (re.compile(r"\bwsiper\b", re.IGNORECASE), "whisper"),
    (re.compile(r"\bwisper\b", re.IGNORECASE), "whisper"),
    (re.compile(r"\bvesper\b", re.IGNORECASE), "whisper"),
    (re.compile(r"\b(javis|travis|charvis|jarviss|javice)\b", re.IGNORECASE), "Jarvis"),
    (re.compile(r"\bo\s*llama\b", re.IGNORECASE), "Ollama"),
    (re.compile(r"\bi satr\b", re.IGNORECASE), "I start"),
    (re.compile(r"\bi satrt\b", re.IGNORECASE), "I start"),
    (re.compile(r"\bi start talking\b", re.IGNORECASE), "I start talking"),
    (re.compile(r"\bwhat('?s)? the whether\b", re.IGNORECASE), "what's the weather"),
]

class WhisperService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            print(f"[*] Initializing local Whisper model ({self.model_size})...")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print(f"[+] Local Whisper model ({self.model_size}) ready for high-fidelity speech recognition.")
        return self._model

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribes audio bytes into text using local Whisper.
        Supports webm, wav, mp3, ogg via PyAV.
        Preserves initial spoken words with speech padding and vocabulary biasing.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        model = self._get_model()

        suffix = os.path.splitext(filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # We use vad_filter=False because audio is already cleanly gated by frontend VAD
            # and vad_filter can aggressively clip short utterances or first words.
            segments, info = model.transcribe(
                tmp_path,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2],
                language="en",
                initial_prompt=WHISPER_SYSTEM_PROMPT,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            raw_transcription = " ".join(segment.text.strip() for segment in segments).strip()

            cleaned = raw_transcription
            for pat in PHANTOM_ARTIFACTS:
                cleaned = pat.sub("", cleaned).strip()

            for pat, repl in PHONETIC_CORRECTIONS:
                cleaned = pat.sub(repl, cleaned)

            cleaned = cleaned.strip()
            # Capitalize first character
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:]

            return cleaned
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

whisper_service = WhisperService()
