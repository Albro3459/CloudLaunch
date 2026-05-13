# OCI TODO

1. Verify the CloudLaunch automation user, API key, and compartment policies against the exact OCI compartment names before manual Lambda testing.
2. Confirm the target subnet, route tables, IPv6 setup, and security rules match the WireGuard instance requirements in [README.md](README.md).
3. After first successful terminate test, decide whether destroyed Resource Manager stacks should also be deleted from OCI or kept for audit/debug history.
