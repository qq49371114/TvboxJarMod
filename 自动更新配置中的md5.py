# 读取fan-mod.json文件中的md5值

import json, requests
import hashlib
import os


# 遍历所有jar包，获取md5
for root, dirs, files in os.walk('./jar'):
    for jar_file in files:
        jar_md5 = ''
        json_md5 = ''
        with open('./jar/' + jar_file, 'rb') as f:
            jar_md5 = hashlib.md5(f.read()).hexdigest()
        # 生成json路径
        json_path = jar_file.replace(".jar", "")
        if json_path.lower().startswith('panda'):
            json_path = 'feimao'
        json_path += '-mod'
        json_path = './conf/' + json_path + '.json'
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
        

# 向url发送web请求，并解析成json对象
# response = requests.get(url)
# data = json.loads(response.text)
        


