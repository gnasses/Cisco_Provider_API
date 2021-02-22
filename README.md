# Cisco_Provider_API
Cisco_Provider_API is a Python/Flask based API to retrieve configuration information from Cisco IOS and NXOS devices. Cisco_Provider_API uses a JWT-based front end for authentication, with user information salted and hashed. Two API endpoints are provided to query devices, but devicename must be known.  One endpoint does not require authentication but can only return a defined command-set. The other endpoint requires an authentication token but can return any show command and most commands that do not require config mode. 

SSH sessions to devices are made on the API back-end using Netmiko, with 3 device authentication methods (extracted from CyberArk API, creds imported from external .py file, or credentials hard-coded for lab devices) shown in a waterfall fashion. Abstracts away device credentials and SSH connection and allows command collection using only RESTful requests. Uses the NTC Templates to automatically return structured data if a text-fsm parser exists and raw data if no parser is avaialble for the requested command. 

![image](https://github.com/gnasses/Cisco_Provider_API/blob/master/Cisco_Provider_API.JPG?raw=true)

**cisco_provider_api.py**

( POST http://myserver.mydomain.com:5005/api/token -- pass username and password to generate token)

( GET  http://myserver.mydomain.com:5005/api/safecommand/ &lt;device>/&lt;command>  -- unauthenticated device show commands from approved list )
  
( GET  http://myserver.mydomain.com:5005/api/command/ &lt;device>/&lt;command>  -- required authentication, run any valid read-only command, may not enter config mode) 
  

**safe_commands.py**

Python file imported by cisco_provider_api.py containing list of commands available via the safecommand API without authentication
