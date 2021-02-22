import os, time, requests
from flask import Flask, jsonify, g, url_for, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from netmiko import Netmiko
from ntc_templates.parse import parse_output
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import ciscocreds, safe_commands, esm

valid = safe_commands.valid

# init
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#extensions
db = SQLAlchemy(app)
auth = HTTPBasicAuth()

# user database functions
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=600):
        return jwt.encode(
            {'id': self.id, 'exp': time.time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except:
            return
        return User.query.get(data['id'])    

#Netmiko classes for all distinct device authentication methods
class CiscoDeviceRO:
    def __init__(self, host, username=ciscocreds.rouser, password=ciscocreds.ropass, device_type='cisco_ios', timeout=90, auth_timeout=90):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.timeout = timeout
        self.auth_timeout = auth_timeout 
        
class CiscoISERO:
    def __init__(self, host, username, password, device_type='cisco_ios', timeout=90, auth_timeout=90):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.timeout = timeout
        self.auth_timeout = auth_timeout         
        
class CiscoDeviceLAB:
    def __init__(self, host, username=ciscocreds.labuser, password=ciscocreds.labpass, device_type='cisco_ios', timeout=90, auth_timeout=90):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.timeout = timeout
        self.auth_timeout = auth_timeout  

# Netmiko Cascading session function to try the multiple credential classes above
def cisco_connector(device):        
    try:
        net_device = CiscoDeviceRO(host=device)
        dev_connect = Netmiko(**net_device.__dict__)
        return dev_connect
    except Exception:
            try:
                response = requests.request("GET", esm.url, headers=esm.headers, params=esm.querystring, verify=False)
                rouser = response.json().get('UserName')
                ropass = response.json().get('Content')               
                net_device = CiscoISERO(host=device, username=rouser, password=ropass)
                dev_connect = Netmiko(**net_device.__dict__) 
                return dev_connect
            except Exception:
                try:
                    net_device = CiscoDeviceLAB(host=device)
                    dev_connect = Netmiko(**net_device.__dict__)
                    return dev_connect
                except Exception as e:
                    ret_error = "Exception found:"+ str(e)
                    return  ret_error

# Netmiko connection function leveraging previous conenctor function                
def cisco_command(device, command):  
    try:
        dev_connect = cisco_connector(device)
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error        
    try:
        result = dev_connect.send_command(command)
        dev_connect.disconnect()
        return result
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error  

#Network OS classification for use by called parsers
def findos(device):        
    try:
        dev_connect = cisco_connector(device)
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error  
    try:
        show_ver = dev_connect.send_command('show version')
        dev_connect.disconnect()
        if "NX-OS" in show_ver:
            os = "cisco_nxos"
        else:
            os = "cisco_ios"
        return os
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error    

#Authentication Functions and routes for API User Auth
#password/token verification        
@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True

#user creation route    
@app.route('/api/users', methods=['POST'])
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400)    # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)    # existing user
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'username': user.username}), 201, {'Location': url_for('get_user', id=user.id, _external=True)}   

#user validation route 
@app.route('/api/users/<int:id>', methods=['GET', 'POST'])
def get_user(id):
    user = User.query.get(id)
    if not user:
        abort(400)
    return jsonify({'username': user.username})

#token generation route
@app.route('/api/token', methods=['GET', 'POST'])
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})

#test route for authentication, simple username return
@app.route('/api/resource', methods=['GET'])
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})

#Cisco Command Collection API Routes
#Safecommand API restricted to exact command syntax in [valid] - no login required
@app.route('/api/safecommand/<device>/<command>', methods=['POST', 'GET'])
def cisco_api_command_safe(device, command):
    #trigger API RunCounter to increment when API is called
    r = requests.request("POST", "http://myserver.mydomain.com:5018/api/trigger/Cisco_Provider", verify=False)
    if command not in valid:
        raise ValueError("Unsupported Command: must be one of %r." %valid)    
    try:
        dev_connect = cisco_connector(device)
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error       
    try:
        os = findos(device)
        result = dev_connect.send_command(command)
        dev_connect.disconnect()
        try:
            output = parse_output(platform=os, command=command, data=result)
            return jsonify(output)
        except:
            output = result
            return output
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error

#command API can run any single command from authenticated user
@app.route('/api/command/<device>/<command>', methods=['POST', 'GET'])
@auth.login_required
def cisco_api_command(device, command): 
    #trigger API RunCounter to increment when API is called
    r = requests.request("POST", "http://myserver.mydomain.com:5018/api/trigger/Cisco_Provider", verify=False)
    try:
        dev_connect = cisco_connector(device)
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error          
    try:
        os = findos(device)
        result = dev_connect.send_command(command)
        dev_connect.disconnect()
        try:
            output = parse_output(platform=os, command=command, data=result)
            return jsonify(output)
        except:
            output = result
            return output
    except Exception as e:
        ret_error = "Exception found:"+ str(e)
        return  ret_error    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005)

