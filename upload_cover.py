#!/usr/bin/env python3
"""Upload a specific cover to WeChat material library."""
import json, sys, urllib.request

WECHAT_APPID = "wx2003a12d1b3d867f"
WECHAT_SECRET = "32dbd01b12d99e18ed4a997e9145f922"
COVER_PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\jt\WorkBuddy\Claw\_cover_city.png"

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    return json.loads(urllib.request.urlopen(url).read()).get("access_token")

def upload(token, path):
    boundary = '----Boundary7MA4YW'
    with open(path, 'rb') as f:
        img_data = f.read()
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode() + img_data + f'\r\n--{boundary}--\r\n'.encode()
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    return json.loads(urllib.request.urlopen(req).read())

token = get_token()
print(f"TOKEN: {'OK' if token else 'FAIL'}")
result = upload(token, COVER_PATH)
print(f"Upload: {result}")
if "media_id" in result:
    print(f"MEDIA_ID={result['media_id']}")
