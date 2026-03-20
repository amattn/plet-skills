# plet_invoke.py (INV)

> Status: not started

> Subprocess launch + transcript capture. Assembles prompt (via plet_inject_prompt.py), launches `claude -p --output-format stream-json`, tees streaming JSONL to transcript file, returns exit code. This replaces the vague "orchestrator captures transcript" responsibility with deterministic code.
