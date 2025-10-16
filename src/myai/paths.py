"""Project-level path helpers."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"
PROMPTS_DIR = REPO_ROOT / "prompts"
TESTS_DIR = REPO_ROOT / "tests"


def data_file(name: str) -> Path:
    """Return the path for a file stored under the shared data directory."""
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / name
