# 发型迁移系统 (Hairstyle Transfer)

基于阿里云百炼和通义千问 AI 的发型迁移 Web 应用，支持人脸融合和素描风格转换功能。

## 功能特性

- **人脸融合**：将发型参考图的发型迁移到客户照片上
- **素描转换**：支持多种素描风格（铅笔/动漫/水墨/彩色）
- **发型提取**：从发型参考图中提取纯发型区域
- **Web 界面**：简洁易用的上传和预览界面
- **自动优化**：上传的图片自动压缩和分辨率优化

## 技术栈

- **后端**：Python 3.10+ / Flask 2.3+
- **AI 服务**：
  - 阿里云百炼 (DashScope) - 通义万相图像生成
  - 阿里云人脸融合 API
  - 阿里云头发分割 API
- **图像处理**：OpenCV / NumPy / Pillow

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量配置并填写：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 阿里云 AccessKey（必填）
ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret

# 百炼 DashScope API Key（素描功能必填）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OSS 配置（可选，默认值已内置）
# OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
# OSS_BUCKET=hair-transfer-bucket
```

### 3. 启动服务

```bash
# 方式一：直接运行
python app.py

# 方式二：使用启动脚本
./start.sh
```

访问 http://localhost:5002

## 目录结构

```
hairstyle-transfer-5.31/
├── app.py              # Flask 主应用
├── hair_transfer.py    # 发型迁移核心服务
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量示例
├── start.sh            # 启动脚本
├── static/             # 静态资源
│   ├── uploads/        # 上传文件目录
│   ├── results/        # 结果图片目录
│   └── hair_extracted/ # 提取的发型目录
└── templates/          # HTML 模板
    └── index.html      # 主页面
```

## API 接口

### POST /api/transfer
发型迁移接口

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| customer_image | File | 是 | 客户照片 |
| original_hair_url | String | 是 | 发型参考图 URL |
| model_version | String | 否 | v1=脸型适配，v2=非脸型适配（默认 v1） |
| enable_sketch | String | 否 | 是否启用素描效果（true/false，默认 false） |
| sketch_style | String | 否 | 素描风格：pencil/anime/ink/vivid（默认 ink） |

### POST /api/extract-hair
发型提取接口

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hairstyle_image | File | 是 | 发型参考图 |

### POST /api/upload-hairstyle
上传发型参考图（预览用）

### GET /api/health
健康检查接口

## 素描风格说明

| 风格 | 说明 |
|------|------|
| `pencil` | 铅笔素描风格，细腻线条，柔和阴影 |
| `anime` | 日系动漫风格，鲜艳色彩，清晰发丝层次 |
| `ink` | 中国传统水墨风格，淡雅色彩，艺术笔触 |
| `vivid` | 鲜艳彩色素描，10-30% 色彩饱和度 |

## 注意事项

1. **图片格式**：支持 PNG、JPG、JPEG、BMP 格式
2. **文件大小**：最大支持 20MB
3. **自动优化**：超过 3MB 或分辨率超过 2000px 的图片会自动压缩
4. **API 密钥**：请妥善保管阿里云 AccessKey，不要提交到代码仓库

## 相关服务

- [阿里云百炼控制台](https://dashscope.console.aliyun.com/)
- [阿里云 AccessKey 管理](https://ram.console.aliyun.com/manage/ak)

## License

MIT License
