#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const LOCALES_DIR = path.join(__dirname, '../src/i18n/locales');
const NAMESPACES = ['common', 'landing', 'arena', 'runs', 'admin', 'errors'];

function flattenKeys(obj, prefix = '') {
  const keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys.push(...flattenKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

function loadKeys(locale, namespace) {
  const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
  if (!fs.existsSync(filePath)) return [];
  const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  return flattenKeys(content);
}

let exitCode = 0;
const missing = [];

for (const namespace of NAMESPACES) {
  const enKeys = new Set(loadKeys('en', namespace));
  const zhKeys = new Set(loadKeys('zh', namespace));
  
  for (const key of enKeys) {
    if (!zhKeys.has(key)) {
      missing.push(`${namespace}.${key}`);
    }
  }
}

if (missing.length > 0) {
  console.error(`Missing keys in zh: ${missing.join(', ')}`);
  exitCode = 1;
} else {
  console.log('All translation keys present in zh');
}

process.exit(exitCode);
