#!/bin/bash

echo "=== 启动 Stripe CLI Webhook 监听 ==="
echo "转发到: http://localhost:3000/api/stripe/webhook"
echo "请确保你的 Next.js 前端正在 localhost:3000 运行"
echo "请确保你的后端服务正在 localhost:8100 运行"
echo ""
echo "按 Ctrl+C 停止监听"
echo ""

# 启动 Stripe CLI 监听
stripe listen --forward-to localhost:3000/api/stripe/webhook