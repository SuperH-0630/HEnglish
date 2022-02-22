import json

conf = {
    "SECRET_KET": "HEnglish",
    "TITLE": "HEnglish :D",
    "ABOUT": "An useful English learning website for personal."
}


def configure(file_path: str, encoding: str = "utf-8"):
    with open(file_path, mode="r", encoding=encoding) as f:
        json_str = f.read()
        _conf: dict = json.loads(json_str)
        conf.update(_conf)
