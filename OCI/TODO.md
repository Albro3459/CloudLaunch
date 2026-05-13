# OCI TODO

* Rewrite `lambda/Deploy` to call OCI REST APIs directly instead of importing the full Python `oci` SDK.
* Keep the shared Lambda layer small: Firebase, Firestore, `requests`, and QR code dependencies only.
* Add a small REST/signing helper for:
  * Resource Manager stack create/get, apply/destroy jobs, job state
  * Compute instance get/terminate and VNIC attachment lookup
  * Virtual Network VNIC lookup for public IP
* Confirm the Deploy Lambda has outbound internet egress to OCI API endpoints. If the Lambda is inside a private VPC subnet, add a NAT gateway or another approved egress path.
* Keep OCI API signing values in a separate AWS Secrets Manager secret named `OCI-Auth`:
```json
{
  "OCI_USER_OCID": "...",
  "OCI_TENANCY_OCID": "...",
  "OCI_FINGERPRINT": "...",
  "OCI_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```
* OCI setup needed for `OCI-Auth`:
  * create or choose an OCI user for CloudLaunch automation
  * add an API signing key for that user
  * store the user OCID, tenancy OCID, key fingerprint, and private key in `OCI-Auth`
  * grant the user only the policies needed for Resource Manager stacks/jobs, compute instances, VNIC reads, and stack cleanup
* Keep Terraform/runtime values in `VPN-Config`, not `OCI-Auth`: compartment, subnet, image, shape, WireGuard values, SES sender, and admin email.
* Update SES for emails from the new domain.
