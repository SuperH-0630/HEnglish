"""
文件名: word.py
通过检索网络词典获得一个词语的中文翻译
使用requests生成一个网络请求
使用bs4解析网页
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict


class WordDict:
    __data_set_search = "english-chinese-simplified"
    __url = f"https://dictionary.cambridge.org/zhs/%E6%90%9C%E7%B4%A2/direct/?datasetsearch={__data_set_search}"

    def __init__(self, user_agent: Optional[str] = None, proxies: Optional[dict] = None):
        if user_agent is None:
            user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) "
                          "Chrome/17.0.963.56 Safari/535.11 ")

        if proxies is None:
            proxies = {'http': "http://localhost:8889", 'https': "http://localhost:8889"}  # 不走系统代理

        self.headers = {"User-Agent": user_agent}  # 配置请求头
        self.proxies = proxies

    def set_headers(self, headers: dict):
        self.headers.update(headers)

    def set_proxies(self, proxies: dict):
        self.proxies.update(proxies)

    def get_requests(self, q: str) -> "Response":
        response = requests.get(self.__url,
                                params={"q": q},
                                headers=self.headers,
                                proxies=self.proxies)
        return Response(response)


class Response:
    def __init__(self, response: requests.Response):
        self._res = response
        self._soup = None
        if self._res.status_code != 200:
            return

        self._soup = BeautifulSoup(self._res.text, "html.parser")
        self.di_body = self._soup.find(name="div", attrs={"class": "di-body"})
        if self.di_body is None:
            self._soup = None
            return

        self.entry = [(i, 1) for i in self.di_body.findAll(name="div", attrs={"class": "pr entry-body__el"})]
        self.entry += [(i, 2) for i in self.di_body.findAll(name="div", attrs={"class": "pv-block"})]
        if len(self.entry) == 0:
            self._soup = None
            return

        self.res: Dict[str: Word] = {}
        for i, f in self.entry:
            name = i.find(name="div", attrs={"class": "di-title"})
            if name is None:
                continue
            if f == 1:
                name_string = str(name.span.span.text)
                part = i.find(name="div", attrs={"class": "posgram dpos-g hdib lmr-5"})
                if part is None:
                    part_string = "unknown"
                else:
                    part_string = str(part.span.text)
            else:
                name_string = str(name.h2.b.text)
                part = i.find(name="div", attrs={"class": "pos dpos"})
                if part is None:
                    part_string = "unknown"
                else:
                    part_string = str(part.span.text)

            word = self.res.get(name_string)
            if word is None:
                word = Word(name_string)
                self.res[name_string] = word

            h = i.find(name="div", attrs={"class": "ddef_h"})
            if h is None:
                continue
            english = str(h.div.text)

            b = i.find(name="div", attrs={"class": "def-body ddef_b"})
            if b is None:
                continue
            chinese = str(b.span.text)

            comment = Word.Comment(part_string, english, chinese)
            eg = b.findAll(name="div", attrs={"class": "examp dexamp"})
            for e in eg:
                es = e.find(name="span", attrs={"class": "eg deg"})
                cs = e.find(name="span", attrs={"class": "trans dtrans dtrans-se hdb break-cj"})
                if es is None:
                    continue
                es = str(es.text).replace("##", " ").replace("@@", " ")
                if cs is not None:
                    cs = str(cs.text).replace("##", " ").replace("@@", " ")
                else:
                    cs = ""
                comment.add_eg(f"{es}##{cs}")
            word.add_comment(comment)
        if len(self.res) == 0:
            self._soup = None

    @property
    def is_find(self):
        return self._soup is not None


class Word:
    class Comment:
        def __init__(self, part: str, english: str, chinese: str):
            self.part = part   # 词性
            self.english = english
            self.chinese = chinese
            self.eg = []

        def add_eg(self, eg: str):
            self.eg.append(eg)

        def __str__(self):
            return f"{self.part} {self.english} {self.chinese} \neg: {self.eg}"

    def __init__(self, name: str):
        self.name = name
        self.comment: Dict[str: "Word.Comment"] = {}  # 注释

    def add_comment(self, c: Comment):
        if self.comment.get(c.english) is None:
            self.comment[c.english] = c

    def __str__(self):
        ret = f"{self.name}:\n"
        for i in self.comment:
            ret += f'note: {self.comment[i]};\n'
        return ret
