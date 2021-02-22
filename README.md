# Cisco_Provider_API
API to retrieve configuration information from Cisco IOS and NXOS devices

![image](https://github.com/gnasses/Cisco_Provider_API/blob/master/Cisco_Provider_API.JPG?raw=true)

**cisco_provider_api.py**

( POST http://myserver.mydomain.com:5005/api/token -- pass username and password to generate token)

( GET  http://myserver.mydomain.com:5005/api/safecommand/ &lt;device>/&lt;command>  -- unauthenticated device show commands from approved list )
  
( GET  http://myserver.mydomain.com:5005/api/command/ &lt;device>/&lt;command>  -- required authentication, run any valid read-only command, may not enter config mode) 
  

**safe_commands.py**

Python file imported by cisco_provider_api.py containing list of commands available via the safecommand API without authentication
