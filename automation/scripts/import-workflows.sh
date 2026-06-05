#!/bin/bash
# ============================================
# 股小智 · n8n 工作流批量导入脚本
# 用法: N8N_API_KEY=xxx bash import-workflows.sh
# ============================================

N8N_HOST="${N8N_HOST:-http://localhost:5678}"
API_KEY="${N8N_API_KEY}"

if [ -z "$API_KEY" ]; then
    echo "❌ 请设置环境变量 N8N_API_KEY"
    echo "获取方式: n8n Settings → API → Create API Key"
    exit 1
fi

WORKFLOWS_DIR="$(dirname "$0")/../workflows"

echo "🚀 开始导入工作流到 $N8N_HOST"
echo "================================"

for file in "$WORKFLOWS_DIR"/*.json; do
    if [ -f "$file" ]; then
        name=$(basename "$file" .json)
        echo "📥 导入: $name"
        
        response=$(curl -s -w "\n%{http_code}" \
            -X POST "$N8N_HOST/api/v1/workflows" \
            -H "X-N8N-API-KEY: $API_KEY" \
            -H "Content-Type: application/json" \
            -d @$file)
        
        http_code=$(echo "$response" | tail -n1)
        
        if [ "$http_code" = "200" ]; then
            echo "  ✅ 成功"
        else
            echo "  ❌ 失败 (HTTP $http_code)"
            echo "$response" | head -n -1
        fi
    fi
done

echo "================================"
echo "🎉 导入完成！请访问 $N8N_HOST 查看工作流"