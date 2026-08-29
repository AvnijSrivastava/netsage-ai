# NetSage AI — Responsible AI Log

This log documents every case in which a human reviewer **edited or
rejected** the AI's diagnosis, why it was wrong, and what the corrected
answer is. This is the core safety artifact for the project: it shows
the human-review gate actually catching AI mistakes rather than being a
rubber stamp.

**Summary:** 30 cases reviewed → 23 Accepted, 4 Edited, 3 Rejected.
**7 of 30 (23%) required human correction** — exceeding the minimum of 5.

---

## 1. Case C004 — VLAN native mismatch (Edited)

- **AI said:** Generic "trunk not forwarding VLAN 40," recommending a
  check of the allowed-VLAN list.
- **What was actually wrong:** The AI failed to notice that the two
  `show interfaces trunk` outputs list *different native VLANs* (1 on
  SW1, 40 on SW2) on the same trunk — a classic native VLAN mismatch,
  not an allowed-VLAN pruning issue.
- **Why it matters:** The AI's suggested fix (checking allowed VLANs)
  would not have solved the problem and would have sent a junior
  engineer down the wrong troubleshooting path.
- **Corrected root cause:** Native VLAN mismatch between SW1 (native
  VLAN 1) and SW2 (native VLAN 40); align native VLANs on both ends.

## 2. Case C008 — Duplicate IP misread as interface flapping (Rejected)

- **AI said:** "Gateway interface flapping under load" — not supported
  by any evidence in the case.
- **What was actually wrong:** The ARP table evidence directly shows
  one IP address (192.168.30.50) mapped to two different MAC
  addresses — a textbook duplicate-IP condition. This was also
  independently flagged by `rule_checker.py` (`DUPLICATE_IP` finding),
  which the AI's answer contradicted.
- **Why it matters:** This is the clearest example in the dataset of
  the AI inventing a plausible-sounding cause instead of reading the
  evidence it was given — exactly the failure mode human review exists
  to catch.
- **Corrected root cause:** Duplicate IP 192.168.30.50 assigned to two
  hosts; identify and reassign the duplicate.

## 3. Case C012 — DHCP pool mask override missed (Edited)

- **AI said:** Vague "demand exceeding pool, add lease time" advice at
  low confidence.
- **What was actually wrong:** The DHCP pool's `network` statement in
  the show output uses a `/28` mask (255.255.255.240) instead of the
  actual `/24` subnet — a specific, evidenced misconfiguration the AI
  did not read closely enough to catch.
- **Corrected root cause:** DHCP pool VLAN30 network statement uses
  255.255.255.240 instead of 255.255.255.0, shrinking the pool to 14
  usable addresses.

## 4. Case C020 — EIGRP loop risk dismissed as normal (Rejected)

- **AI said:** "Expected load balancing, no fault," at medium
  confidence.
- **What was actually wrong:** The AI dismissed a genuine reported
  symptom (intermittent loss) by assuming identical feasible distances
  across two paths are automatically safe, without checking successor
  validity or hold-down timer alignment.
- **Why it matters:** This is a case of the AI being *overconfident in
  a "nothing to see here" direction* — arguably more dangerous than a
  wrong-but-cautious answer, because it could cause a real issue to be
  closed without investigation.
- **Corrected root cause:** Needs further investigation (`debug eigrp`,
  metric tuning, or route filtering) before being called safe.

## 5. Case C024 — Security gap misclassified as VLAN bug (Edited)

- **AI said:** Low-confidence guess of "Layer 2 VLAN leakage,"
  explicitly admitting no supporting evidence.
- **What was actually wrong:** The actual evidence provided (`Outgoing
  access list is not set` / `Incoming access list is not set`) directly
  shows the real gap: **no ACL exists at all** on the guest VLAN's
  router sub-interface. This is a missing security control, not a
  connectivity bug — a meaningful difference for how it should be
  triaged and prioritized.
- **Responsible AI significance:** This case mirrors the "Guest Wi-Fi
  can reach internal server" example in the assignment brief. A
  security-relevant miss like this is exactly why human review is a
  hard requirement here, not an optional QA step.
- **Corrected root cause:** No ACL is applied to the guest VLAN 50
  sub-interface; add one enforcing isolation from internal subnets.

## 6. Case C029 — Hardware swap recommended without checking evidence (Rejected)

- **AI said:** "AP1's radio hardware is likely failing, replace the
  unit," at medium confidence.
- **What was actually wrong:** The case evidence (both APs on channel 6
  at max power) directly supports co-channel interference, a
  configuration issue — but the AI's response text doesn't reference
  that evidence at all, instead jumping to a hardware conclusion.
- **Why it matters:** Following this recommendation would have wasted a
  technician's time and a spare AP on an unnecessary hardware swap.
- **Corrected root cause:** Co-channel interference from both APs on
  channel 6 at max power; apply a 1/6/11 channel plan and reduce power.

## 7. Case C030 — Re-checking an already-verified fact instead of using given evidence (Edited)

- **AI said:** "WLAN-VLAN mapping is likely misconfigured," at medium
  confidence — despite the topology note explicitly stating the
  mapping was already verified correct.
- **What was actually wrong:** The AI ignored the topology note and the
  actual evidence given (`show access-lists` returning no ACL
  referencing VLAN 50 at all), and proposed re-verifying something
  already confirmed instead of identifying the real gap.
- **Responsible AI significance:** A second guest-isolation case in
  this dataset where the AI failed to flag a security control gap —
  reinforcing that this is a systematic pattern (the AI tends to
  default to "VLAN mapping" explanations for wireless isolation issues
  rather than checking whether a Layer 3 ACL exists) worth watching in
  future prompt iterations.
- **Corrected root cause:** No Layer 3 ACL enforces isolation between
  guest VLAN 50 and internal VLAN 10 on R1; VLAN mapping itself was
  fine.

---

## Pattern observed across corrections

Three of the seven corrections (C024, C029, C030) share a common
failure mode: **the AI proposed a plausible generic explanation instead
of anchoring its answer to the specific evidence line(s) provided.**
This directly motivated the `evidence` field requirement in
`prompts/diagnose_prompt.md`, which forces the model to point at a
specific line of show-command output — cases where the `evidence` field
is vague or unsupported (as in C008, C024, C029, C030) are treated as a
signal to weight the diagnosis toward "Reject" during review, and are a
good target for future prompt tightening (e.g., explicitly instructing
the model to output "insufficient evidence" rather than a low-confidence
guess when no evidence line supports a conclusion).
