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

    def search(self, columns: List[str], table: str,
               where: Union[str, List[str]] = None,
               limit: Optional[int] = None,
               offset: Optional[int] = None,
               order_by: Optional[List[Tuple[str, str]]] = None,
               group_by: Optional[List[str]] = None,
               for_update: bool = False):
        if type(where) is list and len(where) > 0:
            where: str = " WHERE " + " AND ".join(f"({w})" for w in where)
        elif type(where) is str and len(where) > 0:
            where = " WHERE " + where
        else:
            where: str = ""

        if order_by is None:
            order_by: str = ""
        else:
            by = [f" {i[0]} {i[1]} " for i in order_by]
            order_by: str = " ORDER BY" + ", ".join(by)

        if limit is None or limit == 0:
            limit: str = ""
        else:
            limit = f" LIMIT {limit}"

        if offset is None:
            offset: str = ""
        else:
            offset = f" OFFSET {offset}"

        if group_by is None:
            group_by: str = ""
        else:
            group_by = "GROUP BY " + ", ".join(group_by)

        columns: str = ", ".join(columns)
        if for_update:
            for_update = "FOR UPDATE"
        else:
            for_update = ""
        return self.__search(f"SELECT {columns} "
                             f"FROM {table} "
                             f"{where} {group_by} {order_by} {limit} {offset} {for_update};")

    def insert(self, table: str, columns: list, values: Union[str, List[str]], not_commit: bool = False):
        columns: str = ", ".join(columns)
        if type(values) is str:
            values: str = f"({values})"
        else:
            values: str = ", ".join(f"{v}" for v in values)
        return self.done(f"INSERT INTO {table}({columns}) VALUES {values};", not_commit=not_commit)

    def delete(self, table: str, where: Union[str, List[str]] = None, not_commit: bool = False):
        if type(where) is list and len(where) > 0:
            where: str = " AND ".join(f"({w})" for w in where)
        elif type(where) is not str or len(where) == 0:  # 必须指定条件
            return None

        return self.done(f"DELETE FROM {table} WHERE {where};", not_commit=not_commit)

    def update(self, table: str, kw: "Dict[str:str]", where: Union[str, List[str]] = None,
               not_commit: bool = False):
        if len(kw) == 0:
            return None

        if type(where) is list and len(where) > 0:
            where: str = " AND ".join(f"({w})" for w in where)
        elif type(where) is not str or len(where) == 0:  # 必须指定条件
            return None

        kw_list = [f"{key} = {kw[key]}" for key in kw]
        kw_str = ", ".join(kw_list)
        return self.done(f"UPDATE {table} SET {kw_str} WHERE {where};", not_commit=not_commit)

    def __search(self, sql) -> Union[None, List]:
        try:
            sqlite = sqlite3.connect(self._db_name)
            cur = sqlite.cursor()
            cur.execute(sql)
            ret = cur.fetchall()
        except sqlite3.Error:
            self.__logger.error(f"Sqlite({self._db_name}) SQL {sql} error", exc_info=True)
            return None
        return ret

    def done(self, sql, not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        sqlite = sqlite3.connect(self._db_name)
        try:
            cur = sqlite.cursor()
            cur.execute(sql)
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
        CREATE TABLE IF NOT EXISTS Word (
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

    def __add_word(self, q: str, add: bool):
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
            name_lower = name.lower().replace("'", "''")
            res = self.search(columns=["word"], table="Word", where=f"LOWER(word)='{name_lower}'")
            if res is not None and len(res) > 0:
                continue
            for c in w.comment:
                comment = r.res[i].comment[c]
                eg = '@@'.join(comment.eg).replace("'", "''")
                part = comment.part.replace("'", "''")
                english = comment.english.replace("'", "''")
                chinese = comment.chinese.replace("'", "''")
                if add:
                    self.insert(table='Word',
                                columns=['word', 'part', 'english', 'chinese', 'eg', 'mp3'],
                                values=f"'{name_lower}', '{part}', '{english}', '{chinese}', '{eg}', '{mp3}'")
                self.__logger.info(f"Add word name: {name_lower} part: {part}")
        return ret

    @staticmethod
    def __make_word(q: str, res: list):
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
        name_lower = q.lower().replace("'", "''")
        res = self.search(columns=["id", "word", "part", "english", "chinese", "eg", "box", "mp3"],
                          table="Word",
                          where=f"LOWER(word)='{name_lower}'")
        if res is None or len(res) <= 0:
            if search:
                return self.__add_word(q, add)
            return None
        self.__logger.debug(f"Find word (not add) {q}")
        return self.__make_word(q, res)

    class UpdateResponse:
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
        response = self.UpdateResponse()
        word_list = self.word_pattern.findall(line)
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
        res = self.search(columns=["box", "word", "part", "english", "chinese", "eg"],
                          table="Word",
                          order_by=[("word", "ASC"), ("box", "ASC")])
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
            name_lower = w.lower().replace("'", "''")
            cur = self.delete(table="Word", where=f"LOWER(word)='{name_lower}'")
            if cur[1].rowcount != -1:
                self.__logger.debug(f"delete word {w} success")
                count += 1
            else:
                self.__logger.debug(f"delete word {w} fail")
        return count

    def delete_all(self):
        self.__logger.debug(f"delete all word")
        cur = self.delete(table="Word")
        return cur[1].rowcount

    def right_word(self, w: str):
        name_lower = w.lower().replace("'", "''")
        res = self.search(columns=["MIN(box)"], table="Word", where=f"LOWER(word)='{name_lower}'")
        if len(res) == 0:
            return False
        box = res[0][0]
        if box != 5:
            box += 1
            name_lower = w.lower().replace("'", "''")
            self.update(table="Word", kw={"box": f"{box}"}, where=f"LOWER(word)='{name_lower}'")
        return True

    def wrong_word(self, w: str):
        name_lower = w.lower().replace('\'', '\'\'')
        self.update(table="Word", kw={"box": "1"}, where=f"LOWER(word)='{name_lower}'")
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

        count = 0
        while count == 0:
            if box == 5:
                return None
            box += 1
            count = self.search(columns=["COUNT(DISTINCT word)"], table="Word", where=f"box<={box}")[0][0]
        get = self.search(columns=["DISTINCT word"], table="Word", where=f"box<={box}",
                          limit=1, offset=random.randint(0, count - 1))[0][0]
        self.__logger.debug(f"Rand word {self.dict_name} from box: {box} count: {count} get: {get}")
        return self.find_word(get, False)
