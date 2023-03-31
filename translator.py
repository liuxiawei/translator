#! /usr/bin/env python
# -*- coding: utf-8 -*-
#======================================================================
#
# translator.py - 命令行翻译（必应，百度，腾讯翻译君）
#
#
# Created by Liuxiawei 
# Modified from skywind (https://github.com/skywind3000/translator) and qsdrqs (https://github.com/qsdrqs/translator)
# Last Modified: 2023/03/31
#
#======================================================================
from __future__ import print_function, unicode_literals
import sys
import time
import os
import re
import random
import copy
import json
import codecs
import pprint
import threading

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models

#----------------------------------------------------------------------
# 编码兼容
#----------------------------------------------------------------------
if sys.version_info[0] < 3:
    reload(sys)   # noqa: F821
    sys.setdefaultencoding('utf-8')
    # sys.stdout = codecs.getwriter('utf-8')(sys.stdout, 'ignore')
    # sys.stderr = codecs.getwriter('utf-8')(sys.stderr, 'ignore')
else:
    # sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    # sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')
    pass


#----------------------------------------------------------------------
# 语言的别名
#----------------------------------------------------------------------
langmap = {
    "arabic": "ar",
    "bulgarian": "bg",
    "catalan": "ca",
    "chinese": "zh-CN",
    "chinese simplified": "zh-CHS",
    "chinese traditional": "zh-CHT",
    "czech": "cs",
    "danish": "da",	
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "haitian creole": "ht",
    "hebrew": "he",
    "hindi": "hi",
    "hmong daw": "mww",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "klingon": "tlh",
    "klingon (piqad)":"tlh-Qaak",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "malay": "ms",
    "maltese": "mt",
    "norwegian": "no",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "slovak": "sk",
    "slovenian": "sl",
    "spanish": "es",
    "swedish": "sv",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "welsh": "cy"
}


#----------------------------------------------------------------------
# BasicTranslator
#----------------------------------------------------------------------
class BasicTranslator(object):

    def __init__ (self, name, **argv):
        self._name = name
        self._config = {}  
        self._options = argv
        self._session = None
        self._agent = None
        self._load_config(name)
        self._check_proxy()

    def __load_ini (self, ininame, codec = None):
        config = {}
        if not ininame:
            return None
        elif not os.path.exists(ininame):
            return None
        try:
            content = open(ininame, 'rb').read()
        except IOError:
            content = b''
        if content[:3] == b'\xef\xbb\xbf':
            text = content[3:].decode('utf-8')
        elif codec is not None:
            text = content.decode(codec, 'ignore')
        else:
            codec = sys.getdefaultencoding()
            text = None
            for name in [codec, 'gbk', 'utf-8']:
                try:
                    text = content.decode(name)
                    break
                except:
                    pass
            if text is None:
                text = content.decode('utf-8', 'ignore')
        if sys.version_info[0] < 3:
            import StringIO
            import ConfigParser
            sio = StringIO.StringIO(text)
            cp = ConfigParser.ConfigParser()
            cp.readfp(sio)
        else:
            import configparser
            cp = configparser.ConfigParser(interpolation = None)
            cp.read_string(text)
        for sect in cp.sections():
            for key, val in cp.items(sect):
                lowsect, lowkey = sect.lower(), key.lower()
                config.setdefault(lowsect, {})[lowkey] = val
        if 'default' not in config:
            config['default'] = {}
        return config

    def _load_config (self, name):
        self._config = {}
        ininame = os.path.expanduser('~/.config/translator/config.ini')
        config = self.__load_ini(ininame)
        if not config:
            return False
        for section in ('default', name):
            items = config.get(section, {})
            for key in items:
                self._config[key] = items[key]
        return True

    def _check_proxy (self):
        proxy = os.environ.get('all_proxy', None)
        if not proxy:
            return False
        if not isinstance(proxy, str):
            return False
        if 'proxy' not in self._config:
            self._config['proxy'] = proxy.strip()
        return True

    def request (self, url, data = None, post = False, header = None):
        import requests
        if not self._session:
            self._session = requests.Session()
        argv = {}
        if header is not None:
            header = copy.deepcopy(header)
        else:
            header = {}
        if self._agent:
            header['User-Agent'] = self._agent
        argv['headers'] = header
        timeout = self._config.get('timeout', 7)
        proxy = self._config.get('proxy', None)
        if timeout:
            argv['timeout'] = float(timeout)
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
            argv['proxies'] = proxies
        if not post:
            if data is not None:
                argv['params'] = data
        else:
            if data is not None:
                argv['data'] = data
        if not post:
            r = self._session.get(url, **argv)
        else:
            r = self._session.post(url, **argv)
        return r

    def http_get (self, url, data = None, header = None):
        return self.request(url, data, False, header)

    def http_post (self, url, data = None, header = None):
        return self.request(url, data, True, header)

    def url_unquote (self, text, plus = True):
        if sys.version_info[0] < 3:
            import urllib
            if plus:
                return urllib.unquote_plus(text)
            return urllib.unquote(text)
        import urllib.parse
        if plus:
            return urllib.parse.unquote_plus(text)
        return urllib.parse.unquote(text)

    def url_quote (self, text, plus = True):
        if sys.version_info[0] < 3:
            import urllib
            if isinstance(text, unicode):    # noqa: F821
                text = text.encode('utf-8', 'ignore')
            if plus:
                return urllib.quote_plus(text)
            return urlparse.quote(text)   # noqa: F821
        import urllib.parse
        if plus:
            return urllib.parse.quote_plus(text)
        return urllib.parse.quote(text)

    def create_translation (self, sl = None, tl = None, text = None):
        res = {}
        res['engine'] = self._name
        res['sl'] = sl              # 来源语言
        res['tl'] = tl              # 目标语言
        res['text'] = text          # 需要翻译的文本
        res['phonetic'] = None      # 音标
        res['definition'] = None    # 简单释义
        res['explain'] = None       # 分行解释
        return res

    # 翻译结果：需要填充如下字段
    def translate (self, sl, tl, text):
        return self.create_translation(sl, tl, text)

    # 是否是英文
    def check_english (self, text):
        for ch in text:
            if ord(ch) >= 128:
                return False
        return True

    # 猜测语言
    def guess_language (self, sl, tl, text):
        if ((not sl) or sl == 'auto') and ((not tl) or tl == 'auto'):
            if self.check_english(text):
                sl, tl = ('en-US', 'zh-CN')
            else:
                sl, tl = ('zh-CN', 'en-US')
        if sl.lower() in langmap:
            sl = langmap[sl.lower()]
        if tl.lower() in langmap:
            tl = langmap[tl.lower()]
        return sl, tl
    
    def md5sum (self, text):
        import hashlib
        m = hashlib.md5()
        if sys.version_info[0] < 3:
            if isinstance(text, unicode):   # noqa: F821
                text = text.encode('utf-8')
        else:
            if isinstance(text, str):
                text = text.encode('utf-8')
        m.update(text)
        return m.hexdigest()



#----------------------------------------------------------------------
# Bing2: 免费 web 接口，只能查单词
#----------------------------------------------------------------------
class BingDict (BasicTranslator):

    def __init__ (self, **argv):
        super(BingDict, self).__init__('bingdict', **argv)
        self._agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:50.0) Gecko/20100101'
        self._agent += ' Firefox/50.0'
        self._url = 'http://bing.com/dict/SerpHoverTrans'
        self._cnurl = 'http://cn.bing.com/dict/SerpHoverTrans'

    def translate (self, sl, tl, text):
        url = ('zh' in tl) and self._cnurl or self._url
        url = self._cnurl
        url = url + '?q=' + self.url_quote(text)
        headers = {
            # 'Host': 'cn.bing.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        try:
            resp = self.http_get(url, None, headers)
        except:
            print("\nbingdict time out")
            exit(-1)
        if not resp:
            return None
        resp = resp.text
        res = self.create_translation(sl, tl, text)
        res['sl'] = 'auto'
        res['tl'] = 'auto'
        res['text'] = text
        res['phonetic'] = self.get_phonetic(resp)
        res['explain'] = self.get_explain(resp)
        return res

    def get_phonetic (self, html):
        if not html:
            return ''
        m = re.findall(
            r'<span class="ht_attr" lang=".*?">\[(.*?)\] </span>', html)
        if not m:
            return None
        return m[0].strip()

    def get_explain (self, html):
        if not html:
            return []
        m = re.findall(
            r'<span class="ht_pos">(.*?)</span><span class="ht_trs">(.*?)</span>', html)
        expls = []
        for item in m:
            expls.append('%s %s' % item)
        return expls



#----------------------------------------------------------------------
# Baidu Translator
#----------------------------------------------------------------------
class BaiduTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(BaiduTranslator, self).__init__('baidu', **argv)
        if 'apikey' not in self._config:
            sys.stderr.write('error: missing apikey in [baidu] section\n')
            sys.exit()
        if 'secret' not in self._config:
            sys.stderr.write('error: missing secret in [baidu] section\n')
            sys.exit()
        self.apikey = self._config['apikey']
        self.secret = self._config['secret']
        langmap = {
            'zh-cn': 'zh',
            'zh-chs': 'zh',
            'zh-cht': 'cht',
            'en-us': 'en', 
            'en-gb': 'en',
            'ja': 'jp',
        }
        self.langmap = langmap

    def convert_lang (self, lang):
        t = lang.lower()
        if t in self.langmap:
            return self.langmap[t]
        return lang

    def translate (self, sl, tl, text):
        sl, tl = self.guess_language(sl, tl, text)
        req = {}
        req['q'] = text
        req['from'] = self.convert_lang(sl)
        req['to'] = self.convert_lang(tl)
        req['appid'] = self.apikey
        req['salt'] = str(int(time.time() * 1000) + random.randint(0, 10))
        req['sign'] = self.sign(text, req['salt'])
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        try:
            r = self.http_post(url, req)
        except:
            print("\nbaidu time out")
            exit(-1)
        resp = r.json()
        res = {}
        res['text'] = text
        res['sl'] = sl
        res['tl'] = tl
        res['info'] = resp
        res['translation'] = self.render(resp)
        res['html'] = None
        res['xterm'] = None
        #print(res)
        return res

    def sign (self, text, salt):
        t = self.apikey + text + salt + self.secret
        return self.md5sum(t)

    def render (self, resp):
        output = ''
        try:
            result = resp['trans_result']
        except:
            result=[]
        for item in result:
            #output += '' + item['src'] + '\n'
            output += ' * ' + item['dst'] + '\n'
        return output
    
    
#----------------------------------------------------------------------
# Tecent Translator
#----------------------------------------------------------------------
class TecentTranslator (BasicTranslator):
    def __init__ (self, **argv):
        super(TecentTranslator, self).__init__('tecent', **argv)
        #print(self._config)
        if 'secretid' not in self._config:
            sys.stderr.write('error: missing SecretId in [tecent] section\n')
            sys.exit()
        if 'secretkey' not in self._config:
            sys.stderr.write('error: missing SecretKey in [tecent] section\n')
            sys.exit()
        self.SecretId = self._config['secretid']
        self.SecretKey = self._config['secretkey']
        langmap = {
            'zh-cn': 'zh',
            'zh-chs': 'zh',
            'zh-cht': 'cht',
            'en-us': 'en', 
            'en-gb': 'en',
            'ja': 'jp',
        }
        self.langmap = langmap

    def convert_lang (self, lang):
        t = lang.lower()
        if t in self.langmap:
            return self.langmap[t]
        return lang

    def translate (self, sl, tl, text):
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"
        sl, tl = self.guess_language(sl, tl, text)
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        cred = credential.Credential(self.SecretId,self.SecretKey)
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = tmt_client.TmtClient(cred, "ap-chengdu", clientProfile)

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.TextTranslateRequest()
        params = {
            "SourceText": text,
            "Source": 'auto',
            "Target": 'zh',
            "ProjectId": 0
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个TextTranslateResponse的实例，与请求对象对应
        resp = client.TextTranslate(req)
        #print(resp)
        # 输出json格式的字符串回包

        res = {}
        res['text'] = text
        res['sl'] = resp.Source
        res['tl'] = resp.Target
        res['info'] = None
        res['translation'] = resp.TargetText
        res['html'] = None
        res['xterm'] = None
        #print(resp.to_json_string())
        return(res)




#----------------------------------------------------------------------
# 分析命令行参数
#----------------------------------------------------------------------
def getopt (argv):
    args = []
    options = {}
    if argv is None:
        argv = sys.argv[1:]
    index = 0
    count = len(argv)
    while index < count:
        arg = argv[index]
        if arg != '':
            head = arg[:1]
            if head != '-':
                break
            if arg == '-':
                break
            name = arg.lstrip('-')
            key, _, val = name.partition('=')
            options[key.strip()] = val.strip()
        index += 1
    while index < count:
        args.append(argv[index])
        index += 1
    return options, args


#----------------------------------------------------------------------
# 引擎注册
#----------------------------------------------------------------------
ENGINES = {
    'baidu': BaiduTranslator,
    'tecent': TecentTranslator,
    #'youdao': YoudaoTranslator,
    'bing': BingDict,
}

#----------------------------------------------------------------------
# 处理输出
#----------------------------------------------------------------------


def print_res(res, text, options):
    if 'json' in options:
        text = json.dumps(res)
        sys.stdout.write(str(text))
        return 0
    if not res:
        return -2
    #if 'text' in res:
        #if res['text']:
            #print(res['text'])
    if 'phonetic' in res:
        if res['phonetic'] and ('phonetic' in options):
            print('[' + res['phonetic'] + ']')
    if 'definition' in res:
        if res['definition']:
            print(res['definition'])
    if 'explain' in res:
        if res['explain']:
            print('\n'.join(res['explain']))
    elif 'translation' in res:
        if res['translation']:
            print(res['translation'])
    if 'alternative' in res:
        if res['alternative']:
            print('\n'.join(res['alternative']))


#----------------------------------------------------------------------
# 多线程翻译
#----------------------------------------------------------------------
class TransThread(threading.Thread):
    def __init__(self, sl, tl, text, engine, options):
        super().__init__()
        self.sl = sl
        self.tl = tl
        self.text = text
        self.engine = engine
        self.options = options

    def run(self):
        translator = self.engine()
        res = translator.translate(self.sl, self.tl, self.text)
        print("----------------------------------------------------------------------")
        print(self.engine.__name__)
        print("----------------------------------------------------------------------")
        print_res(res, self.text.strip(), self.options)


#----------------------------------------------------------------------
# 主程序
#----------------------------------------------------------------------
def main(argv = None):
    if argv is None:
        argv = sys.argv
    argv = [ n for n in argv ]
    options, args = getopt(argv[1:])
    engine = options.get('engine')
    if not engine:
        engine = 'all'
    sl = options.get('from') #selected Language
    if not sl:
        sl = 'auto'
    tl = options.get('to') #translate to Language
    if not tl:
        tl = 'auto'
    if not args:
        msg = 'usage: translator.py {--engine=xx} {--from=xx} {--to=xx}'
        print(msg + ' {-json} text')
        print('engines:', list(ENGINES.keys()))
        return 0
    text = ' '.join(args)
    if engine == 'all':
        #print(">"+text+"\n")
        for engines in ENGINES.values():
            thread = TransThread(sl, tl, text, engines, options)
            thread.start()
        return 0
    cls = ENGINES.get(engine)
    if not cls:
        print('bad engine name: ' + engine)
        return -1
    translator = cls()
    res = translator.translate(sl, tl, text)
    print_res(res,text,options)
    return 0


#----------------------------------------------------------------------
# testing suit
#----------------------------------------------------------------------
if __name__ == '__main__':
    main()
