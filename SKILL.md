---
name: quota-tracker
description: Audits and analyzes Antigravity model quota usage, token burn rate, prompt/output ratios, and bloated conversation threads. Use when the user asks about model quotas, token limits, rate limits, or why they are hitting quota exhaustion.
---

# Antigravity Model Quota & Token Usage Tracker

This skill inspects and reports exact token consumption, model distributions, and conversation thread bloat directly from the local Antigravity runtime databases (`~/.gemini/antigravity/conversations/*.db`).

## When to Use

Activate this skill whenever the user:
- Asks about their model quota usage, token limits, or token velocity.
- Encounters "Quota Exceeded", "Rate Limit Hit", or model throttling errors.
- Wants a breakdown of which models (Gemini Flash, Gemini Pro, Claude) or conversation threads are consuming their quota.
- Wants recommendations on pacing, model switching, or conversation compaction.

## Execution Procedure

Run the embedded analyzer script:

```bash
python scripts/analyze_quota.py
```

On Windows machines without global `python` in PATH, locate the local Python runtime or execute:
```powershell
python (Join-Path $PSScriptRoot "scripts\analyze_quota.py")
```

## Interpreting Results & Best Practices

1. **Thread Monoliths**:
   - Every agent turn re-submits the full conversation transcript. Threads with >100 turns or >5M tokens send tens of thousands of tokens *per tool call*.
   - **Recommendation**: Instruct the user to finalize active artifacts and start a fresh conversation.

2. **Model Selection**:
   - **Gemini 3.8 Flash**: Vastly higher RPM/TPM limits. Best for day-to-day coding, terminal commands, and rapid iterations.
   - **Gemini 3.8 Pro / Claude**: Strict rate limits and heavy token burn. Reserve strictly for complex architectural design or multi-system debugging.

3. **Subagent Sprawls**:
   - Spawning parallel subagents (e.g., via `/teamwork-preview`) fires hundreds of concurrent calls, consuming millions of tokens per hour. Advise scoping subagents tightly.
