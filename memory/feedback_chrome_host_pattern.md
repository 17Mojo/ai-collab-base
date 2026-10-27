---
name: Chrome host 匹配里裸域只等于自己——www 变体必须单列
description: manifest 的 host 模式写 https://qianwen.com/* 时，Chrome 只匹配该域本身、不匹配 www.qianwen.com（只有 *. 才通配）⇒ 内容脚本根本不注入；host_permissions 与 content_scripts.matches 须收敛成同一份清单
type: feedback
from: Agent
---

Chrome 扩展 manifest 的 host 匹配里，**裸域只等于它自己**：

- `https://qianwen.com/*` **不匹配** `https://www.qianwen.com/`；
- `https://*.qianwen.com/*` 才是通配（且它**不**覆盖裸域 `qianwen.com`）。

⇒ 少写 `www.` 变体时，内容脚本**根本没有注入**到真站上，而页面**不报任何错**——
只是「没适配器」。2026-10-26 排演实测：千问真站是 `https://www.qianwen.com/`，
Kimi 真站是 `www.kimi.com`，两处都只写了裸域。

**Why:** 这个坑特别隐蔽，因为**开发时看的 URL 常带 www，而写规则时照抄的是裸域**；
而且症状是「扩展没反应」，很容易被误判成「没装好」或「站点不支持」。
2026-10-26 排演的 6 个缺陷里，这是第 1 个——而且它排在**指南的第 3 步**
（打开网站），后面 3 步根本走不到。

**How to apply:**
- `host_permissions` 与 `content_scripts.matches` **收敛成同一份清单**（各写一份就迟早漏），
  清单单点持有，构建产物里的 manifest 由源 `manifest.json` 生成而非手写第二份。
- 守护测试要按 **Chrome 的匹配规则**（`*.` 才通配）**逐个平台**核对，
  别只测一个平台——漏掉的平台照样绿。
- 与 `feedback_service_worker_no_window.md`、`feedback_single_validation_authority.md` 并排读：
  这三条合起来是「排演查出来的 6 个断点里的前三个」。
