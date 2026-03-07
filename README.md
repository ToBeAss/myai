# myai
My personal AI assistant

> Looking for architecture, feature breakdowns, or optimization notes? Start with [`docs/system_overview.md`](docs/system_overview.md). Detailed legacy write-ups now live under [`docs/archive/`](docs/archive/ARCHIVE_INDEX.md).

## Installation Instructions

### Prerequisites:

- *[List required software or dependencies, e.g., Node.js, Java, Docker, etc.]*
- Python 3.13.2

### Steps:
1. **Clone the repository**
   ```bash
   git clone https://github.com/ToBeAss/myai.git
   ```
2. **Create a virtual environment**
   > Creating a Python virtual environment allows you to manage dependencies separately for different projects, preventing conflicts and maintaining cleaner setups. [Real Python, 2024](https://realpython.com/python-virtual-environments-a-primer/)

    ```bash
    python -m venv venv
    ```
    > For **macOS** you may need to use `python3 -m venv venv`.
3. **Activate the virtual environment**

    * **Windows (Command Prompt)**
        ```bash
        venv\Scripts\activate
        ```
    * **macOS**
        ```bash
        source venv/bin/activate
        ```
4. **Install dependencies**
    ```bash
    pip install -e ".[dev]"
    ```
    > For **macOS** you may need to use `pip3 install -e ".[dev]"`.

    This installs runtime dependencies from `requirements.txt` and development tools
    (such as `pytest`) from `pyproject.toml`.
5. **Create the `.env` file**
    
    Copy the `.env.example` file and rename it `.env`:

    * **Windows (Command Prompt)**
        ```bash
        copy .env.example .env
        ```
    * **macOS**
        ```bash
        cp .env.example .env
        ```
    Open the `.env` file and insert the API keys.

> [!WARNING]
> The `.env` file is used to store sensitive information like API keys and database credentials securely. Make sure not to commit it to version control by adding `.env` to your `.gitignore` file.

## 🚀 Performance Optimizations

This voice assistant is **highly optimized** for low-latency responses:

### ⚡ Chunked Transcription (NEW!)
Transcribes speech in parallel chunks while you continue speaking.
- **300-1200ms faster** response time for multi-phrase commands
- Automatically enabled in `main_continuous.py`
- See the quick overview in [`docs/system_overview.md`](docs/system_overview.md) and the archived deep dive in [`docs/archive/CHUNKED_TRANSCRIPTION_QUICKREF.md`](docs/archive/CHUNKED_TRANSCRIPTION_QUICKREF.md)

### 🎯 Other Optimizations
- **faster-whisper**: 4-5x faster transcription with CTranslate2
- **Dynamic silence detection**: Adaptive thresholds (750-1250ms)
- **Comma-based TTS chunking**: Synthesis starts at natural pauses
- **Parallel processing**: TTS synthesis and playback in separate threads

**Combined result**: ~2-3 seconds faster than baseline! 🎉

For configuration specifics, see [`docs/system_overview.md`](docs/system_overview.md) and the archived reference [`docs/archive/LATENCY_OPTIMIZATION_SETTINGS.md`](docs/archive/LATENCY_OPTIMIZATION_SETTINGS.md)

## Environment Management
* **Deactivate the virtual environment** (when done)
    ```bash
    deactivate
    ```
* **Run tests**
    ```bash
    python -m pytest
    ```
    By default, interactive/manual scripts are excluded from this run.
* **(Optional) Export Installed Packages**
    
    If you add new dependencies, update the `requirements.txt`:
    ```bash
    pip freeze > requirements.txt
    ```