# Y-Statements — Compact Decision Format

A Y-statement captures the essence of an architecture decision in a single
structured sentence. Use it as a lightweight alternative to a full ADR, or
embedded inside the "Decision Outcome" of a MADR ADR to crisply summarize the call.

Source: Olaf Zimmermann, "Architectural Decisions — The Making Of"
(Y-statements / WHY-statements).

---

## The template

> In the context of **<use case / user story / component>**,
> facing **<concern / non-functional requirement>**,
> we decided for **<option>**
> and neglected **<other options>**,
> to achieve **<quality / benefit>**,
> accepting that **<downside / trade-off>**.

---

## Slot-by-slot

| Slot | Captures |
|------|----------|
| In the context of | When/where the decision applies (scope) |
| facing | The driving concern or quality attribute at stake |
| we decided for | The chosen option |
| and neglected | The rejected alternatives |
| to achieve | The benefit / quality the choice secures |
| accepting that | The conceded downside or trade-off |

---

## Example

> In the context of the **checkout service**, facing the need for **strong
> consistency on inventory counts**, we decided for **synchronous writes to a
> single primary database** and neglected **eventually-consistent replicas**, to
> achieve **no oversell under concurrent purchases**, accepting that **write
> throughput is capped by the primary and cross-region latency increases**.

---

## When to use

- Spikes, meeting notes, or PR descriptions where a full ADR is too heavy.
- To distill the "Decision Outcome" of a MADR ADR into one quotable line.
- As a precursor that later graduates into a full MADR ADR once accepted.
