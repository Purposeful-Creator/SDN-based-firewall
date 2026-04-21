"""
test.py - Verify firewall behaviour inside Mininet CLI

Run these commands manually inside the mininet> prompt.
Expected results are listed next to each command.
"""

TESTS = """
=== Firewall verification tests ===

Run inside mininet> prompt:

1. h1 ping -c2 h2
   EXPECTED: works (h1 <-> h2 is allowed)

2. h2 ping -c2 h3
   EXPECTED: works (h2 <-> h3 is allowed)

3. h1 ping -c2 h3
   EXPECTED: fails — 100% packet loss (h1 <-> h3 is BLOCKED)

4. h3 ping -c2 h1
   EXPECTED: fails — 100% packet loss (h3 <-> h1 is BLOCKED)

5. h1 ping -c2 h2
   EXPECTED: works (confirm h1 still reaches h2 after block)

=== What to look for in POX terminal ===

When h1 pings h3 you should see:
  WARNING:firewall:BLOCKED  10.0.0.1 -> 10.0.0.3  (drop flow installed)

When h1 pings h2 you should see:
  DEBUG:firewall:ALLOWED   10.0.0.1 -> 10.0.0.2
"""

if __name__ == '__main__':
    print(TESTS)
