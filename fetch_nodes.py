# main.py（完整可运行版）
import requests
import json
import random
import string
from flask import Flask, Response
import os

app = Flask(__name__)

# 从环境变量读取邀请码（安全！）
INVITE_CODE = os.getenv("INVITE_CODE", "X71WdV62")
DEFAULT_PASSWORD = "AutoPass123!"

def generate_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + "@djjd.com"

def generate_device_id():
    return "-".join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        "3" + ''.join(random.choices(string.hexdigits.lower(), k=3)),
        "8" + ''.join(random.choices(string.hexdigits.lower(), k=3)),
        ''.join(random.choices(string.hexdigits.lower(), k=12))
    ])

def get_nodes():
    # 1. 注册
    email = generate_email()
    device_id = generate_device_id()
    
    reg_res = requests.post(
        "https://api.tianmiao.icu/api/register",
        json={
            "email": email,
            "invite_code": "",
            "password": DEFAULT_PASSWORD,
            "password_word": ""
        },
        headers={
            "deviceid": device_id,
            "devicetype": "1",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.12.0"
        },
        timeout=10
    )
    
    if reg_res.status_code != 200:
        return f"注册失败: {reg_res.text}"
    
    reg_data = reg_res.json()
    token = reg_data["data"]["auth_data"]      # JWT token
    authtoken = reg_data["data"]["token"]      # auth token
    
    # 2. 绑定邀请码（可选）
    if INVITE_CODE:
        requests.post(
            "https://api.tianmiao.icu/api/bandInviteCode",
            json={"invite_code": INVITE_CODE},
            headers={
                "deviceid": device_id,
                "devicetype": "1",
                "token": token,
                "authtoken": authtoken,
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0"
            }
        )
    
    # 3. 获取节点
    node_res = requests.post(
        "https://api.tianmiao.icu/api/nodeListV2",
        json={
            "protocol": "all",
            "include_ss": "1",
            "include_shadowsocks": "1",
            "include_trojan": "1"
        },
        headers={
            "deviceid": device_id,
            "devicetype": "1",
            "token": token,
            "authtoken": authtoken,
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.12.0"
        },
        timeout=15
    )
    
    if node_res.status_code != 200:
        return f"节点获取失败: {node_res.text}"
    
    node_data = node_res.json()
    if node_data.get("code") != 1:
        return f"业务错误: {node_data.get('message')}"
    
    # 4. 提取原始URL（不编码！）
    urls = []
    for group in node_data.get("data", []):
        for node in group.get("node", []):
            url = node.get("url", "").strip()
            if url:
                urls.append(url)
    
    return "\n".join(urls)

@app.route('/')
def fetch_and_return():
    try:
        nodes = get_nodes()
        return Response(nodes, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        return f"❌ 错误: {str(e)}", 500

# 本地测试用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
