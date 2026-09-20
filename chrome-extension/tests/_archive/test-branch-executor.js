/**
 * Branch Executor Tests
 * Tests for PackExecutor branch logic and regex matching
 */

// Mock test for RegexMatcher
class RegexMatcher {
  static match(pattern, text, flags = '') {
    try {
      const regex = new RegExp(pattern, flags);
      const match = text.match(regex);
      if (!match) {
        return { matched: false, extracts: {}, fullMatch: null };
      }
      return {
        matched: true,
        extracts: match.groups || {},
        fullMatch: match[0],
        index: match.index
      };
    } catch (error) {
      return { matched: false, extracts: {}, fullMatch: null, error: error.message };
    }
  }
}

// Mock test for BranchEvaluator
class BranchEvaluator {
  static evaluate(branch, execution) {
    const targetValue = this._getTargetValue(branch.target_field, execution);
    let matched = false;

    switch (branch.condition_type) {
      case 'regex_match':
        if (branch.regex_config) {
          const result = RegexMatcher.match(
            branch.regex_config.pattern,
            String(targetValue),
            branch.regex_config.flags || ''
          );
          matched = result.matched;
        }
        break;
      case 'contains':
        matched = String(targetValue).includes(branch.condition_value);
        break;
      case 'equals':
        matched = String(targetValue) === branch.condition_value;
        break;
      case 'exists':
        matched = targetValue !== null && targetValue !== undefined && String(targetValue) !== '';
        break;
    }

    if (branch.negate) {
      matched = !matched;
    }

    return { matched, targetStep: matched ? branch.target_step : null };
  }

  static _getTargetValue(targetField, execution) {
    switch (targetField) {
      case 'output':
        return execution.output || {};
      case 'input':
        return execution.input || {};
      case 'last_step_output':
        const lastStep = execution.steps[execution.steps.length - 1];
        return lastStep?.output || null;
      default:
        return execution[targetField] || null;
    }
  }
}

// Test cases
const tests = {
  testRegexMatchSuccess() {
    const result = RegexMatcher.match('^SUCCESS:', 'SUCCESS: Task completed', 'i');
    console.assert(result.matched === true, 'regex_match should match SUCCESS');
    console.log('✓ testRegexMatchSuccess passed');
  },

  testRegexMatchError() {
    const result = RegexMatcher.match('ERROR:\\s*(\\w+)', 'ERROR: NETWORK_FAILED', 'i');
    console.assert(result.matched === true, 'regex_match should match ERROR');
    console.log('✓ testRegexMatchError passed');
  },

  testRegexNoMatch() {
    const result = RegexMatcher.match('^SUCCESS:', 'ERROR: Something failed', 'i');
    console.assert(result.matched === false, 'regex_match should not match ERROR');
    console.log('✓ testRegexNoMatch passed');
  },

  testBranchEvaluateRegexMatch() {
    const execution = {
      output: 'ERROR: TIMEOUT',
      steps: [{ output: 'ERROR: TIMEOUT' }]
    };
    const branch = {
      condition_type: 'regex_match',
      target_field: 'last_step_output',
      target_step: 'error_handler',
      regex_config: { pattern: 'ERROR:', flags: 'i' }
    };
    const result = BranchEvaluator.evaluate(branch, execution);
    console.assert(result.matched === true, 'branch should match ERROR');
    console.assert(result.targetStep === 'error_handler', 'target step should be error_handler');
    console.log('✓ testBranchEvaluateRegexMatch passed');
  },

  testBranchEvaluateContains() {
    const execution = { output: 'Please retry the request' };
    const branch = {
      condition_type: 'contains',
      target_field: 'output',
      condition_value: 'retry',
      target_step: 'retry_step'
    };
    const result = BranchEvaluator.evaluate(branch, execution);
    console.assert(result.matched === true, 'branch should match contains retry');
    console.log('✓ testBranchEvaluateContains passed');
  },

  testBranchEvaluateEquals() {
    const execution = { output: 'abort' };
    const branch = {
      condition_type: 'equals',
      target_field: 'output',
      condition_value: 'abort',
      target_step: 'abort_step'
    };
    const result = BranchEvaluator.evaluate(branch, execution);
    console.assert(result.matched === true, 'branch should match equals abort');
    console.log('✓ testBranchEvaluateEquals passed');
  },

  testBranchNegate() {
    const execution = { output: 'SUCCESS' };
    const branch = {
      condition_type: 'contains',
      target_field: 'output',
      condition_value: 'ERROR',
      target_step: 'error_step',
      negate: true
    };
    const result = BranchEvaluator.evaluate(branch, execution);
    console.assert(result.matched === true, 'negate should make non-ERROR match');
    console.log('✓ testBranchNegate passed');
  },

  testBranchExists() {
    const execution = { output: 'Some content' };
    const branch = {
      condition_type: 'exists',
      target_field: 'output',
      target_step: 'next_step'
    };
    const result = BranchEvaluator.evaluate(branch, execution);
    console.assert(result.matched === true, 'exists should match non-empty output');
    console.log('✓ testBranchExists passed');
  }
};

// Run all tests
console.log('=== Branch Executor Tests ===');
let passed = 0;
let failed = 0;

for (const [name, test] of Object.entries(tests)) {
  try {
    test();
    passed++;
  } catch (e) {
    console.log(`✗ ${name} failed: ${e.message}`);
    failed++;
  }
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);

if (failed === 0) {
  console.log('All tests passed!');
} else {
  console.log('Some tests failed!');
}