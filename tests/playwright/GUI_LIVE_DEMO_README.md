# Playwright GUI 直播演示

这个目录包含了用于演示浏览器 GUI 点触和输入 UX 测试的 Playwright 测试脚本。

## 快速开始

### 1. 有头模式 (推荐用于演示)

可以看到浏览器窗口,观察测试执行过程:

```bash
cd tests/playwright
./run_gui_demo.sh headed
```

或者直接运行:

```bash
cd tests/playwright
npx playwright test gui_live_demo.spec.js --headed --workers=1
```

### 2. UI 模式 (推荐用于调试)

打开 Playwright Inspector,可以逐步调试测试:

```bash
cd tests/playwright
./run_gui_demo.sh ui
```

或者直接运行:

```bash
cd tests/playwright
npx playwright test gui_live_demo.spec.js --ui
```

### 3. 调试模式

在每个操作前暂停,按继续按钮执行下一步:

```bash
cd tests/playwright
./run_gui_demo.sh debug
```

或者直接运行:

```bash
cd tests/playwright
npx playwright test gui_live_demo.spec.js --debug
```

### 4. 无头模式

在后台运行,不显示浏览器窗口:

```bash
cd tests/playwright
./run_gui_demo.sh headless
```

或者直接运行:

```bash
cd tests/playwright
npx playwright test gui_live_demo.spec.js
```

## 演示内容

测试脚本包含以下演示场景:

### 1. 页面加载和基本交互
- 导航到测试页面
- 等待页面加载完成
- 高亮元素
- 截图

### 2. 输入框交互
- 点击输入框
- 慢速输入文本 (便于观察)
- 清空输入框
- 填充新内容

### 3. 按钮点击和导航
- 查找链接
- 高亮链接
- 点击链接
- 等待页面加载

### 4. 表单填写和提交
- 填写文本字段
- 选择单选按钮
- 选择复选框
- 提交表单

### 5. 下拉菜单选择
- 点击下拉菜单
- 选择选项

### 6. 鼠标悬停效果
- 鼠标悬停在元素上
- 观察悬停效果

### 7. 拖拽操作
- 定位拖拽元素
- 执行拖拽操作

### 8. 键盘快捷键
- 按下 Enter 键
- 按下 Tab 键
- 按下 Escape 键

### 9. 多窗口和标签页
- 打开新窗口
- 在新窗口中操作
- 关闭新窗口

### 10. 滚动和视口操作
- 滚动到页面底部
- 滚动到页面顶部
- 滚动到特定元素

## 演示技巧

### 慢动作模式

测试脚本中使用了 `delay` 参数来慢速输入,便于观察:

```javascript
await searchBox.type('Playwright GUI 测试演示', { delay: 100 });
```

### 高亮元素

使用 `highlight()` 方法高亮元素:

```javascript
await title.highlight();
```

### 等待时间

使用 `waitForTimeout()` 添加等待时间,便于观察:

```javascript
await page.waitForTimeout(2000);  // 等待 2 秒
```

### 截图

每个演示场景都会截图保存:

```javascript
await page.screenshot({ path: 'demo-screenshots/01-page-loaded.png' });
```

## 查看截图

演示完成后,截图会保存在 `demo-screenshots/` 目录:

```bash
ls -lh demo-screenshots/
```

## 自定义演示

### 修改测试速度

调整 `delay` 参数来改变输入速度:

```javascript
// 快速输入
await input.type('快速输入', { delay: 50 });

// 慢速输入
await input.type('慢速输入', { delay: 200 });
```

### 修改等待时间

调整 `waitForTimeout()` 参数来改变等待时间:

```javascript
// 短等待
await page.waitForTimeout(1000);  // 1 秒

// 长等待
await page.waitForTimeout(5000);  // 5 秒
```

### 添加新的演示场景

在测试文件中添加新的测试用例:

```javascript
test('演示: 新的测试场景', async ({ page }) => {
  console.log('[演示开始] 新的测试场景');
  
  // 添加您的测试代码
  
  console.log('[演示完成] 新的测试场景');
});
```

## 故障排查

### 浏览器未启动

确保已安装 Playwright 浏览器:

```bash
npx playwright install chromium
```

### 测试超时

增加测试超时时间:

```javascript
test.beforeEach(async ({ page }) => {
  test.setTimeout(120000);  // 2 分钟
});
```

### 元素未找到

使用 `waitForSelector()` 等待元素出现:

```javascript
await page.waitForSelector('selector');
```

## 最佳实践

1. **使用有头模式进行演示**: 可以看到浏览器窗口,便于观察
2. **使用慢动作模式**: 便于观众理解每个操作
3. **添加等待时间**: 给观众足够时间观察
4. **截图保存**: 便于后续回顾和分析
5. **控制台日志**: 输出演示进度,便于跟踪

## 相关资源

- [Playwright 官方文档](https://playwright.dev/)
- [Playwright API 参考](https://playwright.dev/docs/api/class-page)
- [Playwright 最佳实践](https://playwright.dev/docs/best-practices)
