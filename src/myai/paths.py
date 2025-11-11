"""Project-level path helpers."""
from pathlib import Path
import uuid


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = _ensure_dir(REPO_ROOT / "data")
PROMPTS_DIR = REPO_ROOT / "prompts"
TESTS_DIR = REPO_ROOT / "tests"
TMP_AUDIO_DIR = DATA_DIR / "tmp_audio"


def data_file(name: str) -> Path:
    """Return the path for a file stored under the shared data directory."""
    return DATA_DIR / name


def ensure_tmp_audio_dir() -> Path:
    """Ensure and return the directory used for temporary audio artifacts."""
    return _ensure_dir(TMP_AUDIO_DIR)


def unique_tmp_audio_file(prefix: str, suffix: str = ".wav") -> Path:
    """Generate a unique path inside the temporary audio directory."""
    directory = ensure_tmp_audio_dir()
    return directory / f"{prefix}_{uuid.uuid4().hex}{suffix}"
