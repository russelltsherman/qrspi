export const meta = {
  name: 'qrspi-batch',
  description: 'Sequentially run /qrspi-work on every Linear ticket in Agent Skills project currently in Selected status',
  whenToUse: 'After moving a batch of tickets to Selected status in the Agent Skills Linear project',
  phases: [
    { title: 'Query', detail: 'List Selected tickets in Agent Skills' },
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
        required: ['id', 'title'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
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

const { tickets } = await agent(
  `Use the mcp__linear-russelltsherman__list_issues tool to list issues with these arguments:
- project: "f2af2d70-7630-4cbe-884f-711d1f795c1a"
- state: "Selected"
- assignee: "me"
- limit: 50

Return every ticket as { id, title } where id is the human identifier like "RUS-8". Return nothing else.`,
  { label: 'list-selected-tickets', phase: 'Query', schema: TICKETS_SCHEMA }
)

log(`Found ${tickets.length} ticket(s) in Selected status: ${tickets.map(t => t.id).join(', ') || '(none)'}`)

if (tickets.length === 0) {
  return { ticketsProcessed: 0, note: 'No Selected tickets in Agent Skills project' }
}

phase('Work')

const results = []
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  log(`[${i + 1}/${tickets.length}] Starting /qrspi-work on ${t.id}: ${t.title}`)

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
