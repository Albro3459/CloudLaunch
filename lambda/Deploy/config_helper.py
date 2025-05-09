import qrcode
from io import BytesIO

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