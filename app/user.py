from core.db import WordDatabase
from werkzeug.security import generate_password_hash, check_password_hash
import os
from configure import conf
from flask_login import UserMixin, AnonymousUserMixin
import shutil
from typing import Optional, Tuple
import time


class AnonymousUser(AnonymousUserMixin):
    ...


class UserWordDataBase(WordDatabase, UserMixin):
    def __check(self, key: int, value: str):
        if len(self.search(table="User", columns=["value"], where=f"key={key}")) == 0:
            self.insert(table="User", columns=["key", "value"], values=f"{key}, '{value}'")  # 默认密码

    def __init__(self, user: str, path: str):
        super().__init__(user, path)
        self.done(f'''
                CREATE TABLE IF NOT EXISTS User (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 记录ID
                    key INTEGER UNIQUE NOT NULL,
                    value TEXT NOT NULL  -- 密码hash
                )''')

        self.__check(1, generate_password_hash('88888888'))
        self.__check(2, time.strftime('%Y#%m#%d', time.localtime(time.time())))  # 更新时间
        self.__check(3, '0')  # right
        self.__check(4, '0')  # wrong
        self.__check(5, '')  # wrong

        self.check_time()
        self.user = user

    def get_id(self):
        return self.user

    def set_value(self, key: int, value):
        value = str(value).replace("'", "''")
        self.update(table="User", kw={"value": f"'{value}'"}, where=f"key={key}")

    def get_value(self, key: int, default=None) -> Optional[str]:
        res = self.search(table="User", columns=["value"], where=f"key={key}")
        if len(res) == 0:
            return default
        return res[0][0]

    def check_passwd(self, passwd: str) -> bool:
        res = self.get_value(1)
        if res is None:
            return False
        return check_password_hash(res, passwd)

    def set_passwd(self, passwd: str):
        self.set_value(1, generate_password_hash(passwd))

    def check_time(self):
        now_time = time.strftime('%Y#%m#%d', time.localtime(time.time()))
        if self.get_value(2) != now_time:
            self.set_value(2, now_time)
            self.set_value(3, 0)
            self.set_value(4, 0)
            self.set_value(5, "")

    def rand_word(self):
        w = super(UserWordDataBase, self).rand_word()
        if w is None:
            return None
        self.__add_history_word(w.name)
        return w

    def right_word(self, w: str):
        self.check_time()
        self.set_value(3, int(self.get_value(3, 0)) + 1)
        return super(UserWordDataBase, self).right_word(w)

    def wrong_word(self, w: str):
        self.check_time()
        self.set_value(4, int(self.get_value(4, 0)) + 1)
        return super(UserWordDataBase, self).wrong_word(w)

    def __add_history_word(self, w):
        history = self.get_value(5, "").split(",")
        history.append(w)
        if len(history) > 10:
            history = history[-10:]
        self.set_value(5, ",".join(history))

    def delete_user(self):
        self.delete_self()

    def get_box_count(self) -> Tuple[list, list, int, int]:
        res = self.search(columns=["COUNT(word)", "COUNT(DISTINCT word)", "box"], table="Word", group_by=["box"])
        ret = [0, 0, 0, 0, 0]
        ret_distinct = [0, 0, 0, 0, 0]
        for i in res:
            ret[i[2] - 1] = i[0]
            ret_distinct[i[2] - 1] = i[1]
        return ret, ret_distinct, sum(ret), sum(ret_distinct)

    def get_history_info(self) -> Tuple[int, int, list]:
        self.check_time()
        right = int(self.get_value(3))
        wrong = int(self.get_value(4))
        history = self.get_value(5, "")
        if len(history) == 0:
            history = []
        else:
            history = self.get_value(5, "").split(",")[::-1]
        return right, wrong, history

    def reset(self):
        self.update(table="Word", kw={"box": "1"}, where="1")


def check_base_db():
    if os.path.exists(os.path.join(conf["DB_TEMPLATE"], "base.db")):
        return
    WordDatabase("base", conf["DB_TEMPLATE"])


def check_template(template: str) -> bool:
    check_base_db()
    return os.path.exists(os.path.join(conf["DB_TEMPLATE"], f"{template}.db"))


def get_template():
    check_base_db()
    file_list = os.listdir(conf["DB_TEMPLATE"])
    template = []
    for i in file_list:
        if i.endswith(".db"):
            i = i[:-3]
            template.append((i, i.replace("_", " ")))
    return template


def create_user(template: str, name: str, passwd: str):
    check_base_db()
    if not os.path.exists(os.path.join(conf["DB_TEMPLATE"], f"{template}.db")):
        return 0, None
    if os.path.exists(os.path.join(conf["DB_PATH"], f"{name}.db")):
        return -1, None

    shutil.copy(os.path.join(conf["DB_TEMPLATE"], f"{template}.db"), os.path.join(conf["DB_PATH"], f"{name}.db"))
    user = UserWordDataBase(name, conf["DB_PATH"])
    if len(passwd) > 0:
        user.set_passwd(passwd)
    return 1, user


def have_user(name: str):
    return os.path.exists(os.path.join(conf["DB_PATH"], f"{name}.db"))


def load_user(name: str, passwd: Optional[str]):
    if not os.path.exists(os.path.join(conf["DB_PATH"], f"{name}.db")):
        return None
    user = UserWordDataBase(name, conf["DB_PATH"])
    if passwd is None or user.check_passwd(passwd):
        return user
    return None

