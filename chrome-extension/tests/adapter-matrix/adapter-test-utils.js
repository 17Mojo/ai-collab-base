/**
 * Adapter Test Utilities
 * Shared utility functions for the adapter test matrix
 */

const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const FIXTURES_DIR = path.join(__dirname, 'fixtures');

/**
 * Load a mock HTML fixture into a JSDOM window
 * @param {string} platformId - Platform identifier (e.g., 'chatgpt')
 * @param {string} hostname - Hostname to simulate for detect() tests
 * @returns {{ window: Window, document: Document }}
 */
function loadFixture(platformId, hostname) {
  const fixturePath = path.join(FIXTURES_DIR, `mock-dom-${platformId}.html`);
  if (!fs.existsSync(fixturePath)) {
    throw new Error(`Fixture not found: ${fixturePath}`);
  }
  const html = fs.readFileSync(fixturePath, 'utf-8');
  const dom = new JSDOM(html, {
    url: `https://${hostname}/`,
    pretendToBeVisual: true,
  });
  return { window: dom.window, document: dom.window.document };
}

/**
 * Find an element using an array of selectors (first match wins)
 * Mirrors the adapter-utils findElement() behavior
 * @param {Document|Element} root - Root element to search from
 * @param {string[]} selectors - Array of CSS selectors
 * @returns {Element|null}
 */
function findElement(root, selectors) {
  for (const selector of selectors) {
    try {
      const el = root.querySelector(selector);
      if (el) return el;
    } catch (e) {
      // Invalid selector, skip
    }
  }
  return null;
}

/**
 * Find all elements using an array of selectors (first non-empty result wins)
 * Mirrors the adapter-utils findElements() behavior
 * @param {Document|Element} root - Root element to search from
 * @param {string[]} selectors - Array of CSS selectors
 * @returns {NodeList|Array}
 */
function findElements(root, selectors) {
  for (const selector of selectors) {
    try {
      const els = root.querySelectorAll(selector);
      if (els.length > 0) return els;
    } catch (e) {
      // Invalid selector, skip
    }
  }
  return [];
}

/**
 * Extract text content from a message element using content selectors
 * Mirrors the adapter-utils extractMessageContent() behavior
 * @param {Element} messageElement - Message container element
 * @param {string[]} contentSelectors - Content selector array
 * @returns {string}
 */
function extractMessageContent(messageElement, contentSelectors) {
  if (!messageElement) return '';
  for (const selector of contentSelectors) {
    try {
      const el = messageElement.querySelector(selector);
      if (el) return el.textContent.trim();
    } catch (e) {
      // Invalid selector, skip
    }
  }
  return messageElement.textContent?.trim() || '';
}

/**
 * Check if an element is visible (not display:none)
 * @param {Element} el - Element to check
 * @returns {boolean}
 */
function isVisible(el) {
  if (!el) return false;
  const style = el.getAttribute('style') || '';
  return !style.includes('display:none') && !style.includes('display: none');
}

/**
 * Run a single test case and return the result
 * @param {string} name - Test name
 * @param {Function} fn - Test function (should throw on failure)
 * @returns {{ name: string, pass: boolean, error: string|null }}
 */
function runTest(name, fn) {
  try {
    const result = fn();
    if (result === false) {
      return { name, pass: false, error: 'Test returned false' };
    }
    return { name, pass: true, error: null };
  } catch (e) {
    return { name, pass: false, error: e.message };
  }
}

/**
 * Format test results for console output
 * @param {string} platformName - Platform display name
 * @param {Array} results - Array of test results
 * @returns {{ pass: number, fail: number, total: number }}
 */
function formatResults(platformName, results) {
  const pass = results.filter(r => r.pass).length;
  const fail = results.filter(r => !r.pass).length;
  const total = results.length;

  console.log(`\n  ${platformName}`);
  console.log(`  ${'─'.repeat(50)}`);

  for (const r of results) {
    const icon = r.pass ? 'PASS' : 'FAIL';
    const detail = r.error ? ` (${r.error})` : '';
    console.log(`    [${icon}] ${r.name}${detail}`);
  }

  console.log(`  Result: ${pass}/${total} passed`);
  return { pass, fail, total };
}

module.exports = {
  loadFixture,
  findElement,
  findElements,
  extractMessageContent,
  isVisible,
  runTest,
  formatResults,
  FIXTURES_DIR,
};
