const { test, expect } = require('@playwright/test');

/**
 * GUI 直播演示测试
 * 用于演示浏览器中的点触和输入 UX 测试
 */

test.describe('GUI 直播演示 - 点触和输入 UX 测试', () => {
  
  test.beforeEach(async ({ page }) => {
    // 设置较长的超时时间,便于演示
    test.setTimeout(120000);
    
    // 启用慢动作模式,便于观察
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('演示: 页面加载和基本交互', async ({ page }) => {
    console.log('[演示开始] 页面加载和基本交互');
    
    // 导航到测试页面
    await page.goto('https://example.com');
    
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 演示: 高亮标题元素
    const title = await page.locator('h1');
    await title.highlight();
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/01-page-loaded.png', fullPage: true });
    
    console.log('[演示完成] 页面加载和基本交互');
  });

  test('演示: 输入框交互', async ({ page }) => {
    console.log('[演示开始] 输入框交互');
    
    // 导航到包含输入框的页面
    await page.goto('https://www.google.com');
    await page.waitForLoadState('networkidle');
    
    // 演示: 定位搜索框
    const searchBox = await page.locator('textarea[name="q"], input[name="q"]').first();
    
    // 演示: 点击输入框
    await searchBox.click();
    await page.waitForTimeout(1000);
    
    // 演示: 慢速输入,便于观察
    await searchBox.type('Playwright GUI 测试演示', { delay: 100 });
    await page.waitForTimeout(2000);
    
    // 演示: 清空输入框
    await searchBox.clear();
    await page.waitForTimeout(1000);
    
    // 演示: 填充新内容
    await searchBox.fill('自动化测试最佳实践');
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/02-input-interaction.png' });
    
    console.log('[演示完成] 输入框交互');
  });

  test('演示: 按钮点击和导航', async ({ page }) => {
    console.log('[演示开始] 按钮点击和导航');
    
    // 导航到测试页面
    await page.goto('https://example.com');
    await page.waitForLoadState('networkidle');
    
    // 演示: 查找链接
    const link = await page.locator('a').first();
    
    // 演示: 高亮链接
    await link.highlight();
    await page.waitForTimeout(2000);
    
    // 演示: 点击链接
    await link.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/03-button-click.png' });
    
    console.log('[演示完成] 按钮点击和导航');
  });

  test('演示: 表单填写和提交', async ({ page }) => {
    console.log('[演示开始] 表单填写和提交');

    // 使用内联页面，避免外部站点波动
    await page.setContent(`
      <main style="font-family: sans-serif; padding: 24px; max-width: 480px;">
        <h1>演示表单</h1>
        <form id="demo-form">
          <label>姓名 <input name="custname" required /></label><br/><br/>
          <label>电话 <input name="custtel" required /></label><br/><br/>
          <label>邮箱 <input name="custemail" type="email" required /></label><br/><br/>
          <fieldset>
            <legend>尺寸</legend>
            <label><input type="radio" name="size" value="small" /> 小</label>
            <label><input type="radio" name="size" value="medium" /> 中</label>
            <label><input type="radio" name="size" value="large" /> 大</label>
          </fieldset>
          <br/>
          <label><input type="checkbox" name="topping" value="cheese" /> 奶酪</label>
          <br/><br/>
          <button type="submit">提交</button>
        </form>
        <pre id="result" style="margin-top:16px; background:#f5f5f5; padding:12px;"></pre>
        <script>
          const form = document.getElementById('demo-form');
          const result = document.getElementById('result');
          form.addEventListener('submit', (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            result.textContent = '已提交: ' + JSON.stringify(data);
          });
        </script>
      </main>
    `);

    const nameInput = page.locator('input[name="custname"]');
    await nameInput.fill('测试用户');

    const telInput = page.locator('input[name="custtel"]');
    await telInput.fill('13800138000');

    const emailInput = page.locator('input[name="custemail"]');
    await emailInput.fill('test@example.com');

    await page.locator('input[value="medium"]').check();
    await page.locator('input[value="cheese"]').check();

    await page.screenshot({ path: 'demo-screenshots/04-form-filled.png' });

    await page.locator('button[type="submit"]').click();
    await page.getByText('已提交:').waitFor({ timeout: 5000 });

    await page.screenshot({ path: 'demo-screenshots/05-form-submitted.png' });

    console.log('[演示完成] 表单填写和提交');
  });

  test('演示: 下拉菜单选择', async ({ page }) => {
    console.log('[演示开始] 下拉菜单选择');
    
    // 使用内联页面，确保选项稳定可选
    await page.setContent(`
      <main style="padding:24px;font-family:sans-serif;">
        <h1>下拉菜单演示</h1>
        <label for="dropdown">选择一个选项</label>
        <select id="dropdown">
          <option value="">Please select</option>
          <option value="1">选项 1</option>
          <option value="2">选项 2</option>
          <option value="3">选项 3</option>
        </select>
        <p id="status"></p>
        <script>
          const dropdown = document.getElementById('dropdown');
          const status = document.getElementById('status');
          dropdown.addEventListener('change', () => {
            status.textContent = '当前选择: ' + dropdown.value;
          });
        </script>
      </main>
    `);
    
    const dropdown = page.locator('#dropdown');
    await dropdown.selectOption({ value: '2' });
    await page.getByText('当前选择: 2').waitFor({ timeout: 3000 });
    
    await page.screenshot({ path: 'demo-screenshots/06-dropdown-selected.png' });
    
    console.log('[演示完成] 下拉菜单选择');
  });

  test('演示: 鼠标悬停效果', async ({ page }) => {
    console.log('[演示开始] 鼠标悬停效果');
    
    // 导航到包含悬停效果的页面
    await page.goto('https://the-internet.herokuapp.com/hovers');
    await page.waitForLoadState('networkidle');
    
    // 演示: 定位悬停元素
    const hoverElement = await page.locator('.figure').first();
    
    // 演示: 鼠标悬停
    await hoverElement.hover();
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/07-hover-effect.png' });
    
    console.log('[演示完成] 鼠标悬停效果');
  });

  test('演示: 拖拽操作', async ({ page }) => {
    console.log('[演示开始] 拖拽操作');
    
    // 导航到包含拖拽功能的页面
    await page.goto('https://the-internet.herokuapp.com/drag_and_drop');
    await page.waitForLoadState('networkidle');
    
    // 演示: 定位拖拽元素
    const source = await page.locator('#column-a');
    const target = await page.locator('#column-b');
    
    // 演示: 高亮元素
    await source.highlight();
    await page.waitForTimeout(1000);
    await target.highlight();
    await page.waitForTimeout(1000);
    
    // 演示: 执行拖拽
    await source.dragTo(target);
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/08-drag-drop.png' });
    
    console.log('[演示完成] 拖拽操作');
  });

  test('演示: 键盘快捷键', async ({ page }) => {
    console.log('[演示开始] 键盘快捷键');
    
    // 导航到测试页面
    await page.goto('https://the-internet.herokuapp.com/key_presses');
    await page.waitForLoadState('networkidle');
    
    // 演示: 定位输入框
    const input = await page.locator('#target');
    
    // 演示: 点击输入框
    await input.click();
    await page.waitForTimeout(500);
    
    // 演示: 按下 Enter 键
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);
    
    // 演示: 按下 Tab 键
    await page.keyboard.press('Tab');
    await page.waitForTimeout(1000);
    
    // 演示: 按下 Escape 键
    await page.keyboard.press('Escape');
    await page.waitForTimeout(1000);
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/09-keyboard-shortcuts.png' });
    
    console.log('[演示完成] 键盘快捷键');
  });

  test('演示: 多窗口和标签页', async ({ page, context }) => {
    console.log('[演示开始] 多窗口和标签页');
    
    // 导航到测试页面
    await page.goto('https://the-internet.herokuapp.com/windows');
    await page.waitForLoadState('networkidle');
    
    // 演示: 点击打开新窗口的链接
    const [newPage] = await Promise.all([
      context.waitForEvent('page'),
      page.click('a[href="/windows/new"]')
    ]);
    
    await newPage.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // 演示: 在新窗口中操作
    const newPageTitle = await newPage.locator('h3');
    await newPageTitle.highlight();
    await page.waitForTimeout(2000);
    
    // 演示: 截图
    await newPage.screenshot({ path: 'demo-screenshots/10-new-window.png' });
    
    // 演示: 关闭新窗口
    await newPage.close();
    await page.waitForTimeout(1000);
    
    console.log('[演示完成] 多窗口和标签页');
  });

  test('演示: 滚动和视口操作', async ({ page }) => {
    console.log('[演示开始] 滚动和视口操作');
    
    // 导航到长页面
    await page.goto('https://the-internet.herokuapp.com/infinite_scroll');
    await page.waitForLoadState('networkidle');
    
    // 演示: 滚动到页面底部
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
    
    // 演示: 滚动到页面顶部
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(2000);
    
    // 演示: 滚动到特定元素
    const element = await page.locator('.jscroll-added').first();
    if (await element.count() > 0) {
      await element.scrollIntoViewIfNeeded();
      await page.waitForTimeout(2000);
    }
    
    // 演示: 截图
    await page.screenshot({ path: 'demo-screenshots/11-scrolling.png', fullPage: true });
    
    console.log('[演示完成] 滚动和视口操作');
  });
});
