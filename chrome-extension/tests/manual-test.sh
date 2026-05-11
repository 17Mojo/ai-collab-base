#!/bin/bash
# 真实Chrome手动测试脚本

EXTENSION_PATH="/Users/raymondna/Documents/ai-collab-system/chrome-extension"
USER_DIR="/tmp/prompt-pack-manual-test-$(date +%s)"

echo "=========================================="
echo "  Prompt Pack - 真实Chrome手动测试"
echo "=========================================="
echo ""
echo "扩展路径: $EXTENSION_PATH"
echo "用户目录: $USER_DIR"
echo ""

# 清理
rm -rf "$USER_DIR" 2>/dev/null

# 启动Chrome
echo "启动Chrome..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$USER_DIR" \
  --disable-extensions-except="$EXTENSION_PATH" \
  --load-extension="$EXTENSION_PATH" \
  "https://kimi.com" \
  "chrome://extensions" &

CHROME_PID=$!

echo ""
echo "Chrome已启动 (PID: $CHROME_PID)"
echo ""
echo "=========================================="
echo "  请按以下步骤操作："
echo "=========================================="
echo ""
echo "步骤1: 检查扩展加载"
echo "  - 在chrome://extensions标签页"
echo "  - 确认'Prompt Pack'扩展已启用"
echo "  - 点击'Service Worker'链接打开DevTools"
echo ""
echo "步骤2: 在Kimi页面测试"
echo "  - 切换到Kimi标签页"
echo "  - 打开DevTools (F12或Cmd+Option+I)"
echo "  - 在Console中执行以下代码:"
echo ""
echo "---"
cat << 'EOF'
window.postMessage({
  type: 'PROMPT_PACK_TEST',
  prompt: '你好，请简短回答：AI是什么？',
  config: { soulProfile: 'luoyonghao', timeout: 60000 }
}, '*');
EOF
echo "---"
echo ""
echo "步骤3: 观察结果"
echo "  - Service Worker DevTools: 查看后台日志"
echo "  - Kimi Console: 查看测试结果"
echo "  - Kimi页面: 观察是否自动注入提示词"
echo ""
echo "=========================================="
echo ""
echo "等待180秒后自动关闭..."
echo ""

sleep 180

echo "关闭Chrome..."
kill $CHROME_PID 2>/dev/null
rm -rf "$USER_DIR" 2>/dev/null

echo "测试完成"