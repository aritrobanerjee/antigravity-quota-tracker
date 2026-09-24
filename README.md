# Antigravity Model Quota & Token Usage Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Platform: Cross--Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

A lightweight, zero-dependency diagnostic tool and **Antigravity Skill** that analyzes local SQLite conversation databases and decodes internal Protobuf telemetry to audit model quotas, token burn rates, and thread bloat across your Google Antigravity IDE workspaces.

---

## Why This Exists: Diagnosing Antigravity Quota & Rate Limit Issues

When working with autonomous agent loops in Google Antigravity (under Google AI Pro, Google One, or internal subscriptions), developers and practitioners frequently encounter unexpected rate limits and quota exhaustion errors, such as:
* `ResourceExhausted: 429 Quota exceeded for quota metric`
* `Rate limit exceeded for model: gemini-3.8-pro` / `gemini-3.8-flash`
* `Daily model quota reached` / `Temporary model throttling`

Because Antigravity's UI only shows a high-level meter or sudden error popups without granular telemetry, it is difficult to determine whether you exhausted your **Requests-Per-Minute (RPM)**, **Tokens-Per-Minute (TPM)**, or **Daily Token Allowance**.

Antigravity actually persists comprehensive telemetry locally inside binary Protobuf messages within `~/.gemini/antigravity/conversations/*.db`. This tool decodes that database to reveal:
- **Lifetime & Daily Token Consumption** (Prompt/Input tokens vs. Completion/Output tokens).
- **Model Distribution & Rate Limits** (Gemini 3.8 Flash, Gemini 3.8 Pro, Claude 3.5/3.7 Sonnet).
- **Thread Monolith Detection**: Pinpoints runaway conversation threads that re-transmit tens of thousands of conversation history tokens on every single tool call.

### How Does This Differ from Antigravity's Built-in `/quota`?

> **A Gas Gauge vs. An Engine Flight Recorder**
> * **Built-in `/quota`**: Shows a point-in-time capacity snapshot (*"You have 15% quota remaining"*).
> * **`antigravity-quota-tracker`**: Shows root-cause forensic attribution (*"Thread X reached 941 turns and burned 10.2M tokens because context wasn't compacted"*).
>
> Use `/quota` to check **how much** capacity you have left. Use `antigravity-quota-tracker` to see **where it went and how to stop burning it**.

---


## Sample Output

```text
================================================================================
           ANTIGRAVITY MODEL QUOTA & TOKEN CONSUMPTION AUDIT
================================================================================

[GLOBAL METRICS]
  Total LLM Invocations:          3,277 calls
  Total Prompt / Input Tokens:    33,602,340 tokens
  Total Completion Tokens:        2,124,221 tokens
  Cumulative Token Volume:        35,726,561 tokens (~35.7M)

[DAILY TOKEN CONSUMPTION]
  Date         | Calls    | Input Tokens    | Output Tokens   | Total Tokens   
  ------------------------------------------------------------------------
  2026-09-22   | 918      | 9,236,369       | 715,230         | 9,951,599      
  2026-09-21   | 919      | 9,055,653       | 567,493         | 9,623,146      
  2026-09-20   | 793      | 7,393,405       | 379,828         | 7,773,233      

[CONSUMPTION BY MODEL]
  Model Name (ID)                          | Calls    | Input Tokens    | Output Tokens   | Total          
  ---------------------------------------------------------------------------------------------------
  Gemini 3.8 Pro Extended / Agentic (1322) | 1,428    | 12,970,753      | 1,104,767       | 14,075,520     
  Gemini 3.8 Flash (Fast/Medium) (1319)    | 1,024    | 11,065,521      | 476,754         | 11,542,275     
  Claude 3.5 Sonnet (1298)                 | 342      | 4,278,734       | 195,786         | 4,474,520      
  Gemini 3.8 Pro (Heavy/Reasoning) (1318)  | 300      | 3,124,611       | 202,049         | 3,326,660      

[TOKEN DRAIN BY TOP CONVERSATION THREADS]
  Conversation Title                         | Calls    | Total Tokens    | Avg Prompt Tokens
  ------------------------------------------------------------------------------------------
  Feature Architecture Discussion            | 941      | 10,242,814      | 10,337         
  Markdown Resume Development Workflow       | 296      | 3,270,853       | 10,400         
  Using Local Models In Antigravity          | 220      | 3,249,956       | 14,373         
```

---

## Installation

### Option 1: Install as a Global Antigravity Skill (Recommended)

To make this skill automatically available to agents in **all** your workspaces:

**macOS / Linux:**
```bash
git clone https://github.com/aritrobanerjee/antigravity-quota-tracker.git ~/.gemini/config/skills/quota-tracker
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/aritrobanerjee/antigravity-quota-tracker.git "$env:USERPROFILE\.gemini\config\skills\quota-tracker"
```

Once installed, simply ask any Antigravity agent in chat:
> *"Audit my quota usage."* or *"Why am I hitting rate limits?"*

The agent will automatically activate the skill and report your live token metrics.

---

### Option 2: Standalone CLI Usage

Requires Python 3.8+ (uses only Python standard library: `sqlite3`, `pathlib`, `glob`, `re`, `datetime`).

```bash
# Clone the repository
git clone https://github.com/aritrobanerjee/antigravity-quota-tracker.git
cd antigravity-quota-tracker

# Run the analyzer
python scripts/analyze_quota.py
```

---

## How to Fix & Prevent Antigravity Quota Exhaustion

Based on real-world telemetry audits across millions of tokens, here are the most effective strategies to prevent hitting quota limits in Antigravity:

1. **Prevent "Thread Monoliths" (High Impact)**:
   * Antigravity re-submits the full conversation transcript on every single user turn and tool call.
   * Long threads (>100 turns) accumulate massive context windows, causing even a 1-line prompt to send 30,000–60,000+ tokens *per invocation*.
   * **Action**: When an initiative is completed or code is written to disk, start a fresh conversation session.

2. **Model Tiering (Flash for Execution, Pro for Architecture)**:
   * **Gemini 3.8 Flash** has substantially higher Requests-Per-Minute (RPM) and daily token limits under Google AI subscriptions.
   * **Gemini 3.8 Pro / Claude 3.7** burn quota rapidly on repetitive terminal commands or file reads.
   * **Action**: Keep Gemini 3.8 Flash active as your primary driver for coding, editing, and execution. Switch to Pro only for initial architecture plans, then switch back to Flash.

3. **Limit Unbounded Subagents**:
   * Running multi-agent commands like `/teamwork-preview` spawns multiple parallel agents that can fire hundreds of calls within minutes.
   * **Action**: Scope subagents to targeted folders rather than whole-repo scans.

---

## Privacy & Security

- **100% Local**: No tokens, telemetry, or conversation data leave your machine.
- **Zero Dependencies**: Pure Python standard library with no external network requests or pip dependencies.
- **Read-Only**: Performs read-only queries against local SQLite database files without modifying any Antigravity internal state.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Disclaimer

This is an independent community open-source project and is not affiliated with, sponsored by, or endorsed by Google, Alphabet Inc., or Anthropic. All product names, logos, and brands are property of their respective owners.

