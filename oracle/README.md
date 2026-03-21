# Oracle WireGuard Stack

This folder contains the Oracle Cloud Infrastructure Terraform package used to launch a WireGuard VPN instance with cloud-init bootstrap scripts.

The Terraform [cloudlaunch.tf](terraform/cloudlaunch.tf) creates the compute instance only. It assumes the subnet, IPv6 setup, route tables, and security rules already exist.

## Prerequisites

Before creating or updating the stack, make sure OCI already has:

* a target compartment
* a subnet for the instance
* IPv6 enabled and routed if you want IPv6 VPN traffic
* ingress for SSH on TCP `22` set to only your approved personal `IPv4/32`
* ingress for WireGuard on UDP `51820`
    * IPv4: `0.0.0.0/0`
    * IPv6: `::/0`
* egress that allows VPN client traffic out to `0.0.0.0/0` and `::/0`

## Files

[cloudlaunch.tf](terraform/cloudlaunch.tf)

* Main Terraform file.
* Declares the input variables.
* Renders the cloud-init templates.
* Creates the OCI compute instance and passes SSH keys plus multipart `user_data`.

[wireguard-cloud-init.sh.tftpl](terraform/wireguard-cloud-init.sh.tftpl)

* Shell script template rendered by Terraform and run by cloud-init.
* Installs WireGuard, `iptables`, and `fail2ban`.
* Disables SSH password auth and root SSH login.
* Enables IPv4 and IPv6 forwarding.
* Writes `/etc/wireguard/<interface>.conf`.
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

When uploading to OCI Stacks, zip only the files Resource Manager actually needs.

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

## Runtime Logs

After the instance launches, useful logs on the VM are:

* `/var/log/cloud-init-output.log`
* `/var/log/wireguard-bootstrap.log`

The WireGuard bootstrap log includes explicit step markers so it is easier to see whether failure happened during package install, SSH hardening, `fail2ban`, sysctl setup, or WireGuard startup.
