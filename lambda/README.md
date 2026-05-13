# Lambda Setup

This folder contains the AWS Lambda functions that authenticate users, read the shared CloudLaunch configuration, call OCI Resource Manager over HTTPS, and email the generated WireGuard config.

## Required Secret

Create one AWS Secrets Manager secret named `CloudLaunch`. Use [CloudLaunch.example](secrets/CloudLaunch.example) as the payload template.

The secret has four top-level objects:

```json
{
  "aws": {
    "SES_SENDER": "CloudLaunch <noreply@example.com>",
    "ADMIN_EMAIL": "admin@example.com"
  },
  "firebase": {
    "type": "service_account"
  },
  "oci": {
    "OCI_REGION": "us-sanjose-1",
    "OCI_REGION_NAME": "San Jose",
    "OCI_USER_OCID": "ocid1.user...",
    "OCI_TENANCY_OCID": "ocid1.tenancy...",
    "OCI_FINGERPRINT": "00:00:00:...",
    "OCI_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
    "OCI_COMPARTMENT_ID": "ocid1.compartment...",
    "OCI_AVAILABILITY_DOMAIN": "...",
    "OCI_SUBNET_ID": "ocid1.subnet...",
    "OCI_SOURCE_IMAGE_ID": "ocid1.image..."
  },
  "vpn": {
    "WG_INTERFACE": "wg0"
  }
}
```

Keep the complete Firebase service-account JSON in `firebase`, all OCI API signing and Terraform values in `oci`, and WireGuard runtime values in `vpn`.

## OCI Deployment Flow

The `Deploy` Lambda does not import the Python `oci` SDK. It signs direct HTTPS requests with the API key values from `CloudLaunch.oci`.

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

The `Deploy` Lambda must reach public OCI endpoints for Resource Manager and Compute/Virtual Network.

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

## Deploy Lambda Packaging Notes

Use [build_deploy_lambda.sh](Deploy/build_deploy_lambda.sh) as the supported workflow for packaging the `Deploy` Lambda.

From the `lambda/Deploy/` directory, run:

```sh
zsh ./build_deploy_lambda.sh
```

The script recreates `~/Desktop/Deploy`, copies the `Deploy` Lambda code into that folder, and adds `terraform/` with the required OCI files.

Zip `~/Desktop/Deploy` and upload that zip as the `Deploy` Lambda code package.

## Manual Test Plan

Before testing, confirm:

* `CloudLaunch` exists and matches [CloudLaunch.example](secrets/CloudLaunch.example).
* The current shared layer is attached to the Lambda functions.
* The Lambda execution role has the IAM permissions above.
* Lambda egress can reach OCI public API endpoints on HTTPS.
* OCI has the automation user, API key, policies, compartment, subnet, image, and security rules described in [OCI/README.md](../OCI/README.md).
* The updated `Deploy` Lambda code package has been uploaded.

In the AWS Console, test `Deploy` with a real Firebase bearer token and a body like:

```json
{
  "headers": {
    "Authorization": "Bearer <firebase-id-token>"
  },
  "body": "{\"action\":\"deploy\",\"email\":\"user@example.com\"}"
}
```

Expected result: the function creates an OCI Resource Manager stack, applies it, records the stack and instance OCIDs in Firebase, resolves the public IPv4 address from the instance VNIC, and sends the SES email.

Test termination with an admin Firebase bearer token and a target map like:

```json
{
  "headers": {
    "Authorization": "Bearer <admin-firebase-id-token>"
  },
  "body": "{\"action\":\"terminate\",\"targets\":{\"<uid>\":{\"us-sanjose-1\":[\"<stack-ocid>\"]}}}"
}
```

Expected result: the function runs an OCI Resource Manager destroy job, directly terminates the compute instance if stack cleanup does not finish it, and marks the Firebase record terminated.

## References

* [OCI request signatures](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/signingrequests.htm)
* [OCI REST APIs](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/usingapi.htm)
* [AWS Lambda VPC internet access](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc-internet.html)
