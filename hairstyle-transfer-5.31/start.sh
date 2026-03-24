#!/bin/bash
# 发型迁移系统 - 启动脚本

echo "=========================================="
echo "  💇 发型迁移系统"
echo "=========================================="
echo ""

# 检查必要环境变量
if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] || [ -z "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ]; then
    echo "❌ 缺少阿里云 AccessKey，请先执行:"
    echo ""
    echo "  export ALIBABA_CLOUD_ACCESS_KEY_ID='你的 AccessKey ID'"
    echo "  export ALIBABA_CLOUD_ACCESS_KEY_SECRET='你的 AccessKey Secret'"
    echo "  export DASHSCOPE_API_KEY='你的 DashScope Key'  # 素描功能需要"
    echo ""
    exit 1
fi

echo "✅ AccessKey 已配置"
[ -n "$DASHSCOPE_API_KEY" ] && echo "✅ DashScope Key 已配置（素描功能可用）" || echo "⚠️  未配置 DASHSCOPE_API_KEY（素描功能不可用）"
echo ""
echo "📍 访问地址: http://localhost:5002"
echo "📍 按 Ctrl+C 停止服务"
echo ""

python3 app.py
