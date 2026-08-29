"""
NetSage AI - Case Dataset Generator
Builds cases.csv: 30 original Packet Tracer-style troubleshooting cases
covering VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, and Wireless faults.

Run: python generate_cases.py
Output: data/cases.csv
"""
import csv
import os

CASES = [
    # ---------------- VLAN (4) ----------------
    {
        "case_id": "C001",
        "category": "VLAN",
        "severity": "High",
        "symptom": "PC-A (VLAN 10, 192.168.10.10/24) cannot ping PC-B (VLAN 10, 192.168.10.20/24) on the same switch.",
        "topology_note": "Both PCs connect to SW1 (Fa0/2 and Fa0/4). No router involved for this test; same subnet, same VLAN expected.",
        "show_output": (
            "SW1# show vlan brief\n"
            "VLAN Name                             Status    Ports\n"
            "10   Sales                            active    Fa0/2\n"
            "20   Engineering                      active    Fa0/4, Fa0/6\n"
            "SW1# show interfaces Fa0/4 switchport\n"
            "Name: Fa0/4\nSwitchport: Enabled\nAdministrative Mode: static access\n"
            "Operational Mode: static access\nAccess Mode VLAN: 20 (Engineering)"
        ),
        "expected_fault": "PC-B's port (Fa0/4) is assigned to VLAN 20 instead of VLAN 10, so the two PCs are on different broadcast domains despite matching IP subnet.",
        "osi_layer": "Layer 2",
        "concept_tag": "vlan_port_assignment",
    },
    {
        "case_id": "C002",
        "category": "VLAN",
        "severity": "Medium",
        "symptom": "New PC plugged into SW2 Fa0/8 gets no VLAN connectivity at all; interface shows connected but device is isolated.",
        "topology_note": "SW2 trunks to SW1 over Gi0/1. Fa0/8 was recently repurposed from a printer port.",
        "show_output": (
            "SW2# show interfaces Fa0/8 switchport\n"
            "Name: Fa0/8\nSwitchport: Enabled\nAdministrative Mode: static access\n"
            "Operational Mode: static access\nAccess Mode VLAN: 999 (VLAN0999)\n"
            "SW2# show vlan brief | include 999\n"
            "999  VLAN0999                         active"
        ),
        "expected_fault": "Fa0/8 is still assigned to VLAN 999, an unused/orphan VLAN left from the printer configuration, instead of the correct data VLAN.",
        "osi_layer": "Layer 2",
        "concept_tag": "vlan_port_assignment",
    },
    {
        "case_id": "C003",
        "category": "VLAN",
        "severity": "High",
        "symptom": "Devices in VLAN 30 on SW3 cannot reach devices in VLAN 30 on SW1, though both switches show VLAN 30 active locally.",
        "topology_note": "SW3-SW1 link is a trunk (Gi0/1). VLAN 30 was added to SW3 yesterday for a new department.",
        "show_output": (
            "SW3# show interfaces trunk\n"
            "Port      Vlans allowed on trunk\n"
            "Gi0/1     1-29,31-4094\n"
            "Port      Vlans allowed and active in management domain\n"
            "Gi0/1     1,20,31\n"
        ),
        "expected_fault": "VLAN 30 is explicitly excluded from the allowed-VLAN list on the Gi0/1 trunk (pruned), so VLAN 30 traffic never crosses the trunk to SW1.",
        "osi_layer": "Layer 2",
        "concept_tag": "trunk_allowed_vlans",
    },
    {
        "case_id": "C004",
        "category": "VLAN",
        "severity": "Low",
        "symptom": "Trunk between SW1 and SW2 is up, but VLAN 40 traffic is not forwarding while VLAN 10 and 20 work fine over the same trunk.",
        "topology_note": "SW1 uses 802.1Q trunking; SW2 was recently reconfigured for a new native VLAN.",
        "show_output": (
            "SW1# show interfaces Gi0/2 trunk\n"
            "Port      Mode    Encapsulation  Status       Native vlan\n"
            "Gi0/2     on      802.1q         trunking     1\n"
            "SW2# show interfaces Gi0/1 trunk\n"
            "Port      Mode    Encapsulation  Status       Native vlan\n"
            "Gi0/1     on      802.1q         trunking     40\n"
        ),
        "expected_fault": "Native VLAN mismatch: SW1 uses native VLAN 1 while SW2 uses native VLAN 40 on the same trunk, causing a VLAN mismatch/CDP warning and untagged VLAN 40 frames to be misclassified.",
        "osi_layer": "Layer 2",
        "concept_tag": "native_vlan_mismatch",
    },
    # ---------------- Default Gateway (4) ----------------
    {
        "case_id": "C005",
        "category": "Gateway",
        "severity": "High",
        "symptom": "PC-C has a valid IP via DHCP but cannot reach anything outside its own subnet, including the gateway.",
        "topology_note": "PC-C is in VLAN 10, subnet 192.168.10.0/24, gateway expected at 192.168.10.1 on R1 sub-interface.",
        "show_output": (
            "PC> ipconfig\n"
            "IP Address: 192.168.10.15\nSubnet Mask: 255.255.255.0\nDefault Gateway: 192.168.10.254\n"
            "R1# show ip interface brief\n"
            "Interface              IP-Address      Status\n"
            "GigabitEthernet0/0.10  192.168.10.1    up"
        ),
        "expected_fault": "DHCP pool is handing out the wrong default-gateway (192.168.10.254) which does not exist on the network; the router's actual sub-interface address is 192.168.10.1.",
        "osi_layer": "Layer 3",
        "concept_tag": "gateway_mismatch",
    },
    {
        "case_id": "C006",
        "category": "Gateway",
        "severity": "Medium",
        "symptom": "PC-D can ping its own gateway but not any host outside the subnet; gateway itself can reach the internet fine.",
        "topology_note": "PC-D statically configured. Subnet is 172.16.5.0/25.",
        "show_output": (
            "PC> ipconfig\n"
            "IP Address: 172.16.5.50\nSubnet Mask: 255.255.255.0\nDefault Gateway: 172.16.5.1\n"
            "R2# show ip interface brief\n"
            "GigabitEthernet0/1     172.16.5.1      up"
        ),
        "expected_fault": "PC-D's subnet mask (/24) does not match the router interface's actual /25 network, so PC-D miscalculates which addresses are local vs. remote and mishandles off-subnet traffic despite the gateway IP being correct.",
        "osi_layer": "Layer 3",
        "concept_tag": "wrong_subnet_mask",
    },
    {
        "case_id": "C007",
        "category": "Gateway",
        "severity": "High",
        "symptom": "All PCs in VLAN 20 lost gateway connectivity simultaneously after a router reload.",
        "topology_note": "Router-on-a-stick setup; VLAN 20 sub-interface should be up/up.",
        "show_output": (
            "R1# show ip interface brief\n"
            "Interface              IP-Address      Status                  Protocol\n"
            "GigabitEthernet0/0.20  192.168.20.1    administratively down   down"
        ),
        "expected_fault": "The VLAN 20 sub-interface was left administratively shut down (likely not saved with 'no shutdown' before reload), so it is down and cannot route for that VLAN.",
        "osi_layer": "Layer 3",
        "concept_tag": "interface_shutdown",
    },
    {
        "case_id": "C008",
        "category": "Gateway",
        "severity": "Medium",
        "symptom": "Two PCs on the same VLAN intermittently lose connectivity to the gateway and to each other; ARP table shows flapping entries.",
        "topology_note": "Static IPs were assigned manually by two different technicians.",
        "show_output": (
            "R1# show arp\n"
            "Internet  Address        Age(min)  Hardware Addr     Type   Interface\n"
            "Internet  192.168.30.50  0         00E0.1234.AAAA     ARPA   Gi0/0.30\n"
            "Internet  192.168.30.50  0         00E0.5678.BBBB     ARPA   Gi0/0.30"
        ),
        "expected_fault": "Duplicate IP address 192.168.30.50 assigned to two different MAC addresses causes ARP flapping and intermittent loss of connectivity for both hosts.",
        "osi_layer": "Layer 3",
        "concept_tag": "duplicate_ip",
    },
    # ---------------- DHCP (4) ----------------
    {
        "case_id": "C009",
        "category": "DHCP",
        "severity": "High",
        "symptom": "New PC on VLAN 10 shows an Automatic Private IP Address (169.254.x.x) and no network access.",
        "topology_note": "R1 configured as DHCP server for VLAN 10 pool; other PCs on VLAN 10 got addresses fine yesterday.",
        "show_output": (
            "R1# show ip dhcp pool VLAN10\n"
            "Pool VLAN10 :\n Utilization mark (high/low)    : 100 / 0\n"
            " Total addresses                : 0\n"
            " Leased addresses               : 0\n"
            "R1# show run | section dhcp pool VLAN10\n"
            "ip dhcp pool VLAN10\n network 192.168.10.0 255.255.255.0"
        ),
        "expected_fault": "DHCP pool VLAN10 has zero usable addresses because the excluded-address range covers the entire pool (or the pool was never given a real range), so the client fails to lease an address and self-assigns APIPA.",
        "osi_layer": "Layer 3",
        "concept_tag": "dhcp_pool_exhausted",
    },
    {
        "case_id": "C010",
        "category": "DHCP",
        "severity": "Medium",
        "symptom": "PC in VLAN 20 receives an IP address from the wrong subnet (192.168.10.x instead of 192.168.20.x).",
        "topology_note": "VLAN 20 clients should get addresses from pool VLAN20 via the ip helper-address on the VLAN 20 sub-interface.",
        "show_output": (
            "R1# show run interface Gi0/0.20\n"
            "interface GigabitEthernet0/0.20\n"
            " encapsulation dot1Q 20\n"
            " ip address 192.168.20.1 255.255.255.0\n"
            " ip helper-address 192.168.10.5"
        ),
        "expected_fault": "The ip helper-address on the VLAN 20 sub-interface points to the wrong DHCP server/pool scope (192.168.10.5, a VLAN 10 host), forwarding VLAN 20 DHCP requests into the VLAN 10 pool.",
        "osi_layer": "Layer 3",
        "concept_tag": "dhcp_relay_misconfig",
    },
    {
        "case_id": "C011",
        "category": "DHCP",
        "severity": "Medium",
        "symptom": "PC gets a valid IP and gateway but has no internet access; can ping gateway and other local hosts fine.",
        "topology_note": "DHCP pool serves VLAN 10; DNS resolution and internet both fail from this PC only.",
        "show_output": (
            "PC> ipconfig /all\n"
            "IP Address: 192.168.10.25\nSubnet Mask: 255.255.255.0\n"
            "Default Gateway: 192.168.10.1\nDNS Servers: 0.0.0.0\n"
            "R1# show run | section dhcp pool VLAN10\n"
            "ip dhcp pool VLAN10\n network 192.168.10.0 255.255.255.0\n default-router 192.168.10.1"
        ),
        "expected_fault": "The DHCP pool VLAN10 has no 'dns-server' statement configured, so clients receive no DNS server address and cannot resolve names even though IP connectivity works.",
        "osi_layer": "Layer 7",
        "concept_tag": "dhcp_missing_dns_option",
    },
    {
        "case_id": "C012",
        "category": "DHCP",
        "severity": "Low",
        "symptom": "Every device on VLAN 30 gets an address from the same small range and IP conflicts increase as more devices join.",
        "topology_note": "VLAN 30 subnet is 192.168.30.0/24 with room for 254 hosts.",
        "show_output": (
            "R1# show run | section dhcp pool VLAN30\n"
            "ip dhcp pool VLAN30\n network 192.168.30.0 255.255.255.240\n default-router 192.168.30.1"
        ),
        "expected_fault": "The DHCP pool's network statement uses mask 255.255.255.240 (/28, only 14 usable hosts) instead of matching the actual /24 subnet, artificially shrinking the address pool and causing exhaustion/conflicts.",
        "osi_layer": "Layer 3",
        "concept_tag": "dhcp_pool_mask_mismatch",
    },
    # ---------------- DNS (4) ----------------
    {
        "case_id": "C013",
        "category": "DNS",
        "severity": "Medium",
        "symptom": "PC can ping the web server by IP (10.10.10.5) but 'http://intranet.local' fails to resolve.",
        "topology_note": "Internal DNS server configured at 192.168.10.5. Web server record was added last week.",
        "show_output": (
            "PC> nslookup intranet.local\n"
            "Server:  192.168.10.5\n"
            "*** 192.168.10.5 can't find intranet.local: Non-existent domain"
        ),
        "expected_fault": "The A record for intranet.local was never created (or was created with a typo) on the DNS server, so the name simply does not exist in the zone, even though the DNS server itself is reachable.",
        "osi_layer": "Layer 7",
        "concept_tag": "missing_dns_record",
    },
    {
        "case_id": "C014",
        "category": "DNS",
        "severity": "High",
        "symptom": "All name resolution fails from every PC on VLAN 10; direct IP connectivity to all servers works.",
        "topology_note": "DNS server is 192.168.10.5, hosted on a server VM in the server VLAN.",
        "show_output": (
            "PC> ping 192.168.10.5\n"
            "Request timed out. (4/4 dropped)\n"
            "PC> ping 192.168.10.1\n"
            "Reply from 192.168.10.1: bytes=32 time=1ms TTL=255"
        ),
        "expected_fault": "The DNS server host (192.168.10.5) itself is unreachable (likely powered off, wrong VLAN, or an ACL blocking it), so no DNS queries can be answered even though the gateway is fine.",
        "osi_layer": "Layer 3",
        "concept_tag": "dns_server_unreachable",
    },
    {
        "case_id": "C015",
        "category": "DNS",
        "severity": "Low",
        "symptom": "Name resolution is extremely slow (10+ seconds) before eventually succeeding.",
        "topology_note": "PC is configured with a primary and secondary DNS server.",
        "show_output": (
            "PC> ipconfig /all\n"
            "DNS Servers: 192.168.10.99\n                203.0.113.5"
        ),
        "expected_fault": "The primary DNS server (192.168.10.99) does not exist on the network, so every lookup times out on the primary before falling back to the working secondary (203.0.113.5), adding delay to every resolution.",
        "osi_layer": "Layer 7",
        "concept_tag": "dns_server_misconfig",
    },
    {
        "case_id": "C016",
        "category": "DNS",
        "severity": "Medium",
        "symptom": "Browsing to 'www.company.com' loads the wrong server's content (test server instead of production).",
        "topology_note": "DNS zone was recently updated during a server migration.",
        "show_output": (
            "PC> nslookup www.company.com\nServer: 192.168.10.5\nAddress: 192.168.10.5\nName: www.company.com\nAddress: 192.168.10.50"
        ),
        "expected_fault": "The A record for www.company.com still points to the old/test server IP (192.168.10.50) instead of the new production server IP; the record was never updated after migration.",
        "osi_layer": "Layer 7",
        "concept_tag": "stale_dns_record",
    },
    # ---------------- Routing (4) ----------------
    {
        "case_id": "C017",
        "category": "Routing",
        "severity": "High",
        "symptom": "VLAN 10 (192.168.10.0/24) hosts can reach VLAN 20 hosts, but neither VLAN can reach the 172.16.0.0/16 branch network via R2.",
        "topology_note": "R1 connects to R2 via a serial link (S0/0/0, 10.0.0.0/30). Static routing is used, no dynamic protocol.",
        "show_output": (
            "R1# show ip route\n"
            "C    192.168.10.0/24 is directly connected, GigabitEthernet0/0.10\n"
            "C    192.168.20.0/24 is directly connected, GigabitEthernet0/0.20\n"
            "C    10.0.0.0/30 is directly connected, Serial0/0/0\n"
        ),
        "expected_fault": "There is no static route (or default route) on R1 pointing toward 172.16.0.0/16 via R2 (10.0.0.2); the route is simply missing from the routing table.",
        "osi_layer": "Layer 3",
        "concept_tag": "missing_static_route",
    },
    {
        "case_id": "C018",
        "category": "Routing",
        "severity": "High",
        "symptom": "OSPF neighbors between R1 and R3 never form; 'show ip ospf neighbor' is empty on both routers.",
        "topology_note": "Both routers are on the same 10.1.1.0/30 link and were configured for OSPF area 0.",
        "show_output": (
            "R1# show run | section router ospf\n"
            "router ospf 1\n network 10.1.1.0 0.0.0.3 area 0\n"
            "R3# show run | section router ospf\n"
            "router ospf 1\n network 10.1.1.0 0.0.0.3 area 1"
        ),
        "expected_fault": "R1 and R3 are configured for mismatched OSPF areas on the same link (area 0 vs. area 1), which prevents adjacency from forming.",
        "osi_layer": "Layer 3",
        "concept_tag": "ospf_area_mismatch",
    },
    {
        "case_id": "C019",
        "category": "Routing",
        "severity": "Medium",
        "symptom": "Traffic from VLAN 10 to the internet works, but return traffic for a specific server subnet (192.168.50.0/24) times out.",
        "topology_note": "R1 has a default route to the ISP and static routes to internal subnets.",
        "show_output": (
            "R1# show ip route static\n"
            "S    192.168.50.0/24 [1/0] via 10.0.0.5\n"
            "R1# ping 10.0.0.5\n"
            "Request timed out. (4/4 dropped)"
        ),
        "expected_fault": "The static route for 192.168.50.0/24 points to next-hop 10.0.0.5, which is unreachable (wrong or outdated next-hop after a network change), so packets are black-holed.",
        "osi_layer": "Layer 3",
        "concept_tag": "wrong_next_hop",
    },
    {
        "case_id": "C020",
        "category": "Routing",
        "severity": "Medium",
        "symptom": "Two branch routers advertising the same subnet via EIGRP cause intermittent routing loops and packet loss.",
        "topology_note": "Both R4 and R5 are configured with EIGRP AS 100 and both connect to 192.168.60.0/24 for redundancy.",
        "show_output": (
            "R4# show ip eigrp topology\n"
            "P 192.168.60.0/24, 2 successors, FD is 28160\n"
            "        via 10.2.2.2 (28160/28160), Serial0/0/1\n"
            "        via 10.2.2.6 (28160/28160), Serial0/0/2"
        ),
        "expected_fault": "Two feasible successors with identical feasible distance (28160/28160) indicate an unintended routing loop condition caused by symmetric link metrics that were not tuned, rather than proper redundancy; combined with mismatched hold-down timers this produces intermittent loss.",
        "osi_layer": "Layer 3",
        "concept_tag": "eigrp_metric_tuning",
    },
    # ---------------- ACL (4) ----------------
    {
        "case_id": "C021",
        "category": "ACL",
        "severity": "High",
        "symptom": "PC in VLAN 30 gets an IP, can ping its gateway, but cannot reach the file server in VLAN 10 at 192.168.10.20.",
        "topology_note": "R1 routes between VLANs; an ACL was recently applied to VLAN 30's sub-interface for security hardening.",
        "show_output": (
            "R1# show access-lists\n"
            "Extended IP access list BLOCK_VLAN30\n"
            "    10 deny ip 192.168.30.0 0.0.0.255 192.168.10.0 0.0.0.255\n"
            "    20 permit ip any any\n"
            "R1# show ip interface Gi0/0.30 | include access list\n"
            "  Outgoing access list is BLOCK_VLAN30"
        ),
        "expected_fault": "ACL 'BLOCK_VLAN30' explicitly denies traffic from VLAN 30 to VLAN 10's subnet and is applied outbound on the VLAN 30 sub-interface, blocking the file server traffic as designed but likely broader than intended.",
        "osi_layer": "Layer 3/4",
        "concept_tag": "acl_deny_rule",
    },
    {
        "case_id": "C022",
        "category": "ACL",
        "severity": "Medium",
        "symptom": "Web traffic (HTTP/HTTPS) to the server works, but SSH management access to the same server from the admin PC fails.",
        "topology_note": "An ACL was applied to restrict server access to only web ports.",
        "show_output": (
            "R1# show access-lists SERVER_ACCESS\n"
            "Extended IP access list SERVER_ACCESS\n"
            "    10 permit tcp any host 192.168.10.20 eq 80\n"
            "    20 permit tcp any host 192.168.10.20 eq 443\n"
            "    30 deny ip any any log"
        ),
        "expected_fault": "The ACL only permits TCP ports 80 and 443 to the server and has an implicit/explicit deny-all after; port 22 (SSH) was never added, so SSH is correctly but unintentionally blocked.",
        "osi_layer": "Layer 4",
        "concept_tag": "acl_missing_permit",
    },
    {
        "case_id": "C023",
        "category": "ACL",
        "severity": "High",
        "symptom": "After applying a new ACL, absolutely no traffic passes through R2, including traffic that should be allowed.",
        "topology_note": "ACL was written to permit specific management traffic and was just applied to Gi0/0 inbound.",
        "show_output": (
            "R2# show access-lists MGMT_ONLY\n"
            "Extended IP access list MGMT_ONLY\n"
            "    10 permit tcp host 10.0.0.10 any eq 22"
        ),
        "expected_fault": "The ACL has only one explicit permit line with no other permits and relies on the implicit 'deny ip any any' at the end of every Cisco ACL, which blocks all traffic that isn't SSH from 10.0.0.10 — the ACL is missing required permit statements for other legitimate traffic.",
        "osi_layer": "Layer 3/4",
        "concept_tag": "acl_implicit_deny",
    },
    {
        "case_id": "C024",
        "category": "ACL",
        "severity": "Medium",
        "symptom": "Guest Wi-Fi users (VLAN 50) can reach the internal file server, which violates the intended guest isolation policy.",
        "topology_note": "Guest VLAN 50 should only reach the internet, not internal subnets 192.168.0.0/16.",
        "show_output": (
            "R1# show ip interface Gi0/0.50 | include access list\n"
            "  Incoming access list is not set\n"
            "  Outgoing access list is not set"
        ),
        "expected_fault": "No ACL is applied to the guest VLAN 50 sub-interface at all, so there is nothing enforcing isolation between the guest network and internal subnets — a security gap, not a connectivity bug.",
        "osi_layer": "Layer 3",
        "concept_tag": "missing_isolation_acl",
    },
    # ---------------- NAT (3) ----------------
    {
        "case_id": "C025",
        "category": "NAT",
        "severity": "High",
        "symptom": "Internal PCs (192.168.10.0/24) cannot reach any internet address; internal-to-internal routing works fine.",
        "topology_note": "R1 is configured for PAT (NAT overload) toward the ISP interface Gi0/1.",
        "show_output": (
            "R1# show run | section ip nat\n"
            "interface GigabitEthernet0/0.10\n ip nat inside\n"
            "interface GigabitEthernet0/1\n description ISP-Uplink\n"
            "ip nat inside source list 1 interface GigabitEthernet0/1 overload"
        ),
        "expected_fault": "The 'ip nat outside' command was never applied to the ISP-facing interface (Gi0/1), so NAT never triggers for outbound traffic even though the inside interface and NAT rule are correctly configured.",
        "osi_layer": "Layer 3",
        "concept_tag": "nat_outside_missing",
    },
    {
        "case_id": "C026",
        "category": "NAT",
        "severity": "Medium",
        "symptom": "Some internal PCs can browse the internet, others cannot, seemingly at random.",
        "topology_note": "NAT uses access-list 1 to define which internal hosts are translated.",
        "show_output": (
            "R1# show access-lists 1\n"
            "Standard IP access list 1\n"
            "    10 permit 192.168.10.0 0.0.0.127"
        ),
        "expected_fault": "The NAT access-list only covers 192.168.10.0/25 (the .0-.127 half of the subnet) due to an incorrect wildcard mask, so hosts in the .128-.255 range are never translated and lose internet access.",
        "osi_layer": "Layer 3",
        "concept_tag": "nat_acl_wildcard_error",
    },
    {
        "case_id": "C027",
        "category": "NAT",
        "severity": "Medium",
        "symptom": "External users cannot reach the internally-hosted web server via the public IP, even though internal users can reach it fine.",
        "topology_note": "Static NAT was configured to map a public IP to the internal web server for port forwarding.",
        "show_output": (
            "R1# show run | include ip nat inside source static\n"
            "ip nat inside source static tcp 192.168.10.20 8080 203.0.113.10 80\n"
        ),
        "expected_fault": "The static NAT rule forwards public port 80 to internal port 8080, but the web server is actually listening on port 80 internally, so the port translation mismatch causes external connections to fail.",
        "osi_layer": "Layer 4",
        "concept_tag": "nat_port_mismatch",
    },
    # ---------------- Wireless (3) ----------------
    {
        "case_id": "C028",
        "category": "Wireless",
        "severity": "Medium",
        "symptom": "Laptop can see the 'Corp-WiFi' SSID and connect, but authentication fails every time with the correct password.",
        "topology_note": "WLC/AP configured with WPA2-PSK for the Corp-WiFi SSID.",
        "show_output": (
            "AP1# show running-config | section wlan\n"
            "wlan Corp-WiFi 1 Corp-WiFi\n security wpa2 psk set-key ascii 0 CorrectPassw0rd!\n"
            "wlan Corp-WiFi 1 Corp-WiFi\n client vlan 99"
        ),
        "expected_fault": "The WLAN is mapped to client VLAN 99, which does not exist / is not trunked to the AP's switch port, so even after successful PSK authentication the client cannot get an IP or complete association into a valid VLAN.",
        "osi_layer": "Layer 2",
        "concept_tag": "wireless_vlan_mapping",
    },
    {
        "case_id": "C029",
        "category": "Wireless",
        "severity": "Low",
        "symptom": "Wireless clients near the edge of the building experience frequent disconnects and low throughput, while clients near the AP are fine.",
        "topology_note": "Single AP covers an open office floor; channel and power settings were left at defaults during install.",
        "show_output": (
            "AP1# show controllers dot11Radio 0\n"
            "Radio Channel: 6\nTransmit Power: 1 (max)\n"
            "AP2# show controllers dot11Radio 0\n"
            "Radio Channel: 6\nTransmit Power: 1 (max)"
        ),
        "expected_fault": "AP1 and AP2 (adjacent coverage cells) are both set to the same channel (6) at max power, causing co-channel interference that degrades signal quality at cell edges rather than a hardware fault.",
        "osi_layer": "Layer 1/2",
        "concept_tag": "wireless_channel_overlap",
    },
    {
        "case_id": "C030",
        "category": "Wireless",
        "severity": "High",
        "symptom": "Guest Wi-Fi clients (VLAN 50) can reach the internal accounting server on VLAN 10, violating the isolation policy.",
        "topology_note": "Guest SSID is mapped to VLAN 50; SSID and VLAN mapping were verified correct on the WLC.",
        "show_output": (
            "R1# show access-lists | include VLAN 50\n"
            "(no output - no ACL references VLAN 50 or 192.168.50.0)\n"
            "R1# show ip interface Gi0/0.50 | include access list\n"
            "  Outgoing access list is not set"
        ),
        "expected_fault": "Guest VLAN 50 correctly separates Layer 2 traffic, but no Layer 3 ACL enforces isolation at the router, so routing between VLAN 50 and VLAN 10 is fully permitted by default — a missing security control, not a wireless config bug.",
        "osi_layer": "Layer 3",
        "concept_tag": "guest_isolation_failure",
    },
]

FIELDS = [
    "case_id", "category", "severity", "symptom", "topology_note",
    "show_output", "expected_fault", "osi_layer", "concept_tag",
]

def main():
    os.makedirs("data", exist_ok=True)
    out_path = "data/cases.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for c in CASES:
            writer.writerow(c)
    print(f"Wrote {len(CASES)} cases to {out_path}")

if __name__ == "__main__":
    main()
