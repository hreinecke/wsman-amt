# wsman-amt
Python script for controlling Intel AMT

This python script allows to control the Intel AMT managment engine.

# Functions
The following functions are supported
- identify
- power
- serial
- listener
- ider
- kvm

# Example
Identify the ME version:
~~~
# python3 ./wsman-amt -H <hostname> -U <username> -P <password> identify
Intel(r) AMT 11.8
~~~

Power on the system:
~~~
# python3 ./wsman-amt -H <hostname> -U <username> -P <password> power on
~~~
