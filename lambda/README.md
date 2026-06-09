# AWS Lambda Setup

This folder contains the AWS Lambda functions for the CloudLaunch AWS deployment platform and the included WireGuard VPN example. The Lambdas authenticate Firebase users, set up and clean up AWS regions, deploy and terminate EC2 servers, read AWS Secrets Manager values, update Firebase state, enforce DynamoDB limits, and send SES emails.

## Lambda Functions

* **TerraformRegion**: admin-only region setup and cleanup. Setup copies the source VPN AMI into a target region, creates the VPC, subnet, internet gateway, route table, security group, key pair, and per-region secret. Cleanup removes the region-specific VPN infrastructure.
* **AMI-Waiter**: checks when a copied AMI becomes available in the target region, marks the region live in Firebase, and sends an admin notification through SES.
* **Deploy**: deploys or terminates VPN EC2 instances. It verifies the Firebase token, checks Firebase role data, enforces DynamoDB usage limits, reads per-region secrets, launches EC2 instances, records instance state, and sends WireGuard config emails.
* **SecureGet**: returns authenticated read-only data needed by the frontend, such as supported AWS regions and selected configuration values.
* **CreateUser**: initializes user records after Firebase sign-in.

## Region Setup Flow

The setup flow prepares a region before any server can be deployed there.

1. The frontend sends an admin request with a target AWS region.
2. `TerraformRegion` verifies the Firebase bearer token and confirms the user has the admin role.
3. The Lambda reads source-region values from Secrets Manager.
4. The source EC2 AMI is copied into the target region.
5. The Lambda creates the regional network stack:
   * VPC with IPv4 and Amazon-provided IPv6 CIDR blocks
   * Subnet
   * Internet gateway
   * Route table with IPv4 and IPv6 default routes
   * Security group for WireGuard and SSH
   * Imported EC2 key pair
6. The Lambda writes the target-region deployment values to `wireguard/config/<region>` in Secrets Manager.
7. `AMI-Waiter` confirms the copied AMI is available and marks the region live in Firebase.

## Region Cleanup Flow

The cleanup flow removes region-level resources so an unused region does not keep producing cloud costs.

`TerraformRegion` can clean a non-source region by:

* terminating EC2 instances in the region
* deregistering VPN AMIs and deleting associated snapshots
* deleting the WireGuard security group
* deleting VPC resources, including subnets, internet gateways, and route tables
* deleting the region secret from Secrets Manager
* updating Firebase records so the region is no longer shown as live

The source region is protected from setup and cleanup requests.

## Deploy and Terminate Flow

The deploy flow launches one VPN server into an already prepared region.

1. The frontend sends `action: "deploy"`, the selected `target_region`, the user email, and a Firebase bearer token.
2. `Deploy` reads `wireguard/config/<target_region>` from Secrets Manager.
3. The Lambda verifies the Firebase token and reads the user's role from Firebase.
4. DynamoDB tables `vpn-users` and `vpn-roles` enforce the example product's per-user and role-based VPN limits.
5. The Lambda confirms the target region is live and that the prepared AMI exists there.
6. If the user already has a live VPN in that region, the Lambda returns the existing VPN configuration values.
7. Otherwise, the Lambda launches a new EC2 instance in the prepared subnet and security group.
8. Instance state is written to Firebase.
9. SES sends the WireGuard client configuration to the user and admin.

The terminate flow is admin-only. It accepts a user-to-region-to-instance map, terminates the requested EC2 instances, and marks matching Firebase records as terminated.

## Required AWS Services

The Lambda execution role needs permissions for the AWS services used by the platform:

* **EC2**: copy and describe AMIs, launch and terminate instances, manage VPCs, subnets, route tables, internet gateways, security groups, key pairs, and snapshots.
* **Secrets Manager**: read `FirebaseServiceAccount` and source-region config, create/update/delete `wireguard/config/<region>` secrets.
* **SES v2**: send VPN config and admin notification emails.
* **DynamoDB**: read and update `vpn-users` and `vpn-roles`.
* **CloudWatch Logs**: create log groups/streams and write Lambda logs.

Firebase is reached over HTTPS by the Lambda runtime. Firebase credentials are stored in AWS Secrets Manager.

## Required Secrets

The current Lambda code reads these AWS Secrets Manager values:

* `FirebaseServiceAccount`: Firebase Admin SDK service-account JSON.
* `wireguard/config/<source-region>`: source VPN image, key, and WireGuard values.
* `wireguard/config/<target-region>`: target-region VPN image, subnet, security group, key, and WireGuard values.

The per-region WireGuard secret includes:

* `VPN_IMAGE_ID`
* `SECURITY_GROUP_ID`
* `SUBNET_ID`
* `KEY_NAME`
* `CLIENT_PRIVATE_KEY`
* `SERVER_PUBLIC_KEY`
* `PUBLIC_KEY_MATERIAL` in the source-region secret

## Runtime Configuration

Suggested Lambda settings:

* `Deploy`
  * Memory: 512 MB
  * Storage: 512 MB
  * Timeout: long enough for EC2 launch, termination, Firebase writes, and SES email
* `TerraformRegion`
  * Memory: 512 MB or higher
  * Storage: 512 MB
  * Timeout: long enough for AMI copy request and AWS network setup
* `AMI-Waiter`
  * Memory: 512 MB
  * Storage: 512 MB
  * Timeout: long enough for AMI copy polling
* `SecureGet`
  * Memory: 512 MB
  * Storage: 512 MB
  * Timeout: 1 minute
* `CreateUser`
  * Memory: 512 MB
  * Storage: 512 MB
  * Timeout: 1 minute

## Required Lambda Layer

The shared layer should include the Python packages used across the functions:

* Firebase Admin SDK
* Google Cloud Firestore client
* Requests
* QR code dependencies

Rebuild and publish a new layer version after dependency changes, then attach the updated layer to functions that import those packages.

## Manual Review Checklist

Before using the Lambdas, confirm:

* `FirebaseServiceAccount` exists in Secrets Manager.
* The source-region `wireguard/config/<source-region>` secret has a valid AMI, key, and WireGuard values.
* Lambda execution roles have the AWS permissions listed above.
* SES sender identities are verified.
* DynamoDB tables `vpn-users` and `vpn-roles` exist for the VPN example implementation.
* Firebase contains the expected user role data.
* Target regions are set up before users deploy into them.
