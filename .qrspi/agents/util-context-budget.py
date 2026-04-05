# QRSPI Context Budget Monitor
# This is a deterministic script, not an LLM agent.
# It runs after each sub-agent call and enforces context limits.


def check_context_budget(session_tokens: int, max_tokens: int) -> dict:
    utilization = session_tokens / max_tokens
    return {
        "utilization_pct": round(utilization * 100, 1),
        "status": (
            "GREEN" if utilization < 0.40 else
            "YELLOW" if utilization < 0.60 else
            "RED"
        ),
        "action": (
            "continue" if utilization < 0.40 else
            "warn_human" if utilization < 0.60 else
            "force_new_session"
        ),
    }
