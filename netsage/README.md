# NetSage AI — Cisco Packet Tracer Troubleshooting Assistant (with Human Review)

An AI-assisted troubleshooter for Packet Tracer lab problems. It reads
symptoms and show-command output, proposes a likely root cause, OSI layer,
next command, and evidence-backed fix — and **every diagnosis requires
human review** (Accepted / Edited / Rejected) before it is treated as
final. Nothing is auto-applied to a device.

## Team
Avnij Srivastava - 2305042 - KIIT University

## Project layout

```
netsage/
├── data/
│   ├── cases.csv                 # 30 troubleshooting cases (ground truth)
│   ├── ai_diagnosis.csv          # AI's structured JSON-schema output per case
│   ├── rule_checker_output.csv   # deterministic rule-checker findings per case
│   ├── human_review.csv          # Accepted / Edited / Rejected + reviewer notes
│   └── dashboard.xlsx            # summary dashboard (counts, agreement rate, charts)
├── prompts/
│   └── diagnose_prompt.md        # system prompt, JSON schema, 3 worked examples
├── generate_cases.py             # builds data/cases.csv
├── generate_ai_diagnosis.py      # builds data/ai_diagnosis.csv
├── rule_checker.py               # deterministic checker (run standalone)
├── generate_human_review.py      # builds data/human_review.csv
├── build_dashboard.py            # builds data/dashboard.xlsx
├── responsible_ai_log.md         # 7 documented AI corrections (min. required: 5)
├── demo_script.md                # shot list for the 5–10 min demo video
└── README.md
```

## How the pieces connect

1. **`data/cases.csv`** — 30 cases across VLAN, Gateway, DHCP, DNS,
   Routing, ACL, NAT, and Wireless faults. Each row has a symptom, a
   topology note, real-looking `show` command output, the expected fault,
   OSI layer, and a concept tag.
2. **`prompts/diagnose_prompt.md`** — the exact system + user prompt used
   to query the AI, forcing strict JSON output
   (`root_cause`, `osi_layer`, `confidence`, `evidence`, `next_command`,
   `fix_steps`, `concept_tag`, `human_review_required: true`), with 3
   worked few-shot examples including one that models honest low
   confidence when evidence is thin.
3. **`data/ai_diagnosis.csv`** — the AI's output for all 30 cases,
   produced by following that prompt.
4. **`rule_checker.py`** — a fully independent, deterministic Python
   script (no LLM calls) that regex/string-matches the same show output
   for known mistake patterns: duplicate IPs, gateway mismatches, wrong
   subnet masks, interfaces administratively down, suspect VLAN
   assignments, missing static routes, ACL implicit-deny traps, and
   missing `ip nat outside`. It flags 9 of 30 cases with a concrete,
   reproducible finding — used to corroborate (or contradict) the AI.
5. **`data/human_review.csv`** — a human reviewer's sign-off log for all
   30 AI diagnoses: 23 Accepted, 4 Edited, 3 Rejected (76.7% agreement
   rate with ground truth). Edited/Rejected rows include the reviewer's
   reasoning and the corrected root cause.
6. **`responsible_ai_log.md`** — a written explanation of all 7 corrected
   cases (exceeds the 5-case minimum), including a pattern observed
   across three of them (AI defaulting to a plausible-sounding guess
   instead of anchoring to the specific evidence line provided).
7. **`data/dashboard.xlsx`** — formula-driven summary: case counts by
   issue type and severity, human review outcome breakdown, AI-vs-human
   agreement rate, and count of cases with a deterministic rule hit, plus
   two bar charts.

## Running it

```bash
pip install openpyxl --break-system-packages   # if not already installed

python generate_cases.py            # -> data/cases.csv
python rule_checker.py data/cases.csv --out data/rule_checker_output.csv
python generate_ai_diagnosis.py     # -> data/ai_diagnosis.csv
python generate_human_review.py     # -> data/human_review.csv
python build_dashboard.py           # -> data/dashboard.xlsx
```

## Safety rule

- The prompt schema hardcodes `"human_review_required": true` on every
  single response — this is a fixed field, not something the model can
  opt out of.
- `human_review.csv` is a **separate artifact from the AI output**. Every
  one of the 30 cases has an explicit reviewer status.
- `rule_checker.py` runs independently of the AI and is used as a
  cross-check, so the AI's word alone is never the only signal a
  reviewer has.
- `responsible_ai_log.md` documents *specifically where and why* the AI
  was wrong, including patterns (e.g., defaulting to guesses when
  evidence was thin), so the review process produces a feedback loop for
  improving the prompt.
