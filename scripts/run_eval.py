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


def execute_single(
    skill_text: str,
    case: dict,
    trial_id: int,
    timeout_ms: int,
) -> ExecutionResult:
    """Execute a single trial of a single test case.

    In a real implementation, this would:
    1. Spin up an isolated container/sandbox
    2. Initialize the agent with the skill as system prompt
    3. Send the messages and capture the full response
    4. Collect output files from the sandbox

    This stub captures the structure for integration with
    the actual agent runtime.
    """
    start = time.time()
    result = ExecutionResult(
        case_id=case["id"],
        trial_id=trial_id,
    )

    try:
        # ── Placeholder for agent execution ──
        # Replace this block with actual agent invocation:
        #
        #   response = agent.run(
        #       system_prompt=skill_text,
        #       messages=build_messages(case),
        #       tools=<tool_set>,
        #       sandbox=IsolatedContainer(),
        #   )
        #   result.output = response.final_output
        #   result.files = sandbox.list_outputs()
        #   result.tokens = response.usage
        #   result.tool_calls = response.tool_trace
        #   result.transcript = response.full_transcript
        #
        messages = build_messages(case)
        result.output = ""
        result.files = []
        result.tokens = {"input": 0, "output": 0}
        result.tool_calls = []
        result.transcript = messages

    except Exception as e:
        result.error = str(e)

    result.duration_ms = (time.time() - start) * 1000
    return result


def run_suite(config: EvalConfig) -> dict:
    """Run the full eval suite and write results."""
    suite = load_suite(config.suite_path)
    skill_text = load_skill(config.skill_path)

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
    parser.add_argument("--skill", required=True, help="Path to skill/agent prompt file")
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
