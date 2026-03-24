#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发型迁移系统 - Flask 主应用
"""

import os
import sys
import uuid
import oss2
import cv2
import requests as req_lib
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from alibabacloud_imageseg20191230.client import Client as ImagesegClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_imageseg20191230 import models as imageseg_models
from alibabacloud_tea_util import models as util_models

from hair_transfer import HairTransferService

# ──────────────────────────────────────────────
# 应用配置
# ──────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB

UPLOAD_DIR = 'static/uploads'
RESULT_DIR = 'static/results'
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'bmp'}

OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'oss-cn-shanghai.aliyuncs.com')
OSS_BUCKET   = os.getenv('OSS_BUCKET', 'hair-transfer-bucket')

HAIR_EXTRACTED_DIR = 'static/hair_extracted'

for d in (UPLOAD_DIR, RESULT_DIR, HAIR_EXTRACTED_DIR):
    os.makedirs(d, exist_ok=True)


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _save_upload(file, prefix: str) -> str:
    """保存上传文件，自动压缩超过 3MB 或分辨率超过 2000px 的图片。"""
    if not file or not _allowed(file.filename):
        raise ValueError("不支持的文件格式，请上传 PNG/JPG/BMP")

    ext = file.filename.rsplit('.', 1)[1].lower()
    path = os.path.join(UPLOAD_DIR, f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}")
    file.save(path)

    # 自动预处理：限制分辨率 ≤ 2000px，文件大小 ≤ 3MB
    img = cv2.imread(path)
    if img is not None:
        h, w = img.shape[:2]
        if max(h, w) > 2000:
            scale = 2000 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        elif os.path.getsize(path) > 3 * 1024 * 1024:
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])

    return path


def _upload_oss(local_path: str) -> str:
    """上传本地文件到 OSS，返回公网 URL。"""
    ak_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    ak_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    if not ak_id or not ak_secret:
        raise ValueError("未设置阿里云 AccessKey 环境变量")

    auth = oss2.Auth(ak_id, ak_secret)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)

    ext = os.path.splitext(local_path)[1]
    obj = f"hairstyle-transfer/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}{ext}"

    result = bucket.put_object_from_file(obj, local_path)
    if result.status != 200:
        raise RuntimeError(f"OSS 上传失败: HTTP {result.status}")

    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{obj}"
    print(f"✅ OSS 上传成功: {url}")
    return url


# ──────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/transfer', methods=['POST'])
def transfer():
    """发型迁移接口"""
    try:
        # 参数校验
        if 'customer_image' not in request.files:
            return jsonify({'error': '缺少客户照片'}), 400
        original_hair_url = request.form.get('original_hair_url')
        if not original_hair_url:
            return jsonify({'error': '缺少发型参考图'}), 400

        # 保存客户照片
        customer_path = _save_upload(request.files['customer_image'], 'customer')

        # 定位发型参考图本地路径
        hairstyle_path = os.path.join(UPLOAD_DIR, original_hair_url.split('/')[-1])
        if not os.path.exists(hairstyle_path):
            return jsonify({'error': '发型参考图不存在，请重新上传'}), 400

        # 上传到 OSS
        hairstyle_oss_url = _upload_oss(hairstyle_path)
        customer_oss_url  = _upload_oss(customer_path)

        # 读取请求参数
        model_version  = request.form.get('model_version', 'v1')
        enable_sketch  = request.form.get('enable_sketch', 'false').lower() == 'true'
        sketch_style   = request.form.get('sketch_style', 'ink')

        # 执行发型迁移
        service = HairTransferService()
        result_image, info = service.transfer(
            hairstyle_url=hairstyle_oss_url,
            customer_url=customer_oss_url,
            model_version=model_version,
            save_dir=RESULT_DIR,
            enable_sketch=enable_sketch,
            sketch_style=sketch_style,
        )

        result_filename = os.path.basename(info['save_path'])
        resp = {
            'success': True,
            'result_url': f'/static/results/{result_filename}',
            'info': {
                'elapsed_time': info['elapsed_time'],
                'template_id': info.get('template_id'),
                'model_version': model_version,
            }
        }

        if enable_sketch and 'sketch_path' in info:
            resp['sketch_url'] = f"/static/results/{os.path.basename(info['sketch_path'])}"
            resp['info']['sketch_style'] = sketch_style

        return jsonify(resp)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract-hair', methods=['POST'])
def extract_hair():
    """发型提取接口：上传发型参考图，返回原图URL和提取的发型URL"""
    try:
        if 'hairstyle_image' not in request.files:
            return jsonify({'success': False, 'message': '缺少发型参考图'}), 400

        # 保存原图
        path = _save_upload(request.files['hairstyle_image'], 'hairstyle')
        original_url = f'/static/uploads/{os.path.basename(path)}'

        # 上传到 OSS 获取公网 URL（头发分割 API 需要公网地址）
        oss_url = _upload_oss(path)

        # 调用阿里云头发分割 API
        ak_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        ak_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        config = open_api_models.Config(
            access_key_id=ak_id,
            access_key_secret=ak_secret,
            endpoint=os.getenv('IMAGESEG_ENDPOINT', 'imageseg.cn-shanghai.aliyuncs.com')
        )
        client = ImagesegClient(config)
        seg_req = imageseg_models.SegmentHairRequest(image_url=oss_url)
        resp = client.segment_hair_with_options(seg_req, util_models.RuntimeOptions())

        if not (resp.body.data and resp.body.data.elements):
            return jsonify({'success': False, 'message': '头发分割 API 返回数据为空'}), 500

        hair_url_remote = resp.body.data.elements[0].image_url

        # 下载发型图到本地
        dl = req_lib.get(hair_url_remote, timeout=30)
        dl.raise_for_status()
        hair_filename = f"hair_{uuid.uuid4().hex[:8]}.png"
        hair_path = os.path.join(HAIR_EXTRACTED_DIR, hair_filename)
        with open(hair_path, 'wb') as f:
            f.write(dl.content)

        return jsonify({
            'success': True,
            'original_url': original_url,
            'extracted_url': f'/static/hair_extracted/{hair_filename}',
        })

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/upload-hairstyle', methods=['POST'])
def upload_hairstyle():
    """上传发型参考图（预览用）"""
    try:
        if 'hairstyle_image' not in request.files:
            return jsonify({'error': '缺少发型参考图'}), 400
        path = _save_upload(request.files['hairstyle_image'], 'hairstyle')
        return jsonify({
            'success': True,
            'original_url': f'/static/uploads/{os.path.basename(path)}',
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health():
    """健康检查"""
    ok = bool(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')) and \
         bool(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET'))
    return jsonify({
        'status': 'ok' if ok else 'warning',
        'message': '服务正常' if ok else '请配置 AccessKey 环境变量',
        'dashscope_configured': bool(os.getenv('DASHSCOPE_API_KEY')),
    })


# ──────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 发型迁移系统")
    print("="*60)

    if not os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'):
        print("❌ 未设置 ALIBABA_CLOUD_ACCESS_KEY_ID，请先配置环境变量后启动")
        sys.exit(1)

    print(f"✅ AccessKey: {os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')[:8]}...")
    print(f"✅ DashScope: {'已配置' if os.getenv('DASHSCOPE_API_KEY') else '未配置（素描功能不可用）'}")
    print("📍 访问地址: http://localhost:5002\n")

    app.run(host='0.0.0.0', port=5002, debug=False)
