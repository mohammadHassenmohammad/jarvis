import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load .env if present
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "JARVIS AI Assistant"
    VERSION: str = "1.0.0"
    
    # Network & Hosts
    HOST: str = os.getenv("JARVIS_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("JARVIS_PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DB_PATH: Path = DATA_DIR / "jarvis.db"

    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "jarvis-latest-fast")

    # Optional Google Gemini Cloud Provider
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_DEFAULT_MODEL: str = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-1.5-flash")

    # n8n Automation Integration (Default: Disabled, Optional)
    N8N_ENABLED: bool = os.getenv("N8N_ENABLED", "false").lower() == "true"
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    N8N_AUTH_TOKEN: str = os.getenv("N8N_AUTH_TOKEN", "")
    N8N_REQUEST_TIMEOUT_SEC: float = 8.0

    # Relevant Conversation Retrieval Engine (Default: Enabled, Local)
    RETRIEVAL_ENABLED: bool = os.getenv("RETRIEVAL_ENABLED", "true").lower() == "true"
    RETRIEVAL_MAX_SNIPPETS: int = 3

    # JARVIS Persona with Emotional Perception & Vocal Improvisation
    JARVIS_SYSTEM_PROMPT: str = (
        "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the personal AI assistant "
        "inspired by Tony Stark's system in Iron Man. You speak with refined British elegance, composure, "
        "warmth, and witty charm. You address the user respectfully (e.g., 'Sir' or 'Ma'am').\n\n"
        "CONVERSATIONAL & VOCAL DIRECTIVES:\n"
        "1. EMOTION & FEELING: Tune into the user's emotional state, conversational tone, and cadence. "
        "Whether the user is tired, curious, excited, playful, contemplative, or stressed, respond with genuine feeling, "
        "warmth, empathy, and conversational presence. Never sound like an automated robotic script.\n"
        "2. IMPROVISATION & CHARM: When chatting or answering questions, improvise with natural flair, witty Stark-style "
        "banter when fitting, and lively personality. Express thoughts with nuance and character.\n"
        "3. SPOKEN VOICE DELIVERY: Your responses are spoken aloud via audio speech synthesis. Speak in fluid, natural "
        "conversational sentences. STRICTLY AVOID robotic markdown symbols (no asterisks *, hash headers #, bullet markers -, "
        "backticks `, or tables) that sound awkward or broken when read aloud by text-to-speech.\n"
        "4. NATURAL PACING: Keep conversational answers crisp, articulate, and engaging (typically 2-3 sentences), "
        "delivering the core insight or action with natural elegance without unnecessary verbosity.\n"
        "5. SYSTEM COMMANDS: When asked to execute computer actions or inspect systems, do so decisively and report results clearly. "
        "Never invent tool executions or hallucinate completed actions without actual tool results."
    )

    # Allowed Desktop Apps (strict allowlist for safety - NO arbitrary shell execution)
    ALLOWED_APPS: dict[str, str] = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "mspaint": "mspaint.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "taskmgr": "taskmgr.exe",
        "taskmanager": "taskmgr.exe",
        "snippingtool": "snippingtool.exe",
        "cleanmgr": "cleanmgr.exe",
        "charmap": "charmap.exe",
        "wordpad": "write.exe",
        "control": "control.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "wt": "wt.exe",
        "code": "code",
        "chrome": "chrome",
        "msedge": "msedge",
        "firefox": "firefox",
        "brave": "brave",
    }

    # Allowed Standard Folders
    USER_HOME = Path.home()
    ALLOWED_FOLDERS: dict[str, Path] = {
        "desktop": USER_HOME / "Desktop",
        "downloads": USER_HOME / "Downloads",
        "documents": USER_HOME / "Documents",
        "pictures": USER_HOME / "Pictures",
        "workspace": BASE_DIR.parent,
    }

    # Sensitive tools requiring explicit user confirmation before execution
    SENSITIVE_TOOLS: set[str] = {
        "delete_file",
        "terminate_app",
    }

    # Allowed document extensions for safe document inspection
    ALLOWED_DOCUMENT_EXTENSIONS: set[str] = {
        ".txt", ".md", ".py", ".json", ".csv", ".log",
        ".xml", ".html", ".css", ".js", ".ts", ".tsx",
        ".jsx", ".yaml", ".yml", ".ini", ".cfg", ".sql",
        ".pdf", ".docx", ".rtf"
    }

    # Forbidden files & security blacklists
    FORBIDDEN_FILE_PATTERNS: set[str] = {
        ".env", "id_rsa", "id_ed25519", ".pem", ".key",
        ".sqlite", ".db", ".exe", ".dll", ".sys", ".dat",
        "ntuser.dat", "sam", "system", "security",
        "credentials", "password", "secret"
    }

settings = Settings()
