from enum import Enum


class VPNStatus(str, Enum):
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"
    TERMINATED = "terminated"


ACTIVE_VPN_STATUSES = [VPNStatus.PENDING.value, VPNStatus.RUNNING.value]


def normalize_vpn_status(status) -> VPNStatus | None:
    if status is None:
        return None
    if isinstance(status, VPNStatus):
        return status

    normalized_status = str(status).strip().lower()
    try:
        return VPNStatus(normalized_status)
    except ValueError:
        return None
