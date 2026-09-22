#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Antigravity Quota Tracker Contributors
"""
Antigravity Quota & Token Usage Analyzer
Audits local SQLite databases and Protobuf telemetry for Google Antigravity.
Zero external dependencies (pure Python standard library).
Cross-platform: Windows, macOS, Linux.
"""

import argparse
import glob
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

def parse_step_metadata(data):
    """Parses Antigravity protobuf step metadata to extract model, token usage, and timestamp."""
    pos = 0
    res = {}
    if not data:
        return res
    while pos < len(data):
        key = 0; shift = 0
        while True:
            if pos >= len(data): return res
            b = data[pos]; pos += 1; key |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        fn = key >> 3; wt = key & 7
        if wt == 0:
            val = 0; shift = 0
            while True:
                if pos >= len(data): return res
                b = data[pos]; pos += 1; val |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
        elif wt == 2:
            length = 0; shift = 0
            while True:
                if pos >= len(data): return res
                b = data[pos]; pos += 1; length |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
            subdata = data[pos:pos+length]
            pos += length
            if fn == 1:  # Timestamp submessage
                sp = 0; ts_sec = None
                while sp < len(subdata):
                    skey = 0; sshift = 0
                    while True:
                        if sp >= len(subdata): break
                        sb = subdata[sp]; sp += 1; skey |= (sb & 0x7f) << sshift
                        if not (sb & 0x80): break
                        sshift += 7
                    sfn = skey >> 3; swt = skey & 7
                    if swt == 0:
                        sval = 0; sshift = 0
                        while True:
                            if sp >= len(subdata): break
                            sb = subdata[sp]; sp += 1; sval |= (sb & 0x7f) << sshift
                            if not (sb & 0x80): break
                            sshift += 7
                        if sfn == 1: ts_sec = sval
                    elif swt == 2:
                        slen = 0; sshift = 0
                        while True:
                            if sp >= len(subdata): break
                            sb = subdata[sp]; sp += 1; slen |= (sb & 0x7f) << sshift
                            if not (sb & 0x80): break
                            sshift += 7
                        sp += slen
                    elif swt == 1: sp += 8
                    elif swt == 5: sp += 4
                    else: break
                if ts_sec: res['timestamp'] = ts_sec
            elif fn == 9:  # Token/Model usage submessage
                sp = 0
                while sp < len(subdata):
                    skey = 0; sshift = 0
                    while True:
                        if sp >= len(subdata): break
                        sb = subdata[sp]; sp += 1; skey |= (sb & 0x7f) << sshift
                        if not (sb & 0x80): break
                        sshift += 7
                    sfn = skey >> 3; swt = skey & 7
                    if swt == 0:
                        sval = 0; sshift = 0
                        while True:
                            if sp >= len(subdata): break
                            sb = subdata[sp]; sp += 1; sval |= (sb & 0x7f) << sshift
                            if not (sb & 0x80): break
                            sshift += 7
                        if sfn == 1: res['model_id'] = sval
                        elif sfn == 2: res['input_tokens'] = sval
                        elif sfn == 3: res['output_tokens'] = sval
                    elif swt == 2:
                        slen = 0; sshift = 0
                        while True:
                            if sp >= len(subdata): break
                            sb = subdata[sp]; sp += 1; slen |= (sb & 0x7f) << sshift
                            if not (sb & 0x80): break
                            sshift += 7
                        sp += slen
                    elif swt == 1: sp += 8
                    elif swt == 5: sp += 4
                    else: break
        elif wt == 1: pos += 8
        elif wt == 5: pos += 4
        else: break
    return res

MODEL_NAMES = {
    1319: "Gemini 3.8 Flash (Fast/Medium)",
    1318: "Gemini 3.8 Pro (Heavy/Reasoning)",
    1322: "Gemini 3.8 Pro Extended / Agentic",
    1298: "Claude 3.5 Sonnet",
    1299: "Claude 3.7 Sonnet",
    1026: "Gemini Flash Default / Fallback",
    1036: "Gemini Pro Experimental",
    1050: "Local / Specialized Agent"
}

def analyze(anonymize=False, data_dir=None):
    if data_dir:
        base_dir = Path(data_dir)
    else:
        base_dir = Path.home() / ".gemini" / "antigravity"

    annotations_dir = base_dir / "annotations"
    conversations_dir = base_dir / "conversations"

    if not conversations_dir.exists():
        print(f"Error: Antigravity conversations directory not found at: {conversations_dir}")
        print("Ensure Google Antigravity is installed and you have run at least one session.")
        sys.exit(1)

    titles = {}
    if annotations_dir.exists():
        for pbtxt in annotations_dir.glob("*.pbtxt"):
            cid = pbtxt.stem
            try:
                with open(pbtxt, "r", encoding="utf-8", errors="ignore") as f:
                    c = f.read()
                    m = re.search(r'title:\s*"([^"]+)"', c)
                    if m:
                        titles[cid] = m.group(1)
            except Exception:
                pass

    convo_stats = {}
    daily_stats = {}
    hourly_recent = {}
    model_stats = {}

    now_ts = datetime.now(timezone.utc).timestamp()
    one_day_ago = now_ts - 86400

    for db_path in conversations_dir.glob("*.db"):
        cid = db_path.stem
        try:
            conn = sqlite3.connect(str(db_path))
            rows = conn.execute("SELECT idx, metadata FROM steps WHERE metadata IS NOT NULL").fetchall()
            for idx, meta in rows:
                info = parse_step_metadata(meta)
                if "input_tokens" in info or "output_tokens" in info:
                    inp = info.get("input_tokens", 0)
                    out = info.get("output_tokens", 0)
                    mod = info.get("model_id", "Unknown")
                    ts = info.get("timestamp")
                    dt = datetime.fromtimestamp(ts, timezone.utc) if ts else None
                    dt_str = dt.strftime("%Y-%m-%d") if dt else "Unknown"

                    if cid not in convo_stats:
                        convo_stats[cid] = {
                            "calls": 0, "input": 0, "output": 0,
                            "first_ts": ts, "last_ts": ts, "models": set()
                        }
                    convo_stats[cid]["calls"] += 1
                    convo_stats[cid]["input"] += inp
                    convo_stats[cid]["output"] += out
                    convo_stats[cid]["models"].add(mod)

                    if dt_str not in daily_stats:
                        daily_stats[dt_str] = {"calls": 0, "input": 0, "output": 0}
                    daily_stats[dt_str]["calls"] += 1
                    daily_stats[dt_str]["input"] += inp
                    daily_stats[dt_str]["output"] += out

                    if mod not in model_stats:
                        model_stats[mod] = {"calls": 0, "input": 0, "output": 0}
                    model_stats[mod]["calls"] += 1
                    model_stats[mod]["input"] += inp
                    model_stats[mod]["output"] += out

                    if ts and ts >= one_day_ago:
                        hour_str = dt.strftime("%Y-%m-%d %H:00 UTC")
                        if hour_str not in hourly_recent:
                            hourly_recent[hour_str] = {"calls": 0, "input": 0, "output": 0}
                        hourly_recent[hour_str]["calls"] += 1
                        hourly_recent[hour_str]["input"] += inp
                        hourly_recent[hour_str]["output"] += out
        except Exception:
            pass

    print("=" * 80)
    print("           ANTIGRAVITY MODEL QUOTA & TOKEN CONSUMPTION AUDIT")
    print("=" * 80)

    total_calls = sum(s["calls"] for s in daily_stats.values())
    total_input = sum(s["input"] for s in daily_stats.values())
    total_output = sum(s["output"] for s in daily_stats.values())
    print(f"\n[GLOBAL METRICS]")
    print(f"  Total LLM Invocations:          {total_calls:,} calls")
    print(f"  Total Prompt / Input Tokens:    {total_input:,} tokens")
    print(f"  Total Completion Tokens:        {total_output:,} tokens")
    print(f"  Cumulative Token Volume:        {total_input + total_output:,} tokens")

    print(f"\n[DAILY TOKEN CONSUMPTION]")
    print(f"  {'Date':<12} | {'Calls':<8} | {'Input Tokens':<15} | {'Output Tokens':<15} | {'Total Tokens':<15}")
    print("  " + "-" * 72)
    for d, s in sorted(daily_stats.items(), reverse=True):
        tot = s["input"] + s["output"]
        print(f"  {d:<12} | {s['calls']:<8,} | {s['input']:<15,} | {s['output']:<15,} | {tot:<15,}")

    print(f"\n[CONSUMPTION BY MODEL]")
    print(f"  {'Model Name (ID)':<40} | {'Calls':<8} | {'Input Tokens':<15} | {'Output Tokens':<15} | {'Total':<15}")
    print("  " + "-" * 100)
    for m, s in sorted(model_stats.items(), key=lambda x: x[1]["input"] + x[1]["output"], reverse=True):
        mname = f"{MODEL_NAMES.get(m, f'Model #{m}')} ({m})"
        tot = s["input"] + s["output"]
        print(f"  {mname:<40} | {s['calls']:<8,} | {s['input']:<15,} | {s['output']:<15,} | {tot:<15,}")

    print(f"\n[TOKEN DRAIN BY TOP CONVERSATION THREADS]")
    print(f"  {'Conversation Title':<42} | {'Calls':<8} | {'Total Tokens':<15} | {'Avg Prompt Tokens'}")
    print("  " + "-" * 90)
    for i, (c, s) in enumerate(sorted(convo_stats.items(), key=lambda x: x[1]["input"] + x[1]["output"], reverse=True)[:10], 1):
        if anonymize:
            title = f"Thread #{i} ({c[:8]}...)"
        else:
            title = titles.get(c, f"Thread ({c[:8]}...)")
        if len(title) > 40:
            title = title[:37] + "..."
        tot = s["input"] + s["output"]
        avg_inp = int(s["input"] / s["calls"]) if s["calls"] else 0
        print(f"  {title:<42} | {s['calls']:<8,} | {tot:<15,} | {avg_inp:<15,}")

    last_24h_input = sum(h["input"] for h in hourly_recent.values())
    last_24h_output = sum(h["output"] for h in hourly_recent.values())
    last_24h_calls = sum(h["calls"] for h in hourly_recent.values())
    print(f"\n[ACTIVE VELOCITY (PAST 24 HOURS)]")
    print(f"  Calls in last 24h: {last_24h_calls:,}")
    print(f"  Tokens consumed in last 24h: {last_24h_input + last_24h_output:,}")

    if hourly_recent:
        print(f"\n  Recent Hourly Breakdown:")
        for h, s in sorted(hourly_recent.items(), reverse=True)[:6]:
            print(f"    {h}: {s['calls']} calls, {s['input']+s['output']:,} tokens (Avg prompt: {int(s['input']/s['calls']):,} tok)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity Quota & Token Usage Analyzer")
    parser.add_argument("--anonymize", action="store_true", help="Mask conversation titles for clean public sharing")
    parser.add_argument("--data-dir", type=str, default=None, help="Custom path to Antigravity directory (defaults to ~/.gemini/antigravity)")
    args = parser.parse_args()
    analyze(anonymize=args.anonymize, data_dir=args.data_dir)
