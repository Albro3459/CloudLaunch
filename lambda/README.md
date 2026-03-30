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
  * Used by the deploy Lambda for OCI SDK authentication.
  * Use the example at [OCI-Auth.example](secrets/OCI-Auth.example) as the template for the secret payload.

## Required Lambda Layer

The Lambda functions rely on a shared Python dependency layer instead of packaging these libraries into each function zip.

This layer needs to include:

* Firebase Admin SDK
* Google Cloud Firestore client
* Requests
* QR code dependencies
* OCI SDK

The build for that layer is defined in [Dockerfile](Dockerfile). Rebuild the layer after dependency changes and attach the updated layer version to the Lambda functions that import `firebase_admin` or `oci`.

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
