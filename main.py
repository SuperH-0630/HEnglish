import configure
import app as App
import os
import logging


env_dict = os.environ
hblog_conf = env_dict.get("HENGLISH_CONF")
if hblog_conf is not None:
    logging.info(f"Configure file {hblog_conf}")
    configure.configure(hblog_conf, encoding="utf-8")


app = App.HEnglishFlask(__name__)
