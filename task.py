import hashlib
import shutil
from typing import List
from requests.exceptions import RequestException
from json import JSONDecodeError

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
from abc import ABC, abstractmethod, ABCMeta

import requests
from bs4 import BeautifulSoup


class Config:
    root_path = os.path.dirname(os.path.abspath(__file__))
    conf_path = os.path.join(root_path, 'conf')
    jar_dir_path = os.path.join(root_path, 'jar')
    jar_official_dir_path = os.path.join(root_path, 'jar_official')
    source_name_cn_en_dict = {"饭太硬": "fan", "肥猫": "feimao"}
    index_url = "https://xn--sss604efuw.top/"
    edge_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
    okhttp_user_agent = 'Okhttp/3.11.0'
    # 蓝奏网盘jar包共享文件夹
    lanzou_dir_url = 'https://samisold.lanzn.com/b0covfueh'
    lanzou_dir_password = 'teng'
    multiple_json_file = os.path.join(conf_path, 'multiple_source_tvbox.json')
    default_multiple_json_obj = {
        "storeHouse": [
            {
                "sourceName": "肥猫",
                "sourceUrl": "http://肥猫.live"
            },
            {
                "sourceName": "饭太硬",
                "sourceUrl": "http://www.饭太硬.top/tv/"
            }
        ],
        "ext": {
            "highWeightApi": ["fre", "南瓜", "星奇", "黑狐", "低端", "咕噜"],
            "lowWeightApi": ["官源", "荐片", "少儿", "小学", "初中", "高中", "儿童", "哔哩"],
            "blockApi": ["荐影", "预告", "急救", "小说", "短剧", "体育", "聚短", "球", "MV", "┃飞"],
            "adKeyword": ["广告", "公众号", "饭太硬", "肥猫", "免费分享", "神秘的哥哥"]
        }
    }
    multiple_json_obj_template = {
        "storeHouse": [],
        "ext": {
            "highWeightApi": [],
            "lowWeightApi": [],
            "blockApi": [],
            "adKeyword": []
        }
    }
    mod_json_types = {"MOD": "_mod.json", "MOD_CN": "_mod_cn.json"}
    mod_json_hosts = {
        'GITHUB': 'https://raw.kkgithub.com/samisold/TvboxJarMod/main/',
        'GITEE': 'https://gitee.com/samisold/TvboxJarMod/raw/main/',
        'LANZOU': 'https://samisold.lanzn.com/'
    }


class SpiderUrlUtils:
    """
    网址：https://fs-im-kefu.7moor-fs1.com/29397395/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1708249660012/fan.txt;md5;87d5916b7bb5c8acacac5490e802828e
    截取host：https://fs-im-kefu.7moor-fs1.com/29397395/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1708249660012/
    截取md5：87d5916b7bb5c8acacac5490e802828e
    截取file_name:fan.txt
    """

    @staticmethod
    def get_md5(spider_url):
        return spider_url.split(';md5;')[1] if spider_url.find(';md5;') != -1 else ''

    @staticmethod
    def get_file_name(spider_url):
        spider_url_without_md5 = SpiderUrlUtils.get_url_without_md5(spider_url)
        return spider_url_without_md5.split('/')[-1]

    @staticmethod
    def get_host_from(spider_url):
        file_name = SpiderUrlUtils.get_file_name(spider_url)
        return SpiderUrlUtils.get_url_without_md5(spider_url).split(file_name)[0]

    @staticmethod
    def get_url_without_md5(spider_url: str):
        return spider_url.split(';md5;')[0] if spider_url.find(';md5;') != -1 else spider_url


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        # 如果cls不在instances字典中
        if cls not in instances:
            # 将cls作为键，将cls(*args, **kwargs)的返回值作为值存入instances字典
            instances[cls] = cls(*args, **kwargs)
        # 返回instances字典中对应的cls的值
        return instances[cls]

    # 返回get_instance函数
    return get_instance


class Observer(ABC):
    @abstractmethod
    def update(self, subject):
        pass


class Subject(ABC):
    @abstractmethod
    def register_observer(self, observer: Observer):
        pass

    @abstractmethod
    def notify(self):
        pass

    @abstractmethod
    def remove_observer(self, observer: Observer):
        pass


class VodSource:
    def __init__(self, source_name, source_url):
        self.source_name = source_name
        self.source_url = source_url

    def json(self):
        return {
            "sourceName": self.source_name,
            "sourceUrl": self.source_url
        }


class VodExt:
    def __init__(self, high_weight_api: list[str], low_weight_api: list[str], block_api: list[str],
                 ad_keyword: list[str]):
        self.high_weight_api = high_weight_api
        self.low_weight_api = low_weight_api
        self.block_api = block_api
        self.ad_keyword = ad_keyword

    def json(self):
        return {
            "highWeightApi": self.high_weight_api,
            "lowWeightApi": self.low_weight_api,
            "blockApi": self.block_api,
            "adKeyword": self.ad_keyword
        }


class File(ABC):
    def __init__(self, file_path):
        self._file_path = file_path

    @property
    def file_name(self):
        return self._file_path.split(os.sep)[-1]

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, file_path):
        self._file_path = file_path

    @abstractmethod
    def save(self):
        pass


class JarFile(File):

    def save(self):
        pass


class JsonFile(File):
    def __init__(self, file_path):
        super().__init__(file_path)
        self._json_obj = self.load()

    @property
    def json_obj(self) -> dict:
        if not self._json_obj:
            self._json_obj = self.load()
        return self._json_obj

    @json_obj.setter
    def json_obj(self, json_obj: dict):
        self._json_obj = json_obj

    def load(self) -> dict:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"json文件不存在: {self.file_path}")
        except json.decoder.JSONDecodeError:
            print(f"json文件格式错误: {self.file_path}")
        except Exception:
            print(f"json文件保存失败: {self.file_path}")

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_obj, f, indent=4, ensure_ascii=False)
                print(f"json文件保存成功: {self.file_path}")
        except FileNotFoundError:
            print(f"json文件不存在: {self.file_path}")
        except json.decoder.JSONDecodeError:
            print(f"json文件格式错误: {self.file_path}")
        except Exception:
            print(f"json文件保存失败: {self.file_path}")


class OfficialJsonFile(Subject, JsonFile, metaclass=ABCMeta):
    def __init__(self, file_path, json_observers: list[Observer] = None, download_url: str = None):
        super().__init__(file_path)
        if not json_observers:
            self._json_observers = []
        else:
            self._json_observers = json_observers
        self._download_url = download_url

    @property
    def download_url(self):
        return self._download_url

    @download_url.setter
    def download_url(self, download_url: str):
        self._download_url = download_url

    def register_observer(self, observer: Observer | list[Observer]):
        self._json_observers.append(observer)

    def notify(self):
        for json_observer in self._json_observers:
            json_observer.update(self)

    def remove_observer(self, observer: Observer | list[Observer]):
        self._json_observers.remove(observer)


class MultipleJsonFile(JsonFile):
    def __init__(self, file_path, store_house: list[VodSource] = None, ext: VodExt = None):
        super().__init__(file_path)
        json_obj = self.json_obj
        self._store_house = store_house if store_house else [VodSource(source['sourceName'], source['sourceUrl']) for
                                                             source in json_obj["storeHouse"]]
        self._ext = ext if ext else self.json_obj["ext"]

    @property
    def store_house(self):
        return self._store_house

    @store_house.setter
    def store_house(self, store_house: list[VodSource]):
        self._store_house = store_house
        store_house_json = [vod_source.json() for vod_source in store_house]
        temp_json_obj = self.json_obj
        temp_json_obj["storeHouse"] = store_house_json
        self._json_obj = temp_json_obj

    @property
    def ext(self):
        return self._ext

    @ext.setter
    def ext(self, ext: VodExt):
        self._ext = ext
        temp_json_obj = self.json_obj
        temp_json_obj["ext"] = ext.json()
        self._json_obj = temp_json_obj


class SingleJsonFile(JsonFile):
    def __init__(self, file_path, spider: str = None, sites: list[dict] = None, spider_host: str = None):
        super().__init__(file_path)
        self._spider = spider if spider else self._json_obj["spider"]
        self._sites = sites if sites else self._json_obj["sites"]
        self._spider_host = spider_host if spider_host else SpiderUrlUtils.get_host_from(self._json_obj["spider"])
        self._jar_md5_dict = {}
        self._missing_jar_dict = {}

    @property
    def sites(self):
        return self._sites

    @property
    def spider(self):
        return self._spider

    @property
    def spider_host(self):
        return self._spider_host

    @spider_host.setter
    def spider_host(self, spider_host: str):
        self._spider_host = spider_host
        temp_json_obj = self.json_obj
        spider = temp_json_obj["spider"]
        # 饭太硬jar包后缀为.txt， 改为.jar
        spider = spider.replace('.txt', '.jar')
        temp_json_obj["spider"] = spider.replace(SpiderUrlUtils.get_host_from(spider), self._spider_host)
        self.json_obj = temp_json_obj
        self._sites = self.json_obj["sites"]
        for site in self._sites:
            if "jar" in site.keys():
                jar_url = site['jar']
                if jar_url.find('jar') == -1:
                    continue
                site['jar'] = jar_url.replace(SpiderUrlUtils.get_host_from(jar_url), self._spider_host)

    def get_jar_md5(self, jar_file_name):
        jar_file_name = jar_file_name.replace('.txt', '.jar')
        if jar_file_name in self._jar_md5_dict.keys():
            return self._jar_md5_dict.get(jar_file_name)
        jar_dir_path = os.path.dirname(self.file_path).replace('conf', 'jar' if isinstance(self,
                                                                                           ModSingleJsonFile) else 'jar_official')
        jar_file_path = os.path.join(jar_dir_path, jar_file_name)
        if not os.path.exists(jar_file_path):
            print(f"方法：get_jar_md5;  {self.file_name}中的jar文件{jar_file_name}不存在")
            return ''
        with open(jar_file_path, 'rb') as f:
            jar_file_md5 = hashlib.md5(f.read()).hexdigest()
            self._jar_md5_dict[jar_file_name] = jar_file_md5
            return jar_file_md5


@singleton
class OfficialMultipleJsonFile(OfficialJsonFile, MultipleJsonFile):
    def __init__(self, file_path=None, json_observers: list[Observer] = None,
                 download_url: str = Config.index_url,
                 store_house: list[VodSource] = None, ext: VodExt = None, force_update: bool = False):
        file_path = file_path if file_path else Config.multiple_json_file
        MultipleJsonFile.__init__(self, file_path, store_house, ext)
        if not json_observers or json_observers == []:
            json_observers = []
            multiple_mod_json_file = [self.file_path.replace(".json", mod_suffix) for mod_type, mod_suffix in
                                      ModJsonFile.MOD_TYPES.items()]
            json_observers.extend([ModMultipleJsonFile(json_file_path) for json_file_path in multiple_mod_json_file])
            official_json_paths = [self.file_path.replace(self.file_name, f'{source_name}.json') for source_name in
                                   Config.source_name_cn_en_dict.values()]
            json_observers.extend(
                [OfficialSingleJsonFile(json_file_path, force_update=force_update) for json_file_path in
                 official_json_paths])
            self._json_observers = json_observers
        else:
            self._json_observers = json_observers
        self._download_url = download_url
        self._force_update = force_update

    """
    描述：更新多仓源json文件
    force: 是否强制下载更新
    """

    def download(self, force_update: bool = None):
        force_update = force_update if force_update else self._force_update
        # 发送 HTTP GET 请求并获取响应内容
        response = requests.get(self._download_url)
        if response.status_code != 200:
            print(f"请求失败: {Config.index_url, response.status_code}")
            return
        response.encoding = "utf-8"
        # 解析 HTML 内容
        soup = BeautifulSoup(response.text, "html.parser")
        # 查找包含指定文本的 span 标签
        span_tags = soup.find_all(name="span", string=Config.source_name_cn_en_dict.keys())
        if len(span_tags) == 0:
            print(f"{Config.index_url}网页解析失败，未找到指定的span标签")
            return
        # 创建一个空列表来存储结果
        remote_store_house_json = []
        # 遍历 span 标签的父 div 节点
        for span_tag in span_tags:
            parent_div = span_tag.parent
            # 获取父 div 节点中 data-clipboard-text 属性的值
            source_url = parent_div.get("data-clipboard-text")
            source_name = span_tag.get_text()
            source = {"sourceName": source_name, "sourceUrl": source_url}
            remote_store_house_json.append(source)
        local_store_house_json = [source.json() for source in self.store_house]
        # todo:可以修改这里为true，设置为永远更新
        if local_store_house_json != remote_store_house_json or force_update:
            self.store_house = [VodSource(source['sourceName'], source['sourceUrl']) for source in
                                remote_store_house_json]
            self.save()
            self.notify()
        else:
            print("多仓源未发现更新")


class OfficialSingleJsonFile(OfficialJsonFile, SingleJsonFile):
    def __init__(self, file_path, json_observers: List[Observer] = None, download_url: str = None,
                 spider: str = None, sites: List[dict] = None, spider_host: str = None, force_update: bool = False):
        SingleJsonFile.__init__(self, file_path, spider, sites, spider_host)
        if not json_observers or json_observers == []:
            json_file_paths = [self.file_path.replace(".json", mod_suffix) for mod_type, mod_suffix in
                               ModJsonFile.MOD_TYPES.items()]
            json_observers = [ModSingleJsonFile(json_file_path) for json_file_path in json_file_paths]
            self._json_observers = json_observers
        else:
            self._json_observers = [json_observers]
        self._download_url = download_url
        self._force_update = force_update

    def update(self, official_multiple_json_file: OfficialMultipleJsonFile):
        # 发送请求, 获取最新官源json文件, 解析json文件获取md5值，存入json_md5_dict
        session = requests.Session()
        for source in official_multiple_json_file.store_house:
            # 从多仓源json中获取源中文名
            source_name = source.source_name
            # 通过源中文名生成对应官方单仓源json文件名: 肥猫 -> feimao.json
            file_name = f'{Config.source_name_cn_en_dict[source_name]}.json'
            # 比对文件名
            if file_name != self.file_name:
                continue
            source_url = source.source_url
            self._download_url = source_url
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
            try:
                remote_json_data = json.loads(data)
            except JSONDecodeError:
                print(vars(e))
                print(f"无效的json数据: {data}")
                continue
            # 判断官源json是否需要更新；增加强制更新选项
            if self.json_obj != remote_json_data or self._force_update:
                self.json_obj = remote_json_data
                self.sync_jar_files()
                self.save()
                self.notify()

    """
    比对json中的jar和本机jar包，修改md5或更新jar包
    """

    def sync_jar_files(self):
        json_obj = self.json_obj
        spider = json_obj.get('spider')
        spider_url = spider.split(';md5;')[0]
        spider_md5 = SpiderUrlUtils.get_md5(spider)
        spider_jar = SpiderUrlUtils.get_file_name(spider).replace('.txt', '.jar')
        if spider_md5.lower() != self.get_jar_md5(spider_jar).lower():
            self._missing_jar_dict[spider_jar] = spider_url
            self.download_jar(os.path.join(Config.jar_official_dir_path, spider_jar), spider_url)
        for site in self.json_obj.get('sites'):
            if 'jar' in site.keys():
                jar_url = site.get('jar')
                if not jar_url:
                    continue
                # 排除.php类型的接口
                if jar_url.find('.jar') == -1:
                    continue
                jar_file_name = SpiderUrlUtils.get_file_name(jar_url)
                jar_md5_from_json = SpiderUrlUtils.get_md5(jar_url)
                jar_md5 = self.get_jar_md5(jar_file_name)
                if (not jar_md5) or (jar_md5_from_json != jar_md5):
                    self._missing_jar_dict[jar_file_name] = jar_url
                    jar_dir_path = os.path.dirname(self.file_path).replace('conf', 'jar_official')
                    self.download_jar(os.path.join(jar_dir_path, jar_file_name), jar_url)

    def download_jar(self, jar_path, jar_url):
        jar_path = jar_path.replace('.txt', '.jar')
        # 设置UA字符串
        # 创建一个Session对象，以便可以保持UA设置
        session = requests.Session()
        session.headers.update({'User-Agent': Config.okhttp_user_agent})
        response = session.get(jar_url)
        with open(jar_path, 'wb') as f:
            f.write(response.content)
            print(jar_path, '更新jar成功')


class ModJsonFile(Observer, JsonFile, metaclass=ABCMeta):
    MOD_TYPES = Config.mod_json_types
    MOD_JSON_HOSTS = Config.mod_json_hosts

    def __init__(self, file_path, mod_host: str = None):
        super().__init__(file_path)
        self._mod_type = self.mod_type
        self._mod_host = mod_host if mod_host else None

    @property
    def mod_type(self):
        # 获取官源json文件名，不含后缀 fan_mod_cn.json -> fan
        file_name_without_suffix = self.file_name.replace('.json', '').split('_mod')[0]
        mod_suffix = self.file_name.replace(file_name_without_suffix, '')
        mod_types = [k for k, v in self.MOD_TYPES.items() if mod_suffix == v]
        self._mod_type = mod_types.pop() if len(mod_types) > 0 else None
        return self._mod_type

    @property
    def mod_host(self):
        if self._mod_host:
            return self._mod_host
        if self.mod_type == 'MOD_CN' and isinstance(self, ModMultipleJsonFile):
            return self.MOD_JSON_HOSTS.get('GITEE')
        if self.mod_type == 'MOD_CN' and isinstance(self, ModSingleJsonFile):
            return self.MOD_JSON_HOSTS.get('LANZOU')
        if self.mod_type == 'MOD':
            return self.MOD_JSON_HOSTS.get('GITHUB')

    @mod_host.setter
    def mod_host(self, mod_host: str):
        self._mod_host = mod_host


class ModMultipleJsonFile(MultipleJsonFile, ModJsonFile):
    def __init__(self, file_path, store_house: list[VodSource] = None, ext: VodExt = None, mod_host: str = None):
        MultipleJsonFile.__init__(self, file_path, store_house, ext)
        self._mod_type = None
        mod_type = self.mod_type
        self._mod_host = mod_host if mod_host else self.MOD_JSON_HOSTS.get(mod_type)

    def update(self, official_multiple_json_file: OfficialMultipleJsonFile):
        temp_obj = official_multiple_json_file.json_obj
        store_house = temp_obj["storeHouse"]
        for source in store_house:
            source_name = Config.source_name_cn_en_dict[source["sourceName"]]
            # 默认使用mod_cn.json配置
            file_name = source_name + Config.mod_json_types.get('MOD_CN')
            source["sourceUrl"] = self.mod_host + 'conf/' + file_name
        self.json_obj = temp_obj
        self.save()


class ModSingleJsonFile(SingleJsonFile, ModJsonFile):
    lanzou_dir_parsed = False
    jar_id_dict = {}

    def __init__(self, file_path, spider: str = None, sites: list[dict] = None, mod_host: str = None,
                 spider_host: str = None):
        SingleJsonFile.__init__(self, file_path, spider, sites, spider_host)
        self._mod_type = None
        mod_type = self.mod_type
        self._mod_host = mod_host if mod_host else self.mod_host
        if mod_type == 'MOD_CN' and not ModSingleJsonFile.lanzou_dir_parsed:
            self.parse_lanzou_dir()
            ModSingleJsonFile.lanzou_dir_parsed = True

    def update(self, official_single_json_file: OfficialSingleJsonFile):
        self.json_obj = official_single_json_file.json_obj
        if self.mod_type == 'MOD_CN':
            self._spider_host = self.mod_host
            temp_json_obj = self.json_obj
            spider = temp_json_obj["spider"]
            spider_jar_name = SpiderUrlUtils.get_file_name(spider).replace('.txt', '.jar')
            spider_jar_id = spider_jar_name if spider_jar_name.find('.jar') == -1 else self.get_lanzou_id_or_file_name(
                spider_jar_name)
            if not spider_jar_id:
                return
            spider_url = self.mod_host + spider_jar_id
            # 饭太硬jar包后缀为.txt， 改为.jar
            spider = spider.replace('.txt', '.jar')
            temp_json_obj["spider"] = spider.replace(spider.split(';md5;')[0], spider_url)
            self.json_obj = temp_json_obj
            self._sites = self.json_obj["sites"]
            for site in self._sites:
                if "jar" in site.keys():
                    jar_url = site['jar']
                    if not jar_url:
                        continue
                    if jar_url.find('.jar') == -1:
                        continue
                    jar_file_name = SpiderUrlUtils.get_file_name(jar_url).replace('.txt', '.jar')
                    jar_id = jar_file_name if jar_file_name.find('.jar') == -1 else self.get_lanzou_id_or_file_name(
                        jar_file_name)
                    jar_new_url = self.mod_host + jar_id
                    site['jar'] = jar_url.replace(jar_url.split(';md5;')[0], jar_new_url)
        else:
            self.spider_host = self.mod_host + 'jar/'
        self.sync_jar_files()
        self.save()

    """
    比对json中的jar和本机jar包，修改md5或更新jar包
    """

    def sync_jar_files(self):
        json_obj = self.json_obj
        spider = json_obj.get('spider')
        spider_md5 = SpiderUrlUtils.get_md5(spider)
        spider_jar_name = SpiderUrlUtils.get_file_name(spider).replace('.txt', '.jar')
        if self.mod_type == 'MOD_CN':
            spider_jar_name = self.get_lanzou_id_or_file_name(spider_jar_name)
        spider = spider.replace(spider_md5, self.get_jar_md5(spider_jar_name))
        json_obj['spider'] = spider
        for site in self.json_obj.get('sites'):
            if 'jar' in site.keys():
                jar_url = site.get('jar')
                if not jar_url:
                    continue
                if jar_url.find('.jar') == -1:
                    continue
                jar_file_name = SpiderUrlUtils.get_file_name(jar_url)
                jar_md5_from_json = SpiderUrlUtils.get_md5(jar_url)
                jar_md5 = self.get_jar_md5(jar_file_name)
                if not jar_md5:
                    self._missing_jar_dict.update({jar_file_name: jar_url})
                    print(f"方法：sync_jar_files;  {self.file_name}中的jar文件{jar_file_name}不存在")
                    continue
                # 如果jar_url中没有md5，则添加md5
                if jar_md5_from_json == '':
                    site['jar'] = jar_url if jar_md5 == '' else jar_url + ";md5;" + jar_md5
                elif jar_md5_from_json != jar_md5:
                    site['jar'] = jar_url.replace(jar_md5_from_json, jar_md5)
        self.json_obj = json_obj

    def parse_lanzou_dir(self):
        # 爬虫获取jar包分享网址
        # 创建一个Session对象，以便可以保持UA设置
        session = requests.Session()
        session.headers.update({'User-Agent': Config.edge_user_agent})
        # 使用session对象发起请求，它会带上我们设置的UA
        lanzou_dir_url = Config.lanzou_dir_url
        response = session.get(lanzou_dir_url)
        if response.status_code == 200:
            response_text = response.text
            data = {
                'lx': '2',
                'fid': '9565547',
                'uid': '821760',
                'pg': '1',
                'rep': '0',
                't': 'iblro9',
                'k': '_hk3q2',
                'up': '1',
                'ls': '1',
                'pwd': 'pwd'
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
            post_url = host[0:len(host) - 1] + url
            t = t_pattern.findall(response_text)[0]
            k = k_pattern.findall(response_text)[0]
            data['pwd'] = Config.lanzou_dir_password
            data['t'] = t
            data['k'] = k
            data['fid'] = fid
            data['uid'] = uid
            response = session.post(url=post_url, data=data)
            if response.status_code == 200:
                data = json.loads(response.text)['text']
                for item in data:
                    ModSingleJsonFile.jar_id_dict[item['name_all']] = item['id']
            else:
                print(f"post请求失败，状态码：{response.status_code}")
        else:
            print(f"蓝奏分享页请求失败，状态码：{response.status_code}")
        session.close()

    def get_lanzou_id_or_file_name(self, name_or_id):
        # 如果是文件名，则返回id
        if name_or_id in ModSingleJsonFile.jar_id_dict.keys():
            return ModSingleJsonFile.jar_id_dict.get(name_or_id)
        else:
            for file_name in ModSingleJsonFile.jar_id_dict.keys():
                if name_or_id == ModSingleJsonFile.jar_id_dict.get(file_name):
                    return file_name
            # 如果不存在，则返回None
            print(f"方法：get_lanzou_id_or_file_name;  蓝奏云共享文件夹中缺少{name_or_id}jar文件")
            return None


if __name__ == '__main__':
    official_multiple_json_file = OfficialMultipleJsonFile(force_update=True)
    official_multiple_json_file.download()
