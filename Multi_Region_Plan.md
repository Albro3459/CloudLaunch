# CloudLaunch Multi-Region / Multi-OCI-Account Plan

## 1. What we actually want

You want CloudLaunch to support this model:

```text
1 OCI region = 1 OCI account / tenancy config
```

Example:

```text
us-sanjose-1  -> OCI account A
us-ashburn-1  -> OCI account B
```

A deployment request must always include a region. There should be **no default region**.

You also want two layers of limits:

```text
User-level limit:
  normal user -> 1 active VPN
  admin -> unlimited user-level VPNs

Region-level limit:
  us-sanjose-1 -> 3 total active VPNs
  us-ashburn-1 -> 4 total active VPNs
  applies to everyone, including admins
```

Concurrency protection is not a priority. That means we can count active Firebase records before deploy and reject if the region is full. No Firestore transaction reservation system is needed right now.

## 2. Current repo context

The current code is already close to the right shape.

The Lambda README says the `Deploy` Lambda signs OCI HTTPS requests directly with the API key values from `CloudLaunch.oci`, then calls OCI Resource Manager, Compute, and Virtual Network APIs. It also says the Lambda needs `secretsmanager:GetSecretValue`, SES, DynamoDB, CloudWatch Logs, and HTTPS egress to Firebase and OCI. ([GitHub][1])

The OCI README says AWS Lambda is the orchestrator, uploads the Terraform package to OCI Resource Manager, creates apply/destroy jobs, and reads Compute/VNIC data afterward. The Terraform creates the compute instance only and assumes the compartment, subnet, IPv6 setup, route tables, and security rules already exist. ([GitHub][2])

The current `Deploy` Lambda pulls a single `oci` secret section, then reads `OCI_REGION` and `OCI_REGION_NAME` from that one section. ([GitHub][3])

Deploy currently checks for existing user instances only in that single `oci_region`, then checks the user's DynamoDB role limit, increments user count, and deploys. ([GitHub][3])

Terminate currently loops through `targets`, reads the Firebase instance, then calls `terminate_instance_resources(oci_config, region, ...)` using the same single global `oci_config`. That will be wrong once different regions use different OCI accounts. ([GitHub][3])

`SecureGet` currently supports `"region"` and `"config"` requests. For `"region"`, it returns the single `OCI_REGION` and `OCI_REGION_NAME` from the single `oci` config. ([GitHub][4])

The Lambda layer Dockerfile only installs dependencies into `/layer/python`: Firebase Admin, Google Cloud Firestore, requests, qrcode, and cryptography. No change should be required for region support unless you add a new dependency. ([GitHub][5])

`build_layer.sh` builds an amd64 Lambda layer image, creates a container, copies `/layer/python`, zips it, and writes the layer zip to the Desktop. No region/account change is needed there. ([GitHub][6])

The Terraform provider already takes `region = var.region`, and the Terraform file declares variables for `region`, `availability_domain`, `compartment_id`, `subnet_id`, and `source_image_id`. That means Terraform does not need to know about "accounts" directly. It just needs to receive the selected region's values. ([GitHub][7])

OCI API signing keys are exactly the right credential type for this setup: Oracle's generated config snippet includes `user`, `fingerprint`, `tenancy`, `region`, and `key_file`. You will store those values in AWS Secrets Manager, with the private key content inline instead of a local `key_file` path. ([Oracle Docs][8])

AWS Secrets Manager is fine for this. AWS's Boto3 API retrieves `SecretString` or `SecretBinary` via `GetSecretValue`, and AWS's Lambda docs describe Secrets Manager as the place for credentials/API keys used by Lambda functions. ([AWS Documentation][9])

## 3. Target AWS Secrets Manager schema

Replace the current single `oci` object with a region map.

### Proposed `CloudLaunch` secret

```json
{
  "aws": {
    "SES_SENDER": "CloudLaunch <noreply@example.com>",
    "ADMIN_EMAIL": "admin@example.com"
  },
  "cloudflare": {
    "CLOUDLAUNCH_WORKER_SECRET": "..."
  },
  "firebase": {
    "...": "existing firebase admin credentials"
  },
  "vpn": {
    "WG_INTERFACE": "wg0",
    "WG_LISTEN_PORT": "51820",
    "WG_ADDRESS_V4": "...",
    "WG_ADDRESS_V6": "...",
    "WG_CLIENT_ADDRESS_V4": "...",
    "WG_CLIENT_ADDRESS_V6": "...",
    "WG_DNS_ADDRESS_V4": "...",
    "WG_DNS_ADDRESS_V6": "...",
    "WG_NETWORK_V4": "...",
    "WG_NETWORK_V6": "...",
    "WG_RATE_LIMIT": "...",
    "WG_RATE_LIMIT_BURST": "...",
    "WG_SERVER_PRIVATE_KEY": "...",
    "WG_SERVER_PUBLIC_KEY": "...",
    "WG_CLIENT_PRIVATE_KEY": "...",
    "WG_CLIENT_PUBLIC_KEY": "...",
    "WG_CLIENT_ALLOWED_IPS_V4": "...",
    "WG_CLIENT_ALLOWED_IPS_V6": "...",
    "WG_PEER_ALLOWED_IPV4": "...",
    "WG_PEER_ALLOWED_IPV6": "...",
    "WG_PEER_PERSISTENT_KEEPALIVE": "25"
  },
  "oci": {
    "regions": {
      "us-sanjose-1": {
        "enabled": true,
        "region_limit": 3,

        "OCI_REGION_NAME": "California",

        "OCI_USER_OCID": "ocid1.user.oc1..aaaa...",
        "OCI_TENANCY_OCID": "ocid1.tenancy.oc1..aaaa...",
        "OCI_FINGERPRINT": "aa:bb:cc:dd:...",
        "OCI_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",

        "OCI_COMPARTMENT_ID": "ocid1.compartment.oc1..aaaa...",
        "OCI_AVAILABILITY_DOMAIN": "xxxx:US-SANJOSE-1-AD-1",
        "OCI_SUBNET_ID": "ocid1.subnet.oc1.us-sanjose-1.aaaa...",
        "OCI_SOURCE_IMAGE_ID": "ocid1.image.oc1.us-sanjose-1.aaaa...",

        "OCI_SSH_AUTHORIZED_KEYS_JSON": "[\"ssh-ed25519 AAAA...\"]",
        "OCI_HASHED_PASSWORD": "...",

        "OCI_INSTANCE_SHAPE": "VM.Standard.A1.Flex",
        "OCI_INSTANCE_MEMORY_GBS": "6",
        "OCI_INSTANCE_OCPUS": "1",
        "OCI_BOOT_VOLUME_SIZE_GBS": "50",
        "OCI_BOOT_VOLUME_VPUS_PER_GB": "10",
        "OCI_IPV6_SUBNET_CIDR": "2603:..."
      },
      "us-ashburn-1": {
        "enabled": true,
        "region_limit": 4,

        "OCI_REGION_NAME": "Virginia",

        "OCI_USER_OCID": "ocid1.user.oc1..bbbb...",
        "OCI_TENANCY_OCID": "ocid1.tenancy.oc1..bbbb...",
        "OCI_FINGERPRINT": "11:22:33:44:...",
        "OCI_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",

        "OCI_COMPARTMENT_ID": "ocid1.compartment.oc1..bbbb...",
        "OCI_AVAILABILITY_DOMAIN": "xxxx:US-ASHBURN-AD-1",
        "OCI_SUBNET_ID": "ocid1.subnet.oc1.iad.bbbb...",
        "OCI_SOURCE_IMAGE_ID": "ocid1.image.oc1.iad.bbbb...",

        "OCI_SSH_AUTHORIZED_KEYS_JSON": "[\"ssh-ed25519 AAAA...\"]",
        "OCI_HASHED_PASSWORD": "...",

        "OCI_INSTANCE_SHAPE": "VM.Standard.A1.Flex",
        "OCI_INSTANCE_MEMORY_GBS": "6",
        "OCI_INSTANCE_OCPUS": "1",
        "OCI_BOOT_VOLUME_SIZE_GBS": "50",
        "OCI_BOOT_VOLUME_VPUS_PER_GB": "10",
        "OCI_IPV6_SUBNET_CIDR": "2603:..."
      }
    }
  }
}
```

However, these fields will stay the same, regardless of region:
```json
"OCI_SSH_AUTHORIZED_KEYS_JSON": "[\"ssh-ed25519 AAAA...\"]",
"OCI_HASHED_PASSWORD": "...",

"OCI_INSTANCE_SHAPE": "VM.Standard.A1.Flex",
"OCI_INSTANCE_MEMORY_GBS": "6",
"OCI_INSTANCE_OCPUS": "1",
"OCI_BOOT_VOLUME_SIZE_GBS": "50",
"OCI_BOOT_VOLUME_VPUS_PER_GB": "10",
"OCI_IPV6_SUBNET_CIDR": "2603:..."
```

Do **not** add `default_region`.

The region must be required from the frontend for deploys.

## 4. Lambda helper changes

### `get_secrets.py`

Keep the existing `OciSecretKey` enum because each region config can still use the same key names.

Add helpers:

```python
class OciSecretKey(StrEnum):
    REGION_NAME = "OCI_REGION_NAME"
    USER_OCID = "OCI_USER_OCID"
    TENANCY_OCID = "OCI_TENANCY_OCID"
    FINGERPRINT = "OCI_FINGERPRINT"
    PRIVATE_KEY = "OCI_PRIVATE_KEY"
    COMPARTMENT_ID = "OCI_COMPARTMENT_ID"
    AVAILABILITY_DOMAIN = "OCI_AVAILABILITY_DOMAIN"
    SUBNET_ID = "OCI_SUBNET_ID"
    SOURCE_IMAGE_ID = "OCI_SOURCE_IMAGE_ID"
    SSH_AUTHORIZED_KEYS_JSON = "OCI_SSH_AUTHORIZED_KEYS_JSON"
    HASHED_PASSWORD = "OCI_HASHED_PASSWORD"
    INSTANCE_SHAPE = "OCI_INSTANCE_SHAPE"
    INSTANCE_MEMORY_GBS = "OCI_INSTANCE_MEMORY_GBS"
    INSTANCE_OCPUS = "OCI_INSTANCE_OCPUS"
    BOOT_VOLUME_SIZE_GBS = "OCI_BOOT_VOLUME_SIZE_GBS"
    BOOT_VOLUME_VPUS_PER_GB = "OCI_BOOT_VOLUME_VPUS_PER_GB"
    IPV6_SUBNET_CIDR = "OCI_IPV6_SUBNET_CIDR"
```

Note:
`REGION` will need to come from the region object's property name

Add:

```python
def get_oci_regions(oci_section: dict) -> dict:
    regions = (oci_section or {}).get("regions")
    if not isinstance(regions, dict) or not regions:
        raise ValueError("Missing required secret value: oci.regions")
    return regions


def get_oci_region_config(oci_section: dict, region: str) -> dict:
    requested_region = (region or "").strip()
    if not requested_region:
        raise ValueError("Missing required region")

    regions = get_oci_regions(oci_section)
    region_config = regions.get(requested_region)

    if not isinstance(region_config, dict) or not region_config:
        raise ValueError(f"Unsupported OCI region: {requested_region}")

    if region_config.get("enabled") is False:
        raise ValueError(f"OCI region is disabled: {requested_region}")

    configured_region = region_config.get(OciSecretKey.REGION.value)
    if configured_region != requested_region:
        raise ValueError(
            f"Region config mismatch: request={requested_region}, config={configured_region}"
        )

    return region_config
```

Why the mismatch check matters: it prevents accidentally mapping `us-ashburn-1` to a California subnet or California tenancy credentials.

## 5. `Deploy` Lambda changes

### Required request shape

Deploy body should become:

```json
{
  "action": "deploy",
  "email": "user@example.com",
  "region": "us-sanjose-1",
  "override_existing_vpn": false
}
```

Note: `override_existing_vpn` will **NOT** override the region limit.

Terminate can keep the existing target map:

```json
{
  "action": "terminate",
  "targets": {
    "<uid>": {
      "us-sanjose-1": ["<stack-ocid>"]
    }
  }
}
```

### Deployment flow

Current code pulls `oci_config = get_secret_section(..., SecretSection.OCI)` and immediately reads OCI region from the property name from that object. That must change because `oci_config` becomes the parent region map. ([GitHub][3])

New flow:

```python
oci_root_config = get_secret_section(cloudlaunch_secret, SecretSection.OCI)

requested_region = (body.get("region") or "").strip()
if not requested_region:
    return {
        "statusCode": 400,
        "body": json.dumps({"error": "Missing required region"})
    }

try:
    oci_region_config = get_oci_region_config(oci_root_config, requested_region)
    oci_region = get_secret_value(oci_region_config, OciSecretKey.REGION)
    oci_region_name = get_secret_value(oci_region_config, OciSecretKey.REGION_NAME)
except ValueError as e:
    return {
        "statusCode": 400,
        "body": json.dumps({"error": str(e)})
    }
```

Then every deploy call should use `oci_region_config`, not the parent `oci` object:

```python
result = deploy_instance(
    oci_region_config,
    vpn_config,
    user_id,
    oci_region
)
```

That fits the existing `vpn_manager.py` design because `_get_oci_auth()` and `_build_stack_variables()` already accept one `oci_config` dict and read values like `OCI_USER_OCID`, `OCI_TENANCY_OCID`, `OCI_COMPARTMENT_ID`, etc. ([GitHub][10])

### User existing-instance check

Current code checks:

```python
vpn = get_user_instances_in_region(user_id, role, oci_region)
```

That still works. The difference is `oci_region` now comes from the request-selected region, not the global secret. The current deploy code already uses this region-specific Firebase query before creating a new VPN. ([GitHub][3])

### Region limit check

Add this before `increment_user_count()` and before `deploy_instance()`.

Recommended helper in `firebase.py`:

```python
ACTIVE_REGION_STATUSES = {"Running", "Deploying", "Pending", "Starting"}

def get_active_instance_count_for_region(region: str) -> int:
    db = firestore.client()
    count = 0

    users_ref = db.collection("Users")
    for user_doc in users_ref.stream():
        instances_ref = (
            users_ref
            .document(user_doc.id)
            .collection("Regions")
            .document(region)
            .collection("Instances")
        )

        for instance_doc in instances_ref.stream():
            instance = instance_doc.to_dict() or {}
            status = instance.get("status")
            if status in ACTIVE_REGION_STATUSES:
                count += 1

    return count
```

If the current Firestore collection name is not `Users`, use the existing one from `firebase.py`. I could not get a clean full render of `firebase.py` through GitHub's public page, so use the actual collection names already in that file.

Then in `lambda_function.py`:

```python
region_limit = oci_region_config.get("region_limit")

if region_limit is not None:
    try:
        region_limit = int(region_limit)
    except (TypeError, ValueError):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Invalid region_limit for {oci_region}"})
        }

    region_active_count = get_active_instance_count_for_region(oci_region)

    if region_active_count >= region_limit:
        return {
            "statusCode": 403,
            "body": json.dumps({
                "error": "Region capacity reached",
                "region": oci_region,
                "limit": region_limit,
                "active": region_active_count
            })
        }
```

Order should be:

```text
1. Parse body
2. Require region
3. Load selected region config
4. Verify Firebase token
5. Get user role
6. Check existing user VPN in requested region
7. Check user-level limit
8. Check region-level limit
9. Increment user count
10. Deploy
11. Save Firebase metadata
12. Send email
```

The region cap must apply to admins too. Do not put it inside the normal-user user-limit branch.

### Termination flow

Terminate must not use the root `oci` object or a stale default. Current terminate calls:

```python
terminate_instance_resources(
    oci_config,
    region,
    stack_id=stack_id,
    instance_ocid=instance_ocid,
)
```

That is only safe while there is one global OCI account. With multi-region accounts, change it to:

```python
oci_region_config = get_oci_region_config(oci_root_config, region)

cleanup_result = terminate_instance_resources(
    oci_region_config,
    region,
    stack_id=stack_id,
    instance_ocid=instance_ocid,
)
```

This is mandatory. Otherwise an Virginia termination could be signed with California tenancy credentials and fail.

## 6. `SecureGet` Lambda changes

`SecureGet` currently supports:

```python
VALID_REQUESTS = {"region", "config"}
```

For `requested == "region"`, it returns one region from the single `oci_config`. ([GitHub][4])

Change this API to support region discovery.

### Option A: keep `requested: "region"` but return multiple regions

Request:

```json
{
  "requested": "region"
}
```

Response:

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
    },
    {
      "oci_region": "us-ashburn-1",
      "oci_region_name": "Virginia",
      "enabled": true,
      "capacity": {
        "limit": 4,
        "active": 1,
        "available": 3
      }
    }
  ]
}
```

This is probably the cleanest migration because the frontend already asks SecureGet for region info.

### Option B: rename request to `regions`

Better long-term API:

```python
VALID_REQUESTS = {"regions", "config"}
```

Request:

```json
{
  "requested": "regions"
}
```

Response same as above.

### SecureGet implementation

Add helper:

```python
def build_public_region_list(oci_root_config):
    regions = get_oci_regions(oci_root_config)
    result = []

    for region_key, region_config in regions.items():
        if region_config.get("enabled") is False:
            continue

        region = get_secret_value(region_config, OciSecretKey.REGION)
        region_name = get_secret_value(region_config, OciSecretKey.REGION_NAME)

        limit = region_config.get("region_limit")
        active = get_active_instance_count_for_region(region)

        result.append({
            "oci_region": region,
            "oci_region_name": region_name,
            "enabled": True,
            "capacity": {
                "limit": int(limit) if limit is not None else None,
                "active": active,
                "available": None if limit is None else max(int(limit) - active, 0)
            }
        })

    return result
```

Do **not** expose tenancy OCIDs, user OCIDs, fingerprints, subnet IDs, image IDs, private keys, password hashes, SSH keys, or compartment IDs through SecureGet.

For `requested == "config"`, probably no change is needed unless the returned WireGuard config response includes region display data. It currently builds client config from IP addresses and VPN secrets, not OCI secrets. ([GitHub][4])

## 7. Firebase updates

### Current shape can mostly stay

Current terminate target shape already groups by region:

```json
{
  "<uid>": {
    "us-sanjose-1": ["<stack-ocid>"]
  }
}
```

The Lambda README's manual terminate test uses exactly that shape. ([GitHub][1])

So you do **not** need a major Firebase schema rewrite.

### Add Firebase helper functions

Add:

```python
def get_active_instance_count_for_region(region: str) -> int:
    ...
```

Optional admin UI helper:

```python
def get_region_capacity_summary(regions_config: dict) -> list[dict]:
    ...
```

### Keep DynamoDB user limits

Your user-level limits currently live in DynamoDB `vpn-users` and `vpn-roles`, as seen in `Deploy` where it creates those DynamoDB table handles and imports `get_max_count_for_role`, `get_user_vpn_count`, and `increment_user_count`. ([GitHub][3])

Keep that as-is for now.

But note the current deploy flow increments the user count before deployment. If a deploy fails after incrementing, there will be drift. This is acceptable. The user will reach out to the admin for help.

## 8. React frontend updates

### Region selection

Deployment UI must require a region.

On page load:

```text
Frontend -> SecureGet requested=regions
SecureGet -> list of enabled regions with capacity
Frontend -> render region selector
```

Example display:

```text
California      2 / 3 used
Virginia       1 / 4 used
```

Disable region if:

```text
enabled == false
active >= limit
```

Then deploy request:

```json
{
  "action": "deploy",
  "email": "<current user email>",
  "region": "us-sanjose-1"
}
```

### No default region

Do not auto-deploy to the first region. Make the user pick one.

It is okay to auto-select the only available region visually, but the deploy request still must include it explicitly.

### Existing VPN display

Wherever the frontend shows VPNs grouped by region, keep that. It already matches the backend target shape.

For admin termination, continue sending:

```json
{
  "action": "terminate",
  "targets": {
    "<uid>": {
      "us-sanjose-1": ["<stack-ocid>"]
    }
  }
}
```

### Error handling

Add UI handling for:

```json
{
  "error": "Missing required region"
}
```

```json
{
  "error": "Unsupported OCI region: us-phoenix-1"
}
```

```json
{
  "error": "Region capacity reached",
  "region": "us-sanjose-1",
  "limit": 3,
  "active": 3
}
```

The last one should show a plain message like:

```text
California is currently full. Choose another region.
```

## 9. Terraform changes

No functional Terraform change is needed for this feature.

Reason: `cloudlaunch.tf` already takes region, compartment, subnet, image, AD, shape, boot volume, and WireGuard settings as variables. The selected Lambda region config can keep feeding those values into the existing Resource Manager stack variables. ([GitHub][7])

What you should update:

1. `terraform.tfvars.example`

   * Add comments explaining values are now per-region in AWS Secrets Manager.
   * Make clear that `terraform.tfvars` is for manual stack testing only.

2. `OCI/README.md`

   * Replace "CloudLaunch.oci" single-region wording with "CloudLaunch.oci.regions.<region>".
   * Add a section for adding a new region/account.

The OCI README already warns that `terraform.tfvars` can contain sensitive values and that uploading it puts those values in the stack artifact. Keep that warning. ([GitHub][2])

## 10. Docker / Lambda packaging updates

No Docker dependency change is needed.

Current Dockerfile installs:

```text
firebase-admin
google-cloud-firestore
requests
qrcode[pil]
cryptography
```

That is still enough. ([GitHub][5])

`build_layer.sh` does not need logic changes. It builds the Lambda layer for `linux/amd64`, copies `/layer/python` out of the container, zips it, and writes the layer zip. ([GitHub][6])

`publish.sh` likely does not need a logic change either. The README says it packages the selected Lambda and, for Deploy, runs `build_deploy_lambda.sh` so the Terraform files are included. ([GitHub][1])

One repo note: I tried `lambda/docker-compose.yml` and got a 404. I do not see a Docker Compose file at that path. If there is a compose file elsewhere in the repo, update only if it contains environment variables or local mocks for the `CloudLaunch` secret shape.

## 11. OCI console work per account / region

For each OCI account/tenancy/region pair, do the following.

### 1. Pick the home/target region

Example:

```text
Account A: us-sanjose-1
Account B: us-ashburn-1
```

### 2. Create a CloudLaunch compartment

Create or choose a compartment for CloudLaunch VPN resources.

Record:

```text
OCI_COMPARTMENT_ID
```

### 3. Create automation group and user

In each OCI account:

```text
Group: CloudLaunchAutomation
User: cloudlaunch-automation
```

Add the user to the group.

### 4. Add API signing key

Generate or upload an API signing key for the automation user.

Record:

```text
OCI_USER_OCID
OCI_TENANCY_OCID
OCI_FINGERPRINT
OCI_PRIVATE_KEY
OCI_REGION
```

Oracle's API key config snippet includes the user OCID, fingerprint, tenancy OCID, region, and private key file path. For Lambda, store the actual private key text in AWS Secrets Manager instead of a file path. ([Oracle Docs][8])

### 5. Add IAM policies

The OCI README's current policy shape is still right:

```text
Allow group CloudLaunchAutomation to manage orm-stacks in compartment <compartment-name>
Allow group CloudLaunchAutomation to manage orm-jobs in compartment <compartment-name>
Allow group CloudLaunchAutomation to manage instances in compartment <compartment-name>
Allow group CloudLaunchAutomation to read virtual-network-family in compartment <compartment-name>
```

It also notes that if subnet, image, or network resources live in another compartment, you need matching read/use policy there. ([GitHub][2])

### 6. Create network prerequisites

Per region/account, create or identify:

```text
VCN
Subnet
Route table
Internet gateway / IPv6 routing if needed
Security list or NSG
```

The OCI README says the Lambda-created stack assumes the compartment, subnet, IPv6 setup, route tables, and security rules already exist. ([GitHub][2])

Required security rules from the README:

```text
SSH TCP 22:
  only your approved personal IPv4/32

WireGuard UDP 51820:
  IPv4 0.0.0.0/0
  IPv6 ::/0 if IPv6 is enabled

Egress:
  allow VPN client traffic out to 0.0.0.0/0 and ::/0
```

([GitHub][2])

### 7. Get region-specific infrastructure values

Record these for each region config:

```text
OCI_AVAILABILITY_DOMAIN
OCI_SUBNET_ID
OCI_SOURCE_IMAGE_ID
OCI_IPV6_SUBNET_CIDR
OCI_INSTANCE_SHAPE
OCI_INSTANCE_MEMORY_GBS
OCI_INSTANCE_OCPUS
OCI_BOOT_VOLUME_SIZE_GBS
OCI_BOOT_VOLUME_VPUS_PER_GB
```

### 8. Make sure quotas/capacity match your Firebase/AWS configured limit

If California is limited to 3, make sure the OCI account can actually run 3 of your selected shape.

If Virginia is limited to 4, make sure that account can actually run 4.

Your app-level region limit prevents CloudLaunch from over-requesting, but OCI quota can still reject you earlier if the tenancy does not have capacity.

## 12. Suggested implementation order

### Phase 1: Secrets schema

1. Update AWS `CloudLaunch` secret from:

```json
"oci": {
  "OCI_REGION": "us-sanjose-1",
  "...": "..."
}
```

to:

```json
"oci": {
  "regions": {
    "us-sanjose-1": {
      "...": "..."
    }
  }
}
```

2. Add California only first.
3. Do not add Virginia until California works with the new schema.

### Phase 2: Backend helper changes

1. Add `get_oci_regions()`.
2. Add `get_oci_region_config()`.
3. Add Firebase active region count helper.
4. Add unit-style local tests for:

   * missing region
   * unsupported region
   * disabled region
   * region mismatch
   * valid single region

### Phase 3: Deploy Lambda

1. Require `region`.
2. Select `oci_region_config`.
3. Use selected config for deploy.
4. Check region cap before deploying.
5. Save selected region/account metadata.
6. Fix terminate to select config by target region.

### Phase 4: SecureGet

1. Change region response to return enabled regions.
2. Include public capacity values.
3. Never return OCI credentials or infrastructure OCIDs.

### Phase 5: Frontend

1. Fetch regions from SecureGet.
2. Require region selection.
3. Send `region` in deploy request.
4. Show region capacity.
5. Handle region-full errors.

### Phase 6: Add second OCI account

1. Set up Virginia OCI account.
2. Add automation user/API key.
3. Add policies.
4. Create/select compartment, subnet, image, AD.
5. Add `us-ashburn-1` to AWS secret.
6. Test SecureGet regions response.
7. Test deploy to Virginia.
8. Test terminate from Virginia.
9. Confirm California still works.

## 13. Expected code touch list

### Lambda

```text
lambda/Deploy/lambda_function.py
lambda/Deploy/get_secrets.py
lambda/Deploy/firebase.py
lambda/SecureGet/lambda_function.py
lambda/SecureGet/get_secrets.py
lambda/SecureGet/firebase.py
```

If `get_secrets.py` and `firebase.py` are duplicated per Lambda folder, update both copies or move shared helpers into shared package code if your packaging supports that.

### Docs

```text
lambda/README.md
OCI/README.md
lambda/CloudLaunch.example
OCI/terraform/terraform.tfvars.example
```

### Frontend

Likely areas:

```text
region selector / deploy form
SecureGet API client
Deploy API client
admin instance list / terminate flow
capacity display
```

### No expected change

```text
lambda/Dockerfile
lambda/build_layer.sh
OCI/terraform/cloudlaunch.tf
OCI/terraform/wireguard-cloud-init.sh.tftpl
OCI/terraform/backdoor-cloud-init.yaml
```

## 14. Bottom line

This is a clean change.

The biggest required backend changes are:

```text
Require region on deploy.
Use region to select OCI credentials/config from AWS Secrets Manager.
Apply a global region cap before deploy.
Use the target region's OCI config during terminate.
Expose enabled regions/capacity through SecureGet.
```

Terraform and Docker are basically fine. The OCI work is repetitive setup per account: automation user, API key, policies, compartment/network/image values, then put those values into AWS Secrets Manager under that region.

[1]: https://github.com/Albro3459/CloudLaunch/blob/oracle/lambda/README.md "CloudLaunch/lambda/README.md at oracle · Albro3459/CloudLaunch · GitHub"
[2]: https://github.com/Albro3459/CloudLaunch/blob/oracle/OCI/README.md "CloudLaunch/OCI/README.md at oracle · Albro3459/CloudLaunch · GitHub"
[3]: https://github.com/Albro3459/CloudLaunch/blob/oracle/lambda/Deploy/lambda_function.py "CloudLaunch/lambda/Deploy/lambda_function.py at oracle · Albro3459/CloudLaunch · GitHub"
[4]: https://github.com/Albro3459/CloudLaunch/blob/oracle/lambda/SecureGet/lambda_function.py "CloudLaunch/lambda/SecureGet/lambda_function.py at oracle · Albro3459/CloudLaunch · GitHub"
[5]: https://github.com/Albro3459/CloudLaunch/blob/oracle/lambda/Dockerfile "CloudLaunch/lambda/Dockerfile at oracle · Albro3459/CloudLaunch · GitHub"
[6]: https://github.com/Albro3459/CloudLaunch/blob/oracle/lambda/build_layer.sh "CloudLaunch/lambda/build_layer.sh at oracle · Albro3459/CloudLaunch · GitHub"
[7]: https://github.com/Albro3459/CloudLaunch/blob/oracle/OCI/terraform/cloudlaunch.tf "CloudLaunch/OCI/terraform/cloudlaunch.tf at oracle · Albro3459/CloudLaunch · GitHub"
[8]: https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm?utm_source=chatgpt.com "Required Keys and OCIDs"
[9]: https://docs.aws.amazon.com/goto/boto3/secretsmanager-2017-10-17/GetSecretValue?utm_source=chatgpt.com "get_secret_value - Boto3 1.43.20 documentation"
[10]: https://raw.githubusercontent.com/Albro3459/CloudLaunch/refs/heads/oracle/lambda/Deploy/vpn_manager.py "raw.githubusercontent.com"
