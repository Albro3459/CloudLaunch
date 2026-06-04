# Lambda Setup

This folder contains the AWS Lambda functions that authenticate users, read the shared CloudLaunch configuration, call OCI Resource Manager over HTTPS, and email the generated WireGuard config.

## Required Secret

Create one AWS Secrets Manager secret named `CloudLaunch`. Use [CloudLaunch.example](secrets/CloudLaunch.example) as the payload template.

The secret has five top-level objects:
* `aws`
* `cloudflare`
* `firebase`
* `oci`
* `vpn`

Keep AWS SES email values in `aws`, the Cloudflare worker shared secret in `cloudflare`, the complete Firebase service-account JSON in `firebase`, OCI account and Terraform runtime values in `oci.regions.<region>`, and WireGuard runtime values in `vpn`.

`oci.regions` is a map keyed by the OCI region code, such as `us-sanjose-1` or `us-ashburn-1`. One region entry represents one OCI account or tenancy configuration.

Each region entry should include:
* `enabled`: `true` to allow new deploys, `false` to hide the region from SecureGet and reject new deploys.
* `region_limit`: app-level maximum active VPNs for that region. This cap applies to admins too.
* `OCI_REGION_NAME`: display name returned to the frontend.
* OCI API signing values: user OCID, tenancy OCID, fingerprint, and private key.
* Terraform runtime values: compartment, availability domain, subnet, source image, shape, boot volume, SSH keys, password hash, and IPv6 subnet CIDR.

Keep disabled region configs in the secret until all existing VPNs in that region are terminated. Admin termination can still use a disabled region's stored account config for cleanup.

## Configuration

* CreateUser:
  * Memory: 512 mb (speeds up cold starts)
  * Storage: 512 mb
  * Timeout: 1 min
* Deploy:
  * Memory: 512 mb (256 minimum)
  * Storage: 512 mb
  * Timeout: 7 min 30 sec (Need enough time to terminate the instance and the stack)
* SecureGet:
  * Memory: 512 mb (speeds up cold starts)
  * Storage: 512 mb
  * Timeout: 1 min

Set `cloudflare.CLOUDLAUNCH_WORKER_SECRET` in the `CloudLaunch` AWS Secrets Manager payload. The Cloudflare Worker stores the same value as a Cloudflare secret, sends it in the `x-cloudlaunch-worker-secret` header, and each Lambda rejects direct requests that do not include it.

## Deploy Flow

Deploy requests must include a `region` field. There is no default region.

For deploy actions, the `Deploy` Lambda:

1. Reads `CloudLaunch.oci.regions.<region>`.
2. Rejects missing, unsupported, or disabled regions.
3. Verifies the Firebase token and reads the user's role.
4. Checks for an existing active VPN for that user in the selected region.
5. Checks the DynamoDB user-level role limit.
6. Counts active Firebase VPN records in the selected region and rejects when `region_limit` is reached.
7. Creates an OCI Resource Manager stack using the selected region account config.
8. Saves stack, instance, status, IP, and WireGuard config data to Firebase.
9. Emails the generated WireGuard config.

For terminate actions, the request keeps the existing admin target map. Each target region is resolved to its own `oci.regions.<region>` config before cleanup, including disabled regions.

## SecureGet Flow

SecureGet supports:

* `requested: "regions"`: returns public region discovery and capacity.
* `requested: "config"`: returns a WireGuard client config for a known public IPv4 address.

The region list response includes only public-safe fields:

```json
{
  "regions": [
    {
      "oci_region": "us-sanjose-1",
      "oci_region_name": "California",
      "enabled": true,
      "capacity": {
        "limit": 3,
        "active": 2,
        "available": 1
      }
    }
  ]
}
```

SecureGet omits disabled regions from the public list and never returns OCI credentials, infrastructure OCIDs, Firebase credentials, password hashes, SSH keys, or WireGuard private keys.

## OCI Deployment Flow

The `Deploy` Lambda does not import the Python `oci` SDK. It signs direct HTTPS requests with the API key values from the selected `CloudLaunch.oci.regions.<region>` entry.

The Lambda calls these OCI APIs:

* Resource Manager: create stack, get stack, create apply/destroy job, get job, read job Terraform state
* Compute: get instance, terminate instance, list VNIC attachments
* Virtual Network: get VNIC and read the public IPv4 address

OCI signing follows Oracle's request-signature requirements: `GET` and `DELETE` sign `(request-target)`, `host`, and `date`; `POST` also signs `x-content-sha256`, `content-type`, and `content-length`. OCI REST APIs use regional HTTPS endpoints with versioned base paths such as `/20160918`.

## Lambda IAM

Attach least-privilege permissions for the AWS services the functions use:

* Secrets Manager: `secretsmanager:GetSecretValue` for the `CloudLaunch` secret.
* SES: `ses:SendEmail` for the verified sender identity or domain used by `aws.SES_SENDER`.
* DynamoDB: `dynamodb:GetItem`, `dynamodb:PutItem`, and `dynamodb:UpdateItem` on `vpn-users` and `vpn-roles`.
* CloudWatch Logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, and `logs:PutLogEvents`.
* VPC-attached Lambdas only: ENI permissions equivalent to the AWS managed `AWSLambdaVPCAccessExecutionRole` policy.

Firebase and OCI are reached over HTTPS by the Lambda runtime. There is no AWS SDK deployment step for OCI.

## Lambda Egress

The `Deploy` Lambda must reach public OCI endpoints for Resource Manager and Compute/Virtual Network in every enabled region.

* No VPC: Lambda runs in the Lambda-managed network and has normal outbound internet access.
* VPC private subnets, IPv4: route `0.0.0.0/0` from the private subnet route table to a NAT gateway in a public subnet.
* VPC dual-stack, IPv6: enable Lambda outbound IPv6 for dual-stack subnets, make sure every selected subnet has IPv4 and IPv6 CIDR blocks, and route `::/0` through an egress-only internet gateway. Keep IPv4 NAT if the target endpoint path still uses IPv4.
* VPC security group: allow outbound HTTPS on TCP `443`.

AWS notes that attaching Lambda to a public subnet does not give the function internet access by itself; use private subnets with the required routes.

## Required Lambda Layer

The shared layer should stay small:

* Firebase Admin SDK
* Google Cloud Firestore client
* Requests
* QR code dependencies
* Cryptography for OCI request signing

The OCI-over-HTTPS flow requires `cryptography` in the shared layer for request signing. The build is defined in [Dockerfile](Dockerfile). Rebuild after dependency changes and attach the updated layer version to functions that import `firebase_admin`, `requests`, `qrcode`, or `cryptography`.

## Layer Build

Use [build_layer.sh](build_layer.sh) to build the Lambda layer zip from the Dockerfile.

From the `lambda/` directory:

```sh
./build_layer.sh
```

To choose a different zip name:

```sh
./build_layer.sh my-layer.zip
```

The script builds the Docker image, copies `/layer/python` out of the container, zips it, and writes the final zip to your Desktop.

Upload the resulting layer zip to AWS Lambda, publish a new layer version, and attach it to the Lambda functions.

## Lambda Deployment

Use [publish.sh](publish.sh) as the supported workflow for publishing Lambda code updates.

From the `lambda/` directory, run one of:

```sh
./publish.sh Deploy
./publish.sh CreateUser
./publish.sh SecureGet
```

The script bumps the selected Lambda's `version.py`, stages the function in `lambda/.publish/stage`, writes the zip to `lambda/.publish/packages`, and publishes it with `aws lambda update-function-code` using the `cloudlaunch` AWS profile.

For the `Deploy` Lambda, `publish.sh` runs [build_deploy_lambda.sh](Deploy/build_deploy_lambda.sh) during staging so the package includes the required `terraform/` files from [OCI/terraform](../OCI/terraform).

## Manual Test Plan

Before testing, confirm:

* `CloudLaunch` exists and matches [CloudLaunch.example](secrets/CloudLaunch.example).
* Each enabled `oci.regions.<region>` entry has a valid OCI account config and realistic `region_limit`.
* The current shared layer is attached to the Lambda functions.
* The Lambda execution role has the IAM permissions above.
* Lambda egress can reach OCI public API endpoints on HTTPS.
* OCI has the automation user, API key, policies, compartment, subnet, image, and security rules described in [OCI/README.md](../OCI/README.md).
* The updated Lambda code packages have been uploaded.

In the AWS Console, test SecureGet region discovery with a real Firebase bearer token and the worker secret:

```json
{
  "headers": {
    "Authorization": "Bearer <firebase-id-token>",
    "x-cloudlaunch-worker-secret": "<worker-secret>"
  },
  "body": "{\"requested\":\"regions\"}"
}
```

Expected result: SecureGet returns a `regions` array with public display names and capacity counts only.

Test `Deploy` with a selected region:

```json
{
  "headers": {
    "Authorization": "Bearer <firebase-id-token>",
    "x-cloudlaunch-worker-secret": "<worker-secret>"
  },
  "body": "{\"action\":\"deploy\",\"email\":\"user@example.com\",\"region\":\"us-sanjose-1\"}"
}
```

Expected result: the function creates an OCI Resource Manager stack in the selected region account, applies it, records the stack and instance OCIDs in Firebase, resolves the public IPv4 address from the instance VNIC, and sends the SES email.

Test termination with an admin Firebase bearer token and a target map:

```json
{
  "headers": {
    "Authorization": "Bearer <admin-firebase-id-token>",
    "x-cloudlaunch-worker-secret": "<worker-secret>"
  },
  "body": "{\"action\":\"terminate\",\"targets\":{\"<uid>\":{\"us-sanjose-1\":[\"<stack-ocid>\"]}}}"
}
```

Expected result: the function selects the target region account config, runs an OCI Resource Manager destroy job, directly terminates the compute instance if stack cleanup does not finish it, and marks the Firebase record terminated.

To confirm disabled-region cleanup, set a region entry to `enabled: false` while leaving its account config intact. Deploy should reject that region, but admin termination for an existing target in that region should still run.

## References

* [OCI request signatures](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/signingrequests.htm)
* [OCI REST APIs](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/usingapi.htm)
* [AWS Lambda VPC internet access](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc-internet.html)
