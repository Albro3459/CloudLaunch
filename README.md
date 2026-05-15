# CloudLaunch:

<div style="display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 80px;">
   <img src="https://github.com/user-attachments/assets/e30a1af1-057b-4209-abbe-99cb62da9d5c" alt="Dashboard" height="400"/>
   <img src="https://github.com/user-attachments/assets/2665ae69-5ab6-4d1d-ab18-f1cd32935ae8" alt="Deploy" height="400"/>
</div>

## About:

 * Live at: [gocloudlaunch.com/](https://www.gocloudlaunch.com/)

 * Instantly deploy a secure <b>WireGuard VPN</b>, pre-configured with IPv4, IPv6, and DNS.

 * The deployment flow is being migrated from AWS EC2/AMI provisioning to Oracle Cloud Infrastructure stacks managed by <b>AWS Lambda</b>.

 * Generate your VPN configuration instantly, scan a QR code, or download the <b>.conf</b> file for easy setup on your devices. All in just a few clicks.

 * <b>Secure, simple, and instant.</b> Your personal cloud VPN, deployed on demand.
 
## Languages and Frameworks:
* React with TypeScript and TailwindCSS for the Frontend
* Python for the AWS Lambda scripts
* Firebase for Authentication and Database
* Cloud tools used:
  * AWS Lambda, SES, DynamoDB, Secrets Manager, IAM, CloudWatch
  * OCI Resource Manager, Compute, Virtual Networking, and Terraform stacks
* If you would like documentation on how to configure a Wireguard EC2 VPN yourself, email me: [brodsky.alex22@gmail.com](brodsky.alex22@gmail.com)

## Usage

* Only the admin account is active for the time being.

* [Email me](mailto:brodsky.alex22@gmail.com) or message me on [LinkedIn](https://www.linkedin.com/in/brodsky-alex22/) if you want to try it.

* To save the config file or scan the QR code, on either the phone or computer, you need the Wireguard app because the VPN uses the Wireguard protocol.
  * Desktop: [wireguard.com](https://www.wireguard.com/install/) or for iPhone: [AppStore](https://apps.apple.com/us/app/wireguard/id1441195209)

#### On Phone

* Demo in the YouTube video.

* Install the Wireguard app on your phone.

* Either download the config file or scan the QR code in the Wireguard app.

* Enable it in Wireguard and Settings and you're done!

#### On Mac

* It's much easier to use the Wireguard Desktop app, but you can follow these steps instead:

* Start WireGuard manually:
  ```sh
  wg-quick up wg-client
  ```

* Check status:
  ```sh
  sudo wg
  ```

* To stop it:
  ```sh
  wg-quick down wg-client
  ```

### Running the React Site:

* See react-frontend folder for React README
