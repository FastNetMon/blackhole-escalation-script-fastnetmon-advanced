

FastNetMon Advanced provides number of options to apply different actions when it discovered DDoS attack. Also, it provides number of options to extend it using different approaches.

In this guide we will provide completely working approach for implementing escalations. Using this script, you can configure FastNetMon to create custom BGP announce for already blocked (blackholed) host when it crosses specified (“emergency”) threshold of traffic.

To use this script, please configure [BGP](https://fastnetmon.com/advanced-quick-start/) Then, please enable [API](https://fastnetmon.com/advanced-api/) You need to set secure password for API and then please specify this password inside specified script on line: “auth_data”.

Please download this script from [GitHub](https://github.com/FastNetMon/blackhole-escalation-script-fastnetmon-advanced):
```
wget https://raw.githubusercontent.com/FastNetMon/blackhole-escalation-script-fastnetmon-advanced/main/escalation_to_bgp_blackhole.py
chmod +x escalation_to_bgp_blackhole.py
sudo cp escalation_to_bgp_blackhole.py /opt
```

Please install dependencies:
```
sudo pip install requests
```

Also, in script you need to change following configuration options according to your requirements:
```
incoming_mbits_threshold = 100
outgoing_mbits_threshold = 100
incoming_packets_threshold = 2000
outgoing_packets_threshold = 2000
bgp_community = '65001:777'
bgp_next_hop = '11.22.33.44'
```

Finally, please add following cron entry in file /etc/cron.d/escalation_to_bgp_blackhole:
```SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
* * * * *  root    /opt/escalation_to_bgp_blackhole.py
```

Apply changes for cron:
```service cron restart```

This script will run each minute, check list of all already blackholed hosts and if they exceed thresholds in script it will announce /24 subnet for them with specified nexthop and community.
