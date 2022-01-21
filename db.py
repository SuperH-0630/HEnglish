import sqlite3
import threading
from typing import Optional, Union, List, Tuple, Dict
import traceback

import pandas
import pandas as pd

import word
import re


class DataBase:
    def __init__(self, name):
        self._db_name = f"{name}.db"

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
            traceback.print_exc()
            print(f"sql='{sql}'")
            return None
        return ret

    def done(self, sql, not_commit: bool = False) -> Union[None, "Tuple[sqlite3, sqlite3.Cursor]"]:
        sqlite = sqlite3.connect(self._db_name)
        try:
            cur = sqlite.cursor()
            cur.execute(sql)
        except sqlite3.Error:
            sqlite.rollback()
            print(f"sql={sql}")
            traceback.print_exc()
            return None
        finally:
            if not not_commit:
                sqlite.commit()
        return sqlite, cur


class WordDatabase(DataBase):
    word_pattern = re.compile("([a-zA-Z\']+)")  # 匹配英语单词

    def __init__(self, dict_name: str = "global"):
        super(WordDatabase, self).__init__(dict_name + "-dict")
        self.dict_name = dict_name
        self.done(f'''
        CREATE TABLE IF NOT EXISTS Word (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编码
            box INTEGER NOT NULL DEFAULT 1 CHECK (box < 6 and box > 0),
            word TEXT NOT NULL,  -- 单词
            part TEXT NOT NULL,  -- 词性
            english TEXT NOT NULL,  -- 英文注释
            chinese TEXT NOT NULL,  -- 中文注释
            eg TEXT  -- 例句
        )''')
        self.wd = word.WordDict()

    def find_word(self, q: str) -> Optional[word.Word]:
        res = self.search(columns=["id", "word", "part", "english", "chinese", "eg"],
                          table="Word",
                          where=f"LOWER(word)='{q.lower()}'")
        if res is None:
            res = []

        if len(res) <= 0:
            r = self.wd.get_requests(q)
            if not r.is_find:
                return None
            ret = None
            for i in r.res:
                w = r.res[i]
                if ret is None:
                    ret = w
                name = w.name
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
                    self.insert(table='Word',
                                columns=['word', 'part', 'english', 'chinese', 'eg'],
                                values=f"'{name_lower}', '{part}', '{english}', '{chinese}', '{eg} '")
            return ret

        w = word.Word(q)
        for i in res:
            c = word.Word.Comment(i[2], i[3], i[4])
            for e in i[5].split("@@"):
                c.add_eg(e)
            w.add_comment(c)
        return w

    def delete_word(self, q: str):
        self.delete(table="Word", where=f"LOWER(word)='{q.lower()}'")

    def delete_all(self):
        self.delete(table="Word")

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
            print(f"Error: {q}")

        def response(self):
            return self._success, self._error, self._error_list

    def update_from_txt(self, file: str):
        response = self.UpdateResponse()
        with open(file, encoding='utf-8') as f:
            for i in f.readlines():
                word_list = self.word_pattern.findall(i)
                for w in word_list:
                    try:
                        if self.find_word(w) is None:
                            response.add_error(w)
                        else:
                            response.add_success()
                    except:
                        response.add_error(w)
                        traceback.print_exc()
        return True, response

    def update_from_table(self, file: str, t: str = 'csv'):
        if t == 'txt':
            return self.update_from_txt(file)
        elif t == 'csv':
            df = pd.read_csv(file, encoding='utf-8')
        elif t == 'excel':
            df = pd.read_excel(file, encoding='utf-8')
        elif t == 'json':
            df = pd.read_json(file, encoding='utf-8')
        else:
            return False, []

        response = self.UpdateResponse()
        for i in df.itertuples():
            try:
                if self.find_word(str(i[0])) is None:
                    response.add_error(str(i[0]))
                else:
                    response.add_success()
            except:
                response.add_error(str(i[0]))
                traceback.print_exc()
        return True, response

    def export_as_txt(self, file: str):
        res = self.search(columns=["word"],
                          table="Word",
                          order_by=[('box', 'DESC')])
        if res is None:
            return False
        export = []
        with open(file + '.txt', encoding='utf-8', mode="w") as f:
            for i in res:
                if i[0] in export:
                    continue
                f.write(i[0] + '\n')
                export.append(i[0])
        return True

    def export_as_table(self, file: str, t: str = 'excel', max_eg: int = 3):
        if t == 'txt':
            return self.export_as_txt(file)

        res = self.search(columns=["box", "word", "part", "english", "chinese", "eg"],
                          table="Word",
                          order_by=[('box', 'DESC')])
        if res is None:
            return False
        df = pandas.DataFrame(columns=["Box", "Word", "Part", "English", "Chinese", "Eg"])
        export = []
        for i in res:
            if i[1] in export:
                continue
            export.append(i[1])
            eg = i[5].split("@@")
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
                eg_str += f"{eng} ({chi})\n"
            df = df.append({"Box": str(i[0]),
                            "Word": str(i[1]),
                            "Part": str(i[2]),
                            "English": str(i[3]),
                            "Chinese": str(i[4]),
                            "Eg": eg_str}, ignore_index=True)
        if t == 'csv':
            df.to_csv(file + ".csv", encoding='utf-8')
        elif t == 'excel':
            df.to_excel(file + ".xlsx", encoding='utf-8')
        elif t == 'json':
            df.to_json(file + ".json", encoding='utf-8')
        else:
            return False


if __name__ == '__main__':
    db = WordDatabase()
    db.export_as_table("resource/English-Word")