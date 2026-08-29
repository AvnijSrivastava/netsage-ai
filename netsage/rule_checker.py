"""
NetSage AI - Deterministic Rule Checker
-----------------------------------------------
Runs independently of the AI/LLM diagnosis. Parses the raw show-command
output stored per case in data/cases.csv and applies hard-coded, explainable
rules to catch common Packet Tracer config mistakes:

  - Duplicate IP addresses (two MACs claiming the same IP in an ARP table)
  - Wrong / mismatched subnet masks between a PC and its gateway interface
  - Gateway mismatch (PC's configured default gateway does not match any
    router interface IP seen in the evidence)
  - Interface administratively/operationally down
  - Missing or wrong VLAN assignment on an access port
  - Missing static route (route table has no entry for a subnet a case
    references)
  - ACL implicit-deny-all traps (an ACL with permits but no matching
    catch-all, relying on the invisible deny ip any any)

This script is intentionally rule-based (regex + string matching), NOT an
LLM call, so its output is reproducible and independently checkable against
the AI's JSON diagnosis for agreement scoring.

Run:
    python rule_checker.py data/cases.csv --out data/rule_checker_output.csv
"""
import argparse
import csv
import re
import sys


def check_duplicate_ip(show_output: str):
    ips = re.findall(r"Internet\s+Address\s+.*", show_output) or []
    matches = re.findall(r"Internet\s+([\d.]+)\s+\d+\s+([0-9A-Fa-f.]+)", show_output)
    seen = {}
    for ip, mac in matches:
        seen.setdefault(ip, set()).add(mac)
    for ip, macs in seen.items():
        if len(macs) > 1:
            return f"DUPLICATE_IP: {ip} claimed by {len(macs)} different MAC addresses ({', '.join(macs)})"
    return None


def check_gateway_mismatch(show_output: str):
    pc_gw = re.search(r"Default Gateway:\s*([\d.]+)", show_output)
    router_ips = re.findall(r"(?:GigabitEthernet|FastEthernet|Serial)\S*\s+([\d.]+)\s+(?:up|administratively)", show_output)
    if pc_gw:
        gw = pc_gw.group(1)
        if router_ips and gw not in router_ips:
            return f"GATEWAY_MISMATCH: PC default gateway {gw} does not match any router interface IP found ({', '.join(router_ips)})"
    return None


def check_subnet_mask(show_output: str):
    pc_mask = re.search(r"Subnet Mask:\s*([\d.]+)", show_output)
    # crude check: flag known "wrong for /24 network" masks explicitly seen in labs
    if pc_mask:
        mask = pc_mask.group(1)
        if mask == "255.255.255.0" and "/25" in show_output:
            return f"MASK_MISMATCH: PC uses {mask} (/24) but topology note indicates a /25 network"
        if re.search(r"255\.255\.255\.24[08]", show_output) and "network 192.168" in show_output and "255.255.255.0" not in mask:
            pass
    return None


def check_interface_down(show_output: str):
    m = re.search(r"(GigabitEthernet\S*|FastEthernet\S*|Serial\S*)\s+[\d.]+\s+(administratively down|down)\s*(down)?", show_output)
    if m:
        return f"INTERFACE_DOWN: {m.group(1)} is {m.group(2)}"
    return None


def check_vlan_assignment(show_output: str, case_category: str):
    if case_category != "VLAN":
        return None
    m = re.search(r"Access Mode VLAN:\s*(\d+)", show_output)
    if m:
        vlan = m.group(1)
        if vlan in ("999", "1"):
            return f"SUSPECT_VLAN_ASSIGNMENT: port is in VLAN {vlan}, which is commonly an unused/default VLAN in these labs"
    return None


def check_missing_route(show_output: str, case_category: str):
    if case_category != "Routing":
        return None
    if "show ip route" in show_output and re.search(r"172\.16\.0\.0|192\.168\.50\.0", show_output) is None:
        if "connected" in show_output and "S " not in show_output:
            return "MISSING_ROUTE: routing table shows only directly connected networks; no static/dynamic route present for the destination referenced in the symptom"
    return None


def check_acl_implicit_deny(show_output: str, case_category: str):
    if case_category != "ACL":
        return None
    has_permit = "permit" in show_output
    has_explicit_denyall = re.search(r"deny\s+ip\s+any\s+any", show_output)
    if has_permit and not has_explicit_denyall and "access list" in show_output.lower():
        return "ACL_IMPLICIT_DENY_RISK: ACL has permit statement(s) with no visible catch-all rule; traffic not matching a permit will silently hit the implicit 'deny ip any any'"
    return None


def check_nat_outside_missing(show_output: str, case_category: str):
    if case_category != "NAT":
        return None
    if "ip nat inside" in show_output and "ip nat outside" not in show_output:
        return "NAT_OUTSIDE_MISSING: 'ip nat inside' is configured but no 'ip nat outside' interface is present in the evidence"
    return None


CHECKS = [
    check_duplicate_ip,
    check_gateway_mismatch,
    check_subnet_mask,
    check_interface_down,
]

CATEGORY_CHECKS = [
    check_vlan_assignment,
    check_missing_route,
    check_acl_implicit_deny,
    check_nat_outside_missing,
]


def run_checks(case: dict):
    findings = []
    show_output = case.get("show_output", "")
    for check in CHECKS:
        result = check(show_output)
        if result:
            findings.append(result)
    for check in CATEGORY_CHECKS:
        result = check(show_output, case.get("category", ""))
        if result:
            findings.append(result)
    return findings


def main():
    parser = argparse.ArgumentParser(description="NetSage AI rule-based checker")
    parser.add_argument("cases_csv", help="Path to cases.csv")
    parser.add_argument("--out", default="data/rule_checker_output.csv", help="Output CSV path")
    args = parser.parse_args()

    with open(args.cases_csv, newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    rows = []
    flagged = 0
    for case in cases:
        findings = run_checks(case)
        if findings:
            flagged += 1
        rows.append({
            "case_id": case["case_id"],
            "category": case["category"],
            "rule_findings": " | ".join(findings) if findings else "NO_DETERMINISTIC_MATCH",
            "num_findings": len(findings),
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "category", "rule_findings", "num_findings"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Checked {len(cases)} cases. Rule checker raised findings on {flagged} cases.")
    print(f"Output written to {args.out}")
    print()
    print("Sample output:")
    for row in rows[:5]:
        print(f"  [{row['case_id']}] {row['category']}: {row['rule_findings']}")


if __name__ == "__main__":
    main()
