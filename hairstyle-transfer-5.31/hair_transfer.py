#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发型迁移核心模块
流程：发型参考图 → 创建人脸融合模板 → 融合客户人脸 → (可选)百炼素描转换
"""

import os
import time
import base64
import tempfile
import requests
import cv2
import numpy as np
from typing import Optional, Tuple

from alibabacloud_facebody20191230.client import Client as FaceBodyClient
from alibabacloud_facebody20191230 import models as facebody_models
from alibabacloud_tea_openapi import models as open_api_models

import dashscope
from dashscope import ImageSynthesis
from http import HTTPStatus

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 素描风格 prompt
SKETCH_PROMPTS = {
    'pencil': '将这张照片转换为铅笔素描风格,保持人物五官特征完全清晰,细腻的线条,柔和的阴影',
    'anime': 'Japanese anime style VIBRANT COLORED illustration, clean precise linework with RICH SATURATED ANIME COLORS, meticulously detailed hair with CLEARLY SEPARATED COLORFUL STRANDS, each hair strand showing DISTINCT SPATIAL DEPTH and VIVID COLOR LAYERING, PRONOUNCED spatial sense with colorful foreground and background hair layers, rich saturated anime colors with professional cel-shading technique, exquisite facial features with typical anime aesthetics and SOFT SKIN TONES, large expressive eyes with detailed highlights COLORFUL iris and VIBRANT reflections, elaborate hair texture with DIMENSIONAL COLORED LAYERS clearly visible, professional anime art style with clean BLACK outlines, VIVID MULTI-COLOR PALETTE typical of Japanese animation with BRIGHT HUES, CLEAR DEPTH PERCEPTION with overlapping COLORED hair strands, masterful anime style with SPATIAL HIERARCHY in COLORFUL hair rendering, each hair layer at DIFFERENT DEPTH PLANES with DISTINCT COLORS creating strong effect, COLORFUL SHADING and HIGHLIGHTS throughout the portrait',
    'ink': 'Traditional Chinese SUBTLE COLORED ink wash painting with LIGHT COLOR SATURATION at 30 percent, delicate brushwork with GENTLE COLORED ink strokes in soft muted hues, elegant hair rendering with VISIBLE LAYERED STRANDS showing DEPTH and SPATIAL SEPARATION, each hair layer clearly DISTINCT with spatial sense between layers, SOFT PASTEL COLOR GRADATION with restrained color palette, artistic interpretation with refined LIGHT COLORED strokes, masterful ink wash technique showing hair VOLUME DEPTH and DIMENSIONAL LAYERS, refined facial features with delicate PALE COLORED ink lines, expressive eyes with precise ink detailing, professional Sumi-e style with MUTED SUBTLE COLORS, dynamic hair strokes with natural LIGHT COLORED ink gradation, CLEAR SPATIAL RELATIONSHIPS between hair strands, PRONOUNCED LAYERING EFFECT with foreground middle and background hair clearly separated, GENTLE COLOR TONES throughout',
    'vivid': 'Vibrant colored sketch style with 10 to 30 percent COLOR SATURATION, pencil sketch foundation with SUBTLE COLOR ACCENTS, maintaining clear sketch lines with LIGHT PASTEL COLOR TOUCHES, preserving character features with GENTLE COLOR HINTS, artistic beauty with RESTRAINED COLORFUL ELEMENTS, soft color wash over detailed pencil work, MUTED COLOR PALETTE with delicate hues, sketch texture visible through LIGHT COLOR LAYERS, balanced monochrome and SUBTLE COLOR combination',
}


class HairTransferService:
    """发型迁移服务（人脸融合 + 百炼素描）"""

    def __init__(self):
        ak_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        ak_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        if not ak_id or not ak_secret:
            raise ValueError("请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")

        self.dashscope_key = os.getenv('DASHSCOPE_API_KEY')

        config = open_api_models.Config(
            access_key_id=ak_id,
            access_key_secret=ak_secret,
            endpoint=os.getenv('FACEBODY_ENDPOINT', 'facebody.cn-shanghai.aliyuncs.com')
        )
        self.facebody = FaceBodyClient(config)

    # ──────────────────────────────────────────────
    # 人脸融合
    # ──────────────────────────────────────────────

    def _add_template(self, image_url: str) -> str:
        req = facebody_models.AddFaceImageTemplateRequest(image_url=image_url)
        resp = self.facebody.add_face_image_template(req)
        if not resp.body or not resp.body.data:
            raise RuntimeError("创建模板失败：API 返回数据为空")
        template_id = resp.body.data.template_id
        print(f"✅ 模板创建成功: {template_id}")
        return template_id

    def _merge_face(self, template_id: str, user_image_url: str, model_version: str = 'v1') -> str:
        req = facebody_models.MergeImageFaceRequest(
            template_id=template_id,
            image_url=user_image_url,
            model_version=model_version,
            add_watermark=False
        )
        resp = self.facebody.merge_image_face(req)
        if not resp.body or not resp.body.data:
            raise RuntimeError("人脸融合失败：API 返回数据为空")
        result_url = resp.body.data.image_url
        print(f"✅ 人脸融合成功: {result_url[:60]}...")
        return result_url

    # ──────────────────────────────────────────────
    # 图像下载
    # ──────────────────────────────────────────────

    def _download(self, url: str, save_path: Optional[str] = None) -> np.ndarray:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise RuntimeError("图像解码失败")
        if save_path:
            cv2.imwrite(save_path, img)
            print(f"✅ 图像已保存: {save_path}")
        return img

    # ──────────────────────────────────────────────
    # 百炼素描转换
    # ──────────────────────────────────────────────

    def _sketch(self, local_image: np.ndarray, style: str) -> Optional[np.ndarray]:
        """
        将本地图像（numpy array）转为 base64 后调用百炼素描 API。
        修复说明：人脸融合返回的是阿里云内部 OSS URL，百炼无权访问，
        必须先把融合结果图转为 base64 再传给百炼。
        """
        if not self.dashscope_key:
            print("⚠️  未设置 DASHSCOPE_API_KEY，跳过素描转换")
            return None

        # 写入临时文件 → 读取为 base64
        tmp = os.path.join(tempfile.gettempdir(), f'sketch_input_{int(time.time())}.jpg')
        cv2.imwrite(tmp, local_image)
        with open(tmp, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        image_input = f'data:image/jpeg;base64,{b64}'
        print(f"   图像已转 base64 ({len(b64)//1024}KB)，调用通义万相...")

        prompt = SKETCH_PROMPTS.get(style, SKETCH_PROMPTS['ink'])
        rsp = ImageSynthesis.call(
            api_key=self.dashscope_key,
            model='wan2.5-i2i-preview',
            prompt=prompt,
            images=[image_input],
            negative_prompt='低分辨率,模糊,失真,变形,五官改变',
            n=1,
            watermark=False
        )

        if rsp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"百炼素描失败: {rsp.code} - {rsp.message}")

        sketch_url = rsp.output.results[0].url
        print(f"✅ 素描转换成功: {sketch_url[:60]}...")
        return self._download(sketch_url)

    # ──────────────────────────────────────────────
    # 主流程
    # ──────────────────────────────────────────────

    def transfer(
        self,
        hairstyle_url: str,
        customer_url: str,
        model_version: str = 'v1',
        save_dir: Optional[str] = None,
        enable_sketch: bool = False,
        sketch_style: str = 'ink',
    ) -> Tuple[np.ndarray, dict]:
        """
        发型迁移主流程

        Args:
            hairstyle_url:  发型参考图 OSS URL（完整人像）
            customer_url:   客户照片 OSS URL
            model_version:  v1=脸型适配，v2=非脸型适配
            save_dir:       结果保存目录
            enable_sketch:  是否启用素描效果
            sketch_style:   素描风格 pencil/anime/ink/vivid

        Returns:
            (result_image, info)
        """
        t0 = time.time()
        info = {}

        print("\n" + "="*60)
        print("🚀 开始发型迁移")
        print("="*60)

        # 步骤1：创建模板
        print("\n📋 步骤1: 创建人脸融合模板")
        template_id = self._add_template(hairstyle_url)
        info['template_id'] = template_id

        # 步骤2：人脸融合
        print("\n🎨 步骤2: 人脸融合")
        result_url = self._merge_face(template_id, customer_url, model_version)
        info['result_url'] = result_url

        # 步骤3：下载融合结果
        print("\n💾 步骤3: 下载融合结果")
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f'result_{int(time.time())}.png')
        else:
            save_path = None
        result_image = self._download(result_url, save_path)
        info['save_path'] = save_path

        # 步骤4：素描转换（可选）
        if enable_sketch:
            print(f"\n🎨 步骤4: 素描转换（{sketch_style}）")
            try:
                sketch_image = self._sketch(result_image, sketch_style)
                if sketch_image is not None:
                    result_image = sketch_image
                    if save_path:
                        sketch_path = save_path.replace('.png', '_sketch.png')
                        cv2.imwrite(sketch_path, sketch_image)
                        info['sketch_path'] = sketch_path
                    info['sketch_enabled'] = True
                    info['sketch_style'] = sketch_style
            except Exception as e:
                print(f"⚠️  素描转换失败（返回融合结果）: {e}")
                info['sketch_error'] = str(e)

        info['elapsed_time'] = f"{time.time() - t0:.2f}秒"
        print(f"\n🎉 完成！耗时 {info['elapsed_time']}")
        print("="*60)

        return result_image, info
