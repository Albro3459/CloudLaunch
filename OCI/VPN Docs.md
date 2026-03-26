# **Original VPN Docs**

* Good reference but now the terraform scripts do this on setup

* **Useful info:**  
  * Mac and iPhone typically share the same IP on the same wifi
    * IP: .../32  
    * They will rotate IPs so we will allow any ip on UDP, but have wireguard setup with conf to only allow access with the right keys. Plus a rate limiter  
  * EC2:  
    * ubuntu@...  
    * or  
    * ubuntu@ec2-....us-west-1.compute.amazonaws.com  
    * ssh is setup now with `ssh cloudlaunch`  
    * 2600:1....:ac5d  \# IPv6  
  * VPC:  
    * .../16  \# IPv4  
    * 2600:...::/56  \# IPv6  
  * Mac:  
    * I set this up in the terminal.  
    * Go to /opt/homebrew/etc/wireguard  
      * Yes it is a git repo, idk dont fuck with it. It is homebrew prolly  
    * There is a README there:  
  * Server:  
    * Wireguard stuff in /etc/wireguard  
    * There is a README in \~/ though  
  * **RUNNING:**  
    * **On the Server (EC2)**  
* Restart the WireGuard service:

  `sudo systemctl restart wg-quick@wg0`

* Check if it's running:

  `sudo systemctl status wg-quick@wg0`

* To see connected clients:

  `sudo wg show`

* To disable:

  `sudo systemctl disable wg-quick@wg0`

  * **On Mac:**  
* Start WireGuard manually:

  `wg-quick up wg-client`

* `Check status:`

  `sudo wg`

* `To stop it:`

  `wg-quick down wg-client`

  * Good luck. I have no doubt that even following this word for word it will still break

    

## **Step 1: Set Up an Ubuntu Instance on AWS**

* ## **AWS EC2 on whatever region (us-west-1)**

  * AWS EC2: **t2.micro** (free tier eligible, \~8.47/month if not free).  
  * **t2.micro** with **Ubuntu 22.04 LTS (x86\_64)**  
* Create RSA keys .pem, mv to \~/.ssh/  
  * chmod 400 \~/.ssh/vpn-ec2-key.pem   
  * Makes it readonly  
* In EC2 \> Security Groups, Inbound rules enable SSH on port 22 (with TCP) for **ONLY** your own `IPv4/32`!
  * Enable WireGuard (Port 51820, UDP) as **(`0.0.0.0/0`)** so you can connect from any WiFi and cellular network. Wireguard conf keys and rate limiter will protect.  
    * AWS makes it hard to get an IPv6 address so if you want it, see the final step 14 as of now:  
      * Then add ::0 to port 51820, UDP for IPv6  
      * and for **outbound** rules there should be 0.0.0.0/0 and ::0 anywhere (2 separate ruled)  
  * Outbound rules: **(`0.0.0.0/0`)** for full VPN functionality.

## **Step 2: SSH in 😈**

* ssh \-i \~/.ssh/vpn-ec2-key.pem ubuntu@ec2-....us-west-1.compute.amazonaws.com

	or  
	ssh \-i \~/.ssh/vpn-ec2-key.pem ubuntu@...

* sudo apt update  
  * Update packages for the vpn  
* edit \~/.ssh/config:  
  Host cloudlaunch  
    HostName ec2-....us-west-1.compute.amazonaws.com  
    User ubuntu  
    IdentityFile \~/.ssh/vpn-ec2-key.pem  
    PubkeyAuthentication yes  
  * Now you can just ssh cloudlaunch  
  * Also use vscode with:  
    code \--folder-uri "vscode-remote://ssh-remote+cloudlaunch"  
    * PS I made an extension to the vscode exec code under \~/code-ssh  
    * Run mv \~/code-ssh \~/code-ssh.txt to make a text file  
      * Then open \~/code-ssh.txt to edit it.

**Step 3: Update & Install WireGuard**

* Run the following commands to update the system and install WireGuard:  
  sudo apt update && sudo apt upgrade \-y

sudo apt install wireguard \-y

Check if WireGuard installed correctly:  
wg \--version

### **Step 4: Generate Keys for WireGuard**

WireGuard needs a **private key** and a **public key** for encryption.  
Run this to generate them:  
`wg genkey | tee privatekey | wg pubkey > publickey`

Then, check the keys:  
`cat privatekey`  
`cat publickey # ...`

* **Private key** (DO NOT share this, only used in `wg0.conf`).  
* **Public key** (needed for clients to connect).

---

### **Step 5: Create the WireGuard Configuration File**

Create the **server config file**:

`sudo nano /etc/wireguard/wg0.conf`

`sudo chmod 600 /etc/wireguard/wg0.conf`



`[Interface]`

`Address = 10.0.0.1/24, fd42:42:42::1/64`

`PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE; ip6tables -t nat -A POSTROUTING -s fd42:42:42::/64 -o eth0 -j MASQUERADE; iptables -A INPUT -p udp --dport 51820 -m conntrack --ctstate NEW -m limit --limit 25/sec --limit-burst 100 -j ACCEPT; iptables -A INPUT -p udp --dport 51820 -j DROP`

`PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE; ip6tables -t nat -D POSTROUTING -s fd42:42:42::/64 -o eth0 -j MASQUERADE; iptables -D INPUT -p udp --dport 51820 -m conntrack --ctstate NEW -m limit --limit 25/sec --limit-burst 100 -j ACCEPT; iptables -D INPUT -p udp --dport 51820 -j DROP`

`ListenPort = 51820`

`PrivateKey = ... # Server private`

---

### **Step 6: Enable IP Forwarding**

WireGuard needs to route traffic through your EC2 instance.

In /etc/sysctl.conf add this to the bottom:  
`# IPv4`  
`net.ipv4.ip_forward = 1`

`# IPv6`  
`net.ipv6.conf.all.forwarding = 1`  
`net.ipv6.conf.all.disable_ipv6 = 0`  
`net.ipv6.conf.default.disable_ipv6 = 0`  
`net.ipv6.conf.lo.disable_ipv6 = 0`

Run to restart and check:  
`sudo sysctl -p`

Check IPv4 if it's enabled:

`sysctl net.ipv4.ip_forward`

It should return:  
`net.ipv4.ip_forward = 1`

Check IPv6:

`ip a | grep inet6`

---

### **Step 7: Start & Enable WireGuard**

Run:  
`sudo systemctl enable --now wg-quick@wg0`

Check status:  
`sudo systemctl status wg-quick@wg0`

It should say **"Active (running)"** ✅  
---

### **Step 8: Allow TCP & UDP Traffic in Firewall**

Allow **TCP 22** and **UDP 51820** in **UFW (Uncomplicated Firewall)**:  
`sudo ufw allow 22/tcp`  
`sudo ufw allow 51820/udp`  
`sudo ufw route allow in on wg0 out on eth0`  
`sudo ufw route allow in on eth0 out on wg0`  
`sudo ufw enable`  
`sudo ufw status`

`sudo ufw status verbose`  
`Should look like:`

`To                         Action      From`  
`--                         ------      ----`  
`22/tcp                     ALLOW IN    Anywhere`                
`51820/udp                  ALLOW IN    Anywhere`                  

`Anywhere on eth0           ALLOW FWD   Anywhere on wg0`             
`Anywhere on wg0            ALLOW FWD   Anywhere on eth0` 

**IMPORTANT:**
* We allow all on `TCP 22` at the firewall level, but you **must** have AWS security groups setup to only allow your `IPv4/32` for `TCP 22`
* Your IP can and will change, so limit at the AWS level, **NOT** the instance level or you will get locked out.

---

## **Step 9: Generate Client Keys**

Run these commands on your LOCAL:

`brew install wireguard-tools  `
`mkdir \-p /opt/homebrew/etc/wireguard  `
`cd /opt/homebrew/etc/wireguard  `
`wg genkey | tee vpn_client_privatekey | wg pubkey > vpn_client_publickey`
`chmod 600 vpn_client_publickey`

## Check the keys:

`cat vpn_client_privatekey`
`cat vpn_client_publickey`

* Client Private Key (for the client config file).

* Client Public Key (needs to be added to the server).

---

## **Step 10: Add Client to Server Config**

On EC2, edit the same server config:

`sudo nano /etc/wireguard/wg0.conf`

At the bottom, add:

`[Peer]`

`PublicKey = ... # Client public`

`AllowedIPs = 10.0.0.2/32, fd42:42:42::2/128`  
`PersistentKeepalive = 25`

Save and exit (`CTRL + X`, `Y`, `ENTER`).

Still on EC2, apply the changes:

`sudo systemctl restart wg-quick@wg0` 

`sudo systemctl status wg-quick@wg0`

Still on EC2, check if the client is added:

`sudo wg show`



---

## **Step 11: Create Client Configuration File**

On your local computer (or phone), create the following WireGuard client config:

Create wg-client.conf in the same /opt/homebrew/etc/wireguard  
chmod 600 wg-client.conf

`[Interface]`

`PrivateKey = ... # Client private`

`Address = 10.0.0.2/24, fd42:42:42::2/64`

`DNS = 10.0.0.1, fd42:42:42::1  # WireGuard server DNS`

`[Peer]`

`PublicKey = ... # Server public`

`Endpoint =` ...`:51820  # EC2 IP`

`AllowedIPs = 0.0.0.0/0, ::/0  # Full-tunnel mode (all traffic through VPN)`

`PersistentKeepalive = 25`

* ## iOS -> Use the WireGuard app, scan a QR code or use files or something

---

## **Step 12: Check some more things:**

On **EC2:**

sudo iptables \-t nat \-L \-v \-n

Should have this:  
338 81246 MASQUERADE  all  \--  \*      eth0    10.0.0.0/24          0.0.0.0/0             
  614 47234 MASQUERADE  all  \--  \*      eth0    0.0.0.0/0            0.0.0.0/0             
    0     0 MASQUERADE  all  \--  \*      eth0    0.0.0.0/0            0.0.0.0/0 

**If it's missing**, reapply it:  
`sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE`  
`Ask chat for the others`

Save the iptables
`sudo apt install iptables-persistent \-y`
`sudo netfilter-persistent save`
`sudo netfilter-persistent reload`

check:  
sudo ufw status verbose  
Make sure it looks like this:  
`22/tcp                     ALLOW IN    Anywhere`                
`51820/udp                  ALLOW IN    Anywhere`                    
`Anywhere on eth0           ALLOW FWD   Anywhere on wg0`             
`Anywhere on wg0            ALLOW FWD   Anywhere on eth0` 

If missing, re-add:

`sudo ufw allow 51820/udp`
`sudo ufw route allow in on wg0 out on eth0`
`sudo ufw route allow in on eth0 out on wg0`
`sudo ufw reload`

ip route show  
You should see something like:  
default via 172.31.16.1 dev eth0 proto dhcp src 172.31.25.216 metric 100   
10.0.0.0/24 dev wg0 proto kernel scope link src 10.0.0.1   
172.31.0.2 via 172.31.16.1 dev eth0 proto dhcp src 172.31.25.216 metric 100   
172.31.16.0/20 dev eth0 proto kernel scope link src 172.31.25.216 metric 100   
172.31.16.1 dev eth0 proto dhcp scope link src 172.31.25.216 metric 100 

GOOD FUCKING LUCK


## **Step 13: RUNNING:**

**On the Server (EC2)**

* Restart the WireGuard service:  
  `sudo systemctl restart wg-quick@wg0`  
* Enable it to start on boot:

`sudo systemctl enable wg-quick@wg0`

* Check if it's running:

`sudo systemctl status wg-quick@wg0`

* To see connected clients:

`sudo wg show`

* To disable:

`sudo systemctl disable wg-quick@wg0`

**On Mac:**

* Start WireGuard manually:

`wg-quick up wg-client`

* `Check status:`

`sudo wg`

* `To stop it:`

`wg-quick down wg-client`

**`It should just be working now after starting the services!!`**  
**`On iPhone you need the Wireguard app`**

* `On Mac`

	`brew install qrencode`

`Scan this with the Wireguard app`  
`qrencode -t ansiutf8 < wg-client.conf # QR Code`

## **OPTIONAL Step 14: IPv6:**

* FIRST: make sure you follow all other steps and IPv4 works and wireguard is configured properly with the keys  
  * The make sure the Security group properly allows Inbound 0.0.0.0/0 and ::0 for UDP to ur port 51820 and Outbound is allowed for all traffic to 0.0.0.0/0 and ::0  
* Need to go to the VPC that the instance is running in  
  * Actions \> Edit CIDR settings to allocate an IPv6 for VPC  
  * Find the subnet for the instance (go to the instance and it should have it somewhere)  
    * Actions \> Edit CIDR  
      * Allocate an IPv6, choose "Amazon-provided IPv6 CIDR block" and the same region as ur instance  
    * Then Actions \> Edit Subnet Settings  
      * Make sure auto-assign IPv4 and IPv6 are BOTH on  
  * Go back to VPC, on the Resource Map, find the Route Table  
    * Add ::0 for Internet Gateway with the same igw as the 0.0.0.0/0 one
