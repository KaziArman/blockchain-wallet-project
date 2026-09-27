### From Windows Defender Interface

You will need to do this on both laptops. Here is the step-by-step guide to doing it the professional way (by creating a specific Port Rule):

## Step 1: Open Advanced Firewall Settings
Click the Start Menu (the Windows logo) on your taskbar.

Type Windows Defender Firewall and hit Enter.

On the left-hand menu of the window that pops up, click Advanced settings. (This will open a new, more technical-looking window).

## Step 2: Create a New Inbound Rule
In this new window, look at the left panel and click on Inbound Rules.

Now, look at the far right panel under "Actions" and click New Rule...

## Step 3: Configure the Ports
Rule Type: Select Port and click Next.

Protocol and Ports: * Ensure TCP is selected at the top.

Select Specific local ports, and in the text box next to it, type exactly: 30303, 8545

Click Next.

Action: Select Allow the connection and click Next.

Profile: Leave all three boxes checked (Domain, Private, and Public). This ensures it works even if Windows categorized your Wi-Fi network weirdly. Click Next.

Name: Give it a name you will remember, like Blockchain Node Ports, and click Finish.


### By using Windows Powershell as administrator

## On Device 1 — Open Windows Firewall for ports 30303 and 8545 run the 2 powershell commands

`netsh advfirewall firewall add rule name="Besu P2P" dir=in action=allow protocol=TCP localport=30303`
`netsh advfirewall firewall add rule name="Besu RPC" dir=in action=allow protocol=TCP localport=8545`

Once bootnode1 is running again, test from Device 1's PowerShell:
powershellTest-NetConnection 192.168.1.239 -Port 30303
Test-NetConnection 192.168.1.239 -Port 8545

Both should now show TcpTestSucceeded: True. If RPC (8545) passes but P2P (30303) still fails, the firewall rule didn't take effect — try temporarily disabling Windows Firewall entirely to test:
`powershellnetsh advfirewall set allprofiles state off`

When your two-device QBFT blockchain network is fully operational — both reading and writing across machines.
Now turn your firewall back on (Device 1):

```powershell
powershellnetsh advfirewall set allprofiles state on
netsh advfirewall firewall add rule name="Besu P2P" dir=in action=allow protocol=TCP localport=30303
netsh advfirewall firewall add rule name="Besu P2P UDP" dir=in action=allow protocol=UDP localport=30303
netsh advfirewall firewall add rule name="Besu RPC" dir=in action=allow protocol=TCP localport=8545
```
