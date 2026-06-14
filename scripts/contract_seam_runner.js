#!/usr/bin/env node
'use strict'
// Consumer-side harness for the JS<->Python contract-seam fixtures (RUS-76, Slice 3).
//
// It exposes the eight envelope parsers defined in
// `.claude/workflows/qrspi-batch.js` so the Python consumer test can drive each
// one against the committed `scripts/fixtures/contract_seam/<seam>/*.json`
// fixtures WITHOUT modifying the orchestrator. The orchestrator is loaded the
// SAME way the Workflow harness loads it (and the same way scripts/check_workflows.js
// compiles it): strip the lone `export` keyword, async-wrap the body, and
// `vm.compileFunction` it with the eight injected globals as parameters (all
// stubbed as no-ops here).
//
// The one extra step over check_workflows.js: a name-referencing
// `return { ...parsers }` shim is spliced in ABOVE the top-level orchestration
// block — immediately before `phase('Query')` — so invoking the compiled async
// function returns the parser map and NEVER executes the ~260 lines of batch
// orchestration that run from `phase('Query')` to the terminal `return`. Placing
// the shim before the terminal return instead would first run the orchestration
// under the no-op global stubs (`agent()` -> undefined, then `tickets.map(...)`)
// and throw before the shim's return is reached. The eight `parse*` functions are
// hoisted `function` declarations and both closed-over consts (RESOLVE_ACTIONS,
// DEFAULT_CRITIC_PHASES) are defined well before `phase('Query')`, so the early
// return exposes them cleanly. The source is transformed ONLY in memory; this
// script never writes back to qrspi-batch.js.
//
// CLI: node scripts/contract_seam_runner.js <parser-name> <fixture-path> [<fixture-path>...]
// For each fixture it prints one line of JSON: {"parser","fixture","result"}.

const fs = require('fs')
const path = require('path')
const vm = require('vm')

const SCRIPT_DIR = __dirname
const REPO_ROOT = path.dirname(SCRIPT_DIR)
const BATCH_JS = path.join(REPO_ROOT, '.claude', 'workflows', 'qrspi-batch.js')

// Globals the Workflow harness injects into the script scope (same list as
// scripts/check_workflows.js INJECTED).
const INJECTED = ['agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow']

// The parser names this harness exposes (the eight envelope parsers in
// qrspi-batch.js). Kept here so the shim returns exactly these by name.
const PARSER_NAMES = [
  'parseResolveEnvelope',
  'parseOrderedTickets',
  'parseRestackEnvelope',
  'parseSyncTrunkEnvelope',
  'parseCleanupEnvelope',
  'parseLandVerdict',
  'parseConfigEnvelope',
  'parseCriticsEnvelope',
  // also expose the const so partial-merge / critics-default assertions can
  // compare against the canonical DEFAULT_CRITIC_PHASES from the same source.
  'DEFAULT_CRITIC_PHASES',
]

// Build the compiled async function whose return value is the parser map.
function loadParsers() {
  const src = fs.readFileSync(BATCH_JS, 'utf8')
  // 1) Drop the lone module-level export so the source is a valid function body.
  const body = src.replace(/^export\s+const\s+meta\b/m, 'const meta')

  // 2) Splice a `return { ...parsers }` shim immediately BEFORE the top-level
  //    orchestration entrypoint `phase('Query')`. Locate it at run time (line
  //    numbers drift) rather than trusting a literal offset.
  const shim = `\nreturn { ${PARSER_NAMES.join(', ')} };\n`
  const marker = /^phase\(['"]Query['"]\)/m
  if (!marker.test(body)) {
    throw new Error("contract_seam_runner: could not locate the `phase('Query')` orchestration boundary in qrspi-batch.js")
  }
  const shimmed = body.replace(marker, (m) => shim + m)

  // 3) Async-wrap (top-level await is used in the body) and compile with the
  //    injected globals as parameters, exactly like check_workflows.js.
  const wrapped = `return (async () => {\n${shimmed}\n})()`
  const fn = vm.compileFunction(wrapped, INJECTED, { filename: BATCH_JS })

  // 4) Invoke with all eight injected globals stubbed as no-ops. The early return
  //    means none of the orchestration that would actually call them runs, but we
  //    still must pass something callable for any references evaluated before the
  //    shim (there are none today; this is belt-and-suspenders).
  const noop = () => {}
  const stubs = {
    agent: async () => undefined,
    parallel: async () => [],
    pipeline: async () => [],
    phase: noop,
    log: noop,
    args: {},
    budget: {},
    workflow: {},
  }
  return fn(stubs.agent, stubs.parallel, stubs.pipeline, stubs.phase, stubs.log, stubs.args, stubs.budget, stubs.workflow)
}

// Invoke the named parser on a fixture's RAW text, supplying the extra args each
// parser needs to ACCEPT its well-formed fixture (ticketId / original / key).
// These mirror the well-formed fixtures' embedded ids so the well-formed case is
// genuinely accepted rather than rejected on an arg mismatch.
function invokeParser(parsers, parserName, rawText) {
  const fn = parsers[parserName]
  if (typeof fn !== 'function') {
    throw new Error(`contract_seam_runner: unknown parser '${parserName}'`)
  }
  switch (parserName) {
    case 'parseResolveEnvelope':
      // worktreeDir in the well-formed fixture ends with /.worktrees/RUS-1.
      return fn(rawText, 'RUS-1')
    case 'parseRestackEnvelope':
      return fn(rawText, 'RUS-1')
    case 'parseConfigEnvelope':
      // well-formed config fixture has key "linearProject".
      return fn(rawText, 'linearProject')
    case 'parseOrderedTickets':
      // well-formed ordered-tickets fixture is [RUS-1, RUS-2]; the parser
      // requires the returned array to be a permutation of `original` ids.
      return fn(rawText, [{ id: 'RUS-1' }, { id: 'RUS-2' }])
    default:
      // parseSyncTrunkEnvelope, parseCleanupEnvelope, parseLandVerdict,
      // parseCriticsEnvelope take only the text.
      return fn(rawText)
  }
}

async function main(argv) {
  const args = argv.slice(2)
  if (args.length < 2) {
    process.stderr.write('usage: node scripts/contract_seam_runner.js <parser-name> <fixture-path> [<fixture-path>...]\n')
    return 1
  }
  const [parserName, ...fixtures] = args
  const parsers = await loadParsers()
  for (const fixture of fixtures) {
    const rawText = fs.readFileSync(fixture, 'utf8')
    const result = invokeParser(parsers, parserName, rawText)
    process.stdout.write(JSON.stringify({ parser: parserName, fixture, result }) + '\n')
  }
  return 0
}

main(process.argv)
  .then((code) => process.exit(code))
  .catch((err) => {
    process.stderr.write(`contract_seam_runner: ${err && err.stack ? err.stack : err}\n`)
    process.exit(2)
  })
