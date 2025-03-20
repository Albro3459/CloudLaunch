# VPN Cloud Automation:

* Check out the quick demo here: https://youtu.be/1d3qo_34Vk4

* Site is live at: https://albro3459.github.io/VPN_Cloud_Automation

  * Users are ubable to create their own accounts at the moment.

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
     * EC2, AMI, Lambda, VPC (amd Subnet), Secrets Manager, IAM, CloudWatch, ECR (ended up not needing it though), and the CLI
     * A large amount of the work was done on AWS and with the AWS CLI
       * If you would like documentation on how to configure a Wireguard EC2 VPN yourself, email me: brodsky.alex22@gmail.com
      
---

#### Running React Site:

cd vpn-frontend;
npm start

cd vpn-frontend;
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch

---

#### On Phone

Install the Wireguard app on your phone.

Scan the QR code in the Wireguard app.

Enable it in settings and you're done!

#### On Mac

It's much better to just use the Wireguard Desktop app (as shown in the demo videos), but you can follow these steps instead:

Start WireGuard manually:
wg-quick up wg-client

Check status:
sudo wg

To stop it:
wg-quick down wg-client

---

#### On the Server (EC2)

Restart the WireGuard service:
sudo systemctl restart wg-quick@wg0

Enable it to start on boot:
sudo systemctl enable wg-quick@wg0

Check if it's running:
sudo systemctl status wg-quick@wg0

To see connected clients:
sudo wg show

To disable WireGuard (prevent auto-start):
sudo systemctl disable wg-quick@wg0

---
