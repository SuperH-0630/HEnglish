""" 旧版数据库导入为新版数据库 """
""" 新版加入了mp3 """

import sqlite3
from core.aliyun import tls
import traceback

first = sqlite3.connect("high_school.db")
new = sqlite3.connect("high_school.db")

new.execute('''CREATE TABLE IF NOT EXISTS Word (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编码
            box INTEGER NOT NULL DEFAULT 1 CHECK (box < 6 and box > 0),
            word TEXT NOT NULL,  -- 单词
            part TEXT NOT NULL,  -- 词性
            english TEXT NOT NULL,  -- 英文注释
            chinese TEXT NOT NULL,  -- 中文注释
            eg TEXT,  -- 例句
            mp3 TEXT  -- mp3 单词音频
        )''')

res = first.execute("SELECT MIN(ID), MAX(id) FROM main.Word;")
min_id, max_id = res.fetchone()
res.close()


error = []
for word_id in range(min_id, max_id + 1):
    res = first.execute(f"SELECT word, part, english, chinese, eg FROM main.Word WHERE id={word_id};")
    word: "list | None" = res.fetchone()
    res.close()

    if word is None:
        continue

    try:
        word = [i.replace("'", "''") for i in word]
        res = tls.start(word[0])
        if not res.success:
            raise Exception
        values = f"(1, '{word[0]}', '{word[1]}', '{word[2]}', '{word[3]}', '{word[4]}', '{res.mp3}')"
        res = new.execute(f"INSERT INTO main.Word(box, word, part, english, chinese, eg, mp3)  VALUES {values};")
        res.close()
        new.commit()
    except Exception as e:
        print(f"Error: {word[0]} {word_id}")
        error.append((word[0], word_id))
        traceback.print_exception(e)
