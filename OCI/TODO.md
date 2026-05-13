# OCI TODO

Backend Lambda + OCI deploy and terminate flow checks. Destroyed Resource Manager stacks can stay in OCI for audit/debug history.

1. Re-check the CloudLaunch automation user, API key, and compartment policies against the exact OCI compartment names before final launch.
2. Re-confirm the target subnet, route tables, IPv6 setup, and security rules match the WireGuard instance requirements in [README.md](README.md).
3. Watch Resource Manager stack count during testing; delete old destroyed stacks only if console noise or service limits become a problem.
