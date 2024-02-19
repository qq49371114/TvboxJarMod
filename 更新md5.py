"""
遍历jar文件夹获取md5, 写入json配置文件
"""

import json, requests
import hashlib
import os
from git import Repo
import traceback
import re, base64
from bs4 import BeautifulSoup

# 需更新的json文件名后缀，不含后缀名，如feimao-mod 或feimao-mod-cn
suffix_list = ['-mod', '-mod-cn']
current_path = os.path.dirname(os.path.abspath(__file__))
conf_path = os.path.join(current_path, 'conf')
jar_dir_path = os.path.join(current_path, 'jar')
jar_official_dir_path = os.path.join(current_path, 'jar_official')
source_name_list = ["肥猫", "饭太硬"]
index_url = "https://xn--sss604efuw.top/"
print(current_path)

# 更新conf目录下的mod.json和mod-cn.json文件
def update_json_md5():
    # 遍历所有jar包，获取md5
    for root, dirs, files in os.walk(jar_dir_path):
        for jar_file in files:
            jar_md5 = ''
            json_md5 = ''
            with open(os.path.join(jar_dir_path, jar_file), 'rb') as f:
                jar_md5 = hashlib.md5(f.read()).hexdigest()
            # 遍历生成json文件路径，并更新json
            for suffix in suffix_list:
                # 生成json路径
                json_path = jar_file.replace(".jar", "")
                if json_path.lower().startswith('panda'):
                    json_path = 'feimao'
                json_path = json_path + suffix + '.json'
                json_path = os.path.join(conf_path, json_path)
                with open(json_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        json_spider = json_md5 = data['spider']
                        if json_spider.find(";md5;") != -1:
                            json_md5 = json_spider.split(';md5;')[1]
                            if json_md5 == jar_md5:
                                continue
                            data['spider'] = json_spider.split(';md5;')[0] + ';md5;' + jar_md5
                        else:
                            json_spider += ';md5;' + jar_md5
                        jar_name_json = json_spider.split(';md5;')[0].split('/')[-1]
                        if jar_name_json != jar_file:
                            json_spider = json_spider.replace(jar_name_json, jar_file)
                        if json_md5 != jar_md5:
                            data['spider'] = json_spider.split(';md5;')[0] + ';md5;' + jar_md5
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                            print(json_path, 'md5值更新成功')
                    except Exception as e:
                        print(e)

# 自动git push多仓源配置json文件到远程仓库
def git_push(repo_path):
    # 首先，我们需要创建一个Git对象，实例化我们想要的仓库
    repo = Repo(repo_path)
    # 接下来，我们想要提交所有修改
    repo.git.add(all=True)
    # 现在，我们想提交这些修改，并提供一个提交消息
    repo.git.commit("-m", "自动更新源")
    # 最后，我们想要将这些提交推送到远程仓库
    push_result = repo.git.push()
    print(push_result)

# 替换feimao-mod.json 接口对象内嵌jar包路径
def update_feimao_json():
    jar_url = ""
    json_updated = False
    # 读取feimao-mod.json文件
    with open(os.path.join(conf_path, 'feimao-mod.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
        sites = data['sites']
        # 获取spider中的jar包网址和md5
        spider = data['spider']
        if spider.find(";md5;") != -1:
            spider = spider.split(';md5;')[0]
            spider_name = spider.split('/')[-1]
            spider_host_url = spider.replace(spider_name, '')
        # 获取内嵌jar网址
        for site in sites:
            if site.find("jar") != -1:
                jar_url = site["jar"] if len(site["jar"]) > 0 else ""
                break
        # 提取内嵌jar包网址中的jar名和md5
        if jar_url.find(";md5;") != -1:
            jar_name = jar_url.split(';md5;')[0].split('/')[-1]
            jar_url_md5 = jar_url.split(';md5;')[1]
        else:
            jar_name = jar_url.split('/')[-1]
            jar_url_md5 = ''
        # 通过内嵌jar包名称生成对应本地jar包路径
        jar_path = os.path.join(jar_dir_path, jar_name)
        jar_md5 = ''
        # 遍历jar文件夹读取对应jar包，获取md5，并存入json对象
        if os.path.exists(jar_path):
            with open(jar_path, 'rb') as f:
                jar_md5 = hashlib.md5(f.read()).hexdigest()
            if jar_url_md5 != jar_md5 and jar_md5 != '':
                for site in sites:
                    if site.find("jar") != -1 and len(site["jar"])>0:
                        site['jar'] = spider_host_url + jar_name + ';md5;' + jar_md5
                        json_updated = True
    # 将json对象写入到feimao-mod.json
    if json_updated:
        with open(os.path.join(conf_path, 'feimao-mod.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def  jar_name_to_source_name(jar_name):
    jar_name = jar_name.lower().replace(".jar", "")
    if jar_name.find("panda") != -1:
        return "肥猫"
    elif jar_name.find("fan") != -1:
        return "饭太硬"
    else:
        return ""

# 更新jar
def update_jar_official():
    # 发送 HTTP GET 请求并获取响应内容
    response = requests.get(index_url)
    response.encoding = "utf-8"
    # print(response.content)
    # 解析 HTML 内容
    soup = BeautifulSoup(response.text, "html.parser")
    # 查找包含指定文本的 span 标签
    span_tags = soup.find_all(name="span", string=source_name_list)
    # 创建一个空列表来存储结果
    sources = {}
    # 遍历 span 标签的父 div 节点
    for span_tag in span_tags:
        parent_div = span_tag.parent
        # 获取父 div 节点中 data-clipboard-text 属性的值
        source_url = parent_div.get("data-clipboard-text")
        source_name = span_tag.get_text()
        # 将结果添加到列表中
        sources[source_name] = source_url
    # 打印结果
    print(sources)
    jar_md5_dict = {}
    json_md5_dict = {}
    try:
        # 读取self.sources, 发送请求, 获取json文件, 解析json文件获取md5值，存入json_md5_dict
        for source_name, source_url in sources.items():
            # 设置UA字符串
            user_agent = 'Okhttp/3.11.0'
            # 创建一个Session对象，以便可以保持UA设置
            session = requests.Session()
            session.headers.update({'User-Agent': user_agent})
            # 使用session对象发起请求，它会带上我们设置的UA
            response = session.get(source_url)
            data = response.text
            # 饭太硬源 解密
            if source_name == '饭太硬':
                # 正则匹配"[A-Za-z0-9]{8}\\*\\*"
                encrypt_code = re.search(r"[A-Za-z0-9]{8}\*\*", data).group()
                data = data[data.index(encrypt_code)+10:-1]
                missing_padding = 4 - len(data) % 4
                if missing_padding:
                    data += '='* missing_padding
                data = str(base64.b64decode(data), encoding='utf-8')            
            json_data = json.loads(data)
            json_spider = json_data['spider']
            json_md5 = json_spider.split(';md5;')[1]
            json_md5_dict[f'{source_name}'] = {}
            json_md5_dict[f'{source_name}']['md5'] = json_md5
            json_md5_dict[f'{source_name}']['url'] = json_spider.split(';md5;')[0]
            json_md5_dict[f'{source_name}']['fileName'] = json_spider.split(';md5;')[0].split('/')[-1]

        # 遍历jar文件夹，获取jar文件md5值，存入jar_md5_dict
        for root, dirs, files in os.walk(jar_official_dir_path):
            for jar_file in files:
                jar_md5 = ''
                jar_path = os.path.join(jar_official_dir_path, jar_file)
                with open(jar_path, 'rb') as f:
                    jar_md5 = hashlib.md5(f.read()).hexdigest()
                jar_md5_dict[jar_name_to_source_name(jar_file)] = {}
                jar_md5_dict[jar_name_to_source_name(jar_file)]['md5'] = jar_md5
                jar_md5_dict[jar_name_to_source_name(jar_file)]['path'] = jar_path
        
        if len(json_md5_dict) > 0:
            if len(jar_md5_dict) == len(json_md5_dict):
                for source_name, json_obj in json_md5_dict.items():
                    jar_md5 = jar_md5_dict[source_name]['md5']
                    jar_path = jar_md5_dict[source_name]['path']
                    json_md5 = json_obj['md5']
                    json_spider = json_obj['url']
                    if jar_md5 != json_md5:
                        try:
                            with open(jar_path, 'wb') as f:
                                response = requests.get(json_spider)
                                f.write(response.content)
                                print(source_name ,'更新jar成功')
                                return True
                        except Exception as e:
                            print(type(e), e)
                            traceback.print_exc()
                            return False
            else:
                for source_name, json_obj in json_md5_dict.items():
                    try:
                        jar_path = os.path.join(jar_official_dir_path, json_obj['fileName'])
                        if source_name == '饭太硬':
                            jar_path = jar_path.replace('.txt', '.jar')
                        with open(jar_path, 'wb') as f:
                            # 设置UA字符串
                            user_agent = 'Okhttp/3.11.0'
                            # 创建一个Session对象，以便可以保持UA设置
                            session = requests.Session()
                            session.headers.update({'User-Agent': user_agent})
                            # 使用session对象发起请求，它会带上我们设置的UA
                            response = session.get(json_obj['url'])
                            f.write(response.content)
                            print(source_name ,'更新jar成功')
                    except Exception as e:
                        traceback.print_exc()
                        return False
        else:
            print('官方json获取失败')
            return False
        return True
    except Exception as e:
        traceback.print_exc()
        return False            

if __name__ == '__main__':
    update_jar_official()
    update_json_md5()
    git_push(current_path)