# OCI TODO

* Rewrite `lambda/Deploy` to call OCI REST APIs directly instead of importing the full Python `oci` SDK.
* Keep the shared Lambda layer small: Firebase, Firestore, `requests`, and QR code dependencies only.
* Add a small REST/signing helper for:
  * Resource Manager stack create/get, apply/destroy jobs, job state
  * Compute instance get/terminate and VNIC attachment lookup
  * Virtual Network VNIC lookup for public IP
* Confirm the Deploy Lambda has outbound internet egress to OCI API endpoints. If the Lambda is inside a private VPC subnet, add a NAT gateway or another approved egress path.
* Keep OCI API signing and Terraform values in the `oci` object inside the single `CloudLaunch` AWS secret.
* Grant the OCI automation user only the policies needed for Resource Manager stacks/jobs, compute instances, VNIC reads, and stack cleanup.
* Update SES for emails from the new domain.
