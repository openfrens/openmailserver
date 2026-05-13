#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const skipDirs = new Set(['.git', 'node_modules', '.next', '.venv', 'dist', 'build', 'coverage', '.turbo']);
const sourceExts = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.py', '.rb']);
const depFields = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'];

function rel(file) {
  return path.relative(root, file) || '.';
}

function walk(dir, out = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ent.isDirectory()) {
      if (!skipDirs.has(ent.name)) walk(path.join(dir, ent.name), out);
    } else {
      out.push(path.join(dir, ent.name));
    }
  }
  return out;
}

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function packageImportName(name) {
  return name.startsWith('@') ? name.split('/').slice(0, 2).join('/') : name.split('/')[0];
}

function pyImportName(name) {
  return name.toLowerCase().replace(/[-.]/g, '_').replace(/\[.*\]$/, '');
}

const files = walk(root);
const sourceTextByDir = new Map();

for (const file of files) {
  if (!sourceExts.has(path.extname(file))) continue;
  const text = read(file);
  let dir = path.dirname(file);
  while (dir.startsWith(root)) {
    sourceTextByDir.set(dir, `${sourceTextByDir.get(dir) || ''}\n${text}`);
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
}

const findings = [];

for (const file of files) {
  const base = path.basename(file);
  if (base === 'package.json') {
    const pkg = JSON.parse(read(file));
    const text = sourceTextByDir.get(path.dirname(file)) || '';
    for (const field of depFields) {
      for (const name of Object.keys(pkg[field] || {})) {
        const imp = packageImportName(name).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const used = new RegExp(`(?:from\\s+['"]${imp}(?:/|['"])|import\\s*\\(['"]${imp}(?:/|['"])|require\\s*\\(['"]${imp}(?:/|['"])|['"]${imp}/)`).test(text);
        if (!used) findings.push(`${rel(file)} ${field}.${name} not found in static JS/TS imports`);
      }
    }
  }

  if (base === 'pyproject.toml' || /^requirements.*\.txt$/.test(base)) {
    const text = sourceTextByDir.get(path.dirname(file)) || '';
    const deps = [];
    if (base === 'pyproject.toml') {
      let inProjectDeps = false;
      let inPoetryDeps = false;
      for (const line of read(file).split('\n')) {
        const trimmed = line.trim();
        if (/^\[.*\]/.test(trimmed)) {
          inPoetryDeps = trimmed === '[tool.poetry.dependencies]';
          inProjectDeps = false;
        }
        if (/^dependencies\s*=\s*\[/.test(trimmed)) inProjectDeps = true;
        if (inProjectDeps && trimmed === ']') inProjectDeps = false;
        if (inProjectDeps) {
          const dep = trimmed.match(/^"([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==/);
          if (dep) deps.push(dep[1]);
        }
        if (inPoetryDeps) {
          const dep = trimmed.match(/^([A-Za-z0-9_.-]+)\s*=\s*"\d/);
          if (dep && dep[1] !== 'python') deps.push(dep[1]);
        }
      }
    } else {
      for (const line of read(file).split('\n')) {
        const m = line.match(/^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==/);
        if (m) deps.push(m[1]);
      }
    }
    for (const name of new Set(deps)) {
      const imp = pyImportName(name);
      if (!new RegExp(`(^|\\n)\\s*(from|import)\\s+${imp}(\\b|\\.)`).test(text)) {
        findings.push(`${rel(file)} ${name} not found in static Python imports`);
      }
    }
  }

  if (base === 'Gemfile') {
    const text = sourceTextByDir.get(path.dirname(file)) || '';
    for (const m of read(file).matchAll(/^gem\s+["']([^"']+)["']/gm)) {
      const requireName = m[1].replace(/-/g, '_');
      if (!new RegExp(`require\\s+['"]${requireName}['"]`).test(text)) {
        findings.push(`${rel(file)} gem ${m[1]} not found in static Ruby requires`);
      }
    }
  }
}

if (!findings.length) {
  console.log('No unused dependencies found by the conservative static scan.');
} else {
  console.log('Potential unused dependencies; review before removing:');
  for (const finding of findings) console.log(`- ${finding}`);
}
