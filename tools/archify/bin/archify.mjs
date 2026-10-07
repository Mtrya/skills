#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkHtmlFile } from '../scripts/check-render-output.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(__dirname, '..');

const TYPES = new Set(['architecture', 'workflow', 'sequence', 'dataflow', 'lifecycle']);
const EXAMPLE_TARGETS = [
  ['workflow', 'agent-tool-call.workflow.json', 'workflow-agent-tool-call-rendered.html'],
  ['sequence', 'cache-miss-request.sequence.json', 'sequence-cache-miss-request.html'],
  ['dataflow', 'product-analytics.dataflow.json', 'dataflow-product-analytics.html'],
  ['lifecycle', 'agent-run.lifecycle.json', 'lifecycle-agent-run.html'],
  ['architecture', 'web-app.architecture.json', 'web-app-rendered.html'],
];

function usage() {
  return `Usage:
  archify render <type> <input.json> [output.html]
  archify validate <type> <input.json> [--json] [--layout-json]
  archify inspect <type> <input.json>
  archify check <output.html>
  archify examples [output-dir]

Types:
  architecture, workflow, sequence, dataflow, lifecycle
`;
}

function fail(message, code = 2) {
  console.error(message);
  process.exit(code);
}

function rendererPath(type) {
  if (!TYPES.has(type)) {
    fail(`Unknown diagram type "${type}". Expected one of: ${[...TYPES].join(', ')}`);
  }
  return path.join(skillRoot, 'renderers', type, `render-${type}.mjs`);
}

function runNode(args, options = {}) {
  return spawnSync(process.execPath, args, {
    cwd: options.cwd || process.cwd(),
    encoding: 'utf8',
    stdio: options.stdio || 'inherit',
  });
}

function failed(result) {
  return !!result.error || result.status !== 0;
}

function exitFrom(result) {
  if (result.error) fail(result.error.message, 1);
  process.exit(result.status ?? 1);
}

function commandRender(args) {
  const [type, input, output] = args;
  if (!type || !input) fail(usage());
  const result = runNode([rendererPath(type), input, ...(output ? [output] : [])]);
  if (failed(result)) exitFrom(result);
}

function commandCheck(args) {
  const [html] = args;
  if (!html) fail(usage());
  const result = checkHtmlFile(html);
  const output = JSON.stringify(result, null, 2);
  if (result.ok) console.log(output);
  else {
    console.error(output);
    process.exit(1);
  }
}

function commandExamples(args) {
  const outputRoot = examplesOutputRoot(args[0]);
  for (const [mode, input, output] of EXAMPLE_TARGETS) {
    const result = runNode([
      rendererPath(mode),
      path.join(skillRoot, 'examples', input),
      path.join(outputRoot, output),
    ], { cwd: skillRoot });
    if (failed(result)) exitFrom(result);
  }
}

function examplesOutputRoot(preferred) {
  if (preferred) return path.resolve(preferred);
  const repoExamples = path.resolve(skillRoot, '..', 'examples');
  if (fs.existsSync(repoExamples)) return repoExamples;
  const cwd = path.resolve(process.cwd());
  const base = cwd === skillRoot || cwd.startsWith(`${skillRoot}${path.sep}`) ? os.tmpdir() : cwd;
  return path.join(base, 'archify-examples');
}

function commandValidate(args) {
  const json = args.includes('--json');
  const layoutJson = args.includes('--layout-json');
  const rest = args.filter((arg) => arg !== '--json' && arg !== '--layout-json');
  const [type, input] = rest;
  if (!type || !input) fail(usage());

  if (layoutJson) {
    if (type !== 'architecture') {
      fail('--layout-json is currently supported for architecture diagrams only.');
    }
    const result = runNode([rendererPath(type), input, '/dev/null', '--layout-json']);
    if (failed(result)) exitFrom(result);
    return;
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-validate-'));
  const out = path.join(tmp, `${type}.html`);
  let exitCode = 0;

  try {
    const render = runNode([rendererPath(type), input, out], { stdio: ['ignore', 'ignore', 'inherit'] });
    if (failed(render)) {
      exitCode = render.error ? 1 : (render.status ?? 1);
    } else {
      const result = checkHtmlFile(out);
      if (!result.ok) {
        console.error(JSON.stringify(result, null, 2));
        exitCode = 1;
      } else {
        if (json) {
          console.log(JSON.stringify({
            ok: true,
            type,
            input: path.resolve(input),
            checks: result.checks,
          }, null, 2));
        } else {
          console.log(`ok ${type} ${path.resolve(input)} (${result.checks.length} checks)`);
        }
      }
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  if (exitCode !== 0) process.exit(exitCode);
}

const [command, ...args] = process.argv.slice(2);

switch (command) {
  case undefined:
  case '-h':
  case '--help':
  case 'help':
    console.log(usage());
    break;
  case 'render':
    commandRender(args);
    break;
  case 'validate':
    commandValidate(args);
    break;
  case 'inspect':
    commandValidate([...args, '--layout-json']);
    break;
  case 'check':
    commandCheck(args);
    break;
  case 'examples':
    commandExamples(args);
    break;
  default:
    fail(`Unknown command "${command}".\n\n${usage()}`);
}
