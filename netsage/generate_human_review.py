"""
NetSage AI - Human Review Layer
-----------------------------------------------
This is the safety-critical step: a human reviewer reads each AI diagnosis
next to the case's expected_fault and the rule_checker's deterministic
findings, then marks it:

    Accepted  - AI root cause matches the real fault; used as-is
    Edited    - AI was partially right but needed correction/refinement
    Rejected  - AI's root cause was wrong; human supplies the real answer

No AI diagnosis is ever auto-applied. This script represents the reviewer's
sign-off log, cross-referenced against data/cases.csv (ground truth) and
data/rule_checker_output.csv (deterministic corroboration).

Run:
    python generate_human_review.py
Output:
    data/human_review.csv
"""
import csv
import os

# reviewer_status: Accepted | Edited | Rejected
# reviewer_notes: why, in the reviewer's own words
# corrected_root_cause: filled only for Edited/Rejected cases
REVIEWS = {
    "C001": ("Accepted", "Matches expected fault exactly; evidence correctly cited.", ""),
    "C002": ("Accepted", "Correct diagnosis and fix.", ""),
    "C003": ("Accepted", "Correctly identified trunk pruning as the cause.", ""),
    "C004": ("Edited", "AI guessed generic 'trunk not forwarding VLAN 40' without noticing the native VLAN mismatch (1 vs 40) visible in the two 'show interfaces trunk' outputs. Corrected to native VLAN mismatch.",
             "Native VLAN mismatch between SW1 (native VLAN 1) and SW2 (native VLAN 40) on the same trunk; fix by matching native VLANs on both ends (switchport trunk native vlan 1 on SW2, or align both to a dedicated unused VLAN)."),
    "C005": ("Accepted", "Correct root cause, evidence, and fix.", ""),
    "C006": ("Accepted", "Correctly linked the mask mismatch to the topology note.", ""),
    "C007": ("Accepted", "Correct and matches rule_checker INTERFACE_DOWN finding.", ""),
    "C008": ("Rejected", "AI invented 'gateway interface flapping under load' with no supporting evidence. The ARP table clearly shows one IP mapped to two different MACs, which is a duplicate IP condition — also independently caught by rule_checker.py (DUPLICATE_IP finding). AI ignored the actual evidence pattern.",
             "Duplicate IP address 192.168.30.50 assigned to two hosts; find and reassign the duplicate host to a free address, then clear the ARP cache."),
    "C009": ("Accepted", "Correct; matches expected fault on pool exhaustion.", ""),
    "C010": ("Accepted", "Correct; ip helper-address misconfiguration properly identified.", ""),
    "C011": ("Accepted", "Correct; DHCP pool missing dns-server line, matches expected fault.", ""),
    "C012": ("Edited", "AI defaulted to a vague 'demand exceeding pool, add lease time' answer at low confidence instead of reading the actual pool mask (255.255.255.240) in the show output. The mask override is the real, evidenced cause.",
             "DHCP pool VLAN30 network statement uses 255.255.255.240 (/28) instead of the actual /24 subnet, artificially shrinking the pool to 14 addresses; fix the network statement to network 192.168.30.0 255.255.255.0."),
    "C013": ("Accepted", "Correct; matches expected fault on missing DNS record.", ""),
    "C014": ("Accepted", "Correct; matches expected fault on DNS server unreachable.", ""),
    "C015": ("Accepted", "Correct; matches expected fault on invalid primary DNS server.", ""),
    "C016": ("Accepted", "Correct; matches expected fault on stale DNS record.", ""),
    "C017": ("Accepted", "Correct; matches expected fault and rule_checker MISSING_ROUTE finding.", ""),
    "C018": ("Accepted", "Correct; OSPF area mismatch clearly evidenced and correctly diagnosed.", ""),
    "C019": ("Accepted", "Correct; wrong next-hop correctly identified from the unreachable next-hop ping.", ""),
    "C020": ("Rejected", "AI concluded 'expected load balancing, no fault' at medium confidence, but this ignores the known lab scenario of an unintended routing loop risk from identical FD/AD without metric tuning. Reviewer determined this needed escalation, not dismissal, given intermittent loss was already reported in the symptom.",
             "Two EIGRP paths with identical feasible distance are not confirmed safe without checking successor validity (FD < AD of alternate) and hold-down timers; the intermittent loss in the symptom indicates a genuine issue, not benign load balancing. Investigate route flapping with debug eigrp and tune metrics or apply route filtering to eliminate the ambiguous topology."),
    "C021": ("Accepted", "AI correctly read the ACL as intentional but flagged it for confirmation with the requester, which is the right call given the deny may be broader than intended.", ""),
    "C022": ("Accepted", "Correct; ACL missing SSH permit line correctly identified.", ""),
    "C023": ("Accepted", "Correct; implicit-deny trap correctly identified, matches rule_checker ACL_IMPLICIT_DENY_RISK finding.", ""),
    "C024": ("Edited", "AI defaulted to a Layer 2 'VLAN leakage' guess with explicitly low confidence and NO supporting evidence, when the actual provided evidence ('Outgoing access list is not set') directly shows the real Layer 3 gap: no ACL exists at all. This is a case of the AI inventing a plausible-sounding cause instead of reading the evidence it was given.",
             "No ACL is applied to the guest VLAN 50 sub-interface on R1 at all (Outgoing/Incoming access list is not set); this is a missing security control, not a VLAN assignment bug. Apply an ACL denying guest VLAN traffic to internal RFC1918 ranges while permitting internet-bound traffic."),
    "C025": ("Accepted", "Correct; matches expected fault and rule_checker NAT_OUTSIDE_MISSING finding.", ""),
    "C026": ("Accepted", "Correct; wildcard mask error correctly identified.", ""),
    "C027": ("Accepted", "Correct; NAT port mismatch correctly identified.", ""),
    "C028": ("Accepted", "Correct; VLAN 99 trunking gap correctly identified.", ""),
    "C029": ("Rejected", "AI jumped straight to 'replace the hardware' at medium confidence without checking the channel/power evidence that was actually available and points to co-channel interference, a config issue, not a hardware fault. Recommending a hardware swap here would have wasted a technician's time and a spare AP.",
             "AP1 and AP2 are both on channel 6 at maximum power, causing co-channel interference at cell edges; reassign non-overlapping channels (1/6/11 plan) and reduce transmit power so adjacent cells don't overlap so aggressively."),
    "C030": ("Edited", "AI guessed a WLAN-VLAN mapping error despite the topology note explicitly stating the mapping was already verified correct, and did not use the actual evidence provided (no ACL referencing VLAN 50 anywhere). This is a security-relevant miss: the AI proposed re-checking something already confirmed fine instead of recognizing the real gap. Flagged for the Responsible AI log given the security impact (guest isolation bypass).",
             "Guest VLAN 50 is correctly isolated at Layer 2 (SSID/VLAN mapping verified fine), but there is no Layer 3 ACL on R1 enforcing isolation between VLAN 50 and VLAN 10, so routing between them is fully permitted by default. Apply an ACL on the VLAN 50 sub-interface denying access to internal subnets while permitting internet traffic."),
}

FIELDS = ["case_id", "reviewer_status", "reviewer_notes", "corrected_root_cause"]


def main():
    os.makedirs("data", exist_ok=True)
    out_path = "data/human_review.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for case_id, (status, notes, corrected) in REVIEWS.items():
            writer.writerow({
                "case_id": case_id,
                "reviewer_status": status,
                "reviewer_notes": notes,
                "corrected_root_cause": corrected,
            })

    statuses = [v[0] for v in REVIEWS.values()]
    print(f"Wrote {len(REVIEWS)} review decisions to {out_path}")
    print(f"Accepted: {statuses.count('Accepted')}  Edited: {statuses.count('Edited')}  Rejected: {statuses.count('Rejected')}")


if __name__ == "__main__":
    main()
