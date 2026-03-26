Here are the recovery steps we actually used after locking SSH down too tightly on the EC2 WireGuard box.

**Recovery**
1. Launch a temporary rescue EC2 instance in the same Availability Zone as the locked instance.
2. Make sure you can SSH into the rescue instance before touching the VPN box.
3. Stop the locked VPN instance.
4. Detach its root EBS volume.
5. Attach that volume to the rescue instance as a secondary disk. `sdd` which gets mapped to `xvdd`
6. SSH into the rescue instance and find the attached partition:
```bash
lsblk
```
In our case the rescue instance root disk was `xvda`, and the attached disk was `xvdd` with the root partition at `xvdd1`.

7. Mount it:
```bash
sudo mkdir -p /mnt/recover
sudo mount /dev/xvdd1 /mnt/recover
```
Use the actual partition from `lsblk`.

8. Inspect the persisted firewall rules:
```bash
sudo sed -n '1,220p' /mnt/recover/etc/ufw/user.rules
sudo sed -n '1,260p' /mnt/recover/etc/iptables/rules.v4
```
The lockout came from the saved SSH allow rule only permitting the old home IP:
```text
-A ufw-user-input -p tcp --dport 22 -s 70.177.51.55 -j ACCEPT
```

9. We also disabled `ufw` from starting on boot while recovering:
```bash
sudo sed -n '1,40p' /mnt/recover/etc/ufw/ufw.conf
```
Set:
```text
ENABLED=no
```

10. Make sure both of these files allow SSH from anywhere:
- `/mnt/recover/etc/ufw/user.rules`
- `/mnt/recover/etc/iptables/rules.v4`

Each file should contain this rule:
```text
-A ufw-user-input -p tcp -m tcp --dport 22 -j ACCEPT
```

11. Verify the rule exists in both files:
```bash
sudo grep -n 'ufw-user-input.*dport 22' /mnt/recover/etc/ufw/user.rules /mnt/recover/etc/iptables/rules.v4
```

12. Unmount the volume:
```bash
sudo umount /mnt/recover
```

13. Detach it from the rescue instance.
14. Reattach it to the original instance as the root volume.
15. Start the original instance.
16. SSH back in, preferably over the WireGuard tunnel first:
```bash
ssh -i ~/.ssh/vpn-ec2-key.pem ubuntu@10.0.0.1
```

**What Actually Happened**
- AWS security groups were not the primary issue.
- The instance had persisted host firewall rules that only allowed `22/tcp` from the old public IP.
- Disabling `ufw` alone was not enough because the saved iptables rules were still being restored on boot.
- The fix was making sure the SSH allow rule existed in both saved firewall files.

**Practical Rule**
- `22/tcp`: control it in the EC2 Security Group unless you intentionally want host-level filtering too
- `51820/udp`: open publicly for WireGuard
- if you do use host firewall rules, make sure they do not silently narrow SSH more than the Security Group does
