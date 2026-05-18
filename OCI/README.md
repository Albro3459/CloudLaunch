# Oracle WireGuard Stack

This folder contains the Oracle Cloud Infrastructure Terraform package used to launch a WireGuard VPN instance with cloud-init bootstrap scripts.

AWS Lambda is the orchestrator. The `Deploy` Lambda signs direct HTTPS requests to OCI Resource Manager, uploads this Terraform package as a stack, creates apply/destroy jobs, and reads Compute/VNIC data after the job finishes. OCI Terraform creates the WireGuard instance.

The Terraform [cloudlaunch.tf](terraform/cloudlaunch.tf) creates the compute instance only. It assumes the compartment, subnet, IPv6 setup, route tables, and security rules already exist.

If you want to create another VPN without replacing the instance tracked by the current stack, use the separate package in [terraform-additional](terraform-additional). Upload that directory as a different OCI stack so it gets its own Terraform state.

## OCI Automation User

Create a dedicated OCI user for CloudLaunch automation.

1. Create an OCI group such as `CloudLaunchAutomation`.
2. Create an automation user and add it to that group.
3. Generate an API signing key pair for the user.
4. Upload the public key to the user's API keys.
5. Update the AWS `CloudLaunch` secrets
  * See what is required in the `oci` object in [CloudLaunch.example](../lambda/secrets/CloudLaunch.example)

Use an unencrypted PEM private key. 

**NOTE:**
The Lambda stores and signs from the Secrets Manager value directly. It does not read a local OCI config file.

## OCI Policies

Grant the automation group only the access needed for stack orchestration and cleanup in the target compartment.

Policy intent:

* Manage Resource Manager stacks and jobs for the CloudLaunch Terraform package.
* Read Resource Manager job state so Lambda can resolve the Terraform state output.
* Read compute instance state after apply and during cleanup.
* Terminate compute instances when Resource Manager cleanup does not remove the instance cleanly.
* Read VNIC attachments and VNICs so Lambda can find the public IPv4 address.

Example policy shape:

```text
Allow group CloudLaunchAutomation to manage orm-stacks in compartment <compartment-name>
Allow group CloudLaunchAutomation to manage orm-jobs in compartment <compartment-name>
Allow group CloudLaunchAutomation to manage instances in compartment <compartment-name>
Allow group CloudLaunchAutomation to read virtual-network-family in compartment <compartment-name>
```

Tune names and scope to your tenancy. If the subnet, image, or network resources live in another compartment, add the matching read/use policy there.

## Network Prerequisites

Before the Lambda creates a stack, make sure OCI already has:

* a target compartment
* a subnet for the instance
* IPv6 enabled and routed if you want IPv6 VPN traffic
* an image OCID compatible with the Terraform shape and cloud-init scripts
* ingress for SSH on TCP `22` set to only your approved personal `IPv4/32`
* ingress for WireGuard on UDP `51820`
  * IPv4: `0.0.0.0/0`
  * IPv6: `::/0`
* egress that allows VPN client traffic out to `0.0.0.0/0` and `::/0`

The subnet OCID, source image OCID, availability domain, shape, boot volume settings, and IPv6 subnet CIDR belong in `CloudLaunch.oci`.

## Files

[cloudlaunch.tf](terraform/cloudlaunch.tf)

* Main Terraform file.
* Declares the input variables.
* Renders the cloud-init templates.
* Creates the OCI compute instance and passes SSH keys plus multipart `user_data`.

[wireguard-cloud-init.sh.tftpl](terraform/wireguard-cloud-init.sh.tftpl)

* Shell script template rendered by Terraform and run by cloud-init.
* Installs WireGuard, `iptables`, `fail2ban`, Unbound, and DNS blocklist refresh tooling.
* Disables SSH password auth and root SSH login.
* Enables IPv4 and IPv6 forwarding.
* Writes `/etc/wireguard/<interface>.conf`.
* Configures Unbound as the VPN DNS resolver with ad/tracker blocking.
* Starts `wg-quick@<interface>`.
* Writes step markers into `/var/log/wireguard-bootstrap.log` so bootstrap failures are easier to pinpoint.

[backdoor-cloud-init.yaml](terraform/backdoor-cloud-init.yaml)

* Cloud-init config that creates the emergency `backdoor` user.
* Sets the password hash from Terraform input.
* Appends `DenyUsers backdoor` to SSH config so this user cannot log in over SSH.
* Intended only for console access through OCI when normal SSH access is unavailable.

[terraform.tfvars.example](terraform/terraform.tfvars.example)

* Example values for all required Terraform inputs.
* Use this as the template when creating or updating your real `terraform.tfvars`.

[terraform.tfvars](terraform/terraform.tfvars)

* Real stack values for this environment.
* Contains sensitive values such as the WireGuard private key and password hash.
* If you package this file into the stack zip, those values become part of the uploaded stack artifact.

[.terraform.lock.hcl](terraform/.terraform.lock.hcl)

* Terraform dependency lock file.
* Useful for local reproducibility.
* Not required in the zip you upload to OCI Stacks.

[terraform-additional](terraform-additional)

* Separate standalone Terraform package for creating another VPN instance in a different OCI stack.
* Intended for parallel instances so you do not replace the one managed by [terraform](terraform).
* Starts with different example display names and WireGuard address ranges so you have a safer baseline when cloning a second VPN.

## Backdoor User

The `backdoor` user exists only as an emergency recovery path.

What it does:

* account name: `backdoor`
* password login is allowed on the local console because cloud-init sets the provided password hash
* password login over SSH is blocked because the bootstrap disables SSH password authentication globally and the cloud-init file adds `DenyUsers backdoor`
* `sudo` is passwordless so you can recover access if your normal SSH path is broken

How to use it:

1. Open the OCI instance.
2. Go to the console connection / Cloud Shell style serial login flow.
3. Log in as `backdoor` with the password that matches the `hashed_password` Terraform input.

This user is for recovery only.

## Local Validation

```sh
cd terraform &&
terraform init &&
terraform validate
```

What these do:

* `terraform init` downloads the OCI provider and prepares the local working directory
* `terraform validate` checks Terraform syntax, type usage, and provider schema compatibility

Useful notes:

* `.terraform/` is local init output and should not be committed
* `terraform validate` requires `terraform init` first on a clean machine
* if you change provider-related settings later, rerun `terraform init`

## Creating Or Updating The OCI Stack

For the Lambda flow, [lambda/Deploy/build_deploy_lambda.sh](../lambda/Deploy/build_deploy_lambda.sh) copies the Terraform files into the Lambda package, and the Lambda uploads them to Resource Manager as a zip-backed config source.

If you manually upload to OCI Stacks, zip only the files Resource Manager actually needs.

Include:

* [cloudlaunch.tf](terraform/cloudlaunch.tf)
* [wireguard-cloud-init.sh.tftpl](terraform/wireguard-cloud-init.sh.tftpl)
* [backdoor-cloud-init.yaml](terraform/backdoor-cloud-init.yaml)
* [terraform.tfvars](terraform/terraform.tfvars)

Do not include:

* `.terraform/`
* local provider binaries
* editor files
* logs
* example env
* any other local scratch files

Usually you do not need to include [.terraform.lock.hcl](terraform/.terraform.lock.hcl) for OCI Stacks.

Example packaging flow from repo root:

```sh
cd terraform &&
STACK_TMP="/tmp/cloudlaunch-stack-$(date +%F_%H-%M-%S)" &&
mkdir -p "$STACK_TMP" &&
cp cloudlaunch.tf "$STACK_TMP"/ &&
cp wireguard-cloud-init.sh.tftpl "$STACK_TMP"/ &&
cp backdoor-cloud-init.yaml "$STACK_TMP"/ &&
cp terraform.tfvars "$STACK_TMP"/ &&
cd "$STACK_TMP" &&
zip -r ~/Desktop/cloudlaunch-stack.zip . &&
cd - && cd ../
```

Then in OCI Stacks:

1. Create a new stack or edit the existing one.
2. Upload the zip.
3. Review the variables OCI detects.
4. Plan/apply the stack.

If you prefer to manage variables in the OCI stack UI instead of packaging them, leave `terraform.tfvars` out of the zip and set the variables directly in the stack.

The Lambda path does not use `terraform.tfvars`; it sends stack variables from the AWS `CloudLaunch` secret.

## Runtime Logs

After the instance launches, useful logs on the VM are:

* `/var/log/cloud-init-output.log`
* `/var/log/wireguard-bootstrap.log`

Check with 
```sh
sudo sed -n '1,240p' /var/log/wireguard-bootstrap.log
# or
tail -f /var/log/wireguard-bootstrap.log
```

The WireGuard bootstrap log includes explicit step markers so it is easier to see whether failure happened during package install, SSH hardening, `fail2ban`, sysctl setup, or WireGuard startup.

## References

* [OCI request signatures](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/signingrequests.htm)
* [OCI REST APIs](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/usingapi.htm)
