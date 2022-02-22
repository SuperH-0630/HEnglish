from flask import Flask
import configure
from . import home


class HEnglishFlask(Flask):
    def __init__(self, import_name, **kwargs):
        super().__init__(import_name, **kwargs)
        self.update_config()

        @self.context_processor
        def inject_base():
            return {"title": self.config["TITLE"],
                    "about": self.config["ABOUT"]}

        self.register_blueprint(home.home, url_prefix="/")

    def update_config(self):
        self.config.update(configure.conf)
        self.logger.info("Update config")
