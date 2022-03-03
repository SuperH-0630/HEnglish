from flask import Flask, render_template
from flask.logging import default_handler
from flask_login import LoginManager
import configure
from app import home, test, user, word_list
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
            if configure.conf["LOG_FILE_NAME_PID"]:
                log_file_name = os.path.join(configure.conf["LOG_HOME"], f"flask-{os.getpid()}.log")
            else:
                log_file_name = os.path.join(configure.conf["LOG_HOME"], "flask.log")
            handle = logging.handlers.TimedRotatingFileHandler(log_file_name)
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

        func = {"render_template": render_template}
        for i in [400, 401, 403, 404, 405, 408, 410, 413, 414, 423, 500, 501, 502]:
            exec(f"def error_{i}(e):\n"
                 f"\treturn render_template('error.html', error_status={i}, error_info=e)", func)
            self.errorhandler(i)(func[f"error_{i}"])

        self.register_blueprint(home.home, url_prefix="/")
        self.register_blueprint(test.test, url_prefix="/study")
        self.register_blueprint(word_list.word_list, url_prefix="/word")

    def update_config(self):
        self.config.update(configure.conf)
        self.logger.info("Update config")
