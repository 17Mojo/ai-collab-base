# Playwright Runtime Regression

This suite verifies Prompt Pack popup behavior with a deterministic Chrome host
mock so CI can exercise runtime paths without relying on a real extension host.

## Primary Entry Points

### Install

```bash
cd tests/playwright
npm ci
npx playwright install chromium
```

### Execution Matrix

| Layer | Script | CI Script | Tests | Purpose |
|-------|--------|-----------|-------|---------|
| **Gate** | `test:popup:gate` | `test:popup:gate:ci` | 20 | Core quality gate (must pass) |
| **Extended** | `test:popup:extended` | `test:popup:extended:ci` | 20 | Extended validation (recommended) |
| **Nightly** | `test` | `test:ci` | 36+ | Full suite (comprehensive) |

**Gate Layer** (阻塞发布):
- Runtime: `test:runtime` / `test:runtime:ci`
- Accessibility: `test:a11y` / `test:a11y:ci`
- Axe Audit: `test:a11y:axe` / `test:a11y:axe:ci`
- Combined: `test:popup:gate` / `test:popup:gate:ci`

**Extended Layer** (建议通过):
- Visual Regression: `test:visual` / `test:visual:ci`
- Performance: `test:perf` / `test:perf:ci`
- Combined: `test:popup:extended` / `test:popup:extended:ci`

**Nightly Layer** (全面验证):
- Full Suite: `test` / `test:ci`

### Runtime Regression

```bash
npm run test:runtime
```

Runs the two suites that currently define the popup runtime gate:

- `tests/popup.runtime.spec.js`
- `tests/error_handling.spec.js`

### Popup Accessibility Smoke

```bash
npm run test:a11y
```

This is the dedicated popup accessibility smoke suite. It verifies the popup's
minimum keyboard and semantic contract without expanding into full visual or
screen-reader audits.

CI-equivalent command:

```bash
npm run test:a11y:ci
```

### Popup Accessibility Axe Audit

```bash
npm run test:a11y:axe
```

This suite runs a stricter `axe-core` audit on the popup's critical states. It
is intended to catch semantic structure and contrast regressions that are too
subtle for the lightweight smoke checks.

CI-equivalent command:

```bash
npm run test:a11y:axe:ci
```

### Popup Gate (Combined)

```bash
npm run test:popup:gate
```

Runs all gate layer tests: runtime + error + a11y + axe.

CI-equivalent command:

```bash
npm run test:popup:gate:ci
```

### Popup Extended (Combined)

```bash
npm run test:popup:extended
```

Runs all extended layer tests: axe + visual + perf.

CI-equivalent command:

```bash
npm run test:popup:extended:ci
```

### CI-equivalent Runtime Regression

```bash
npm run test:runtime:ci
```

This is the canonical command for CI-style reproduction. It enables `CI=1`, so
the shared Playwright config writes the same artifact set used in CI:

- JUnit: `logs/playwright-junit.xml`
- HTML report: `logs/playwright-report/`
- JSON report: `logs/playwright-report.json`
- failure traces/screenshots: `logs/playwright-results/`

### Full Suite

```bash
npm run test
```

### GUI Demo

```bash
npm run test:gui-demo
```

## Suite Boundaries

### `popup.runtime.spec.js`

Validates the stable happy-path runtime contract:

- popup boot from `chrome.storage.local`
- pack list render and selection
- execute flow through `chrome.tabs.sendMessage`
- settings open through `chrome.runtime.openOptionsPage`

### `error_handling.spec.js`

Validates runtime failures and edge conditions:

- empty pack list
- storage failure
- invalid pack payload
- execute failure
- long/special-character pack names
- rapid repeat execute
- runtime timeout

### `popup.a11y.spec.js`

Validates the popup accessibility smoke contract:

- keyboard tab flow reaches primary actions
- focus-visible styling appears on keyboard focus
- accessible labels exist for primary and row-level buttons
- `role=status` announces execution state changes
- error state exposes alert + retry affordance
- empty state keeps import action reachable

### `popup.a11y.axe.spec.js`

Validates the popup against `axe-core` across critical runtime states:

- selected idle state
- empty state
- runtime error state
- completed state

Failure triage order:

1. inspect the violation ids in terminal output
2. open `logs/playwright-results/` screenshot + trace
3. fix semantic structure first (`role`, heading order, landmarks)
4. then fix contrast and visual token regressions

### `prompt_pack_gui_demo.spec.js`

Provides a deterministic live demo path for stakeholder walkthroughs. It is not
the default CI gate, but it should remain green alongside runtime regression.

## Reporting and Failure Triage

### Show the HTML Report

```bash
cd tests/playwright
npm run report:show
```

### Generate Failure Summary

```bash
cd tests/playwright
npm run report:summary
```

This script generates a markdown summary file (`logs/playwright-failure-summary.md`) that aggregates:
- Suite pass/fail statistics
- Failed test names and error messages
- Trace/screenshot/report triage paths
- Automatically falls back to `logs/playwright-junit.xml` when JSON output is unavailable

**Benefits**:
- Quickly identify all failures without opening HTML report
- Machine-readable summary for CI integration
- Direct links to diagnostic artifacts

### Open a Failure Trace

```bash
cd tests/playwright
npx playwright show-trace ../../logs/playwright-results/<test-dir>/trace.zip
```

### Re-run One Failed Spec in Debug Mode

```bash
cd tests/playwright
npx playwright test tests/error_handling.spec.js --debug
```

### Re-run a Single Test By Name

```bash
cd tests/playwright
npx playwright test tests/error_handling.spec.js --grep "网络超时"
```

## Observability Signals

The popup/runtime suites intentionally emit structured logs to make failures
explainable in CI:

- `[TEST STEP]` for test-side execution progress
- `[BROWSER ERROR]` for browser console errors
- `[BROWSER WARNING]` for browser console warnings

When a regression happens, check signals in this order:

1. terminal output for the failing step
2. `logs/playwright-results/` for screenshot + trace
3. `logs/playwright-report/` for the HTML summary
4. `logs/playwright-report.json` for machine-readable failure details

### `popup_visual_regression.spec.js`

Validates the popup visual appearance across different viewports and states:

- **Viewport coverage**:
  - Default (400x600)
  - Small screen (320x480)
  - Large screen (600x800)
  - Compact (360x640)
  - Mobile (375x667)

- **State coverage**:
  - Initial state
  - Pack list
  - Selected state
  - Executed state
  - Empty state (no packs)
  - Error state (execution failure)

**Snapshot Maintenance**:

When to update snapshots:
- Intentional UI changes (design updates, layout adjustments)
- New visual features or components
- Font or styling changes

When it's a real regression:
- Unexpected visual changes without code changes
- Layout breaks in specific viewports
- Missing or misaligned elements

**Failure Triage**:

1. Check if the change is intentional (UI update)
2. If intentional: update snapshots with `npx playwright test --update-snapshots`
3. If unintentional: investigate the root cause
4. For viewport-specific failures: check responsive CSS
5. For state-specific failures: check state management logic

## Notes for Follow-up Waves

- a11y and visual regression should layer on top of `test:runtime`, not replace it
- if new popup states are introduced, extend `error_handling.spec.js` before
  widening the CI gate
- avoid changing artifact paths casually; downstream receipt/report tooling reads
  from the current `logs/` layout
- popup a11y smoke should stay lightweight; use it to catch semantic regressions,
  not to replace deeper manual accessibility review
- visual regression snapshots should be updated only when UI changes are intentional
- new viewport sizes should be added to cover real-world device scenarios
