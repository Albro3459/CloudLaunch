# RUNNING:

## On the Server (EC2)

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

## On Mac

Start WireGuard manually:
wg-quick up wg-client

Check status:
sudo wg

To stop it:
wg-quick down wg-client
