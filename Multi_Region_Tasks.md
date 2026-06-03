# CloudLaunch Multi-Region Task List

Research source: `Multi_Region_Plan.md` plus local repo review on `oracle-multi-region`.

Important local findings:

- `Deploy` still reads a single `CloudLaunch.oci` object and passes that same config to deploy and terminate.
- `SecureGet` still returns one `region` object, not a public list of regions and capacity.
- Frontend already has region state, but `VPNdeployHelper` sends `target_region`; target API should send `region`.
- Frontend currently auto-selects the first region. Desired behavior is no hidden default region.
- Firebase data already uses `Users/<uid>/Regions/<region>/Instances/<instance>`, so no schema rewrite is needed.
- Terraform already accepts region, compartment, subnet, image, shape, boot volume, and WireGuard values as variables.
- Docker/layer/package scripts do not need dependency changes for this work.
- `lambda/secrets/CloudLaunch.json` is ignored by git. Keep it local only. Do not copy real secret values into docs or commits.

## Commit 1: Add region-mapped OCI secret helpers

Files:

- `lambda/Deploy/get_secrets.py`
- `lambda/SecureGet/get_secrets.py`

Tasks:

- Add `get_oci_regions(oci_section)` to validate `oci.regions` exists and is a non-empty object.
- Add `get_oci_region_config(oci_section, region)` to trim and require the requested region.
- Reject unsupported and disabled regions with clear `ValueError` messages.
- Normalize the returned region config so existing callers can still read `OciSecretKey.REGION`.
- Resolve the plan/code mismatch: the plan wants the region from the map key, while `vpn_manager._build_stack_variables()` currently reads `OCI_REGION`. Use one of these approaches and apply it consistently:
  - Preferred: return a copied region config with `OCI_REGION` injected from the map key, and reject if an optional existing `OCI_REGION` value disagrees.
  - Alternative: require `OCI_REGION` inside every region object and validate it equals the map key.
- Keep sensitive OCI fields private. Do not add any helper that exposes tenancy OCIDs, user OCIDs, fingerprints, subnet IDs, image IDs, private keys, password hashes, SSH keys, or compartment IDs.

Validation:

- Manually review helper behavior for missing region, unsupported region, disabled region, mismatch, and valid region.
- Do not add automated tests unless specifically requested.

## Commit 2: Enforce selected region and capacity in Deploy Lambda

Files:

- `lambda/Deploy/lambda_function.py`
- `lambda/Deploy/firebase.py`

Tasks:

- Parse deploy requests with required body field `region`.
- Stop using root `oci_config` for deploy calls. Use `oci_root_config` only to select `oci_region_config`.
- Return `400` for missing, unsupported, disabled, or mismatched regions.
- Use the selected `oci_region_config` for:
  - `get_secret_value(..., OciSecretKey.REGION_NAME)`
  - existing VPN lookup
  - `deploy_instance(...)`
  - response region metadata
  - SES email region name
- Add `get_active_instance_count_for_region(region)` in `lambda/Deploy/firebase.py`.
- Count active instances from actual Firestore paths: `Users/<uid>/Regions/<region>/Instances`.
- Use current local statuses from `vpn_status.py`: `pending` and `running`.
- Check `region_limit` before `increment_user_count()` and before `deploy_instance()`.
- Apply region cap to admins too. `override_existing_vpn` must not bypass region cap.
- Make admin user-level limit unlimited by bypassing the DynamoDB max-count check for `role == "admin"`.
- Keep normal user limit as one active VPN unless DynamoDB role config says otherwise.
- Consider whether to accept legacy `target_region` temporarily. Final frontend payload must use `region`.
- Keep failure response body for full regions shaped for frontend handling:

```json
{
  "error": "Region capacity reached",
  "region": "us-sanjose-1",
  "limit": 3,
  "active": 3
}
```

Validation:

- Build/manual review only unless tests are explicitly requested.
- Confirm deploy order remains: parse, require region, select config, verify token, read role, check existing user VPN, check user limit, check region limit, increment, deploy, save Firebase, email.

## Commit 3: Use per-region OCI config during termination

Files:

- `lambda/Deploy/lambda_function.py`

Tasks:

- In the terminate loop, select `oci_region_config = get_oci_region_config(oci_root_config, region)` for each target region.
- Pass selected `oci_region_config` to `terminate_instance_resources(...)`.
- Return clear errors for invalid target regions instead of trying cleanup with the wrong tenancy credentials.
- Keep the existing target request shape:

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

Validation:

- Manual review that every termination path signs OCI requests with the target region account config.

## Commit 4: Return public region capacity from SecureGet

Files:

- `lambda/SecureGet/lambda_function.py`
- `lambda/SecureGet/get_secrets.py`
- `lambda/SecureGet/firebase.py`

Tasks:

- Support public region discovery through SecureGet.
- Prefer `requested: "regions"` if doing a clean API break, or keep `requested: "region"` and return a `regions` array for smoother migration.
- Add `get_active_instance_count_for_region(region)` to SecureGet Firebase helpers, using the same Firestore path and lowercase active statuses as Deploy.
- Add a `build_public_region_list(oci_root_config)` style helper.
- Include only safe fields:
  - `oci_region`
  - `oci_region_name`
  - `enabled`
  - `capacity.limit`
  - `capacity.active`
  - `capacity.available`
- Omit disabled regions from the public list unless the frontend needs to show unavailable regions intentionally.
- Validate `region_limit` can be converted to an integer when present.
- Keep `requested: "config"` behavior unchanged for WireGuard config generation.

Validation:

- Confirm SecureGet never returns OCI credentials or infrastructure OCIDs.
- Confirm capacity count matches Deploy region-cap logic.

## Commit 5: Require explicit region selection in frontend

Files:

- `react-frontend/src/helpers/APIHelper.ts`
- `react-frontend/src/helpers/regionsHelper.ts`
- `react-frontend/src/stores/ociRegionsStore.ts`
- `react-frontend/src/pages/Home.tsx`
- `react-frontend/src/components/VPNTable.tsx`
- `react-frontend/src/pages/VPNSuccess.tsx`, only if region display typing needs cleanup

Tasks:

- Update `SecureGetRegionsHelper` request to match backend choice: `requested: "regions"` or the migrated `requested: "region"` response.
- Parse a `regions` array instead of a single `region` object.
- Extend `Region` type with optional capacity fields:
  - `enabled`
  - `capacity.limit`
  - `capacity.active`
  - `capacity.available`
- Keep `getRegionName(...)` working for existing table and success-page display.
- Replace static region display with a real selector.
- Do not silently auto-select the first region on page load.
- If there is only one available region, visual auto-selection is acceptable only if the `region` state is explicit before deploy.
- Disable full regions when `capacity.active >= capacity.limit`.
- Show capacity like `2 / 3 used`.
- Change deploy request body from `target_region` to `region`.
- Block deploy if no region is selected.
- Preserve admin terminate target shape and existing VPN table grouping.
- Add frontend error handling for:
  - `Missing required region`
  - `Unsupported OCI region: ...`
  - `Region capacity reached`
- Show a plain region-full message such as `<Region name> is currently full. Choose another region.`

Validation:

- Run React build when implementing this commit: `npm run build` from `react-frontend`.
- Manually check normal user deploy, admin override, region-full disabled UI, QR/config display, and admin termination.

## Commit 6: Update examples and docs for multi-region OCI accounts

Files:

- `lambda/secrets/CloudLaunch.example`
- `lambda/README.md`
- `OCI/README.md`
- `OCI/terraform/terraform.tfvars.example`
- `README.md`, if public wording should mention selectable OCI regions

Tasks:

- Rewrite `lambda/secrets/CloudLaunch.example` so `oci` contains `regions`.
- Include California and Virginia example entries with placeholder-only values.
- Add `enabled` and `region_limit` examples.
- Keep real `lambda/secrets/CloudLaunch.json` ignored and untouched.
- Update `lambda/README.md` manual deploy sample to include `region`.
- Update `lambda/README.md` SecureGet docs to describe region list response.
- Update `OCI/README.md` wording from `CloudLaunch.oci` to `CloudLaunch.oci.regions.<region>`.
- Add an OCI section for adding a new region/account:
  - choose tenancy/account and target region
  - create/select compartment
  - create automation group and user
  - add API signing key
  - add policies
  - create/select VCN, subnet, routing, IPv6, and security rules
  - record availability domain, subnet OCID, image OCID, shape, boot volume, and IPv6 CIDR
  - set app-level `region_limit` to match OCI capacity
- Update `terraform.tfvars.example` comments to say it is for manual stack testing only and runtime values now come from selected AWS secret region config.
- Do not change `lambda/Dockerfile`, `lambda/build_layer.sh`, `lambda/Deploy/build_deploy_lambda.sh`, or `OCI/terraform/cloudlaunch.tf` unless implementation uncovers a new dependency or Terraform variable gap.

Validation:

- Search docs/examples for stale single-region wording after edits.
- Confirm no real OCIDs, private keys, hashes, or Firebase credentials are copied into tracked files.

## Commit 7: Publish and configure one-region migration

This is an operational commit/checkpoint only if repo files change. Most tasks happen in AWS/OCI/Firebase and should not create code changes.

Tasks:

- Update AWS Secrets Manager `CloudLaunch` to the new `oci.regions` schema with California only.
- Leave Virginia out until California works with the new schema.
- Publish `Deploy` and `SecureGet` Lambdas after code changes.
- Confirm Cloudflare Worker needs no payload changes; it proxies request bodies unchanged.
- Verify `CloudLaunch` Lambda IAM still covers Secrets Manager, SES, DynamoDB, CloudWatch Logs, and any needed VPC ENI permissions.
- Manually test SecureGet region list with Firebase token.
- Manually test deploy to California.
- Manually test terminate from California.
- Confirm Firebase instance records still appear under `Users/<uid>/Regions/<region>/Instances`.
- Confirm ignored local files stay ignored:
  - `lambda/secrets/CloudLaunch.json`
  - `OCI/terraform/terraform.tfvars`
  - `cloudflare/.dev.vars`
  - `react-frontend/src/Secrets/firebaseConfig.ts`

## Commit 8: Add second OCI account and verify multi-region behavior

This is mostly operational. Create a repo commit only if docs/examples need correction after real setup.

Tasks:

- Set up Virginia OCI account/tenancy and target `us-ashburn-1`.
- Create CloudLaunch compartment or identify existing compartment.
- Create automation group and automation user.
- Add API signing key and store private key text in AWS Secrets Manager, not in repo.
- Add required IAM policies for Resource Manager, jobs, instances, and virtual networking.
- Create/select network prerequisites: VCN, subnet, route table, internet gateway/IPv6 routing, and security rules.
- Record per-region values:
  - `OCI_USER_OCID`
  - `OCI_TENANCY_OCID`
  - `OCI_FINGERPRINT`
  - `OCI_PRIVATE_KEY`
  - `OCI_COMPARTMENT_ID`
  - `OCI_AVAILABILITY_DOMAIN`
  - `OCI_SUBNET_ID`
  - `OCI_SOURCE_IMAGE_ID`
  - `OCI_IPV6_SUBNET_CIDR`
  - shape and boot volume values
- Add `us-ashburn-1` to AWS `CloudLaunch.oci.regions`.
- Confirm `region_limit` does not exceed real OCI quota/capacity.
- Test SecureGet shows both regions and correct capacity.
- Test deploy to Virginia.
- Test terminate from Virginia.
- Re-test California deploy/terminate after Virginia is enabled.

## Suggested final validation checklist

- `Deploy` returns `400` for missing region.
- `Deploy` returns `400` for unsupported/disabled region.
- `Deploy` returns `403` when region capacity is full.
- Admin can create multiple user-level VPNs only when region capacity allows.
- Normal user cannot create more than allowed user-level VPNs.
- `override_existing_vpn` only bypasses existing-user-VPN reuse for admins.
- Terminate uses target region OCI credentials.
- SecureGet returns region list and capacity only.
- Frontend cannot deploy without an explicit selected region.
- Full regions are disabled in UI.
- Existing VPN table and admin terminate flow still work.
- No real secret values appear in tracked files or docs.
