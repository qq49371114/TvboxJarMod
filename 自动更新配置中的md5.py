"""
遍历jar文件夹获取md5, 写入json配置文件
"""

import json, requests
import hashlib
import os
from git import Repo

# 需更新的json文件名后缀，不含后缀名，如feimao-mod 或feimao-mod-cn
suffix_list = ['-mod', '-mod-cn']
current_path = os.path.dirname(os.path.abspath(__file__))
conf_path = os.path.join(current_path, 'conf')
print(current_path)

# 更新json
def update_json_md5():
    # 遍历所有jar包，获取md5
    for root, dirs, files in os.walk('./jar'):
        for jar_file in files:
            jar_md5 = ''
            json_md5 = ''
            with open('./jar/' + jar_file, 'rb') as f:
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
    repo.git.push()

if __name__ == '__main__':
    update_json_md5()
    git_push('./')