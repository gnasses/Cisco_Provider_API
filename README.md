# Cisco_Provider_API
API to retrieve configuration information from Cisco IOS and NXOS devices

![image](https://github.optum.com/NS/Cisco_Provider_API/blob/master/Cisco_Provider_API.JPG?raw=true)

**cisco_provider_api.py**

( POST http://apvrp63353:5005/api/token -- pass username and password to generate token)

( GET  http://apvrp63353:5005/api/safecommand/ &lt;command&gt;  -- unauthenticated device show commands from approved list )
  
( GET  http://apvrp63353:5005/api/command/<device>/<command>  -- required authentication, run any valid read-only command, may not enter config mode) 
  
