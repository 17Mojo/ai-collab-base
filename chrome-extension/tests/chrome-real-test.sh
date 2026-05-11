#!/bin/bash
# 真实Chrome测试脚本 - 使用系统Chrome加载扩展并测试

EXTENSION_PATH="/Users/raymondna/Documents/ai-collab-system/chrome-extension"
USER_DIR="/tmp/prompt-pack-chrome-test-$(date +%s)"

echo "=== 真实Chrome测试 ==="
echo "扩展路径: $EXTENSION_PATH"
echo "用户目录: $USER_DIR"

# 清理旧目录
rm -rf "$USER_DIR"

# 启动Chrome（带扩展）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$USER_DIR" \
  --disable-extensions-except="$EXTENSION_PATH" \
  --load-extension="$EXTENSION_PATH" \
  --auto-open-devtools-for-tabs \
  "https://kimi.com" \
  "chrome://extensions" &

CHROME_PID=$!
echo "Chrome PID: $CHROME_PID"

echo ""
echo "Chrome已启动，请："
echo "1. 在chrome://extensions页面找到 'Prompt Pack' 扩展"
echo "2. 点击 'Service Worker' 链接打开DevTools"
echo "3. 在Service Worker DevTools的Console中查看日志"
echo "4. 在Kimi页面的Console中执行测试代码："
echo ""
echo "window.postMessage({"
echo "  type: 'PROMPT_PACK_TEST',"
echo "  prompt: '人工智能对教育的影响',"
echo "  config: { soulProfile: 'luoyonghao', timeout: 90000 }"
echo "}, '*');"
echo ""
echo "浏览器保持打开 180 秒..."
sleep 180

echo "关闭Chrome..."
kill $CHROME_PID 2>/dev/null || true
rm -rf "$USER_DIR"

echo "测试完成"