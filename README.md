# VPN Cloud Automation:

* Check out the quick demo here: [https://youtu.be/1d3qo_34Vk4](https://youtu.be/Zpeojm-HI8g)

* Site is live at: [https://albro3459.github.io/VPN_Cloud_Automation](https://albro3459.github.io/VPN_Cloud_Automation)

  * Only the admin account is active for the time being.

  * To save the config file or scan the QR code, on either the phone or computer, you need the Wireguard app because the VPN uses the Wireguard protocol.

## About: 

 * Instantly deploy a secure WireGuard VPN on an AWS EC2 instance in the region of your choice, pre-configured for both IPv4 and IPv6 connectivity.

 * The entire deployment process is automated using AWS Lambda, ensuring a fast, efficient, and hassle-free setup.

 * Generate your VPN configuration instantly, download the .conf file, or scan a QR code for easy setup on your devices—all in just a few clicks.

 * Secure, simple, and instant. Your personal cloud VPN, deployed on demand with little to no setup needed.

---
 
## Languages and Frameworks:
   * React with TypeScript and TailwindCSS for the Frontend
   * Python for the AWS Lambda script
   * Firebase for Authentication
   * AWS tools used:
     * EC2, AMI, Lambda, DynamoDB, Secrets Manager, VPC (amd Subnet), IAM, CloudWatch, ECR (ended up not needing it though), and the CLI
     * A large amount of the work was done on AWS and with the AWS CLI
       * If you would like documentation on how to configure a Wireguard EC2 VPN yourself, email me: brodsky.alex22@gmail.com
      
---

#### Running React Site:

See vpn-frontend folder for React README

---

#### On Phone

Demo in the YouTube video.

Install the Wireguard app on your phone.

Either download the config file or scan the QR code in the Wireguard app.

Enable it in Wireguard and Settings and you're done!

---

#### On Mac

It's much better to just use the Wireguard Desktop app (as shown in the demo video), but you can follow these steps instead:

Start WireGuard manually:
```sh
wg-quick up wg-client
```

Check status:
```sh
sudo wg
```

To stop it:
```sh
wg-quick down wg-client
```

---

#### On the Server (EC2)

Restart the WireGuard service:
```sh
sudo systemctl restart wg-quick@wg0
```

Enable it to start on boot:
```sh
sudo systemctl enable wg-quick@wg0
```

Check if it's running:
```sh
sudo systemctl status wg-quick@wg0
```

To see connected clients:
```sh
sudo wg show
```

To disable WireGuard (prevent auto-start):
```sh
sudo systemctl disable wg-quick@wg0
```
