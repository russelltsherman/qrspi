#!/usr/bin/env node
'use strict'
// Static syntax gate for Claude Code Workflow scripts (.claude/workflows/*.js).
//
// A workflow script is NOT a standalone Node module: it carries `export const
// meta` (ESM-only) AND a top-level `return` + top-level `await` (legal only
// inside the harness's async function wrapper). So it is "dual-illegal" outside
// the harness — `node --check` parses it as ESM (top-level return errors) or
// CommonJS (export errors) depending on the Node version, making a naive check
// unreliable across runners.
//
// This gate instead validates the file the way the harness loads it: strip the
// single `export` keyword from `export const meta`, then COMPILE (not run) the
// body as an async function with the injected globals in scope. That accepts
// top-level return/await and catches real syntax errors, deterministically,
// regardless of Node's module-detection mode.
//
// Usage: node scripts/check_workflows.js <file.js> [<file.js> ...]
// Exit 0 if every file compiles, 1 if any fails (or no files given).

const fs = require('fs')
const vm = require('vm')

// Globals the Workflow harness injects into the script scope.
const INJECTED = ['agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow']

function checkFile(file) {
  const src = fs.readFileSync(file, 'utf8')
  // Drop the lone module-level export so the source is a valid function body.
  const body = src.replace(/^export\s+const\s+meta\b/m, 'const meta')
  // Wrap in an async IIFE so top-level await is legal; the outer function takes
  // the injected globals as params so references resolve at compile time.
  const wrapped = `return (async () => {\n${body}\n})()`
  vm.compileFunction(wrapped, INJECTED, { filename: file })
}

function main(argv) {
  const files = argv.slice(2)
  if (files.length === 0) {
    console.error('check_workflows: no files given')
    return 1
  }
  let failed = 0
  for (const file of files) {
    try {
      checkFile(file)
      console.log(`  OK   ${file}`)
    } catch (err) {
      failed++
      console.error(`  FAIL ${file}: ${err && err.message ? err.message : err}`)
    }
  }
  console.log(`\n${files.length - failed} ok, ${failed} failed`)
  return failed ? 1 : 0
}

if (require.main === module) {
  process.exit(main(process.argv))
}

module.exports = { checkFile, main }
