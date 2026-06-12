#!/usr/bin/env python3
"""Execute an eval suite against a skill/agent prompt version.

Runs each test case multiple trials in isolated environments,
capturing full transcripts, outputs, and metrics.
"""

import argparse
import json
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class ExecutionResult:
    case_id: str
    trial_id: int
    output: str = ""
    files: list = field(default_factory=list)
    duration_ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    error: Optional[str] = None
    executed: bool = False


@dataclass
class EvalConfig:
    skill_path: str
    suite_path: str
    output_dir: str
    trials: int = 3
    max_workers: int = 4
    timeout_ms: int = 120000


def load_suite(suite_path: str) -> dict:
    """Load and validate the eval suite definition."""
    with open(suite_path) as f:
        suite = json.load(f)

    required = {"name", "cases"}
    missing = required - set(suite.keys())
    if missing:
        raise ValueError(f"Suite missing required fields: {missing}")

    for case in suite["cases"]:
        case_required = {"id", "prompt", "assertions"}
        case_missing = case_required - set(case.keys())
        if case_missing:
            raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")

    return suite


def load_skill(skill_path: str) -> str:
    """Load the agent prompt / skill text."""
    with open(skill_path) as f:
        return f.read()


def build_messages(case: dict) -> list:
    """Build the message sequence for a test case."""
    messages = []

    # Include conversation history if present
    history = case.get("context", {}).get("conversation_history", [])
    messages.extend(history)

    # Load fixture files as context
    context_files = case.get("context", {}).get("files", [])
    file_context_parts = []
    for file_path in context_files:
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()
            file_context_parts.append(f"--- {file_path} ---\n{content}")

    # Build the user message
    user_content = case["prompt"]
    if file_context_parts:
        user_content += "\n\n" + "\n\n".join(file_context_parts)

    messages.append({"role": "user", "content": user_content})
    return messages


def call_model(
    system: str,
    messages: list,
    model: str,
    max_tokens: int,
    timeout_s: float,
) -> dict:
    """Single mockable seam wrapping the Anthropic Messages API.

    Returns the loose ``ModelReply`` shape::

        {
            "output": str,
            "tokens": {"input": int, "output": int},
            "raw_transcript_turn": dict,
        }

    ``anthropic`` is imported locally so module import / test collection never
    pulls in the SDK; tests stub this function to run fully offline. The API key
    is read from the SDK's standard environment variable (``ANTHROPIC_API_KEY``)
    and ``timeout_s`` is applied as the per-request timeout.
    """
    import anthropic  # local import: keeps the SDK out of module import

    client = anthropic.Anthropic(timeout=timeout_s)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    # Concatenate text blocks from the response content.
    output_parts = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            output_parts.append(text)
    output = "".join(output_parts)

    # Normalize SDK usage into the existing {input, output} token shape.
    usage = getattr(response, "usage", None)
    tokens = {
        "input": getattr(usage, "input_tokens", 0) if usage else 0,
        "output": getattr(usage, "output_tokens", 0) if usage else 0,
    }

    # Assistant turn for the transcript, expressed as plain dicts.
    raw_transcript_turn = {"role": "assistant", "content": output}

    return {
        "output": output,
        "tokens": tokens,
        "raw_transcript_turn": raw_transcript_turn,
    }


def execute_single(
    skill_text: str,
    case: dict,
    trial_id: int,
    timeout_ms: int,
    model: str,
    max_tokens: int,
) -> ExecutionResult:
    """Execute a single trial of a single test case.

    Builds the message sequence via ``build_messages`` and invokes the model
    through the ``call_model`` seam (the system prompt is the skill text). On a
    successful return it populates ``output``, ``tokens`` (normalized to the
    ``{input, output}`` shape), ``transcript`` (input messages + the assistant
    turn), and sets ``executed = True``. Any exception — including a request
    timeout — is captured into ``result.error`` with ``executed`` left ``False``.

    ``files`` and ``tool_calls`` stay empty: the SDK seam does not surface
    sandbox files or a tool trace.
    """
    start = time.time()
    result = ExecutionResult(
        case_id=case["id"],
        trial_id=trial_id,
    )

    messages = build_messages(case)
    try:
        reply = call_model(
            system=skill_text,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            timeout_s=timeout_ms / 1000,
        )
        result.output = reply["output"]
        result.tokens = reply["tokens"]
        result.files = []
        result.tool_calls = []
        result.transcript = messages + [reply["raw_transcript_turn"]]
        result.executed = True

    except Exception as e:
        result.error = str(e)
        result.executed = False

    result.duration_ms = (time.time() - start) * 1000
    return result


def run_suite(config: EvalConfig) -> dict:
    """Run the full eval suite and write results."""
    suite = load_suite(config.suite_path)
    skill_text = load_skill(config.skill_path)

    # Model id + max_tokens come from suite.json `defaults`. Both are required
    # to make a real model call; a missing key is a hard error with a clear
    # message rather than a silent fallback (the questions suite, for example,
    # declares max_tokens but no model — that must surface, not be papered over).
    defaults = suite.get("defaults", {})
    if "model" not in defaults:
        raise ValueError(
            "Suite `defaults.model` is required to execute the model call; "
            f"none found in {config.suite_path}"
        )
    if "max_tokens" not in defaults:
        raise ValueError(
            "Suite `defaults.max_tokens` is required to execute the model call; "
            f"none found in {config.suite_path}"
        )
    model = defaults["model"]
    max_tokens = defaults["max_tokens"]

    # Create output directory
    os.makedirs(config.output_dir, exist_ok=True)

    # Compute skill version hash
    skill_hash = hashlib.sha256(skill_text.encode()).hexdigest()[:12]

    all_results = []
    cases = suite["cases"]
    total_runs = len(cases) * config.trials

    print(f"Running {total_runs} executions ({len(cases)} cases x {config.trials} trials)")
    print(f"Skill hash: {skill_hash}")
    print(f"Max workers: {config.max_workers}")
    print()

    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {}
        for case in cases:
            for trial in range(config.trials):
                future = executor.submit(
                    execute_single,
                    skill_text,
                    case,
                    trial,
                    config.timeout_ms,
                    model,
                    max_tokens,
                )
                futures[future] = (case["id"], trial)

        completed = 0
        for future in as_completed(futures):
            case_id, trial = futures[future]
            completed += 1
            try:
                result = future.result()
                all_results.append(asdict(result))
                status = "ERROR" if result.error else "OK"
                print(f"  [{completed}/{total_runs}] {case_id} trial={trial} {status} ({result.duration_ms:.0f}ms)")
            except Exception as e:
                print(f"  [{completed}/{total_runs}] {case_id} trial={trial} EXCEPTION: {e}")
                all_results.append({
                    "case_id": case_id,
                    "trial_id": trial,
                    "error": str(e),
                })

    # Write results
    output = {
        "skill_hash": skill_hash,
        "skill_path": config.skill_path,
        "suite": suite["name"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "trials": config.trials,
            "timeout_ms": config.timeout_ms,
        },
        "results": all_results,
    }

    output_path = os.path.join(config.output_dir, "results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to {output_path}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Run QRSPI eval suite")
    # --skill is the primary name; --agent is an alias resolving to the same
    # dest (args.skill), so everything downstream is unchanged. Exactly one of
    # the two must be supplied.
    skill_group = parser.add_mutually_exclusive_group(required=True)
    skill_group.add_argument(
        "--skill", dest="skill", help="Path to skill/agent prompt file"
    )
    skill_group.add_argument(
        "--agent",
        dest="skill",
        help="Alias for --skill (path to skill/agent prompt file)",
    )
    parser.add_argument("--suite", required=True, help="Path to eval suite JSON")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--trials", type=int, default=3, help="Trials per case (default: 3)")
    parser.add_argument("--workers", type=int, default=4, help="Max parallel workers (default: 4)")
    parser.add_argument("--timeout", type=int, default=120000, help="Timeout per execution in ms")
    args = parser.parse_args()

    config = EvalConfig(
        skill_path=args.skill,
        suite_path=args.suite,
        output_dir=args.output,
        trials=args.trials,
        max_workers=args.workers,
        timeout_ms=args.timeout,
    )

    run_suite(config)


if __name__ == "__main__":
    main()
