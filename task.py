from git import Repo
from requests.exceptions import RequestException

"""
魔改jar包执行流程：
1. 逆向修改jar包 
2. 复制到jar文件夹 
3. 上传到蓝奏云
4. 执行task.py
5. 执行git
"""

import base64
import json
import os
import re

import requests
from bs4 import BeautifulSoup


class Config:
    root_path = r'D:\Project\android\TvboxJarMod'
    conf_path = os.path.join(root_path, 'conf')
    jar_dir_path = os.path.join(root_path, 'jar')
    jar_official_dir_path = os.path.join(root_path, 'jar_official')
    # source_name_cn_en_dict = {"饭太硬": "fan", "肥猫": "feimao","王小二":"wangxiaoer"}
    source_name_cn_en_dict = {"饭太硬": "fan","王小二":"wangxiaoer"}
    index_url = "https://xn--sss604efuw.com/"
    edge_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
    okhttp_user_agent = 'Okhttp/3.11.0'
    # 蓝奏网盘jar包共享文件夹
    lanzou_dir_url = 'https://samisold.lanzn.com/b0covfueh'
    lanzou_dir_password = 'teng'
    multiple_json_file = os.path.join(conf_path, 'multiple_source_tvbox.json')
    default_multiple_json_obj = {
        "urls": [
            {
                "name": "饭太硬",
                "url": "http://饭太硬.com/tv/"
            },
            {
                "name": "肥猫",
                "url": "http://肥猫.live"
            }
        ],
        "ext": {
            "highWeightApi": [
                "fre",
                "南瓜",
                "星奇",
                "黑狐",
                "低端",
                "咕噜"
            ],
            "lowWeightApi": [
                "官源",
                "荐片",
                "少儿",
                "小学",
                "初中",
                "高中",
                "儿童",
                "哔哩"
            ],
            "blockApi": [
                "荐影",
                "预告",
                "急救",
                "小说",
                "短剧",
                "体育",
                "聚短",
                "球",
                "MV",
                "┃飞"
            ],
            "adKeyword": [
                "广告",
                "公众号",
                "饭太硬",
                "肥猫",
                "免费分享",
                "神秘的哥哥"
            ],
            "adRegex": [
                "(?:from|content)\":\"([^\"]*?(?:公众号|神秘的哥哥|肥猫)[^\"]*?[\\s：:-])",
                "(?:vod_name)\":\"[^\"]*?(┃.*?)\""
            ]
        }
    }
    multiple_json_obj_template = {
        "urls": [],
        "ext": {
            "highWeightApi": [],
            "lowWeightApi": [],
            "blockApi": [],
            "adKeyword": []
        }
    }
    mod_json_hosts = {
        'GITHUB': 'https://raw.kkgithub.com/samisold/TvboxJarMod/main/',
        'GITEE': 'https://gitee.com/samisold/TvboxJarMod/raw/main/',
        'LANZOU': 'https://samisold.lanzn.com/'
    }


class TvboxConfigManager(object):
    def __init__(self, force_update=None):
        self.force_update = force_update if force_update else False
        self.local_conf_obj = Config.default_multiple_json_obj

    def update_multi_config(self) -> bool:
        # 发送 HTTP GET 请求并获取响应内容
        # 发送 HTTP GET 请求并获取响应内容
        response = requests.get(Config.index_url)
        if response.status_code != 200:
            print(f"请求失败: {Config.index_url, response.status_code}")
            return False
        response.encoding = "utf-8"
        # 解析 HTML 内容
        soup = BeautifulSoup(response.text, "html.parser")
        # 查找包含指定文本的 span 标签
        span_tags = soup.find_all(name="span", string=Config.source_name_cn_en_dict.keys())
        if len(span_tags) == 0:
            print(f"{Config.index_url}网页解析失败，未找到指定的span标签")
            return False
        # 创建一个空列表来存储结果
        remote_store_house_json = []
        # 遍历 span 标签的父 div 节点
        for span_tag in span_tags:
            parent_div = span_tag.parent
            # 获取父 div 节点中 data-clipboard-text 属性的值
            source_url = parent_div.get("data-clipboard-text")
            source_name = span_tag.get_text()
            source = {"name": source_name, "url": source_url}
            remote_store_house_json.append(source)
        if len(remote_store_house_json) == 0:
            print(f"未获取到json源数据：{Config.index_url}")
            return False
        self.local_conf_obj = Config.default_multiple_json_obj
        remote_conf_obj = Config.default_multiple_json_obj
        remote_conf_obj["urls"] = remote_store_house_json
        if remote_conf_obj != self.local_conf_obj:
            self.local_conf_obj = remote_conf_obj
            with open(Config.multiple_json_file, "w", encoding="utf-8") as f:
                json.dump(self.local_conf_obj, f, ensure_ascii=False, indent=4)
            return True
        elif self.force_update:
            print("执行强制更新")
            return True
        else:
            print("多仓源未发现更新")
            return False

    def update_single_config(self):
        # 发送请求, 获取最新官源json文件, 解析json文件获取md5值，存入json_md5_dict
        session = requests.Session()
        for source in self.local_conf_obj["urls"]:
            # 从多仓源json中获取源中文名
            source_name = source["name"]
            # 通过源中文名生成对应官方单仓源json文件名: 肥猫 -> feimao.json
            file_name = f'{Config.source_name_cn_en_dict[source_name]}.json'
            file_path = os.path.join(Config.conf_path, file_name)

            source_url = source["url"]
            # 设置UA字符串
            session.headers.update({'User-Agent': Config.okhttp_user_agent})
            # 使用session对象发起请求，它会带上我们设置的UA
            try:
                response = session.get(source_url)
            except RequestException as e:
                print(f"网络请求失败: {e}")
                continue
            response.encoding = 'utf-8'
            data = response.text
            # 饭太硬源 解密
            if source_name == '饭太硬':
                # 正则匹配"[A-Za-z0-9]{8}\\*\\*"
                encrypt_code = re.search(r"[A-Za-z0-9]{8}\*\*", data).group()
                data = data[data.index(encrypt_code) + 10:-1]
                missing_padding = 4 - len(data) % 4
                if missing_padding:
                    data += '=' * missing_padding
                data = str(base64.b64decode(data), encoding='utf-8', errors='ignore')
                # 修复解密中的小bug
                data = fr'{data}'.replace('//{', '{')
                data = fr'{data}' + '}' if data[-1] != '}' else data
            data = fr'{data}'.replace('/*{', '{')
            data = fr'{data}'.replace(',*/', ',')
            with open(file_path, 'r', encoding='utf-8') as f:
                local_data = f.read()
            if local_data != data:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data)
                print(f"{file_name}更新成功")
            else:
                print(f"{file_name}未发现更新")

    def git_push(self, repo_path, desc="自动更新源"):
        # 首先，我们需要创建一个Git对象，实例化我们想要的仓库
        repo = Repo(repo_path)
        # 接下来，我们想要提交所有修改
        repo.git.add(all=True)
        # 现在，我们想提交这些修改，并提供一个提交消息
        repo.git.commit("-m", desc)
        # 最后，我们想要将这些提交推送到远程仓库
        repo.git.push()


if __name__ == '__main__':
    config_manager = TvboxConfigManager(force_update=True)
    updated = config_manager.update_multi_config()
    if updated:
        config_manager.update_single_config()
        config_manager.git_push(Config.root_path)
