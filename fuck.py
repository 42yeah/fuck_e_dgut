# fuck_e_dgut by 42yeah

# This is free and unencumbered software released into the public
# domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a
# compiled binary, for any purpose, commercial or non-commercial, and
# by any means.

# In jurisdictions that recognize copyright laws, the author or
# authors of this software dedicate any and all copyright interest in
# the software to the public domain. We make this dedication for the
# benefit of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to
# this software under copyright law.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# For more information, please refer to <http://unlicense.org/>

import urllib.request
import urllib.parse
import json
import getopt
import sys
import re
import datetime

def get_config(path: str):
    fd = open(path, "r")
    info = json.load(fd)
    fd.close()
    return info

default_config_path = "./config.json"
config = get_config(default_config_path)

# Obtain token from stupid CAS
cas_response = urllib.request.urlopen(config["cas_url"])
cas_response_body = cas_response.read().decode("utf-8")
cas_set_cookies = cas_response.getheader("Set-Cookie")
cas_sessid = re.search("PHPSESSID=(.*?);", cas_set_cookies).group(0)

# Fetch token with the power of REGULAR EXPRESSION!
matched_token = re.search("var token = \"(.*?)\"", cas_response_body)
cas_auth_token = matched_token.group(0).split("\"")[1]

# Fake CAS Login and obtain key
cas_post_data = urllib.parse.urlencode({
    "username": config["username"],
    "password": config["password"],
    "__token__": cas_auth_token,
    "wechat_verify": ""
}).encode("utf-8")
cas_auth_request = urllib.request.Request(config["cas_url"])
cas_auth_request.add_header("Cookie", cas_sessid)
cas_auth_status = json.loads(urllib.request.urlopen(cas_auth_request, cas_post_data).read().decode("utf-8"))
if cas_auth_status["code"] != 1:
    print("错误！验证失败：", cas_auth_status["info"])
    exit(-1)
e_token = re.search("token=(.*?)&", cas_auth_status["info"]).group(0)

# Forge login request to e.dgut in order to get uid
e_auth_response = urllib.request.urlopen(config["e_dgut_login_url"] + "?" + e_token)
uid = re.search("uid=(.*?)&", e_auth_response.url).group(0)[4:-1]
access_token = re.search("access_token=(.*?)&", e_auth_response.url).group(0)[13:-1]

# With uid and access_token in hand, we can actually get a HUGE
# buttload of data!
def fetch_with_access_token(url, access_token, additional_headers = None):
    request = urllib.request.Request(url)
    request.add_header("x-authorization-access_token", access_token)
    if additional_headers != None:
        for header in additional_headers:
            request.add_header(header["key"], header["value"])
    return urllib.request.urlopen(request)

# User info
user_info = json.loads(fetch_with_access_token(config["e_dgut_user_info_url"] ,access_token).read().decode("utf-8"))

# Organization id
org_id = user_info["info"]["orgs"]["id"]

# Approvers
form_data = fetch_with_access_token(config["e_dgut_form_data_url"] + "?defId=" + config["leave_permit_form_id"], access_token).read().decode("utf-8")
approver_code = re.search("code=(.*?)&", form_data).group(0)[:-1]
approver_body = json.loads(fetch_with_access_token(config["e_dgut_approver_url"] + "?" + approver_code + "&field=xue_yuan_&value=" + org_id, access_token).read().decode("utf-8")) # Damn, this is long.
approvers = approver_body["info"][0]["shen_pi_ren_"]

# Class
class_data = json.loads(fetch_with_access_token("http://219.222.186.78:17750/api/studentLeaveOnLoadDao",
                                                access_token, [{ "key": "Origin", "value": config["e_dgut_home_url"] }]).read().decode("utf8"))
class_name = class_data["data"]["dataResult"]["classes"]
major_name = class_data["data"]["dataResult"]["major"]

# ... And we can finally apply for leave!
today = datetime.date.today().strftime("%Y-%m-%d")
huge_dict = {
    "xueHao": config["username"],
    "shenPiRen": approvers,
    "baiMingDanQuanXian": "C",
    "fanXiaoLuXian": config["return_route"],
    "fanXiaoChengZuoJTGJ": config["return_transportation"],
    "liXiaoLuXian": config["leave_route"],
    "liXiaoChengZuoJTGJ": config["leave_transportation"],
    "jiaTingZhuZhi": config["home_location"],
    "jiaChangDianHua": config["parents_phone"],
    "qingJiaYuanYin": "原因详细",
    "liXiaoMuDiDi": "{\"street\":\"\",\"province\":\"44\",\"city\":\"4419\",\"district\":\"\"}",
    "qingJiaLeiXing": config["leave_reason"],
    "qingJiaTianShu": 0,
    "fanXiaoShiJian": today,
    "liXiaoShiJian": today,
    "lianXiDianHua": config["contact"],
    "banJi": class_name,
    "zhuanYe": major_name,
    "id": ""
}
huge_dict_str = json.dumps(huge_dict)
outer_dict = {
    "parameters": [
        {
            "value": config["leave_permit_form_id"],
            "key": "defId"
        },
        {
            "value": 0,
            "key": "version"
        },
        {
            "value": huge_dict_str,
            "key": "data"
        }
    ]
}

# ,,, And send it.
request = urllib.request.Request(config["e_dgut_leave_apply_url"])
request.add_header("x-authorization-access_token", access_token)
request.add_header("Content-Type", "application/json;charset=UTF-8")
apply_post_data = json.dumps(outer_dict).encode("utf-8")
apply_request = urllib.request.urlopen(request, apply_post_data)
apply_status = apply_request.read().decode("utf-8")

print(apply_status)

# TODO Process the JSON as you wish! Example return:
