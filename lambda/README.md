# Lambda Setup

This Lambda code expects a shared Python layer and several AWS Secrets Manager secrets to exist before the functions are deployed.

## Required Secrets

Create these AWS Secrets Manager secrets:

* `FirebaseServiceAccount`
  * Used by the Lambda functions that call `firebase_admin`.
  * Use the example at [FirebaseServiceAccount.example](secrets/FirebaseServiceAccount.example) as the template for the secret payload.

* `VPN-Config`
  * Used for deployment configuration, WireGuard values, SES sender settings, and other runtime values.
  * Use the example at [VPN-Config.example](secrets/VPN-Config.example) as the template for the secret payload.

* `OCI-Auth`
  * Used by the deploy Lambda for OCI REST API request signing.
  * Use the example at [OCI-Auth.example](secrets/OCI-Auth.example) as the template for the secret payload.

## OCI Deployment

The `Deploy` Lambda manages Oracle Cloud Infrastructure over HTTPS with signed REST requests. It does not use the Python OCI SDK because the SDK is too large for an AWS Lambda layer, even when the layer zip is uploaded through S3.

The Lambda needs outbound egress to public OCI API endpoints for Resource Manager, Compute, and Virtual Network calls. If the Lambda runs outside a VPC, normal Lambda internet egress should be enough. If it is attached to private VPC subnets, configure a NAT gateway or another approved outbound path.

`OCI-Auth` contains only OCI request-signing values:

```json
{
  "OCI_USER_OCID": "...",
  "OCI_TENANCY_OCID": "...",
  "OCI_FINGERPRINT": "...",
  "OCI_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

In OCI, create or choose an automation user, add an API signing key, and grant only the policies needed to manage Resource Manager stacks/jobs, inspect or terminate compute instances, and read VNIC details. Keep Terraform/runtime values in `VPN-Config`, not `OCI-Auth`.

## Required Lambda Layer

The Lambda functions rely on a shared Python dependency layer instead of packaging these libraries into each function zip.

This layer needs to include:

* Firebase Admin SDK
* Google Cloud Firestore client
* Requests
* QR code dependencies

The build for that layer is defined in [Dockerfile](Dockerfile). Rebuild the layer after dependency changes and attach the updated layer version to the Lambda functions that import `firebase_admin`, `requests`, or `qrcode`.

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
