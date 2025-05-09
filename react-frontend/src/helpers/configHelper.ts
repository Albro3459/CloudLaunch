export const generateConfig = (CLIENT_PRIVATE_KEY: string, SERVER_PUBLIC_KEY: string, EC2_IP: string, ): string => {
    const conf = 
`[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = 10.0.0.2/24, fd42:42:42::2/64
DNS = 1.1.1.1, 2606:4700:4700::1111

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${EC2_IP}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
`;
    return conf;
};
  