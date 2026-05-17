# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

## Project overview

Flask web app for AI-powered hairstyle transfer using Alibaba Cloud APIs (face fusion, hair segmentation, DashScope image-to-image). Python 3.10+.

## Essential commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in API keys

# Run
python app.py          # serves on http://localhost:5002
./start.sh             # same, but checks env vars first
```

## Required environment variables

Set via `.env` file or shell:

- `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` — required for face fusion & hair segmentation
- `DASHSCOPE_API_KEY` — required for sketch conversion (optional, feature disabled if absent)

## Architecture

- `app.py` — Flask routes, file upload/save/OSS logic, serves on port **5002**
- `hair_transfer.py` — `HairTransferService`: face template creation → face fusion → optional sketch via DashScope `wan2.5-i2i-preview`

## Key gotchas

- **DashScope URL**: set to `https://dashscope.aliyuncs.com/api/v1` (hardcoded in `hair_transfer.py`)
- **Face fusion returns internal OSS URLs** that DashScope cannot access — the sketch converter must receive the image as base64, not as a URL (already fixed in code)
- **Images are auto-resized** to max 2000px / 3MB on upload in `_save_upload()`
- **No tests exist** — this is a small 2-file project
- **Port 5002** is hardcoded in `app.py`
- **Debug mode is OFF** (`debug=False`)

## Git / PR conventions

- Single branch: `main`
- Chinese commit messages are used in this repo
