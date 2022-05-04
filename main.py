import configure
import os
import logging


env_dict = os.environ
henglish_conf = env_dict.get("HENGLISH_CONF")
if henglish_conf is not None:
    logging.info(f"Configure file {henglish_conf}")
    configure.configure(henglish_conf, encoding="utf-8")


import app as App

app = App.HEnglishFlask(__name__)
