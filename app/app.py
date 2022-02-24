from flask import Flask
from flask.logging import default_handler
from flask_login import LoginManager
import configure
from app import home
from app import test
from app import user
import logging.handlers
import logging
import os
import sys


class HEnglishFlask(Flask):
    def __init__(self, import_name, **kwargs):
        super().__init__(import_name, **kwargs)

        self.logger: logging.Logger
        self.logger.removeHandler(default_handler)
        self.logger.propagate = False
        self.logger.setLevel({"DEBUG": logging.DEBUG,
                              "INFO": logging.INFO,
                              "WARNING": logging.WARNING,
                              "ERROR": logging.ERROR}.get(configure.conf["LOG_LEVEL"], logging.INFO))
        if len(configure.conf["LOG_HOME"]):
            handle = logging.handlers.TimedRotatingFileHandler(
                os.path.join(configure.conf["LOG_HOME"], f"flask-{os.getpid()}.log"))
            handle.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(asctime)s "
                                                  "(%(filename)s:%(lineno)d %(funcName)s) "
                                                  "%(process)d %(thread)d "
                                                  "%(message)s"))
            self.logger.addHandler(handle)
        if configure.conf["LOG_STDERR"]:
            handle = logging.StreamHandler(sys.stderr)
            handle.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(asctime)s "
                                                  "(%(filename)s:%(lineno)d %(funcName)s) "
                                                  "%(process)d %(thread)d "
                                                  "%(message)s"))
            self.logger.addHandler(handle)

        self.update_config()
        self.login_manager = LoginManager()
        self.login_manager.init_app(self)
        self.login_manager.anonymous_user = user.AnonymousUser  # 设置未登录的匿名对象

        @self.context_processor
        def inject_base():
            return {"title": self.config["TITLE"],
                    "about": self.config["ABOUT"]}

        @self.login_manager.user_loader
        def user_loader(name: str):
            return user.load_user(name, None)

        self.register_blueprint(home.home, url_prefix="/")
        self.register_blueprint(test.test, url_prefix="/test")

    def update_config(self):
        self.config.update(configure.conf)
        self.logger.info("Update config")
