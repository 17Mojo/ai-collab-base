#!/bin/bash

# GUI 直播演示脚本
# 用于启动 Playwright 浏览器直播演示

echo "============================================================"
echo "Playwright GUI 直播演示"
echo "============================================================"
echo ""

# 创建截图目录
mkdir -p demo-screenshots

# 检查参数
MODE=${1:-"headed"}  # 默认使用 headed 模式

if [ "$MODE" = "headed" ]; then
    echo "启动模式: 有头模式 (可以看到浏览器窗口)"
    echo ""
    echo "提示: 浏览器窗口将自动打开,您可以观察测试执行过程"
    echo "提示: 测试将慢速执行,便于观察每个操作"
    echo ""
    
    # 运行有头模式测试
    npx playwright test gui_live_demo.spec.js --headed --workers=1
    
elif [ "$MODE" = "ui" ]; then
    echo "启动模式: UI 模式 (Playwright Inspector)"
    echo ""
    echo "提示: Playwright Inspector 将打开,您可以逐步调试测试"
    echo "提示: 可以暂停、继续、单步执行测试"
    echo ""
    
    # 运行 UI 模式测试
    npx playwright test gui_live_demo.spec.js --ui
    
elif [ "$MODE" = "debug" ]; then
    echo "启动模式: 调试模式"
    echo ""
    echo "提示: 测试将在每个操作前暂停,按继续按钮执行下一步"
    echo ""
    
    # 运行调试模式测试
    npx playwright test gui_live_demo.spec.js --debug
    
else
    echo "启动模式: 无头模式 (后台运行)"
    echo ""
    echo "提示: 浏览器将在后台运行,不会显示窗口"
    echo ""
    
    # 运行无头模式测试
    npx playwright test gui_live_demo.spec.js
fi

echo ""
echo "============================================================"
echo "演示完成"
echo "============================================================"
echo ""
echo "截图已保存到: demo-screenshots/"
echo ""
echo "查看截图:"
ls -lh demo-screenshots/
