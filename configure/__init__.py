import json
import os

root = os.path.abspath(os.path.join(__file__, '..', '..'))
conf = {
    "SECRET_KEY": "HEnglish",
    "TITLE": "HEnglish :D",
    "FOOTER": "Power by HEnglish",
    "ABOUT": "An useful English learning website for personal.",
    "DB_TEMPLATE": f"{os.path.join(root, 'resource', 'template')}",
    "DB_PATH": f"{os.path.join(root, 'var', 'db')}",
    "LOG_HOME": f"{os.path.join(root, 'var', 'log')}",
    "LOG_STDERR": True,
    "LOG_LEVEL": "DEBUG",
    "SERVER_NAME": None,
    "MAX_CONTENT_LENGTH": 5 * 1024 * 1024,  # Flask 文件上传最大大小
    "LOG_FILE_NAME_PID": False,
    "INVITE_URL": "12345678",
    "ALIYUN_KEY": "",
    "ALIYUN_SECRET": "",
    "TLS_URL": "",
    "TLS_APPID": ""
}


def configure(file_path: str, encoding: str = "utf-8"):
    with open(file_path, mode="r", encoding=encoding) as f:
        json_str = f.read()
        _conf: dict = json.loads(json_str)
        conf.update(_conf)

    os.makedirs(conf["DB_TEMPLATE"], exist_ok=True)
    os.makedirs(conf["DB_PATH"], exist_ok=True)
    os.makedirs(conf["LOG_HOME"], exist_ok=True)
