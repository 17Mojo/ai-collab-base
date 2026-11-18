# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。

## Phase 0 · 立项

- [x] 0.1 产出 proposal / spec delta / tasks（E1）
- [x] 0.2 `openspec validate retire-frozen-ab-platforms --strict` 零错误（E2）

## Phase 1 · 事实源收口

- [x] 1.1 结果报告落两轮回执、判据结算、根因分层、覆盖精度、风险回滚（E3）
- [x] 1.2 `known_gaps.json` N25 open → closed，追加 6 条证据，open 归零（E4）
- [x] 1.3 `platform-freeze.mjs` 头部注释记裁定，不碰白名单常量与变异锚点（E5）
- [x] 1.4 deepseek A/B 回执 + 变体 Pack + 只读预检提交；longcat 无回执（E6）

## Phase 2 · 验证与归档

- [x] 2.1 扩展全套 326/326、平台冻结守护全绿、变异 125/125（E7）
- [x] 2.2 提交 + PR + 合入登记（40 位 sha）+ 归档 + archived validate（E8）

## 实测证据

### E1 · 工件

```
openspec/changes/retire-frozen-ab-platforms/{proposal.md,tasks.md,
  specs/active-platform-registry/spec.md}
```

### E2 · validate

```
$ openspec validate retire-frozen-ab-platforms --strict
Change 'retire-frozen-ab-platforms' is valid
```

### E3 · 结果报告

```
collaboration/results/RESULT-N25-AB-2026-11-18.md
四段式：执行命令 / 验证结果（5 小节含测试结论）/ 风险 / 回滚 + 状态行
```

### E4 · N25 关单

```
python3 -c "import json; d=json.load(open('known_gaps.json'));
  print(d['gaps'][24]['status'], d['gaps'][24]['closed_at'])"
closed 2026-11-18
Counter({'closed': 29, 'wontfix': 1})   # open = 0
```

### E5 · 注释裁定

```
platform-freeze.mjs 头部新增「同日第二次裁定（N25 收口）」段；
ACTIVE_PLATFORM_IDS / FROZEN_AB_PLATFORMS / 闸门语句三处变异锚点未触碰（diff 核）。
```

### E6 · 证据文件

```
git status 新增未跟踪：
  L2-deepseek-auto-2026-11-18.ab-{no-boundary,with-boundary}.json / .png
  ab-pack-2026-11-18.{no-boundary,with-boundary}.json
  session-wall-ab-plan-2026-11-18.json
  L2-precheck-2026-11-18.deepseek-longcat.json
longcat 无 L2-longcat-*.ab-*.json（裁定停止，未启动）。
```

### E7 · 测试

```
$ cd chrome-extension && CODEBUDDY_SAFE_DELETE_ENABLED=0 npm test
# tests 326 / pass 326 / fail 0 / skipped 0 / duration_ms 10805

$ CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs
全部 125 条变异都被杀死。

$ CODEBUDDY_SAFE_DELETE_ENABLED=0 node --test tests/platform-freeze.test.mjs tests/session-wall-ab.test.mjs
# tests 24 / pass 24 / fail 0

$ openspec validate retire-frozen-ab-platforms --strict
Change 'retire-frozen-ab-platforms' is valid
```

### E8 · 收口

```
（提交、PR、合入登记与归档完成后写入本节）
```
