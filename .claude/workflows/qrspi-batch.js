export const meta = {
  name: 'qrspi-batch',
  description: 'Sequentially run /qrspi-work on every assigned Linear ticket currently in Selected or Plan Approved status',
  whenToUse: 'After moving a batch of tickets to Selected or Plan Approved status across any Linear project',
  phases: [
    { title: 'Query', detail: 'List Selected and Plan Approved tickets assigned to me' },
    { title: 'Work', detail: 'Run /qrspi-work on each ticket, one at a time' },
  ],
}

const TICKETS_SCHEMA = {
  type: 'object',
  required: ['tickets'],
  properties: {
    tickets: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'status'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
        },
      },
    },
  },
}

const RESULT_SCHEMA = {
  type: 'object',
  required: ['ticketId', 'newStatus', 'summary'],
  properties: {
    ticketId: { type: 'string' },
    newStatus: { type: 'string' },
    summary: { type: 'string' },
  },
}

phase('Query')

// list_issues accepts only one state per call, so query each status separately
// across all projects, then merge. Plan Approved tickets are further along, so
// process them ahead of Selected tickets.
const STATUSES = ['Plan Approved', 'Selected']

const batches = await parallel(
  STATUSES.map(status => () =>
    agent(
      `Use the mcp__linear-russelltsherman__list_issues tool to list issues with these arguments:
- state: "${status}"
- assignee: "me"
- limit: 250

Do not pass a project argument — include tickets from every project. Return every ticket as { id, title, status } where id is the human identifier like "RUS-8" and status is "${status}". Return nothing else.`,
      { label: `list-${status.toLowerCase().replace(/\s+/g, '-')}-tickets`, phase: 'Query', schema: TICKETS_SCHEMA }
    )
  )
)

// Merge in STATUSES order (Plan Approved first), dedupe by id keeping first seen.
const seen = new Set()
const tickets = []
for (const batch of batches) {
  if (!batch) continue
  for (const t of batch.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    tickets.push(t)
  }
}

log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)

if (tickets.length === 0) {
  return { ticketsProcessed: 0, note: 'No Selected or Plan Approved tickets assigned to me' }
}

phase('Work')

const results = []
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  log(`[${i + 1}/${tickets.length}] Starting /qrspi-work on ${t.id} (${t.status}): ${t.title}`)

  const result = await agent(
    `You are executing the qrspi-work skill orchestrator for Linear ticket ${t.id}.

Procedure:
1. Read .claude/skills/qrspi-work/SKILL.md from the repo root and follow it verbatim for ticket ${t.id}.
2. Do not cd before starting — the SKILL.md sets up its own git worktree at .worktrees/${t.id}/ and cds into it.
3. Run autonomously through the current phase. Stop when the ticket parks at a human review gate (Plan Review or Code Review), reaches Done, or hits an error you cannot recover from.

When finished, return:
- ticketId: "${t.id}"
- newStatus: the ticket's Linear status after this invocation (re-query with mcp__linear-russelltsherman__get_issue_status to confirm)
- summary: one to three sentences on what advanced this run`,
    { label: `qrspi-work:${t.id}`, phase: 'Work', schema: RESULT_SCHEMA }
  )

  if (result) {
    log(`[${i + 1}/${tickets.length}] ${t.id} → ${result.newStatus}`)
    results.push(result)
  } else {
    log(`[${i + 1}/${tickets.length}] ${t.id} skipped or failed`)
  }
}

return {
  ticketsProcessed: results.length,
  results,
}
