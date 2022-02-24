from flask import blueprints, render_template
from flask_login import current_user, login_required
from .user import UserWordDataBase

test = blueprints.Blueprint("test", __name__)


@test.route("/")
@login_required
def question():
    user: UserWordDataBase = current_user
    word = user.rand_word()
    if word is None:
        return render_template("not_word.html")
    return render_template("test.html", word=word, len=len)  # 需要使用len函数
