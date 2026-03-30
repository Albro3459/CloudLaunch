import base64
import json
import re
import time
import zipfile
from io import BytesIO
from pathlib import Path

import oci

from firebase import (
    attach_instance_ocid,
    mark_instance_failed,
    mark_instance_running,
    upsert_stack_backed_instance_record,
)
from get_secrets import get_secret_value

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

def _get_oci_config(auth_secret_values, region):
    config = {
        "user": get_secret_value(auth_secret_values, "OCI_USER_OCID"),
        "tenancy": get_secret_value(auth_secret_values, "OCI_TENANCY_OCID"),
        "fingerprint": get_secret_value(auth_secret_values, "OCI_FINGERPRINT"),
        "key_content": get_secret_value(auth_secret_values, "OCI_PRIVATE_KEY"),
        "region": region,
    }

    oci.config.validate_config(config)
    return config

def _get_clients(auth_secret_values, region):
    config = _get_oci_config(auth_secret_values, region)
    return {
        "resource_manager": oci.resource_manager.ResourceManagerClient(config),
        "compute": oci.core.ComputeClient(config),
        "virtual_network": oci.core.VirtualNetworkClient(config),
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

def _build_stack_variables(secret_values, instance_name):
    ssh_authorized_keys = secret_values.get("OCI_SSH_AUTHORIZED_KEYS_JSON")
    if isinstance(ssh_authorized_keys, str):
        ssh_authorized_keys = json.loads(ssh_authorized_keys)
    if not isinstance(ssh_authorized_keys, list) or not ssh_authorized_keys:
        raise ValueError("OCI_SSH_AUTHORIZED_KEYS_JSON must be a JSON array of SSH public keys")

    variables = {
        "availability_domain": get_secret_value(secret_values, "OCI_AVAILABILITY_DOMAIN"),
        "compartment_id": get_secret_value(secret_values, "OCI_COMPARTMENT_ID"),
        "subnet_id": get_secret_value(secret_values, "OCI_SUBNET_ID"),
        "source_image_id": get_secret_value(secret_values, "OCI_SOURCE_IMAGE_ID"),
        "ssh_authorized_keys": json.dumps(ssh_authorized_keys),
        "hashed_password": get_secret_value(secret_values, "OCI_HASHED_PASSWORD"),
        "instance_display_name": instance_name,
        "vnic_display_name": instance_name,
        "ipv6_subnet_cidr": get_secret_value(secret_values, "OCI_IPV6_SUBNET_CIDR"),
        "shape": get_secret_value(secret_values, "OCI_INSTANCE_SHAPE"),
        "shape_memory_in_gbs": str(get_secret_value(secret_values, "OCI_INSTANCE_MEMORY_GBS")),
        "shape_ocpus": str(get_secret_value(secret_values, "OCI_INSTANCE_OCPUS")),
        "boot_volume_size_in_gbs": str(get_secret_value(secret_values, "OCI_BOOT_VOLUME_SIZE_GBS")),
        "boot_volume_vpus_per_gb": str(get_secret_value(secret_values, "OCI_BOOT_VOLUME_VPUS_PER_GB")),
        "wg_interface": get_secret_value(secret_values, "WG_INTERFACE"),
        "wg_listen_port": str(get_secret_value(secret_values, "WG_LISTEN_PORT")),
        "wg_address_v4": get_secret_value(secret_values, "WG_ADDRESS_V4"),
        "wg_address_v6": get_secret_value(secret_values, "WG_ADDRESS_V6"),
        "wg_dns_address_v4": get_secret_value(secret_values, "WG_DNS_ADDRESS_V4"),
        "wg_dns_address_v6": get_secret_value(secret_values, "WG_DNS_ADDRESS_V6"),
        "wg_network_v4": get_secret_value(secret_values, "WG_NETWORK_V4"),
        "wg_network_v6": get_secret_value(secret_values, "WG_NETWORK_V6"),
        "wg_rate_limit": get_secret_value(secret_values, "WG_RATE_LIMIT"),
        "wg_rate_limit_burst": str(get_secret_value(secret_values, "WG_RATE_LIMIT_BURST")),
        "wg_server_private_key": get_secret_value(secret_values, "WG_SERVER_PRIVATE_KEY"),
        "wg_client_public_key": get_secret_value(secret_values, "WG_CLIENT_PUBLIC_KEY"),
        "wg_peer_allowed_ipv4": get_secret_value(secret_values, "WG_PEER_ALLOWED_IPV4"),
        "wg_peer_allowed_ipv6": get_secret_value(secret_values, "WG_PEER_ALLOWED_IPV6"),
        "wg_peer_persistent_keepalive": str(get_secret_value(secret_values, "WG_PEER_PERSISTENT_KEEPALIVE")),
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

def _create_stack(resource_manager_client, secret_values, user_id):
    stack_name = _build_display_name(user_id)
    stack_details = oci.resource_manager.models.CreateStackDetails(
        compartment_id=get_secret_value(secret_values, "OCI_COMPARTMENT_ID"),
        display_name=stack_name,
        description=f"CloudLaunch VPN stack for {user_id}",
        config_source=oci.resource_manager.models.CreateZipUploadConfigSourceDetails(
            zip_file_base64_encoded=_zip_terraform_package()
        ),
        variables=_build_stack_variables(secret_values, stack_name),
        freeform_tags={
            "managed-by": "cloudlaunch",
            "vpn-user-id": user_id,
        },
    )
    stack = resource_manager_client.create_stack(stack_details).data
    return _wait_for_stack_state(resource_manager_client, stack.id, {"ACTIVE"}, STACK_CREATE_TIMEOUT_SECONDS)

def _create_job(resource_manager_client, stack_id, operation_details, display_name):
    job_details = oci.resource_manager.models.CreateJobDetails(
        stack_id=stack_id,
        display_name=display_name,
        job_operation_details=operation_details,
    )
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
            oci.resource_manager.models.CreateDestroyJobOperationDetails(
                execution_plan_strategy="AUTO_APPROVED"
            ),
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
            "detail": f"Destroy job {destroy_job.id} ended in state {job.lifecycle_state}",
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


def _safe_mark_instance_failed(user_id, target_region, stack_id, error_message):
    try:
        mark_instance_failed(user_id, target_region, stack_id, error_message)
    except Exception as exc:
        print(f"Failed to persist Deploy record failure for stack {stack_id}: {exc}")


def deploy_instance(secret_values, auth_secret_values, user_id, target_region):
    stack = None
    instance_id = None

    try:
        clients = _get_clients(auth_secret_values, target_region)
        resource_manager_client = clients["resource_manager"]
        compute_client = clients["compute"]
        virtual_network_client = clients["virtual_network"]

        stack = _create_stack(resource_manager_client, secret_values, user_id)
        upsert_stack_backed_instance_record(user_id, target_region, stack.id, stack.display_name)

        apply_job = _create_job(
            resource_manager_client,
            stack.id,
            oci.resource_manager.models.CreateApplyJobOperationDetails(
                execution_plan_strategy="AUTO_APPROVED"
            ),
            f"Apply {stack.display_name}",
        )
        apply_result = _wait_for_job(resource_manager_client, apply_job.id, JOB_TIMEOUT_SECONDS)
        if getattr(apply_result, "lifecycle_state", None) != "SUCCEEDED":
            raise RuntimeError(f"OCI apply job failed with state {apply_result.lifecycle_state}")

        time.sleep(2)
        tf_state = json.loads(resource_manager_client.get_job_tf_state(apply_job.id).data)
        instance_id = _get_instance_ocid_from_state(tf_state)
        if not instance_id:
            raise RuntimeError("OCI apply completed but instance OCID could not be resolved from Terraform state")

        attach_instance_ocid(user_id, target_region, stack.id, instance_id)

        public_ip = _get_instance_public_ip(
            compute_client,
            virtual_network_client,
            get_secret_value(secret_values, "OCI_COMPARTMENT_ID"),
            instance_id,
        )

        mark_instance_running(user_id, target_region, stack.id, public_ip)
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
            _safe_mark_instance_failed(user_id, target_region, stack.id, error)
        return {
            "error": error,
            "instance_id": instance_id,
            "instance_name": getattr(stack, "display_name", None),
            "public_ip": None,
            "stack_id": getattr(stack, "id", None),
        }

def terminate_instance_resources(auth_secret_values, target_region, stack_id=None, instance_ocid=None):
    clients = _get_clients(auth_secret_values, target_region)
    resource_manager_client = clients["resource_manager"]
    compute_client = clients["compute"]

    if stack_id:
        stack_result = _destroy_stack(resource_manager_client, stack_id)
    else:
        stack_result = {
            "id": None,
            "status": "skipped",
            "detail": "No stack ID available",
        }

    stack_cleanup_completed = stack_result["status"] in {"destroyed", "absent"}

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
