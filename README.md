# VPN Cloud Automation:

* Check out the quick demo here: https://youtu.be/1d3qo_34Vk4

Live at: https://albro3459.github.io/VPN_Cloud_Automation

Users are ubable to create their own accounts at the moment.

## About: 

 * Instantly deploy a secure WireGuard VPN on an AWS EC2 instance in the region of your choice, pre-configured for both IPv4 and IPv6 connectivity.

 * The entire deployment process is automated using AWS Lambda, ensuring a fast, efficient, and hassle-free setup.

 * Generate your VPN configuration instantly, download the .conf file, or scan a QR code for easy setup on your devices—all in just a few clicks.

 * Secure, simple, and instant. Your personal cloud VPN, deployed on demand.

---

#### Running React Site:

cd vpn-frontend;
npm start

cd vpn-frontend;
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch

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

#### On Mac

Start WireGuard manually:
wg-quick up wg-client

Check status:
sudo wg

To stop it:
wg-quick down wg-client
