import qrcode
from io import BytesIO

from get_secrets import VpnSecretKey, get_secret_value

def get_wireguard_config_options(secret_values):
    return {
        "address_v4": str(get_secret_value(secret_values, VpnSecretKey.CLIENT_ADDRESS_V4)),
        "address_v6": str(get_secret_value(secret_values, VpnSecretKey.CLIENT_ADDRESS_V6)),
        "dns_v4": str(get_secret_value(secret_values, VpnSecretKey.DNS_ADDRESS_V4)),
        "dns_v6": str(get_secret_value(secret_values, VpnSecretKey.DNS_ADDRESS_V6)),
        "listen_port": str(get_secret_value(secret_values, VpnSecretKey.LISTEN_PORT)),
        "allowed_ips_v4": str(get_secret_value(secret_values, VpnSecretKey.CLIENT_ALLOWED_IPS_V4)),
        "allowed_ips_v6": str(get_secret_value(secret_values, VpnSecretKey.CLIENT_ALLOWED_IPS_V6)),
        "persistent_keepalive": str(get_secret_value(secret_values, VpnSecretKey.PEER_PERSISTENT_KEEPALIVE)),
    }

def get_config(client_private_key, server_public_key, ip_address, wireguard_options):
    print(f"Creating Wireguard Config for {ip_address}.")

    options = wireguard_options or {}
    address_v4 = options["address_v4"]
    address_v6 = options["address_v6"]
    dns_v4 = options["dns_v4"]
    dns_v6 = options["dns_v6"]
    listen_port = options["listen_port"]
    allowed_ips_v4 = options["allowed_ips_v4"]
    allowed_ips_v6 = options["allowed_ips_v6"]
    persistent_keepalive = options["persistent_keepalive"]
    
    config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {address_v4}, {address_v6}
DNS = {dns_v4}, {dns_v6}

[Peer]
PublicKey = {server_public_key}
Endpoint = {ip_address}:{listen_port}
AllowedIPs = {allowed_ips_v4}, {allowed_ips_v6}
PersistentKeepalive = {persistent_keepalive}
"""
    return config

def build_QR_code(config_data):
    # Returns bytes
    print(f"Building QR Code.")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(config_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer.read()
