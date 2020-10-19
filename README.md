Tag-Based IPsec VPN Failover - Meraki APIv1
============= 
### Initial Notes

This script is based of ryanpjbyrne, guillaume6hat, and Meraki provided script: https://documentation.meraki.com/MX/Site-to-site_VPN/Tag-Based_IPsec_VPN_Failover. 

Thank you Guys!!

I just modified the API Calls, documentation details, data manipulation, and some prints, in order to use Meraki APIv1 Endpoints and Python3.

## Overview
Tagged Based VPN Failover is utilized for third party Data Center Failover and OTT SD WAN Integration. This is accomplished by utilizing the API at each branch or Data Center. Each MX appliance will utilize IPsec VPN with cloud VPN nodes. IPsec along with the API is utilized to facilitate the dynamic tag allocation.

Spoke sites will form a VPN tunnel to the primary DC. Dual active VPN tunnels to both DC’s is not possible with IPSec given that interesting traffic is often needed to bring up an IPSec tunnel and that interesting traffic will be routed to the first tunnel/peer configured and never the second.

Each spoke will be configured with a tracked IP of its primary DC under the traffic shaping page.

If the tracked IP experiences loss in the last 5 minutes, the API script (below) will re-tag the network in order to swap to the secondary IPSec VPN tunnel.

Once the tracked IP has not had any loss in the last 5 minutes, the tags will be swapped back to swap back to the primary DC (to avoid flapping)

### Step 0 - Add the Primary IPSec Peer IP Address for Monitoring 

Navigate to Security & SD-WAN > Traffic Shaping and add the IP of the primary peer under the uplink statistics.  The MX will start sending ICMP requests to this IP to track reachability. 

### Step 1 - "Fake" Network for creating/keeping the Tags

Navigate to Organization > Overview on the Meraki Dashboard and create a new empty network to add the tag you will be using. For instance:
- New Fake Network Name: "Z_FakeSite_For_Tags"
- Tags for this network: "Tag_ZS_B_DOWN", "Tag_ZS_B_UP", "Tag_ZS_P_DOWN", "Tag_ZS_P_UP"  -> B for Backup, P for Primary

### Step 2 - Configuration of IPSec Peer tags

Navigate to one Site > Security & SD-WAN > Site-to-site VPN > Non-Meraki VPN peers, on the Meraki Dashboard.  
Select the IPSec Peer you wish to tag and add only the "UP" tag for each IPSEC peer.  
For instance:

Primary IPSec Peer Tag: "Tag_ZS_P_UP"
Backup IPSec Peer Tag: "Tag_ZS_B_UP"

### Step 3 - Configuration of Network tags

Navigate to Organization > Overview on the Meraki Dashboard.  
Select the Network Sites you wish to tag and add one tag for each IPSEC peer.  
Initial Tags should be similar to this:

Network Site 1: "Tag_ZS_P_UP", "Tag_ZS_B_DOWN" -> Primary UP, Backup DOWN (this is the default state)

#### Step 4 - Run the script: 

Configure `meraki-parameters.json` with API Key and Org-ID then run:
`python3 tag-based-vpn-failover-meraki-apiv1.py`



