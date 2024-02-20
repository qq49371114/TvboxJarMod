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
import shutil

current_path = os.path.dirname(os.path.abspath(__file__))
conf_path = os.path.join(current_path, 'conf')
jar_dir_path = os.path.join(current_path, 'jar')
jar_official_dir_path = os.path.join(current_path, 'jar_official')
source_name_list = ["肥猫", "饭太硬"]
index_url = "https://xn--sss604efuw.top/"
mod_repo_host = 'https://raw.kkgithub.com/samisold/TvboxJarMod/main/jar/'
mod_repo_cn_host = 'https://samisold.lanzn.com/'
# 蓝奏网盘jar包共享文件夹
lanzou_dir_url = 'https://samisold.lanzn.com/b0covfueh'
lanzou_dir_password = 'teng'
source_name_list = ["肥猫", "饭太硬"]
multiple_json_file = os.path.join(current_path, 'multiple_source_tvbox.json')
print(current_path)

# 输入http://like.xn--z7x900a.live:66/jar/PandaQ231205.jar;md5;9cc29f6286b2fe7910628852929c4bdb
# 返回值: [http://like.xn--z7x900a.live:66/, PandaQ231205.jar, 9cc29f6286b2fe7910628852929c4bdb]
def deconstruct_jar_url(jar_url):
    jar_host = ''
    jar_name = ''
    jar_url_md5 = ''
    if jar_url.find(";md5;") != -1:
        jar_host = jar_url.split(';md5;')[0]
        jar_url_md5 = jar_url.split(';md5;')[1]
        jar_name = jar_host.split('/')[-1]
        jar_host = jar_host.replace(jar_name, '')
    else:
        jar_name = jar_url.split('/')[-1]
        jar_host = jar_url.replace(jar_name, '')
        jar_url_md5 = ''
    jar_name = jar_name.replace('.txt', '.jar') if jar_name.find('.txt') != -1 else jar_name
    return [jar_host, jar_name, jar_url_md5]

def get_source_name_en(source_name):
    if source_name == '肥猫':
        return 'feimao'
    elif source_name == '饭太硬':
        return 'fan'

 # 返回值: 源数据字典{源网站名: 源地址}
# 参数url: 包含最新源地址的网页，默认为"饭太硬"
def get_multiple_sources_obj(url=index_url):
    # 发送 HTTP GET 请求并获取响应内容
    response = requests.get(url)
    response.encoding = "utf-8"
    # print(response.content)
    # 解析 HTML 内容
    soup = BeautifulSoup(response.text, "html.parser")
    # 查找包含指定文本的 span 标签
    span_tags = soup.find_all(name="span", string=source_name_list)
    # 创建一个空列表来存储结果
    results = {}
    # 遍历 span 标签的父 div 节点
    for span_tag in span_tags:
        parent_div = span_tag.parent
        # 获取父 div 节点中 data-clipboard-text 属性的值
        source_url = parent_div.get("data-clipboard-text")
        source_name = span_tag.get_text()
        # 将结果添加到列表中
        results[source_name] = source_url
    # 打印结果
    print(results)
    return results

# 更新本地多仓源json文件
# 返回值：布尔值，更新是否成功
def  check_and_update_multiple_json_file():
    remote_json = get_multiple_sources_obj()
    try:
        updated = False
        # 加载 JSON 文件
        with open(multiple_json_file, "r", encoding="utf-8") as f:
            local_json = json.load(f)
        # 获取 JSON 对象中的 storeHouse 属性下的数组对象
        local_json_sources = local_json["storeHouse"]
        # 遍历数组对象
        for local_json_source in local_json_sources:
            # 获取 sourceName 属性的值
            local_json_source_name = local_json_source["sourceName"]
            # 检查 sourceName 是否在网站名字典中
            if local_json_source_name in remote_json.keys():
                # 获取网址字典中对应的网址
                remote_source_url = remote_json[local_json_source_name]
                # 检查 source_url 属性的值是否与网址字典中的网址匹配
                if local_json_source["sourceUrl"] != remote_source_url:
                    # 如果不匹配，则将 sourceUrl 属性的值修改为网址字典中的网址
                    local_json_source["sourceUrl"] = remote_source_url
                    updated = True
                    print(f'{local_json_source_name} 更新成功')
        if updated:
            # 将修改后的 JSON 对象保存到文件中
            with open(multiple_json_file, "w", encoding="utf-8") as f:
                json.dump(local_json, f, indent=4, ensure_ascii=False)
                print('多仓源json文件更新成功')
        else:
            print('多仓源json已最新, 无需更新')
        return updated
    except Exception as e:
        traceback.print_exc()
        print('更新多仓源json文件失败')
        return False

# 更新官方源json, -mod.json 文件
# 返回值：布尔值，更新是否成功
def  check_and_update_json_files():
    multiple_source_json = None
    updated_json_files = []
    jumped_json_files = []
    # 读取本地多仓源json文件
    if not os.path.exists(multiple_json_file):
        print('多仓源json文件不存在')
        return False
    try:
        with open(multiple_json_file, "r", encoding="utf-8") as f:
            multiple_source_json = json.load(f)
    except Exception as e:
        traceback.print_exc()
        print('多仓源json文件读取失败')
        return False
    if multiple_source_json['storeHouse'] is None:
        print('多仓源json文件内容为空')
        return False
    # 发送请求, 获取json文件, 解析json文件获取md5值，存入json_md5_dict
    for source in multiple_source_json["storeHouse"]:
        source_name = source["sourceName"]
        source_url = source["sourceUrl"]
        # 设置UA字符串
        user_agent = 'Okhttp/3.11.0'
        # 创建一个Session对象，以便可以保持UA设置
        session = requests.Session()
        session.headers.update({'User-Agent': user_agent})
        # 使用session对象发起请求，它会带上我们设置的UA
        response = session.get(source_url)
        response.encoding = 'utf-8'
        data = response.text
        json_file_name = f'{get_source_name_en(source_name)}.json'
        json_file_path = os.path.join(conf_path, json_file_name)
        # 饭太硬源 解密
        if source_name == '饭太硬':
            # 正则匹配"[A-Za-z0-9]{8}\\*\\*"
            encrypt_code = re.search(r"[A-Za-z0-9]{8}\*\*", data).group()
            data = data[data.index(encrypt_code)+10:-1]
            missing_padding = 4 - len(data) % 4
            if missing_padding:
                data += '='* missing_padding
            data = str(base64.b64decode(data), encoding='utf-8') 
            # 修复解密中的小bug
            data = data.replace('//{','{')
        remote_json_data = json.loads(data, strict=False)
        if os.path.exists(json_file_path):
            try:
                # 检查json文件是否已最新
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    local_json_data = json.load(f)
                if local_json_data == remote_json_data:
                    print(f'{json_file_name} json文件已最新, 无需更新')
                    continue
            except:
                print('本地json文件损坏，开始重新下载')
        with open (json_file_path, 'w', encoding='utf-8') as f:
            json.dump(remote_json_data, f, indent=4, ensure_ascii=False)
            updated_json_files.append(json_file_name)

    # 遍历更新-mod.json文件
    # 读取feimao-mod.json文件，判断文件是否损坏，如果损坏则重建
    for root, dirs, files in os.walk(conf_path):
        for conf_file in files:
            if conf_file.find("-mod.json") == -1:
                continue
            mod_cn_json_file = os.path.join(conf_path, conf_file)
            mod_json_file = os.path.join(conf_path, conf_file.replace('-mod.json', '.json'))
            # 读取json文件
            mod_cn_jar_name = ''
            with open (mod_json_file, 'r', encoding='utf-8') as f:
                mod_json_obj = json.load(f)
            try:
                with open (mod_cn_json_file, 'r', encoding='utf-8') as f:
                    json_obj = json.load(f)
                    spider = json_obj['spider']
                    json_jar_host, mod_cn_jar_name, json_jar_md5 = deconstruct_jar_url(spider)
            except:
                # 文件损坏，重建
                print(f'{mod_cn_json_file} 文件损坏，开始重建')
            if mod_cn_jar_name != '':
                mod_spider = mod_json_obj['spider']
                mod_jar_host, mod_jar_name, mod_jar_md5 = deconstruct_jar_url(mod_spider)
                if mod_cn_jar_name == mod_jar_name:
                    print(f'{mod_cn_json_file} 文件已最新, 无需更新')
                    continue
            if os.path.exists(mod_cn_json_file):
                os.remove(mod_cn_json_file)
            shutil.copy2(mod_json_file, mod_cn_json_file)
            with open(mod_cn_json_file, 'w', encoding='utf-8') as f:
                json_obj = mod_json_obj
                json_jar_host, mod_cn_jar_name, json_jar_md5 = deconstruct_jar_url(json_obj['spider'])
                json_obj['spider'] = mod_repo_host + mod_cn_jar_name
                sites = json_obj['sites']
                for site in sites:
                    if site.get("jar") and site['jar'].find(".jar") != -1:
                        jar_host, jar_name, jar_md5 = deconstruct_jar_url(site['jar'])
                        site['jar'] = mod_repo_cn_host + jar_name
                json.dump(json_obj, f, indent=4, ensure_ascii=False)
                updated_json_files.append(conf_file)
    all_json_files = os.listdir(conf_path)
    print(all_json_files)
    print(f'{len(updated_json_files)} json文件更新成功：{updated_json_files}')
    print(f'{len(all_json_files)} 跳过更新：{set(all_json_files)-set(updated_json_files)}')

# 更新conf目录下的mod.json和mod-cn.json文件
def update_json_md5():
    # 遍历jar文件夹，获取jar文件md5值，存入jar_md5_dict
    jar_md5_dict = {}
    for root, dirs, files in os.walk(jar_dir_path):
        for jar_file in files:
            jar_md5 = ''
            jar_path = os.path.join(jar_dir_path, jar_file)
            with open(jar_path, 'rb') as f:
                jar_md5 = hashlib.md5(f.read()).hexdigest()
            jar_md5_dict[jar_file] = {}
            jar_md5_dict[jar_file]['md5'] = jar_md5
            jar_md5_dict[jar_file]['path'] = jar_path
    # 读取conf下mod.json文件
    for root, dirs, json_files in os.walk(conf_path):
        for json_file in json_files:
            # 定位mod.json
            if json_file.find('mod.json') == -1 and json_file.find('mod-cn.json') == -1:
                continue
            mod_json_path = os.path.join(conf_path, json_file)
            json_updated = False
            with open(mod_json_path, 'r', encoding='utf-8') as f:
                mod_json_obj = json.load(f)
                # 获取spider中的jar包网址和md5
                json_jar_host, jar_file_name, json_jar_md5 = deconstruct_jar_url(mod_json_obj['spider'])
                if jar_file_name in jar_md5_dict:
                    spider = mod_json_obj['spider']
                    jar_host, jar_file_name, jar_md5 = deconstruct_jar_url(spider)
                    if jar_md5 != jar_md5_dict[jar_file_name]['md5']:
                        mod_json_obj['spider'] = jar_host + jar_file_name + ';md5;' + jar_md5_dict[jar_file_name]['md5']
                        json_updated = True
                # 获取sites中的jar包网址和md5
                sites = mod_json_obj['sites']
                for site in sites:
                    if site.get("jar"):
                        json_jar_host, jar_file_name, json_jar_md5 = deconstruct_jar_url(site["jar"])
                        if jar_file_name in jar_md5_dict:
                            spider = site["jar"]
                            jar_host, jar_file_name, jar_md5 = deconstruct_jar_url(spider)
                            if jar_md5 != jar_md5_dict[jar_file_name]['md5']:
                                site["jar"] = jar_host + jar_file_name + ';md5;' + jar_md5_dict[jar_file_name]['md5']
                                json_updated = True
                if json_updated:
                    with open(mod_json_path, 'w', encoding='utf-8') as f:
                        json.dump(mod_json_obj, f, indent=4, ensure_ascii=False)
                        print(f'{json_file} 更新成功')
                    # 直接复制mod.json到mod-cn.json
                    mod_cn_json_path = mod_json_path.replace('mod.json', 'mod-cn.json')
                    shutil.copy2(mod_json_path, mod_cn_json_path)
                    print(f'{json_file.replace("mod.json", "mod-cn.json")} 已重新创建')
                else:
                    print(f'{json_file} md5已经是最新, 无需更新')
                   

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
    # 读取conf下官方json文件，读取md5，url，filename存入json_md5_dict
    json_md5_dict = {}
    for root, dirs, files in os.walk(conf_path):
        for file in files:
            # 定位官方json
            if file.find('mod') == -1:
                json_path = os.path.join(conf_path, file)
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_obj = json.load(f)
                    # 获取spider中的jar包网址和md5
                    spider = json_obj['spider']
                    json_jar_host, json_jar_name, json_jar_md5 = deconstruct_jar_url(spider)
                    if json_jar_name not in json_md5_dict:
                        json_md5_dict[json_jar_name] = {}
                        json_md5_dict[json_jar_name]['md5'] = json_jar_md5
                        json_md5_dict[json_jar_name]['url'] = json_jar_host + json_jar_name
                    # 获取sites中的jar包网址和md5
                    sites = json_obj['sites']
                    for site in sites:
                        if site.get("jar") and site["jar"].find(".jar") != -1:
                            json_jar_host, json_jar_name, json_jar_md5 = deconstruct_jar_url(site["jar"])
                            if json_jar_name not in json_md5_dict:
                                json_md5_dict[json_jar_name] = {}
                                json_md5_dict[json_jar_name]['md5'] = json_jar_md5
                                json_md5_dict[json_jar_name]['url'] = json_jar_host + json_jar_name
    # 遍历jar文件夹，获取jar文件md5值，存入jar_md5_dict
    jar_md5_dict = {}
    for root, dirs, files in os.walk(jar_official_dir_path):
        for jar_file in files:
            jar_md5 = ''
            jar_path = os.path.join(jar_official_dir_path, jar_file)
            with open(jar_path, 'rb') as f:
                jar_md5 = hashlib.md5(f.read()).hexdigest()
            jar_md5_dict[jar_file] = {}
            jar_md5_dict[jar_file]['md5'] = jar_md5
            jar_md5_dict[jar_file]['path'] = jar_path
    # 如果获取的json不为空
    if len(json_md5_dict) > 0:
        expired_jars = set(jar_md5_dict.keys()) - set(json_md5_dict.keys())
        for expired_jar in expired_jars:
            expired_jar_path = os.path.join(jar_official_dir_path, expired_jar)
            os.remove(expired_jar_path)
            print(expired_jar, 'jar已经过期, 删除')
        for jar_file, json_obj in json_md5_dict.items():
            jar_md5_matched = None
            # json中的jar包名与本地jar包名匹配
            if jar_md5_dict.get(jar_file):
                jar_md5_matched = jar_md5_dict[jar_file]['md5']
                jar_path_matched = jar_md5_dict[jar_file]['path']
                json_md5_matched = json_obj['md5']
                if jar_md5_matched.lower() == json_md5_matched.lower():
                    print(jar_file ,'jar已经是最新')
                    continue
            else:
                jar_path_matched = os.path.join(jar_official_dir_path, jar_file)
                print(jar_file, 'jar包不存在, 准备下载')
            json_jar_matched = json_obj['url']
            # 设置UA字符串
            user_agent = 'Okhttp/3.11.0'
            # 创建一个Session对象，以便可以保持UA设置
            session = requests.Session()
            session.headers.update({'User-Agent': user_agent})
            response = session.get(json_jar_matched)
            try:
                with open(jar_path_matched, 'wb') as f:
                    f.write(response.content)
                    print(jar_file ,'更新jar成功')
                    return True
            except Exception as e:
                print(type(e), e)
                traceback.print_exc()
                return False

# 爬取蓝奏文件夹共享页面，获取jar包网址，并更新mod-cn.json配置文件
def update_lanzou_json():
    # 爬虫获取jar包分享网址
     # 设置UA字符串
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
    # 创建一个Session对象，以便可以保持UA设置
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    # 使用session对象发起请求，它会带上我们设置的UA
    response = session.get(lanzou_dir_url)
    response_text = response.text
    data = { 
        'lx':'2',
        'fid':'9565547',
        'uid':'821760',
        'pg':'1',
        'rep':'0',
        't':'iblro9',
        'k':'_hk3q2',
        'up':'1',
        'ls':'1',
        'pwd':'pwd'
        }
    # 正则获取var iblro9 = '1708316234'
    url_pattern = re.compile(r"url\s?:\s?'(.*?)'")
    fid_pattern = re.compile(r"'fid'\:(.*?)\,")
    uid_pattern = re.compile(r"'uid'\:(.*?)\,")
    t_pattern = re.compile(r'var\s?.*?\s?=\s?\'(\d+)\'')
    k_pattern = re.compile(r'var\s?.*?\s?=\s?\'([a-z0-9]{32})\'')
    fid = fid_pattern.findall(response_text)[0]
    uid = uid_pattern.findall(response_text)[0]
    url = url_pattern.findall(response_text)[0]
    host = lanzou_dir_url.split('/')[-1]
    host = lanzou_dir_url.replace(host, '')
    post_url = host + url
    t = t_pattern.findall(response_text)[0]
    k = k_pattern.findall(response_text)[0]
    data['pwd'] = lanzou_dir_password
    data['t'] = t
    data['k'] = k
    data['fid'] = fid
    data['uid'] = uid
    # print(data)
    response = session.post(url=post_url, data=data)
    host = response.url.replace(url, '')
    data = json.loads(response.text)['text']
    jar_id_dict ={}
    for i in data:
        jar_id_dict[i['name_all']] = i['id']

    # 存放jar包名：蓝奏id，完整网址
    json_id_dict = {}
    # 读mod.json获取jar包名
    for root, dirs, conf_files in os.walk(conf_path):
        for conf_file in conf_files:
            # 从mod.json中读取jar包名字
            if conf_file.find('mod.json') != -1:
                mod_cn_json_file = conf_file.replace('mod.json', 'mod-cn.json')
                mod_cn_json_path = os.path.join(conf_path, mod_cn_json_file)
                with open(os.path.join(conf_path, conf_file), 'r', encoding='utf-8') as f:
                    mod_json_obj = json.load(f)
                    mod_jar_host, mod_jar_name, mod_jar_md5 = deconstruct_jar_url(mod_json_obj['spider'])
                    if jar_id_dict.get(mod_jar_name):
                        mod_json_obj['spider'] = host + jar_id_dict[mod_jar_name] + ';md5;' + mod_jar_md5
                        sites = mod_json_obj['sites']
                        for site in sites:
                            if site.get('jar') and site['jar'].find('.jar') != -1:
                                site_jar_host, site_jar_name, site_jar_md5 = deconstruct_jar_url(site['jar'])
                                site['jar'] = host + jar_id_dict[site_jar_name] + ';md5;' + site_jar_md5
                    else:
                        print(f'蓝奏云文件夹分享未找到{mod_jar_name}, 请更新jar包')
                        continue
                with open(os.path.join(conf_path, mod_cn_json_path), 'r', encoding='utf-8') as f:
                    mod_cn_json_obj = json.load(f)
                    mod_cn_jar_host, mod_cn_jar_id, mod_cn_jar_md5 = deconstruct_jar_url(mod_cn_json_obj['spider'])
                # md5值不同，直接覆盖mod-cn.json
                if mod_jar_md5 != mod_cn_jar_md5:
                    shutil.copy2(os.path.join(conf_path, conf_file), mod_cn_json_path)
                    print(f'md5值不同, 直接覆盖{mod_cn_json_file}')
                if mod_cn_jar_id == jar_id_dict.get(mod_jar_name):
                    print(f'{mod_cn_json_file} 无需更新，已跳过')
                    continue
                with open(mod_cn_json_path, 'w', encoding='utf-8') as f:
                    json.dump(mod_json_obj, f, ensure_ascii=False, indent=4)
                    print(f'{mod_cn_json_file} 更新成功')


if __name__ == '__main__':
    # 1. 更新多仓源json
    check_and_update_multiple_json_file()
    # 2. 更新官方源json, -mod.json文件
    check_and_update_json_files()
    # 3. 更新官方源jar包
    update_jar_official()
    # 4. 更新json中的md5
    update_json_md5()
    # 5. 更新-mod-cn.json蓝奏云地址
    update_lanzou_json()
    # git_push(current_path)