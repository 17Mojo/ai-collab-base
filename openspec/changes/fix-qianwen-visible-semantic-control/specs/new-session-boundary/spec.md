## ADDED Requirements

### Requirement: 可见语义入口优先于宽泛文案匹配

「新对话」入口定位 SHALL 在**可见文案匹配之前**先扫描语义属性声明的窄入口
（`data-session-switch-target="new-chat"` / `data-testid="sidebar-new-chat"`），
并 SHALL 以 `isElementRendered` 作为该层的准入条件。命中时策略 MUST 记为 `semantic`。

理由：站点把 hover-reveal 面板改为默认可见后，外层 `div.newChatReveal-*` 同时满足
`[class*="newChat"]` 与「textContent 是『新对话』」，但它没有 click handler。
宽泛文案层先命中会点空容器，真入口永远轮不到；回执只剩 `click-no-effect`，
无法分辨是「入口坏了」还是「选错了元素」。

#### Scenario: 可视 hover 面板里同时有同名容器与语义入口

- **WHEN** 页面存在可见的 `div.newChatReveal-*`（文本「新对话」），其子节点是
  `div[data-session-switch-target="new-chat"]`（文本同为「新对话」）
- **THEN** 定位结果 MUST 是语义入口节点，`strategy` MUST 为 `semantic`
- **AND** 点击后消息数 MUST 严格下降，否则如实报 `click-no-effect`
- **AND** MUST NOT 返回外层容器

#### Scenario: 语义入口不可见时仍走隐藏兜底

- **WHEN** 语义入口整条祖先链是 `opacity-0 / pointer-events-none`
- **THEN** 可见语义层 MUST 跳过它
- **AND** 既有隐藏兜底层仍可命中，`strategy` 仍为 `hidden-semantic`

### Requirement: 可见语义层与隐藏兜底层共用同一判定

两层 SHALL 使用同一套语义命中判据：文案全等、aria-label 全等、
或带 `new_chat` 的锚点；并 SHALL 同样排除输入/发送区里的同名诱饵。
两层 MUST NOT 各自维护一份判定实现。

#### Scenario: 语义入口落在输入区

- **WHEN** 一个带 `data-session-switch-target="new-chat"` 的元素位于 composer 区内
- **THEN** 两层都 MUST NOT 选中它
- **AND** 定位可继续回退到页面其他合法入口

#### Scenario: 变异守护

- **WHEN** 清空可见语义层的选择器集合
- **THEN** 可视 hover 面板那条 jsdom 用例 MUST 变红
- **AND** 不得靠「随便一条测试失败」过关
