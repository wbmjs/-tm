#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import base64
import urllib.parse
import time
import os
from requests.exceptions import RequestException
from typing import List, Dict, Optional

# ==================== 配置区 ====================
BASE_URL = "https://server6.huozhong.xyz/api/nodesystem/user"
AUTH_URL = "https://server9.huozhong.xyz/realms/vpn_application/protocol/openid-connect/token"

# 从环境变量读取（GitHub Actions / 其他平台推荐方式）
USERNAME = os.getenv("HUOZHONG_USERNAME")
PASSWORD = os.getenv("HUOZHONG_PASSWORD")
CLIENT_ID = os.getenv("HUOZHONG_CLIENT_ID", "vpn-user")
CLIENT_SECRET = os.getenv("HUOZHONG_CLIENT_SECRET")

# 如果缺少关键环境变量，直接退出并提示
if not all([USERNAME, PASSWORD, CLIENT_SECRET]):
    print("错误：缺少必要的环境变量")
    print("请设置以下环境变量：")
    print("  HUOZHONG_USERNAME")
    print("  HUOZHONG_PASSWORD")
    print("  HUOZHONG_CLIENT_SECRET")
    exit(1)

# 输出文件（在 GitHub Actions 中会 commit 回仓库）
OUTPUT_FILE = "huozhong_vless_vmess_links.txt"


def login_and_get_token() -> Optional[str]:
    """使用用户名密码登录，获取新的 Bearer Token"""
    print("正在尝试登录获取新 Token...")
    
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    
    headers = {
        "User-Agent": "ktor-client",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "accept-charset": "UTF-8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    try:
        resp = requests.post(AUTH_URL, data=payload, headers=headers, timeout=15)
        print(f"登录状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"登录失败: {resp.text[:300]}")
            return None
        
        data = resp.json()
        token = data.get("access_token")
        if not token:
            print("响应中无 access_token")
            return None
        
        expires_in = data.get("expires_in", 0)
        print(f"登录成功！新 Token 获取成功，有效期约 {expires_in//60} 分钟")
        return token
    
    except Exception as e:
        print(f"登录异常: {str(e)}")
        return None


def get_node_list(token: str) -> List[Dict]:
    print("正在请求 nodeList 接口...")
    headers = {
        "User-Agent": "ktor-client",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "authorization": f"Bearer {token}",
        "accept-charset": "UTF-8",
        "Content-Type": "application/json"
    }
    
    try:
        url = f"{BASE_URL}/nodeList?platform=android"
        resp = requests.post(url, headers=headers, json={}, timeout=15)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"错误响应: {resp.text[:300]}")
            return []
        
        data = resp.json()
        if not isinstance(data, list):
            print("响应不是列表格式")
            return []
        
        print(f"成功获取 {len(data)} 个节点")
        return data
    
    except Exception as e:
        print(f"获取节点列表异常: {str(e)}")
        return []


def extract_node_name(node: Dict) -> str:
    """从 nodeList 提取节点名称，用于备注"""
    if name := node.get("nameCn"):
        return name.strip()
    if name := node.get("nameEn"):
        return name.strip()
    if region := node.get("regionNameCn"):
        return f"{region.strip()} 节点"
    return f"Node-{node.get('nodeId', '未知')}"


def get_client_config(node_id: int, token: str, max_retries: int = 4, backoff_factor: float = 2.0) -> Optional[Dict]:
    url = f"{BASE_URL}/clientConfig"
    payload = {"nodeId": node_id}
    headers = {
        "User-Agent": "ktor-client",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "authorization": f"Bearer {token}",
        "accept-charset": "UTF-8",
        "Content-Type": "application/json"
    }
    
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                print(f"  node {node_id} 配置获取成功")
                return resp.json()
            else:
                print(f"  node {node_id} HTTP {resp.status_code} (尝试 {attempt+1}/{max_retries+1})")
                if attempt == max_retries:
                    return None
        
        except RequestException as e:
            print(f"  node {node_id} 连接异常 (尝试 {attempt+1}/{max_retries+1}): {str(e)}")
            if attempt == max_retries:
                print(f"  node {node_id} 重试 {max_retries} 次后仍失败，跳过")
                return None
            
            wait_time = backoff_factor ** attempt
            print(f"  等待 {wait_time:.1f} 秒后重试...")
            time.sleep(wait_time)
    
    return None


def generate_vmess_link(config: Dict, node_name: str) -> str:
    vnext = config["settings"]["vnext"][0]
    user = vnext["users"][0]
    stream = config["streamSettings"]
    tcp_header = stream.get("tcpSettings", {}).get("header", {})
    
    vmess_dict = {
        "v": "2",
        "ps": node_name,
        "add": vnext["address"],
        "port": vnext["port"],
        "id": user["id"],
        "aid": user.get("alterId", 0),
        "scy": user.get("security", "auto"),
        "net": stream["network"],
        "type": tcp_header.get("type", "none"),
        "host": "",
        "path": "",
        "tls": stream.get("security", "none"),
        "sni": ""
    }
    
    json_str = json.dumps(vmess_dict, separators=(',', ':'), ensure_ascii=False)
    b64 = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8').rstrip('=')
    return f"vmess://{b64}"


def generate_vless_link(config: Dict, node_name: str) -> str:
    vnext = config["settings"]["vnext"][0]
    user = vnext["users"][0]
    stream = config["streamSettings"]
    
    if stream.get("security") == "reality":
        reality = stream["realitySettings"]
        params = {
            "security": "reality",
            "encryption": user.get("encryption", "none"),
            "pbk": reality["publicKey"],
            "headerType": "none",
            "fp": reality["fingerprint"],
            "type": stream["network"],
            "sni": reality["serverName"],
            "sid": reality["shortId"]
        }
    else:
        params = {"security": stream.get("security", "none")}
    
    query = urllib.parse.urlencode(params)
    remark = urllib.parse.quote(node_name)
    link = f"vless://{user['id']}@{vnext['address']}:{vnext['port']}?{query}#{remark}"
    return link


def save_link_only(link: str):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")


def main():
    print("火种VPN - 自动提取 vless / vmess 链接")
    print(f"输出文件: {OUTPUT_FILE}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 清空旧文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        pass
    
    # 步骤1: 登录获取 Token
    token = login_and_get_token()
    if not token:
        print("登录失败，无法继续。请检查环境变量中的用户名/密码是否正确")
        return
    
    # 步骤2: 获取节点列表
    nodes = get_node_list(token)
    if not nodes:
        print("没有获取到任何节点，结束")
        return
    
    success_count = 0
    
    for node in nodes:
        node_id = node.get("nodeId")
        if not node_id:
            continue
        
        node_name = extract_node_name(node)
        
        config = get_client_config(node_id, token)
        if not config:
            continue
        
        protocol = config.get("protocol", "").lower()
        
        if protocol not in ["vless", "vmess"]:
            print(f"  跳过不支持的协议: {protocol} (node {node_id})")
            continue
        
        try:
            if protocol == "vmess":
                link = generate_vmess_link(config, node_name)
            else:
                link = generate_vless_link(config, node_name)
            
            save_link_only(link)
            success_count += 1
            
            print(f"已保存 {protocol.upper()} 节点 {node_id} ({node_name})")
            # 打印前60个字符便于日志查看
            print(f"  {link[:80]}{'...' if len(link) > 80 else ''}")
        
        except Exception as e:
            print(f"生成 {protocol} 链接失败 (node {node_id}): {str(e)}")
    
    print(f"\n完成！共保存 {success_count} 条 vless/vmess 链接")
    print(f"文件已写入: {OUTPUT_FILE}")
    if success_count == 0:
        print("警告：没有成功生成任何链接，请检查账号状态或网络")
    print("\n安全提醒：请立即修改火种VPN密码！")


if __name__ == "__main__":
    main()
