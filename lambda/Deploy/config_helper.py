
def get_config(client_private_key, server_public_key, ip_address):
    print(f"Creating Wireguard Config for {ip_address}.")
    
    config = f"""[Interface]
PrivateKey = {client_private_key}
Address = 10.0.0.2/24, fd42:42:42::2/64
DNS = 1.1.1.1, 2606:4700:4700::1111

[Peer]
PublicKey = {server_public_key}
Endpoint = {ip_address}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return config

def build_QR_code(config=""):
    # Build the QR code later twin
    print(f"Building QR Code.")
    return "plain for now twin"