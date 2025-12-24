# fetch_nodes.py
import requests
import json
import random
import string
import os
import sys

# 从环境变量读取配置
INVITE_CODE = os.getenv("INVITE_CODE")
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

def main():
    print("🚀 开始自动获取节点...")
    email = generate_email()
    device_id = generate_device_id()
    print(f"📧 使用邮箱: {email}")
    
    # 1. 注册
    try:
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
        reg_res.raise_for_status()
        reg_data = reg_res.json()
        
        if reg_data.get("code") != 1:
            print(f"❌ 注册失败: {reg_data.get('message')}")
            sys.exit(1)
            
        token = reg_data["data"]["auth_data"]    # JWT token
        authtoken = reg_data["data"]["token"]    # auth token
        print("✅ 注册成功，已获取认证令牌")
        
    except Exception as e:
        print(f"🔥 注册异常: {str(e)}")
        sys.exit(1)
    
    # 2. 绑定邀请码
    if INVITE_CODE:
        try:
            bind_res = requests.post(
                "https://api.tianmiao.icu/api/bandInviteCode",
                json={"invite_code": INVITE_CODE},
                headers={
                    "deviceid": device_id,
                    "devicetype": "1",
                    "token": token,
                    "authtoken": authtoken,
                    "Content-Type": "application/json",
                    "User-Agent": "okhttp/4.12.0"
                },
                timeout=10
            )
            if bind_res.status_code == 200:
                print("✅ 邀请码绑定成功")
            else:
                print("⚠️ 邀请码绑定失败（可能已绑定）")
        except Exception as e:
            print(f"⚠️ 绑定异常: {str(e)}")
    
    # 3. 获取节点
    try:
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
        node_res.raise_for_status()
        node_data = node_res.json()
        
        if node_data.get("code") != 1:
            print(f"❌ 节点获取失败: {node_data.get('message')}")
            sys.exit(1)
            
        # 提取原始URL（不编码！）
        urls = []
        for group in node_data.get("data", []):
            for node in group.get("node", []):
                url = node.get("url", "").strip()
                if url:
                    urls.append(url)
        
        if not urls:
            print("❌ 未获取到任何节点")
            sys.exit(1)
            
        # 输出到标准输出（供后续步骤捕获）
        print("\n".join(urls))
        print(f"\n✅ 成功获取 {len(urls)} 个节点", file=sys.stderr)
        
    except Exception as e:
        print(f"🔥 节点获取异常: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
