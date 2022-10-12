import sqlite3
from typing import Optional, Union, List, Tuple, Dict
import logging
import pandas
from core import word
import re
import os
import random
import configure
import time


class DataBase:
    __logger = logging.getLogger("main.database")
    __logger.setLevel({"DEBUG": logging.DEBUG,
                       "INFO": logging.INFO,
                       "WARNING": logging.WARNING,
                       "ERROR": logging.ERROR}.get(configure.conf["LOG_LEVEL"], logging.INFO))

    def __init__(self, name, path: str = ""):
        self._db_name = os.path.join(path, f"{name}.db")
        self.__logger.info(f"Mark {self._db_name}")

    def delete_self(self):
        os.remove(self._db_name)

    def search(self, sql: str, *args) -> Union[None, List]:
        return self.__search(sql, args)

    def insert(self, sql: str, *args, not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        return self.done(sql, args, not_commit=not_commit)

    def delete(self, sql: str, *args, not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        return self.done(sql, args, not_commit=not_commit)

    def update(self, sql: str, *args, not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        return self.done(sql, args, not_commit=not_commit)

    def __search(self, sql, args) -> Union[None, List]:
        try:
            sqlite = sqlite3.connect(self._db_name)
            cur = sqlite.cursor()
            cur.execute(sql, args)
            ret = cur.fetchall()
        except sqlite3.Error:
            self.__logger.error(f"Sqlite({self._db_name}) SQL {sql} error", exc_info=True)
            return None
        return ret

    def done(self, sql, args=(), not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        sqlite = sqlite3.connect(self._db_name)
        try:
            cur = sqlite.cursor()
            cur.execute(sql, args)
        except sqlite3.Error:
            sqlite.rollback()
            self.__logger.error(f"Sqlite({self._db_name}) SQL {sql} error", exc_info=True)
            return None
        finally:
            if not not_commit:
                sqlite.commit()
        return sqlite, cur


class WordDatabase(DataBase):
    word_pattern = re.compile("([a-zA-Z\']+)")  # 匹配英语单词
    __logger = logging.getLogger("main.database.dict")

    def __init__(self, dict_name, path: str = ""):
        super(WordDatabase, self).__init__(dict_name, path)
        self.dict_name = dict_name
        self.done(f'''
        CREATE TABLE IF NOT EXISTS main.Word (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编码
            box INTEGER NOT NULL DEFAULT 1 CHECK (box < 6 and box > 0),
            word TEXT NOT NULL,  -- 单词
            part TEXT NOT NULL,  -- 词性
            english TEXT NOT NULL,  -- 英文注释
            chinese TEXT NOT NULL,  -- 中文注释
            eg TEXT,  -- 例句
            mp3 TEXT  -- mp3 单词音频
        )''')
        self.wd = word.WordDict()

        http_header = configure.conf.get("HEADER")
        if http_header:
            self.wd.set_headers(http_header)

        http_proxy = configure.conf.get("PROXY")
        if http_header:
            self.wd.set_proxies(http_proxy)

    def __add_word(self, q: str, add: bool):
        """
        访问词典, 添加一个新单词
        :param add: 表示是否添加到数据库
        """
        r = self.wd.get_requests(q)
        if not r.is_find:
            return None
        ret = None
        for i in r.res:
            w = r.res[i]
            if ret is None:
                ret = w
            name = w.name
            mp3 = w.mp3
            name_lower = name.lower()
            res = self.search("SELECT word FROM main.Word WHERE LOWER(word)=?", name_lower)
            if res is not None and len(res) > 0:
                continue
            for c in w.comment:
                comment = r.res[i].comment[c]
                eg = '@@'.join(comment.eg)  # 例句之间使用@@分隔
                part = comment.part
                english = comment.english
                chinese = comment.chinese
                if add:
                    self.insert("INSERT INTO main.Word(word, part, english, chinese, eg, mp3) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                name_lower, part, english, chinese, eg, mp3)
                self.__logger.info(f"Add word name: {name_lower} part: {part}")
        return ret

    @staticmethod
    def __make_word(q: str, res: list):
        """ 将 find_word 获取的SQL数据转换为word对象 """
        w = word.Word(q, res[0][7])
        box = 6
        for i in res:
            c = word.Word.Comment(i[2], i[3], i[4])
            for e in i[5].split("@@"):
                c.add_eg(e)
            w.add_comment(c)
            box = min(i[6], box)
        w.set_box(box)
        return w

    def find_word(self, q: str, search: bool = True, add: bool = True) -> Optional[word.Word]:
        """
        数据库中找单词
        :param q: 单词
        :param search: 是否在字典查找
        :param add: 是否查找后添加到数据库
        :return: 单词
        """
        name_lower = q.lower()
        res = self.search("SELECT id, word, part, english, chinese, eg, box, mp3 "
                          "FROM main.Word "
                          "WHERE LOWER(word)=?", name_lower)
        if res is None or len(res) <= 0:
            if search:
                return self.__add_word(q, add)
            return None
        self.__logger.debug(f"Find word (not add) {q}")
        return self.__make_word(q, res)

    def find_word_by_index(self, index) -> Optional[word.Word]:
        res = self.search("SELECT DISTINCT word "
                          "FROM main.Word "
                          "ORDER BY word "
                          "LIMIT 1 OFFSET ?", index)
        if res is None or len(res) <= 0:
            return None
        return self.find_word(res[0][0], False, False)

    class UpdateResponse:
        """ 记录单词导入(更新)的个数, 和失败的单词 """
        def __init__(self):
            self._success = 0
            self._error = 0
            self._error_list = []

        def add_success(self):
            self._success += 1

        def add_error(self, q: str):
            self._error += 1
            self._error_list.append(q)

        def response(self):
            return self._success, self._error, self._error_list

    def import_txt(self, line: str, sleep: int = 1):
        """ 在字符串中导入单词 """
        response = self.UpdateResponse()
        word_list = self.word_pattern.findall(line)  # 匹配line中的所有英语单词
        for w in word_list:
            time.sleep(sleep)
            try:
                if self.find_word(w, True, True) is None:
                    self.__logger.debug(f"update word {w} fail")
                    response.add_error(w)
                else:
                    self.__logger.debug(f"update word {w} success")
                    response.add_success()
            except Exception as e:
                response.add_error(w)
                self.__logger.debug(f"update word {w} fail", exc_info=True)
        return True, response

    @staticmethod
    def eg_to_str(eg_filed: str, max_eg: int, html: bool = False):
        """ 例句转换成HTML格式或人类可读格式 """
        eg = eg_filed.split("@@")
        eg_str = ""
        count_eg = 0
        for e in eg:
            count_eg += 1
            if max_eg != -1 and count_eg > max_eg:
                break

            ec = e.split("##")
            if len(ec) == 2:
                eng, chi = ec
            else:
                eng = ec[0]
                chi = ""
            if len(eng.replace(" ", "")) == 0:
                continue
            if html:
                eg_str += f"{eng} ({chi})<br>"
            else:
                eg_str += f"{eng} ({chi})\n"
        return eg_str

    def export_frame(self, max_eg: int = 3, html: bool = False) -> Optional[pandas.DataFrame]:
        """ 导出数据库 Pandas DataFrame """
        res = self.search("SELECT box, word, part, english, chinese, eg "
                          "FROM main.Word "
                          "ORDER BY word, box")
        if res is None:
            return None

        df_box = []
        df_word = []
        df_part = []
        df_english = []
        df_chinese = []
        df_eg = []
        for i in res:
            if i[1] in df_word:
                continue
            df_box.append(str(i[0]))
            df_word.append(str(i[1]))
            df_part.append(str(i[2]))
            df_english.append(str(i[3]))
            df_chinese.append(str(i[4]))
            df_eg.append(self.eg_to_str(i[5], max_eg, html))
            self.__logger.debug(f"export word {i[1]}")
        return pandas.DataFrame(data={"Box": df_box,
                                      "Word": df_word,
                                      "Part": df_part,
                                      "English note(s)": df_english,
                                      "Chinese note(s)": df_chinese,
                                      "Example sentence(s)": df_eg})

    def delete_txt(self, line: str):
        count = 0
        word_list = self.word_pattern.findall(line)
        for w in word_list:
            name_lower = w.lower()
            cur = self.delete("DELETE FROM main.Word WHERE LOWER(word)-?", name_lower)
            if cur[1].rowcount != -1:
                self.__logger.debug(f"delete word {w} success")
                count += 1
            else:
                self.__logger.debug(f"delete word {w} fail")
        return count

    def delete_all(self):
        self.__logger.debug(f"delete all word")
        cur = self.delete("DELETE FROM main.Word WHERE true")
        return cur[1].rowcount

    def right_word(self, w: str):
        name_lower = w.lower()
        res = self.search("SELECT MIN(box) FROM main.Word WHERE LOWER(word)=?", name_lower)
        if len(res) == 0:
            return False
        box = res[0][0]
        if box != 5:
            box += 1
            name_lower = w.lower()
            self.update("UPDATE main.Word SET box=? WHERE LOWER(word)=?", box, name_lower)
        return True

    def wrong_word(self, w: str):
        name_lower = w.lower().replace('\'', '\'\'')
        self.update("UPDATE main.Word SET box=1 WHERE LOWER(word)=?", name_lower)
        return True

    def rand_word(self):
        r = random.randint(0, 15)
        if r < 5:
            box = 0  # 5
        elif r < 9:
            box = 1  # 4
        elif r < 12:
            box = 2  # 3
        elif r < 14:
            box = 3  # 2
        else:
            box = 4  # 1
        # box 的概率比分别为：5:4:3:2:1

        first_box = box
        count = self.search("SELECT COUNT(DISTINCT word) FROM main.Word WHERE box=?", box)[0][0]
        while count == 0:
            if box == 4:
                box = 0
            else:
                box += 1

            if box == first_box:
                break
            count = self.search("SELECT COUNT(DISTINCT word) FROM main.Word WHERE box=?", box)[0][0]
        get = self.search("SELECT DISTINCT word FROM main.Word WHERE box=? LIMIT 1 OFFSET ?",
                          box, random.randint(0, count - 1))[0][0]
        self.__logger.debug(f"Rand word {self.dict_name} from box: {box} count: {count} get: {get}")
        return self.find_word(get, False)
