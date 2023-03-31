# Translator

命令行聚合翻译工具，支持必应，百度，腾讯翻译君

## Preface

命令行翻译工具，可单独使用，可集成 Vim/Emacs，也可搭配 GoldenDict

- 可以方便的同 GoldenDict 等工具集成。

## Screenshots

### 命令行

![](images/linux.png)

### GoldenDict

![](images/goldendict.png)

同一个页面内同时集成多个翻译引擎，一次查询所有结果同时显示。

## Requirements

Python 3.5+ 以及 requests 、tencentcloud-sdk-python库：

```bash
pip install requests
pip install --upgrade tencentcloud-sdk-python
```

想要支持代理的话，安装 requests 的 socks 包：

```bash
pip install requests[socks]
```


## Configuration

配置位于 `~/.config/translator/config.ini`，内容类似：

```ini
# 所有翻译引擎共享的公共设置，比如网络超时，代理设置
[default]
timeout = 10


# 必应翻译
[bing]
proxy = socks5://localhost:1080

# 百度翻译：默认实现需要自行申请 apikey/secret
[baidu]
apikey = xxxxx
secret = xxxxx

[tecent]
secretid = XXX
secretkey = XXX


```

Windows 下面的话，该文件位于：

    C:\Users\你的用户名\.config\translator

用记事本打开编辑即可。

## Usage

```bash
translator.py [--engine=引擎名称] [--from=语言] [--to=语言] {文字}
```

### 密钥申请


- 百度：到 [百度翻译开放平台](http://api.fanyi.baidu.com/api/trans/product/index)，申请开通。

- 腾讯翻译君：到 [腾讯翻译君](https://fanyi.qq.com/translateapi)，申请开通。


### 词典集成

要集成 GoldenDict，先在命令行下测试 Python 可以顺利运行该脚本，然后设置你的词典：

![](images/setup.png)

按 F3 打开词典设置，然后点 “程序”，选择 “纯文本”，后面是名字和运行命令,假设你的 Python 安装在 C:\python37 而脚本在 D:\Github\translator，那么命令为：

    C:\python37\python d:\Github\translator\translator.py --engine=azure "%GDWORD%"

注意 `%GDWORD%` 需要用双引号引起来，这样的话词组不会出错。

最后是图标路径（图标请自己下载），你想要同时展示多少个翻译引擎就参考上面，配置多少行 `--engine=` 不同的命令即可。


