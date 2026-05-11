#!/usr/bin/env node

/**
 * Playwright 失败摘要与制品分诊脚本
 * 
 * 功能:
 * 1. 解析 logs/playwright-report.json (优先) 或 logs/playwright-junit.xml
 * 2. 生成 markdown 摘要文件,聚合 suite 通过/失败数
 * 3. 列出失败用例名、trace/screenshot/report triage 路径
 * 4. 帮助 CI/nightly 更快定位失败,无需人工逐个翻 artifact
 */

const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '../../..');
const logsDir = path.join(repoRoot, 'logs');
const jsonReportPath = path.join(logsDir, 'playwright-report.json');
const junitReportPath = path.join(logsDir, 'playwright-junit.xml');
const summaryOutputPath = path.join(logsDir, 'playwright-failure-summary.md');

/**
 * 将绝对/相对路径标准化为仓库相对路径，便于在 CI 与本地一致展示。
 */
function toRepoRelativePath(rawPath) {
  if (!rawPath || typeof rawPath !== 'string') {
    return null;
  }

  const absolutePath = path.isAbsolute(rawPath)
    ? rawPath
    : path.resolve(repoRoot, rawPath);
  return path.relative(repoRoot, absolutePath).split(path.sep).join('/');
}

function normalizeStatus(status) {
  const value = String(status || '').toLowerCase();
  if (['failed', 'timedout', 'timed_out', 'interrupted'].includes(value)) {
    return 'failed';
  }
  if (value === 'passed' || value === 'expected') {
    return 'passed';
  }
  if (value === 'skipped') {
    return 'skipped';
  }
  return value || 'unknown';
}

function escapeMarkdownCell(value) {
  return String(value ?? '').replace(/\|/g, '\\|').replace(/\n/g, '<br>');
}

function extractFailureRecord({ suiteName, spec, test, result }) {
  const attachments = Array.isArray(result?.attachments) ? result.attachments : [];
  const trace = attachments.find((item) => {
    const name = String(item?.name || '').toLowerCase();
    const contentType = String(item?.contentType || '').toLowerCase();
    return name.includes('trace') || contentType.includes('zip');
  });
  const screenshot = attachments.find((item) => {
    const name = String(item?.name || '').toLowerCase();
    const contentType = String(item?.contentType || '').toLowerCase();
    return name.includes('screenshot') || contentType.startsWith('image/');
  });

  let errorMessage = 'No error message recorded';
  if (typeof result?.error === 'string' && result.error.trim()) {
    errorMessage = result.error.trim();
  } else if (typeof test?.error === 'string' && test.error.trim()) {
    errorMessage = test.error.trim();
  } else if (result?.error?.message) {
    errorMessage = result.error.message;
  }

  return {
    suite: suiteName,
    spec: spec.title || 'Unknown Spec',
    file: spec.file || 'unknown',
    line: spec.line || 0,
    error: errorMessage,
    trace: toRepoRelativePath(trace?.path),
    screenshot: toRepoRelativePath(screenshot?.path),
  };
}

function classifySpec(spec) {
  const tests = Array.isArray(spec.tests) ? spec.tests : [];
  if (tests.length === 0) {
    return { status: 'skipped', failure: null };
  }

  let sawPassed = false;
  let sawSkipped = false;
  let failure = null;

  for (const test of tests) {
    const testStatus = normalizeStatus(test.status);
    if (testStatus === 'failed') {
      const failingResult = Array.isArray(test.results)
        ? [...test.results].reverse().find((item) => normalizeStatus(item?.status) === 'failed')
        : null;
      failure = extractFailureRecord({
        suiteName: '',
        spec,
        test,
        result: failingResult || null,
      });
      return { status: 'failed', failure };
    }
    if (testStatus === 'passed') {
      sawPassed = true;
    } else if (testStatus === 'skipped') {
      sawSkipped = true;
    }
  }

  if (sawPassed) {
    return { status: 'passed', failure: null };
  }
  if (sawSkipped) {
    return { status: 'skipped', failure: null };
  }
  return { status: 'unknown', failure: null };
}

/**
 * 解析 JSON 报告
 */
function parseJsonReport() {
  if (!fs.existsSync(jsonReportPath)) {
    return null;
  }

  try {
    const content = fs.readFileSync(jsonReportPath, 'utf8');
    const report = JSON.parse(content);

    const suites = {};
    let totalTests = 0;
    let passedTests = 0;
    let failedTests = 0;
    let skippedTests = 0;
    const failures = [];

    if (report.suites) {
      report.suites.forEach((suite) => {
        parseSuiteRecursive(suite, suites, failures, (stats) => {
          totalTests += stats.total;
          passedTests += stats.passed;
          failedTests += stats.failed;
          skippedTests += stats.skipped;
        }, []);
      });
    }

    return {
      source: 'json',
      totalTests,
      passedTests,
      failedTests,
      skippedTests,
      suites,
      failures,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error('Failed to parse JSON report:', error.message);
    return null;
  }
}

/**
 * 解析 JUnit XML 报告，作为 JSON 缺失时的 fallback。
 */
function parseJunitReport() {
  if (!fs.existsSync(junitReportPath)) {
    return null;
  }

  try {
    const xml = fs.readFileSync(junitReportPath, 'utf8');
    const suites = {};
    const failures = [];
    let totalTests = 0;
    let passedTests = 0;
    let failedTests = 0;
    let skippedTests = 0;

    const suitePattern = /<testsuite\b([^>]*)>([\s\S]*?)<\/testsuite>/g;
    let suiteMatch;
    while ((suiteMatch = suitePattern.exec(xml)) !== null) {
      const attributes = suiteMatch[1];
      const body = suiteMatch[2];
      const suiteNameMatch = attributes.match(/name="([^"]*)"/);
      const suiteName = suiteNameMatch ? suiteNameMatch[1] : 'Unknown Suite';

      const suiteStats = { total: 0, passed: 0, failed: 0, skipped: 0 };
      const testcasePattern = /<testcase\b([^>]*)>([\s\S]*?)<\/testcase>/g;
      let testcaseMatch;
      while ((testcaseMatch = testcasePattern.exec(body)) !== null) {
        const testcaseAttrs = testcaseMatch[1];
        const testcaseBody = testcaseMatch[2];
        const specNameMatch = testcaseAttrs.match(/name="([^"]*)"/);
        const classNameMatch = testcaseAttrs.match(/classname="([^"]*)"/);
        const specName = specNameMatch ? specNameMatch[1] : 'Unknown Spec';
        const fileName = classNameMatch ? classNameMatch[1] : suiteName;

        totalTests += 1;
        suiteStats.total += 1;

        if (/<skipped\b/i.test(testcaseBody)) {
          skippedTests += 1;
          suiteStats.skipped += 1;
          continue;
        }

        const failureMatch = testcaseBody.match(/<(failure|error)\b[^>]*>([\s\S]*?)<\/\1>/i);
        if (failureMatch) {
          failedTests += 1;
          suiteStats.failed += 1;
          failures.push({
            suite: suiteName,
            spec: specName,
            file: fileName,
            line: 0,
            error: failureMatch[2].trim() || 'Failure recorded in JUnit output',
            trace: null,
            screenshot: null,
          });
          continue;
        }

        passedTests += 1;
        suiteStats.passed += 1;
      }

      suites[suiteName] = suiteStats;
    }

    return {
      source: 'junit',
      totalTests,
      passedTests,
      failedTests,
      skippedTests,
      suites,
      failures,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Failed to parse JUnit report:', error.message);
    return null;
  }
}

/**
 * 递归解析 Playwright JSON suite。
 */
function parseSuiteRecursive(suite, suites, failures, statsCallback, titleStack) {
  const currentStack = [...titleStack];
  if (suite.title) {
    currentStack.push(suite.title);
  }

  const suiteName = currentStack.length > 0 ? currentStack.join(' > ') : (suite.file || 'Unknown Suite');
  let total = 0;
  let passed = 0;
  let failed = 0;
  let skipped = 0;

  if (Array.isArray(suite.specs)) {
    suite.specs.forEach((spec) => {
      const classification = classifySpec(spec);
      total += 1;
      if (classification.status === 'passed') {
        passed += 1;
      } else if (classification.status === 'failed') {
        failed += 1;
        if (classification.failure) {
          classification.failure.suite = suiteName;
          failures.push(classification.failure);
        }
      } else {
        skipped += 1;
      }
    });
  }

  if (Array.isArray(suite.suites)) {
    suite.suites.forEach((nestedSuite) => {
      parseSuiteRecursive(nestedSuite, suites, failures, (nestedStats) => {
        total += nestedStats.total;
        passed += nestedStats.passed;
        failed += nestedStats.failed;
        skipped += nestedStats.skipped;
      }, currentStack);
    });
  }

  if (!suites[suiteName]) {
    suites[suiteName] = { total: 0, passed: 0, failed: 0, skipped: 0 };
  }
  suites[suiteName].total += total;
  suites[suiteName].passed += passed;
  suites[suiteName].failed += failed;
  suites[suiteName].skipped += skipped;

  statsCallback({ total, passed, failed, skipped });
}

/**
 * 生成 Markdown 摘要
 */
function generateMarkdownSummary(data) {
  const lines = [];

  lines.push('# Playwright 测试失败摘要');
  lines.push('');
  lines.push(`**生成时间**: ${data.timestamp}`);
  lines.push(`**数据来源**: ${data.source === 'json' ? 'playwright-report.json' : 'playwright-junit.xml (fallback)'}`);
  lines.push('');

  // 总体统计
  lines.push('## 总体统计');
  lines.push('');
  lines.push('| 指标 | 数量 | 百分比 |');
  lines.push('|------|------|--------|');
  const passRate = data.totalTests > 0 ? ((data.passedTests / data.totalTests) * 100).toFixed(1) : 0;
  const failRate = data.totalTests > 0 ? ((data.failedTests / data.totalTests) * 100).toFixed(1) : 0;
  const skipRate = data.totalTests > 0 ? ((data.skippedTests / data.totalTests) * 100).toFixed(1) : 0;
  lines.push(`| 总测试数 | ${data.totalTests} | 100% |`);
  lines.push(`| 通过 | ${data.passedTests} | ${passRate}% |`);
  lines.push(`| 失败 | ${data.failedTests} | ${failRate}% |`);
  lines.push(`| 跳过 | ${data.skippedTests} | ${skipRate}% |`);
  lines.push('');

  // Suite 统计
  lines.push('## Suite 统计');
  lines.push('');
  lines.push('| Suite | 总数 | 通过 | 失败 | 跳过 | 通过率 |');
  lines.push('|-------|------|------|------|------|--------|');
  
  Object.entries(data.suites).forEach(([suiteName, stats]) => {
    const rate = stats.total > 0 ? ((stats.passed / stats.total) * 100).toFixed(1) : 0;
    lines.push(`| ${escapeMarkdownCell(suiteName)} | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.skipped} | ${rate}% |`);
  });
  lines.push('');

  // 失败详情
  if (data.failures.length > 0) {
    lines.push('## 失败详情');
    lines.push('');

    data.failures.forEach((failure, index) => {
      lines.push(`### ${index + 1}. ${failure.spec}`);
      lines.push('');
      lines.push(`**Suite**: ${failure.suite}`);
      lines.push('');
      lines.push(`**文件**: ${failure.file}:${failure.line}`);
      lines.push('');
      lines.push(`**错误信息**:`);
      lines.push('```');
      lines.push(failure.error);
      lines.push('```');
      lines.push('');

      // Triage 路径
      lines.push('**诊断路径**:');
      lines.push('');
      if (failure.trace) {
        lines.push(`- Trace: \`${failure.trace}\``);
      }
      if (failure.screenshot) {
        lines.push(`- Screenshot: \`${failure.screenshot}\``);
      }
      lines.push(`- HTML Report: \`logs/playwright-report/\``);
      lines.push(`- JSON Report: \`logs/playwright-report.json\``);
      lines.push('');
    });
  } else {
    lines.push('## ✅ 所有测试通过');
    lines.push('');
    lines.push('没有失败的测试用例。');
    lines.push('');
  }

  // 快速访问
  lines.push('## 快速访问');
  lines.push('');
  lines.push('```bash');
  lines.push('# 查看 HTML 报告');
  lines.push('npm run report:show');
  lines.push('');
  lines.push('# 查看 Trace (如果有失败)');
  lines.push('npx playwright show-trace logs/playwright-results/<test-dir>/trace.zip');
  lines.push('```');
  lines.push('');

  return lines.join('\n');
}

/**
 * 主函数
 */
function main() {
  console.log('Playwright 失败摘要生成器');
  console.log('='.repeat(60));

  let data = null;
  if (fs.existsSync(jsonReportPath)) {
    console.log('解析 JSON 报告...');
    data = parseJsonReport();
  }
  if (!data && fs.existsSync(junitReportPath)) {
    console.log('JSON 报告不可用，回退到 JUnit 报告...');
    data = parseJunitReport();
  }

  if (!data) {
    console.error('错误: 未找到可用的 Playwright 报告');
    console.error('请先运行测试: npm run test:ci');
    process.exit(1);
  }

  console.log(`总测试数: ${data.totalTests}`);
  console.log(`通过: ${data.passedTests}`);
  console.log(`失败: ${data.failedTests}`);
  console.log(`跳过: ${data.skippedTests}`);
  console.log('');

  // 生成 Markdown 摘要
  console.log('生成 Markdown 摘要...');
  const markdown = generateMarkdownSummary(data);

  // 写入文件
  fs.writeFileSync(summaryOutputPath, markdown, 'utf8');
  console.log(`摘要已保存到: ${summaryOutputPath}`);
  console.log('');

  // 输出摘要预览
  console.log('摘要预览:');
  console.log('-'.repeat(60));
  console.log(markdown.split('\n').slice(0, 20).join('\n'));
  console.log('...');
  console.log('-'.repeat(60));

  // 返回退出码
  process.exit(data.failedTests > 0 ? 1 : 0);
}

main();
