export const generateConfig = (CLIENT_PRIVATE_KEY: string, SERVER_PUBLIC_KEY: string, SERVER_IP: string, ): string => {
    const conf = 
`[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = 10.0.0.2/24, fd42:42:42::2/64
DNS = 10.0.0.1, fd42:42:42::1

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_IP}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
`;
    return conf;
};
  
