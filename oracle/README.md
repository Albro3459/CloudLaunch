# Oracle WireGuard Bootstrap

This folder contains a Terraform-ready bootstrap template for standing up a WireGuard server on an OCI instance with cloud-init user data.

TODO:
* ingress and egress rules needed!
```
UDP 51820 ingress
SSH ingress
egress to 0.0.0.0/0 and ::/0
VCN/subnet IPv6 enabled and routed
```
* set all vars

## Files

`wireguard-cloud-init.sh.tftpl`

* Installs WireGuard on Ubuntu.
* Enables IPv4 and IPv6 forwarding.
* Writes `/etc/wireguard/wg0.conf`.
* Detects the instance's primary NIC automatically instead of hard-coding `eth0`.
* Starts and enables `wg-quick`.

## Terraform example

OCI instance user data is passed through the `metadata` map, and the value should be base64 encoded. Oracle's Terraform provider documents both the `metadata` field on `oci_core_instance` and cloud-init usage through `user_data`:

* [OCI Terraform provider: `oci_core_instance`](https://registry.terraform.io/providers/oracle/oci/latest/docs/resources/core_instance)
* [OCI docs: Launching an instance with cloud-init](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm)

```hcl
locals {
  wireguard_user_data = templatefile("${path.module}/oracle/wireguard-cloud-init.sh.tftpl", {
    wg_interface      = "wg0"
    listen_port       = 51820
    wg_address_v4     = "10.0.0.1/24"
    wg_address_v6     = "fd42:42:42::1/64"
    wg_network_v4     = "10.0.0.0/24"
    wg_network_v6     = "fd42:42:42::/64"
    rate_limit        = "25/second"
    rate_limit_burst  = 100
    server_private_key = var.wireguard_server_private_key
    peer = {
      public_key           = var.wireguard_client_public_key
      allowed_ipv4         = "10.0.0.2/32"
      allowed_ipv6         = "fd42:42:42::2/128"
      persistent_keepalive = 25
    }
  })
}

resource "oci_core_instance" "vpn" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_id
  display_name        = "wireguard-vpn"
  shape               = var.shape

  create_vnic_details {
    subnet_id        = var.subnet_id
    assign_public_ip = true
  }

  metadata = {
    user_data = base64encode(local.wireguard_user_data)
  }

  source_details {
    source_type = "image"
    source_id   = var.image_id
  }
}
```

## Notes

* Keep the WireGuard private key in Terraform variables or a secret source, not in git.
* The client public key from the original doc is intentionally not committed here.
* You still need OCI ingress rules for UDP `51820` and SSH, plus egress that allows the VPN traffic out.
* The bootstrap log lands in `/var/log/wireguard-bootstrap.log` on the instance.
