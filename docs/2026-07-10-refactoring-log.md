# Refactoring Log — Mindful Blog Workflow Engine

**Date**: 2026-07-10  
**Refactoring Architect**: Solutions Architect / Code Reviewer

## 1. Overview of Changes

Following the Code Review Report, we refactored the codebase to resolve several security, correctness, and architecture concerns. The primary goal was to modularize the 892-line monolithic script, fix a key collision in YAML files, add warnings for hardcoded keys, implement API retries, and clean up duplicate variable declarations.

---

## 2. Refactored Directory Structure

The engine has been successfully modularized from a single monolith into a package structure:

```text
write_blog/
├── engine/
│   ├── __init__.py           # Package definition
│   ├── utils.py              # Shared path and YAML IO utilities
│   ├── parser.py             # Response parsers and word/token metrics
│   ├── openai_client.py      # OpenAI HTTP calls, retry loops, key fetching
│   ├── learning.py           # Prompts and reports for learning loop
│   ├── workflow.py           # Core flow runner & step orchestrator
│   └── run_workflow.py       # Backward-compatible CLI entrypoint
├── tests/
│   ├── test_handoff_parser.py
│   └── test_openai_client.py # Added to test retries and security warnings
└── docs/
    ├── 2026-07-10-code-review-report.md
    └── 2026-07-10-refactoring-log.md (This file)
```

---

## 3. Detailed Fixes & Refactoring Vectors

### Vector 1: Inconsistent YAML Keys (future_self.yaml)
- **Problem**: `future_self.yaml` defined a duplicate-like structure where `include` was declared at the root of `output`. Although valid YAML since keys were at different depths, it caused architectural inconsistency with other skills which used `sections`.
- **Solution**: Changed the root key `include` under `output` in `skills/future_self.yaml` to `sections` to match the project-wide schema standard used in `story_architect.yaml`, etc.

### Vector 2: API Key Leak Prevention Warning
- **Problem**: Storing direct `api_key` in config files is insecure and prone to accidental repository commits.
- **Solution**: Added a `warnings.warn()` message in `get_api_key()` to notify the user if an API key is directly hardcoded in the configuration dictionary rather than referenced via environment variables.

### Vector 3: Dead Code Elimination
- **Problem**: The function `load_step_outputs_from_run()` contained a duplicate definition of the dictionary `outputs`, where the second declaration shadowed and wiped the first.
- **Solution**: Restructured the function inside `engine/workflow.py` to cleanly parse files and JSON without redundant dictionary instantiations.

### Vector 4: API Error Retries with Exponential Backoff
- **Problem**: API calls did not handle temporary HTTP errors (such as 429 Rate Limit, 500 Internal Error, or 503 Service Unavailable), causing a multi-step pipeline run to abort completely on any transient network issue.
- **Solution**: Wrapped the network request inside `call_openai()` in a retry loop using exponential backoff ($2^{\text{attempt}}$ seconds sleep) with a default limit of 3 attempts.

### Vector 5: Modularizing the Monolithic Engine
- **Problem**: `run_workflow.py` was a monolith containing client, parsers, prompts, and CLI logic.
- **Solution**: Split functions into domain-specific files (`utils.py`, `parser.py`, `openai_client.py`, `learning.py`, `workflow.py`). Updated the main CLI script (`run_workflow.py`) to inject the project root directory into `sys.path` and delegate tasks to the core modules.

---

## 4. Verification Evidence

All tests compile and run successfully using standard Python libraries.

### 1. Running Test Suite
We created new unit tests in `tests/test_openai_client.py` to assert correct warning triggers and mock HTTP 429 error retries. Both parser and client unit tests pass:

```powershell
python -m unittest discover -s tests
.....
----------------------------------------------------------------------
Ran 5 tests in 0.003s

OK
```

### 2. Manual Dry Run Check
Executed dry run of the workflow using the modular CLI:
```powershell
python engine/run_workflow.py --input examples/blog_input_template.md --dry-run
Workflow run saved to: D:\Nghiên cứu AI\write_blog\runs\20260710_203238_raw-notes
Full log: D:\Nghiên cứu AI\write_blog\runs\20260710_203238_raw-notes\run_log.md
```

### 3. Dry Run Offline Learning Check
Verified that downstream parsing and local diff calculation function properly:
```powershell
python engine/run_workflow.py --learn-from-run runs/20260710_180536_raw-notes --offline-learning --dry-run
Learning run saved to: D:\Nghiên cứu AI\write_blog\runs\20260710_180536_raw-notes\learning\20260710_203243
Learning report: D:\Nghiên cứu AI\write_blog\runs\20260710_180536_raw-notes\learning\20260710_203243\editorial_learning_report.md
```
