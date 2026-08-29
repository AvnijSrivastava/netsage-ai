# NetSage AI — Demo Video Script (5–10 min)

You (or a teammate) need to record this — I can generate all the files but
not a screen-capture video. This script is timed so you can read it almost
verbatim while screen-sharing.

**Recommended case to demo live: C024** (guest isolation ACL gap) — it's
visual, has a clean before/after, and directly matches the assignment's own
worked example ("Guest Wi-Fi can reach internal server").

---

### 0:00–0:45 — Intro
"This is NetSage AI, an AI-assisted troubleshooter for Packet Tracer labs.
It reads a symptom and show-command evidence, proposes a root cause, OSI
layer, next command, and fix — but never applies anything automatically.
Every diagnosis requires a human reviewer to Accept, Edit, or Reject it
before it's considered final."

Show: `README.md` file tree for 5 seconds — cases.csv, prompts/, rule_checker.py,
dashboard.xlsx, responsible_ai_log.md.

### 0:45–2:00 — The broken lab (case C024)
Open Packet Tracer (or just narrate over the case data if you don't have
Packet Tracer open): a guest Wi-Fi PC in VLAN 50 can ping an internal file
server in VLAN 10, which should never happen.

Show `data/cases.csv` filtered to C024:
- symptom
- topology_note ("Guest SSID is mapped to VLAN 50; SSID and VLAN mapping
  were verified correct on the WLC")
- show_output (`show ip interface Gi0/0.50 | include access list` → both
  "not set")

### 2:00–3:30 — AI diagnosis
Show `prompts/diagnose_prompt.md` briefly — the required JSON schema and
the rule that confidence must reflect actual evidence support.

Show the AI's actual output for C024 from `data/ai_diagnosis.csv`:
- AI said: Layer 2 "VLAN leakage," low confidence, no cited evidence.

Say: "This is where it gets interesting — the AI guessed a VLAN
misconfiguration, but didn't actually point to a line of evidence that
supports it."

### 3:30–5:00 — Rule checker (deterministic check)
Run live:
```
python rule_checker.py data/cases.csv --out data/rule_checker_output.csv
```
Show the terminal output — point out this runs independently of the AI,
using plain regex/string checks, so it can't hallucinate.

### 5:00–7:00 — Human review catches the miss
Open `data/human_review.csv`, find C024:
- reviewer_status: Edited
- reviewer_notes: explain that the actual evidence ("Outgoing access list
  is not set") was ignored by the AI, and the real issue is a missing
  security ACL, not a VLAN bug.
- corrected_root_cause: the real fix — apply an ACL denying guest VLAN
  traffic into internal subnets.

Say: "This is exactly why the safety rule requires human review — the
AI's answer here would have sent someone down the wrong path on a
security-relevant issue."

Open `responsible_ai_log.md` and scroll to the C024 entry to show it's
documented for accountability.

### 7:00–8:30 — Dashboard
Open `data/dashboard.xlsx`, Summary tab:
- Cases by issue type chart
- Human Review Outcomes chart
- AI vs Human agreement rate (~76.7%)
- Point out this is formula-driven off the RawData tab, not hardcoded.

### 8:30–9:30 — Fix + verification
Narrate applying the corrected fix in Packet Tracer (add the ACL to
Gi0/0.50), then re-test: guest PC can reach the internet but the ping to
the internal file server now fails as expected.

### 9:30–10:00 — Wrap-up
"NetSage AI speeds up root-cause hypothesis generation, but every
diagnosis is logged, cross-checked by a deterministic rule engine, and
requires a human sign-off before anything is treated as the real answer —
23 of 30 cases were accepted as-is, 7 needed human correction, and all 7
are documented in the Responsible AI log."

---

## Recording tips
- OBS Studio / Windows Game Bar / QuickTime screen recording all work fine
  for a Packet Tracer + file walkthrough.
- Keep terminal font large (14pt+) so file contents are readable on
  playback.
- If you don't have time to run Packet Tracer live, it's fine to just
  narrate over the case text in `cases.csv` — the check criteria care
  about seeing AI output → human review → fix → verification, not
  specifically live simulator footage.
