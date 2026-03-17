# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Flask-based AI hairstyle transfer web application** that uses Alibaba Cloud APIs (Bailian/DashScope) to apply hairstyles from reference images to customer photos. The app supports hair extraction preview, face fusion, and sketch-style artistic conversion.

## Commands

### Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env to add your BAILIAN_API_KEY
```

### Running the Application

```bash
# Method 1: Using start script (checks env vars)
./start.sh

# Method 2: Direct run
python app.py

# Access: http://localhost:5002
```

### Key Environment Variables

```bash
# Required for production mode
export BAILIAN_API_KEY='sk-xxxxx'

# Required for hair extraction feature (Aliyun)
export ALIBABA_CLOUD_ACCESS_KEY_ID='your-key-id'
export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-key-secret'
```

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `app.py` | Flask主应用 - routes: `/`, `/api/extract-hair`, `/api/transfer` |
| `bailian_image2image.py` | 百炼图生图 API 调用 - wan2.5-i2i-preview 模型 |
| `hair_segmentation.py` | 头发分割 API - SegmentHair 提取透明背景发型 |
| `sketch_converter.py` | OpenCV 素描转换 (备用方案) |
| `bailian_sketch_converter.py` | 百炼素描转换 (主方案) |
| `image_preprocessor.py` | 图像预处理 - 尺寸调整/压缩 |
| `oss_upload_complete.py` | OSS 上传模块 - 获取公网 URL |

### API Flow

```
1. User uploads hairstyle reference + customer photo
2. Images uploaded to OSS → public URLs
3. Hairstyle extraction (optional): HairSegmentation.segment_hair()
4. Hair transfer: BailianImage2ImageHairTransfer.transfer_hair()
   - Uses wan2.5-i2i-preview model
   - Async task polling (~60-120s)
5. Sketch conversion (optional): bailian_sketch_converter or sketch_converter
6. Result returned to frontend
```

### Key Classes

- `BailianImage2ImageHairTransfer` - Main hair transfer service (bailian_image2image.py)
- `HairSegmentation` - Hair extraction service (hair_segmentation.py)
- `AliyunHairTransferFixed` - Combined service (aliyun_hair_transfer_fixed.py)

### Frontend

Single-page app in `templates/index.html`:
- Image upload with preview
- Parameter controls (strength, sketch style)
- Real-time status updates
- Result display with zoom

### Configuration Notes

- **Port**: 5002
- **Upload limit**: 20MB
- **Supported formats**: PNG, JPG, JPEG
- **Image requirements**: 384x384 ~ 1024x1024 for API

### API Costs (参考)

- Hair segmentation: ~0.0025 CNY/call
- Face fusion: ~0.0025 CNY/call
- Sketch conversion: ~0.08 CNY/call
