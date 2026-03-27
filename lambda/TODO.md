# TODO

* add these secrets to aws to build the terraform vars:
{
  "OCI_REGION": "...",
  "OCI_COMPARTMENT_ID": "...",
  "OCI_AVAILABILITY_DOMAIN": "...",
  "OCI_SUBNET_ID": "...",
  "OCI_SOURCE_IMAGE_ID": "...",

  "OCI_SSH_AUTHORIZED_KEYS_JSON": "...",
  "OCI_HASHED_PASSWORD": "...",

  "OCI_INSTANCE_SHAPE": "...",
  "OCI_INSTANCE_MEMORY_GBS": "...",
  "OCI_INSTANCE_OCPUS": "...",
  "OCI_BOOT_VOLUME_SIZE_GBS": "...",
  "OCI_BOOT_VOLUME_VPUS_PER_GB": "...",
  "OCI_IPV6_SUBNET_CIDR": "...",

  "WG_INTERFACE": "...",
  "WG_LISTEN_PORT": "...",
  "WG_ADDRESS_V4": "...",
  "WG_ADDRESS_V6": "...",
  "WG_DNS_ADDRESS_V4": "...",
  "WG_DNS_ADDRESS_V6": "...",
  "WG_NETWORK_V4": "...",
  "WG_NETWORK_V6": "...",
  "WG_RATE_LIMIT": "...",
  "WG_RATE_LIMIT_BURST": "...",

  "WIREGUARD_SERVER_PRIVATE_KEY": "...",
  "WIREGUARD_SERVER_PUBLIC_KEY": "...",
  "WIREGUARD_CLIENT_PRIVATE_KEY": "...",
  "WIREGUARD_CLIENT_PUBLIC_KEY": "...",
  "WG_PEER_ALLOWED_IPV4": "...",
  "WG_PEER_ALLOWED_IPV6": "...",
  "WG_PEER_PERSISTENT_KEEPALIVE": "...",

  "SES_SENDER": "CloudLaunch <noreply@gocloudlaunch.com>",
  "ADMIN_EMAIL": "brodsky.alex22@gmail.com"
}

* update ses for emails from the new domain