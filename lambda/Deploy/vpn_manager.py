import base64
import hashlib
import json
import re
import time
import zipfile
from email.utils import formatdate
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import requests

from firebase import (
    attach_instance_ocid,
    mark_instance_failed,
    mark_instance_running,
    upsert_stack_backed_instance_record,
)
from get_secrets import OciSecretKey, VpnSecretKey, get_secret_value

STACK_CREATE_TIMEOUT_SECONDS = 300
JOB_TIMEOUT_SECONDS = 1800
PUBLIC_IP_TIMEOUT_SECONDS = 300
INSTANCE_TERMINATION_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5
STACK_TERRAFORM_FILES = (
    "cloudlaunch.tf",
    "wireguard-cloud-init.sh.tftpl",
    "backdoor-cloud-init.yaml",
)

class OciServiceError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"OCI API returned {status} {code}: {message}")
        self.status = status
        self.code = code


def _rsa_sha256_sign(private_key, signing_string):
    normalized_key = private_key.strip().replace("\\n", "\n").encode("utf-8")
    signer = serialization.load_pem_private_key(normalized_key, password=None)
    signature = signer.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def _to_namespace(value):
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    if isinstance(value, dict):
        return SimpleNamespace(**{
            _to_snake_case(key): _to_namespace(item)
            for key, item in value.items()
        })
    return value


def _to_snake_case(value):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).replace("-", "_").lower()


class OciResponse:
    def __init__(self, data):
        self.data = data


class OciSignedRestClient:
    def __init__(self, auth, service, api_version):
        self.auth = auth
        self.host = f"{service}.{auth['region']}.oraclecloud.com"
        self.api_version = api_version

    def get(self, path, params=None, raw_text=False, accept=None):
        return self._request("GET", path, params=params, raw_text=raw_text, accept=accept)

    def post(self, path, payload):
        return self._request("POST", path, payload=payload)

    def delete(self, path, params=None):
        return self._request("DELETE", path, params=params)

    def _request(self, method, path, params=None, payload=None, raw_text=False, accept=None):
        target = f"/{self.api_version}{path}"
        if params:
            query = "&".join(
                f"{quote(str(key), safe='-._~')}={quote(str(value), safe='-._~')}"
                for key, value in params.items()
                if value is not None
            )
            if query:
                target = f"{target}?{query}"

        url = f"https://{self.host}{target}"
        body = b""
        headers = {
            "accept": accept or "application/json",
            "date": formatdate(timeval=None, localtime=False, usegmt=True),
            "host": self.host,
        }
        signed_headers = ["(request-target)", "host", "date"]

        if method in {"POST", "PUT"}:
            body = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
            headers.update({
                "content-length": str(len(body)),
                "content-type": "application/json",
                "x-content-sha256": base64.b64encode(hashlib.sha256(body).digest()).decode("ascii"),
            })
            signed_headers.extend(["x-content-sha256", "content-type", "content-length"])

        headers["authorization"] = self._build_authorization_header(method, target, headers, signed_headers)
        response = requests.request(method, url, headers=headers, data=body, timeout=30)
        if response.status_code >= 400:
            raise _build_oci_error(response)
        if raw_text:
            return OciResponse(response.text)
        if not response.text:
            return OciResponse(None)
        return OciResponse(_to_namespace(response.json()))

    def _build_authorization_header(self, method, target, headers, signed_headers):
        signing_values = {
            "(request-target)": f"{method.lower()} {target}",
            **headers,
        }
        signing_string = "\n".join(
            f"{header}: {signing_values[header]}"
            for header in signed_headers
        )
        signature = _rsa_sha256_sign(self.auth["private_key"], signing_string)
        key_id = f"{self.auth['tenancy']}/{self.auth['user']}/{self.auth['fingerprint']}"
        return (
            'Signature version="1",'
            f'keyId="{key_id}",'
            'algorithm="rsa-sha256",'
            f'headers="{" ".join(signed_headers)}",'
            f'signature="{signature}"'
        )


def _build_oci_error(response):
    code = "UNKNOWN"
    message = response.text
    try:
        body = response.json()
        code = body.get("code") or code
        message = body.get("message") or message
    except ValueError:
        pass
    return OciServiceError(response.status_code, code, message)


class ResourceManagerClient:
    def __init__(self, auth):
        self.client = OciSignedRestClient(auth, "resourcemanager", "20180917")

    def create_stack(self, details):
        return self.client.post("/stacks", details)

    def get_stack(self, stack_id):
        return self.client.get(f"/stacks/{quote(stack_id, safe='')}")

    def create_job(self, details):
        return self.client.post("/jobs", details)

    def get_job(self, job_id):
        return self.client.get(f"/jobs/{quote(job_id, safe='')}")

    def get_job_logs_content(self, job_id):
        return self.client.get(
            f"/jobs/{quote(job_id, safe='')}/logs/content",
            raw_text=True,
            accept="text/plain; charset=utf-8",
        )

    def get_job_tf_state(self, job_id):
        return self.client.get(
            f"/jobs/{quote(job_id, safe='')}/tfState",
            raw_text=True,
            accept="application/octet-stream",
        )

    def list_stack_associated_resources(self, stack_id):
        return self.client.get(f"/stacks/{quote(stack_id, safe='')}/associatedResources")

    def delete_stack(self, stack_id):
        return self.client.delete(f"/stacks/{quote(stack_id, safe='')}")


class ComputeClient:
    def __init__(self, auth):
        self.client = OciSignedRestClient(auth, "iaas", "20160918")

    def get_instance(self, instance_id):
        return self.client.get(f"/instances/{quote(instance_id, safe='')}")

    def terminate_instance(self, instance_id):
        return self.client.delete(
            f"/instances/{quote(instance_id, safe='')}",
            params={"preserveBootVolume": "false"},
        )

    def list_vnic_attachments(self, compartment_id, instance_id):
        return self.client.get(
            "/vnicAttachments",
            params={
                "compartmentId": compartment_id,
                "instanceId": instance_id,
            },
        )


class VirtualNetworkClient:
    def __init__(self, auth):
        self.client = OciSignedRestClient(auth, "iaas", "20160918")

    def get_vnic(self, vnic_id):
        return self.client.get(f"/vnics/{quote(vnic_id, safe='')}")


def _get_oci_auth(auth_secret_values, region):
    return {
        "user": get_secret_value(auth_secret_values, OciSecretKey.USER_OCID),
        "tenancy": get_secret_value(auth_secret_values, OciSecretKey.TENANCY_OCID),
        "fingerprint": get_secret_value(auth_secret_values, OciSecretKey.FINGERPRINT),
        "private_key": get_secret_value(auth_secret_values, OciSecretKey.PRIVATE_KEY),
        "region": region,
    }

def _get_clients(auth_secret_values, region):
    auth = _get_oci_auth(auth_secret_values, region)
    return {
        "resource_manager": ResourceManagerClient(auth),
        "compute": ComputeClient(auth),
        "virtual_network": VirtualNetworkClient(auth),
    }

def _get_terraform_directory():
    terraform_dir = Path(__file__).resolve().parent / "terraform"
    if terraform_dir.is_dir():
        return terraform_dir
    raise FileNotFoundError(f"Deploy terraform directory is missing: {terraform_dir}")

def _zip_terraform_package():
    terraform_dir = _get_terraform_directory()
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename in STACK_TERRAFORM_FILES:
            source = terraform_dir / filename
            if not source.is_file():
                raise FileNotFoundError(f"Missing terraform file required for OCI stack packaging: {source}")
            zip_file.write(source, arcname=filename)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def _normalize_name(value):
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value or "").strip("-")
    return normalized or "cloudlaunch"

def _build_display_name(user_id):
    timestamp = int(time.time())
    normalized_user_id = _normalize_name(user_id)
    return f"VPN-{normalized_user_id}-{timestamp}"

def _build_stack_variables(oci_config, vpn_config, instance_name):
    ssh_authorized_keys = oci_config.get(OciSecretKey.SSH_AUTHORIZED_KEYS_JSON.value)
    if isinstance(ssh_authorized_keys, str):
        ssh_authorized_keys = json.loads(ssh_authorized_keys)
    if not isinstance(ssh_authorized_keys, list) or not ssh_authorized_keys:
        raise ValueError("oci.OCI_SSH_AUTHORIZED_KEYS_JSON must be a JSON array of SSH public keys")

    variables = {
        "availability_domain": get_secret_value(oci_config, OciSecretKey.AVAILABILITY_DOMAIN),
        "region": get_secret_value(oci_config, OciSecretKey.REGION),
        "compartment_id": get_secret_value(oci_config, OciSecretKey.COMPARTMENT_ID),
        "subnet_id": get_secret_value(oci_config, OciSecretKey.SUBNET_ID),
        "source_image_id": get_secret_value(oci_config, OciSecretKey.SOURCE_IMAGE_ID),
        "ssh_authorized_keys": json.dumps(ssh_authorized_keys),
        "hashed_password": get_secret_value(oci_config, OciSecretKey.HASHED_PASSWORD),
        "instance_display_name": instance_name,
        "vnic_display_name": instance_name,
        "ipv6_subnet_cidr": get_secret_value(oci_config, OciSecretKey.IPV6_SUBNET_CIDR),
        "shape": get_secret_value(oci_config, OciSecretKey.INSTANCE_SHAPE),
        "shape_memory_in_gbs": str(get_secret_value(oci_config, OciSecretKey.INSTANCE_MEMORY_GBS)),
        "shape_ocpus": str(get_secret_value(oci_config, OciSecretKey.INSTANCE_OCPUS)),
        "boot_volume_size_in_gbs": str(get_secret_value(oci_config, OciSecretKey.BOOT_VOLUME_SIZE_GBS)),
        "boot_volume_vpus_per_gb": str(get_secret_value(oci_config, OciSecretKey.BOOT_VOLUME_VPUS_PER_GB)),
        "wg_interface": get_secret_value(vpn_config, VpnSecretKey.INTERFACE),
        "wg_listen_port": str(get_secret_value(vpn_config, VpnSecretKey.LISTEN_PORT)),
        "wg_address_v4": get_secret_value(vpn_config, VpnSecretKey.ADDRESS_V4),
        "wg_address_v6": get_secret_value(vpn_config, VpnSecretKey.ADDRESS_V6),
        "wg_dns_address_v4": get_secret_value(vpn_config, VpnSecretKey.DNS_ADDRESS_V4),
        "wg_dns_address_v6": get_secret_value(vpn_config, VpnSecretKey.DNS_ADDRESS_V6),
        "wg_network_v4": get_secret_value(vpn_config, VpnSecretKey.NETWORK_V4),
        "wg_network_v6": get_secret_value(vpn_config, VpnSecretKey.NETWORK_V6),
        "wg_rate_limit": get_secret_value(vpn_config, VpnSecretKey.RATE_LIMIT),
        "wg_rate_limit_burst": str(get_secret_value(vpn_config, VpnSecretKey.RATE_LIMIT_BURST)),
        "wg_server_private_key": get_secret_value(vpn_config, VpnSecretKey.SERVER_PRIVATE_KEY),
        "wg_client_public_key": get_secret_value(vpn_config, VpnSecretKey.CLIENT_PUBLIC_KEY),
        "wg_peer_allowed_ipv4": get_secret_value(vpn_config, VpnSecretKey.PEER_ALLOWED_IPV4),
        "wg_peer_allowed_ipv6": get_secret_value(vpn_config, VpnSecretKey.PEER_ALLOWED_IPV6),
        "wg_peer_persistent_keepalive": str(get_secret_value(vpn_config, VpnSecretKey.PEER_PERSISTENT_KEEPALIVE)),
    }

    return variables

def _wait_for_stack_state(resource_manager_client, stack_id, terminal_states, timeout_seconds):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        stack = resource_manager_client.get_stack(stack_id).data
        lifecycle_state = getattr(stack, "lifecycle_state", None)
        if lifecycle_state in terminal_states:
            return stack
        if lifecycle_state in {"FAILED", "DELETED"}:
            raise RuntimeError(f"Stack {stack_id} entered unexpected state {lifecycle_state}")
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for stack {stack_id} to reach {terminal_states}")

def _wait_for_job(resource_manager_client, job_id, timeout_seconds):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        job = resource_manager_client.get_job(job_id).data
        lifecycle_state = getattr(job, "lifecycle_state", None)
        if lifecycle_state in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return job
        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for job {job_id} to finish")

def _create_stack(resource_manager_client, oci_config, vpn_config, user_id):
    stack_name = _build_display_name(user_id)
    stack_details = {
        "compartmentId": get_secret_value(oci_config, OciSecretKey.COMPARTMENT_ID),
        "displayName": stack_name,
        "description": f"CloudLaunch VPN stack for {user_id}",
        "configSource": {
            "configSourceType": "ZIP_UPLOAD",
            "zipFileBase64Encoded": _zip_terraform_package(),
        },
        "variables": _build_stack_variables(oci_config, vpn_config, stack_name),
        "freeformTags": {
            "managed-by": "cloudlaunch",
            "vpn-user-id": user_id,
        },
    }
    stack = resource_manager_client.create_stack(stack_details).data
    return _wait_for_stack_state(resource_manager_client, stack.id, {"ACTIVE"}, STACK_CREATE_TIMEOUT_SECONDS)

def _create_job(resource_manager_client, stack_id, operation, display_name):
    job_details = {
        "stackId": stack_id,
        "displayName": display_name,
        "jobOperationDetails": {
            "operation": operation,
            "executionPlanStrategy": "AUTO_APPROVED",
        },
    }
    return resource_manager_client.create_job(job_details).data

def _get_instance_ocid_from_state(tf_state):
    resources = tf_state.get("resources") or []
    for resource in resources:
        if resource.get("type") != "oci_core_instance":
            continue
        for instance in resource.get("instances") or []:
            attributes = instance.get("attributes") or {}
            instance_id = attributes.get("id")
            if instance_id:
                return instance_id

    modules = tf_state.get("modules") or []
    for module in modules:
        for resource in (module.get("resources") or {}).values():
            if resource.get("type") != "oci_core_instance":
                continue
            primary = resource.get("primary") or {}
            attributes = primary.get("attributes") or {}
            instance_id = attributes.get("id")
            if instance_id:
                return instance_id

    return None

def _get_job_logs_tail(resource_manager_client, job_id, max_chars=3000):
    try:
        time.sleep(1)
        logs = resource_manager_client.get_job_logs_content(job_id).data or ""
    except Exception as exc:
        return f"Unable to fetch job logs for {job_id}: {exc}"

    logs = logs.strip()
    if not logs:
        return f"No job logs returned for {job_id}"
    return logs[-max_chars:]

def _inspect_stack_associated_resources(resource_manager_client, stack_id):
    try:
        resources = resource_manager_client.list_stack_associated_resources(stack_id).data
        # TODO: Follow OCI pagination if this stack starts managing more than the VPN instance.
        items = list(getattr(resources, "items", None) or [])
        instance_ocid = None

        for resource in items:
            resource_type = getattr(resource, "resource_type", None)
            resource_id = getattr(resource, "resource_id", None)
            if resource_type == "oci_core_instance" and resource_id:
                instance_ocid = resource_id
                break

        return {
            "ok": True,
            "has_resources": bool(items),
            "instance_ocid": instance_ocid,
            "stack_absent": False,
            "detail": f"Stack associated resources inspected: {len(items)} found",
        }
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "ok": True,
                "has_resources": False,
                "instance_ocid": None,
                "stack_absent": True,
                "detail": "Stack already absent",
            }
        return {
            "ok": False,
            "has_resources": None,
            "instance_ocid": None,
            "stack_absent": False,
            "detail": f"Unable to inspect associated resources for stack {stack_id}: {exc}",
        }

def _get_instance_public_ip(compute_client, virtual_network_client, compartment_id, instance_id):
    deadline = time.time() + PUBLIC_IP_TIMEOUT_SECONDS

    while time.time() < deadline:
        attachments = compute_client.list_vnic_attachments(
            compartment_id=compartment_id,
            instance_id=instance_id,
        ).data

        for attachment in attachments:
            vnic = virtual_network_client.get_vnic(attachment.vnic_id).data
            if getattr(vnic, "public_ip", None):
                return vnic.public_ip

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for public IP on instance {instance_id}")


def _is_missing_resource_error(exception):
    status = getattr(exception, "status", None)
    code = str(getattr(exception, "code", "") or "").upper()
    message = str(exception).lower()

    if status == 404:
        return True
    if code in {
        "NOTAUTHORIZEDORNOTFOUND",
        "NOTFOUND",
        "RELATEDRESOURCE_NOT_AUTHORIZED_OR_NOT_FOUND",
        "RESOURCE_NOT_FOUND",
    }:
        return True
    return (
        "not found" in message
        or "does not exist" in message
        or "notauthorizedornotfound" in message
    )


def _get_instance_cleanup_status(compute_client, instance_id):
    try:
        instance = compute_client.get_instance(instance_id).data
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "id": instance_id,
                "status": "absent",
                "detail": "Instance already absent",
            }
        raise

    lifecycle_state = getattr(instance, "lifecycle_state", None)
    if lifecycle_state == "TERMINATED":
        return {
            "id": instance_id,
            "status": "terminated",
            "detail": "Instance terminated",
        }
    return {
        "id": instance_id,
        "status": "active",
        "detail": f"Instance state is {lifecycle_state}",
    }


def _wait_for_instance_absence_or_termination(compute_client, instance_id, timeout_seconds):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        status = _get_instance_cleanup_status(compute_client, instance_id)
        if status["status"] in {"absent", "terminated"}:
            return status
        time.sleep(POLL_INTERVAL_SECONDS)

    return {
        "id": instance_id,
        "status": "timeout",
        "detail": f"Timed out waiting for instance {instance_id} to terminate",
    }


def _terminate_instance_directly(compute_client, instance_id):
    try:
        status = _get_instance_cleanup_status(compute_client, instance_id)
        if status["status"] in {"absent", "terminated"}:
            return status

        compute_client.terminate_instance(instance_id)
        return _wait_for_instance_absence_or_termination(
            compute_client,
            instance_id,
            INSTANCE_TERMINATION_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "id": instance_id,
                "status": "absent",
                "detail": "Instance already absent",
            }
        return {
            "id": instance_id,
            "status": "failed",
            "detail": str(exc),
        }

def _delete_stack_record(resource_manager_client, stack_id, detail):
    try:
        resource_manager_client.delete_stack(stack_id)
        return {
            "id": stack_id,
            "status": "deleted",
            "detail": detail,
        }
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "id": stack_id,
                "status": "absent",
                "detail": "Stack already absent",
            }
        return {
            "id": stack_id,
            "status": "failed",
            "detail": str(exc),
        }


def _destroy_stack(resource_manager_client, stack_id):
    try:
        stack = resource_manager_client.get_stack(stack_id).data
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "id": stack_id,
                "status": "absent",
                "detail": "Stack already absent",
            }
        return {
            "id": stack_id,
            "status": "failed",
            "detail": str(exc),
        }
    if getattr(stack, "lifecycle_state", None) == "DELETED":
        return {
            "id": stack_id,
            "status": "absent",
            "detail": "Stack already absent",
        }

    try:
        destroy_job = _create_job(
            resource_manager_client,
            stack_id,
            "DESTROY",
            f"Destroy {stack_id}",
        )
        job = _wait_for_job(resource_manager_client, destroy_job.id, JOB_TIMEOUT_SECONDS)
        if getattr(job, "lifecycle_state", None) == "SUCCEEDED":
            return {
                "id": stack_id,
                "status": "destroyed",
                "detail": f"Destroy job {destroy_job.id} succeeded",
            }

        try:
            stack = resource_manager_client.get_stack(stack_id).data
        except Exception as exc:
            if _is_missing_resource_error(exc):
                return {
                    "id": stack_id,
                    "status": "absent",
                    "detail": "Stack became absent during destroy",
                }
        if getattr(stack, "lifecycle_state", None) == "DELETED":
            return {
                "id": stack_id,
                "status": "absent",
                "detail": "Stack became absent during destroy",
            }

        return {
            "id": stack_id,
            "status": "failed",
            "detail": (
                f"Destroy job {destroy_job.id} ended in state {job.lifecycle_state}. "
                f"Log tail: {_get_job_logs_tail(resource_manager_client, destroy_job.id)}"
            ),
        }
    except Exception as exc:
        if _is_missing_resource_error(exc):
            return {
                "id": stack_id,
                "status": "absent",
                "detail": "Stack already absent",
            }
        return {
            "id": stack_id,
            "status": "failed",
            "detail": str(exc),
        }


def _safe_mark_instance_failed(user_id, oci_region, stack_id, error_message):
    try:
        mark_instance_failed(user_id, oci_region, stack_id, error_message)
    except Exception as exc:
        print(f"Failed to persist Deploy record failure for stack {stack_id}: {exc}")


def deploy_instance(oci_config, vpn_config, user_id, oci_region):
    stack = None
    instance_id = None

    try:
        clients = _get_clients(oci_config, oci_region)
        resource_manager_client = clients["resource_manager"]
        compute_client = clients["compute"]
        virtual_network_client = clients["virtual_network"]

        stack = _create_stack(resource_manager_client, oci_config, vpn_config, user_id)
        upsert_stack_backed_instance_record(user_id, oci_region, stack.id, stack.display_name)

        apply_job = _create_job(
            resource_manager_client,
            stack.id,
            "APPLY",
            f"Apply {stack.display_name}",
        )
        apply_result = _wait_for_job(resource_manager_client, apply_job.id, JOB_TIMEOUT_SECONDS)
        if getattr(apply_result, "lifecycle_state", None) != "SUCCEEDED":
            raise RuntimeError(
                f"OCI apply job {apply_job.id} failed with state {apply_result.lifecycle_state}. "
                f"Log tail: {_get_job_logs_tail(resource_manager_client, apply_job.id)}"
            )

        time.sleep(2)
        tf_state = json.loads(resource_manager_client.get_job_tf_state(apply_job.id).data)
        instance_id = _get_instance_ocid_from_state(tf_state)
        if not instance_id:
            raise RuntimeError("OCI apply completed but instance OCID could not be resolved from Terraform state")

        attach_instance_ocid(user_id, oci_region, stack.id, instance_id)

        public_ip = _get_instance_public_ip(
            compute_client,
            virtual_network_client,
            get_secret_value(oci_config, OciSecretKey.COMPARTMENT_ID),
            instance_id,
        )

        mark_instance_running(user_id, oci_region, stack.id, public_ip)
        return {
            "error": None,
            "instance_id": instance_id,
            "instance_name": stack.display_name,
            "public_ip": public_ip,
            "stack_id": stack.id,
        }
    except Exception as e:
        error = f"OCI deployment failed: {e}"
        print(error)
        if stack is not None:
            _safe_mark_instance_failed(user_id, oci_region, stack.id, error)
        return {
            "error": error,
            "instance_id": instance_id,
            "instance_name": getattr(stack, "display_name", None),
            "public_ip": None,
            "stack_id": getattr(stack, "id", None),
        }

def terminate_instance_resources(auth_secret_values, oci_region, stack_id=None, instance_ocid=None):
    clients = _get_clients(auth_secret_values, oci_region)
    resource_manager_client = clients["resource_manager"]
    compute_client = clients["compute"]

    stack_state = None
    if stack_id and not instance_ocid:
        stack_state = _inspect_stack_associated_resources(resource_manager_client, stack_id)
        if not stack_state["ok"]:
            return {
                "ok": False,
                "stack": {
                    "id": stack_id,
                    "status": "failed",
                    "detail": stack_state["detail"],
                },
                "instance": {
                    "id": None,
                    "status": "skipped",
                    "detail": "Skipped instance cleanup because stack associated resources could not be inspected",
                },
            }

        instance_ocid = stack_state["instance_ocid"]
        if instance_ocid:
            print(f"Recovered instance OCID {instance_ocid} from associated resources for stack {stack_id}.")
        elif stack_state.get("stack_absent"):
            print(f"Stack {stack_id} already absent while inspecting associated resources.")

    if stack_id:
        if instance_ocid:
            stack_result = _destroy_stack(resource_manager_client, stack_id)
        elif stack_state and stack_state.get("stack_absent"):
            stack_result = {
                "id": stack_id,
                "status": "absent",
                "detail": stack_state["detail"],
            }
        elif stack_state and stack_state["has_resources"]:
            stack_result = {
                "id": stack_id,
                "status": "failed",
                "detail": "Stack has associated resources but no compute instance OCID; refusing to delete stack record",
            }
        else:
            print(f"Deleting stack {stack_id} without destroy because no instance OCID was recorded or found.")
            stack_result = _delete_stack_record(
                resource_manager_client,
                stack_id,
                "Deleted stack record with no recorded or discoverable instance OCID",
            )
    else:
        stack_result = {
            "id": None,
            "status": "skipped",
            "detail": "No stack ID available",
        }

    stack_cleanup_completed = stack_result["status"] in {"destroyed", "deleted", "absent"}

    if instance_ocid:
        if stack_cleanup_completed:
            instance_result = _wait_for_instance_absence_or_termination(
                compute_client,
                instance_ocid,
                INSTANCE_TERMINATION_TIMEOUT_SECONDS,
            )
            if instance_result["status"] not in {"absent", "terminated"}:
                instance_result = _terminate_instance_directly(compute_client, instance_ocid)
        else:
            instance_result = _terminate_instance_directly(compute_client, instance_ocid)
    else:
        instance_result = {
            "id": None,
            "status": "skipped",
            "detail": "No instance OCID available",
        }

    cleanup_completed = stack_cleanup_completed and (
        not instance_ocid or instance_result["status"] in {"absent", "terminated"}
    )

    return {
        "ok": cleanup_completed,
        "stack": stack_result,
        "instance": instance_result,
    }
