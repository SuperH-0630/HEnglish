from core.db import WordDatabase
from werkzeug.security import generate_password_hash, check_password_hash
import os
from configure import conf
from flask_login import UserMixin, AnonymousUserMixin
import shutil
from typing import Optional, Tuple


class AnonymousUser(AnonymousUserMixin):
    ...


class UserWordDataBase(WordDatabase, UserMixin):
    def __init__(self, user: str, path: str):
        super().__init__(user, path)
        self.done(f'''
                CREATE TABLE IF NOT EXISTS User (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 记录ID
                    passwd TEXT NOT NULL  -- 密码hash
                )''')
        if self.search(columns=["COUNT(ID)"], table="User")[0][0] == 0:
            self.insert(table="User", columns=["passwd"], values=f"'{generate_password_hash('88888888')}'")  # 默认密码
        self.user = user

    def get_id(self):
        return self.user

    def check_passwd(self, passwd: str) -> bool:
        res = self.search(table="User", columns=["passwd"], limit=1, order_by=[("ID", "ASC")])
        if len(res) == 0:
            return False
        return check_password_hash(res[0][0], passwd)

    def set_passwd(self, passwd: str, record_id: int = 1):
        self.update(table="User", kw={"passwd": f"'{generate_password_hash(passwd)}'"}, where=f"id={record_id}")

    def delete_user(self):
        self.delete_self()

    def get_box_count(self) -> Tuple[list, int]:
        res = self.search(columns=["COUNT(id)", "box"], table="Word", group_by=["box"])
        ret = [0, 0, 0, 0, 0]
        for i in res:
            ret[i[1] - 1] = i[0]
        return ret, sum(ret)

    def reset(self):
        self.update(table="Word", kw={"box": "1"}, where="1")


def check_base_db():
    if os.path.exists(os.path.join(conf["DB_TEMPLATE"], "base.db")):
        return
    WordDatabase("base", conf["DB_TEMPLATE"])


def check_template(template: str) -> bool:
    check_base_db()
    return os.path.exists(os.path.join(conf["DB_TEMPLATE"], f"{template}.db"))


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


def load_user(name: str, passwd: Optional[str]):
    if not os.path.exists(os.path.join(conf["DB_PATH"], f"{name}.db")):
        return None
    user = UserWordDataBase(name, conf["DB_PATH"])
    if passwd is None or user.check_passwd(passwd):
        return user
    return None

