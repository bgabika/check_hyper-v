
# check_hyper-v

COREX Microsoft Hyper-V check plugin for Icinga 2
 
### Features
 - checks Microsoft Hyper-V service & feature state
 - checks VMs state: cpu, memory usage, connected switch, VM health, uptime
 - prints performance data for Icinga 2 Graphite Module ( and other solutions like Graphite )
 - warning/critical thresholds for cpu and memory check
 - for more details run check_hyper-v.py --help

### Usage

<pre><code>
# cd /usr/lib/nagios/plugins
# ./check_hyper-v.py --hostname 10.44.200.72 --sshuser john.doe --sshkey /var/lib/nagios/.ssh/id_rsa --memwarning 85 --memcritical 95 --cpuwarning 85 --cpucritical 95 
CRITICAL - Memory usage: 'KVS Zero' VM state is Running, CPU usage: 10.0%, memory usage: 103.99% (9.36 GB / 9.0 GB), switch name: VLAN2, VM health: Operating normally, uptime: 6.06:41:50 |KVS Zero memory=103.99%;85;95;0;100 KVS Zero cpu=10.0%;85;95;0;100
OK - Windows vmms service state is Running.
OK - Microsoft-Hyper-V feature state is Enabled.
OK - 'BackofficeW7' VM state is Running, CPU usage: 0.0%, memory usage: 0.0% (0.0 MB / 4.0 GB), switch name: VLAN2, VM health: Operating normally, uptime: 42.06:05:48 |BackofficeW7 memory=0.0%;85;95;0;100 BackofficeW7 cpu=0.0%;85;95;0;100
OK - 'Windows 10 Account VM' VM state is Running, CPU usage: 6.0%, memory usage: 58.0% (9.28 GB / 16.0 GB), switch name: VLAN2, VM health: Operating normally, uptime: 12.01:47:08 |Global Store Controller memory=58.0%;85;95;0;100 Global Store Controller cpu=6.0%;85;95;0;100
#
</code></pre>


### Version

 - 1.1

### ToDo

 - waiting for bugs or feature requests (-:

## Changelog

 - [initial release] version 1.1

