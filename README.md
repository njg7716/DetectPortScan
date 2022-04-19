# What does this do?
detectScan.py will use raw sockets to detect a port scan
from detectScan import scancheck.

Once 3 ports have been scanned, an MQTT message will be sent to AWS with the source IP and the time.

It will not report on that offending IP address again until after 5 mins has past at which point the list of offending IP addresses is cleared.

Personally, I have my AWS account set up so when an MQTT message of this topic comes in, a text alert is sent to me with the offending IP address and time the scan occured.