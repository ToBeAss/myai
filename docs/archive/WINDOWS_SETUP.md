# Windows Setup Guide

## Issue Fixed ✅

The original `requirements.txt` contained **macOS-only packages** (`pyobjc` and related frameworks) that prevented installation on Windows. These have been removed since they are not used in the codebase.

## Changes Made

1. **Removed PyObjC packages** (154 packages removed) - these are macOS-specific UI frameworks
2. **Removed uvloop** - version 0.21.0 doesn't support Windows (it's not actually imported in the code)

## Installation Instructions for Windows

### Prerequisites

- Python 3.13.2 (or compatible version)
- Windows 10/11

### Steps

1. **Clone the repository**
   ```powershell
   git clone https://github.com/ToBeAss/myai.git
   cd myai
   ```

2. **Create a virtual environment**
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment**
   ```powershell
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```
   
   > ✅ **All dependencies now install successfully on Windows!**

5. **Create the `.env` file**
   
   Copy the `.env.example` file and rename it `.env`:
   ```powershell
   copy .env.example .env
   ```
   
   Open the `.env` file and insert your API keys:
   - `OPENAI_API_KEY` - for OpenAI GPT models
   - `GOOGLE_APPLICATION_CREDENTIALS` - path to your Google Cloud TTS credentials JSON

## Audio Requirements

The assistant uses the following audio libraries (all cross-platform):
- **PyAudio** - for microphone input ✅ Works on Windows
- **pygame** - for audio playback ✅ Works on Windows
- **simpleaudio** - alternative audio playback ✅ Works on Windows

> **Note**: If you encounter audio issues, ensure your microphone is properly configured in Windows settings.

## Running the Assistant

Once installed, you can run the assistant with:

```powershell
python main.py
```

Or for continuous listening mode:

```powershell
python main_continuous.py
```

## Troubleshooting

### Issue: "PyObjC requires macOS to build"
**Solution**: This has been fixed in the current `requirements.txt`. If you still see this error, make sure you've pulled the latest changes.

### Issue: Audio not working
**Solution**: 
1. Check Windows microphone permissions
2. Verify your default audio devices in Windows Settings
3. Try running as administrator if microphone access is denied

### Issue: Google Cloud TTS errors
**Solution**: 
1. Ensure `GOOGLE_APPLICATION_CREDENTIALS` in `.env` points to a valid JSON credentials file
2. Verify the file path uses forward slashes or escaped backslashes
3. Example: `GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/credentials.json`

## What Was Removed

The following macOS-only packages were removed (not used in the codebase):
- `pyobjc` and `pyobjc-core`
- 152 `pyobjc-framework-*` packages (Cocoa, AppKit, AVFoundation, etc.)
- `uvloop==0.21.0` (Windows incompatible; not imported in code)

These packages are only needed for macOS GUI applications and are not required for this voice assistant.

## Contributing

If you need to update `requirements.txt` in the future, please:
1. Use platform-specific requirements if needed
2. Test on both macOS and Windows before committing
3. Document any platform-specific dependencies

## Need Help?

- Check the main [README.md](README.md) for general setup
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if available
- Open an issue on GitHub with error logs
