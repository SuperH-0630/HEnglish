from flask import blueprints, render_template, current_app, abort, redirect, url_for, flash, make_response
from flask_login import current_user, login_required
from app.user import UserWordDataBase
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadData


test = blueprints.Blueprint("test", __name__)


@test.route("/")
@login_required
def question():
    user: UserWordDataBase = current_user
    word = user.rand_word()
    if word is None:
        return render_template("not_word.html")
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    word_id = serializer.dumps({"word": word.name})
    return render_template("test.html", word=word, len=len, word_id=word_id)  # 需要使用len函数


@test.route("/right/<string:word_id>")
@login_required
def right(word_id: str):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        word: dict = serializer.loads(word_id, max_age=120)  # 120s内生效
        user: UserWordDataBase = current_user
        user.right_word(word["word"])
    except (BadData, KeyError):
        abort(404)
    return redirect(url_for("test.question"))


@test.route("/wrong/<string:word_id>")
@login_required
def wrong(word_id: str):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        word: dict = serializer.loads(word_id, max_age=120)  # 120s内生效
        user: UserWordDataBase = current_user
        user.wrong_word(word["word"])
    except (BadData, KeyError):
        abort(404)
    return redirect(url_for("test.question"))


@test.route("/delete/<string:word>")
@login_required
def delete(word: str):
    user: UserWordDataBase = current_user
    user.delete_txt(word)
    flash(f"Word '{word}' is deleted.")
    return redirect(url_for("test.question"))


@test.route("/download/<string:word>")
@login_required
def download(word: str):
    user: UserWordDataBase = current_user
    w = user.find_word(word, False)
    if w is None:
        abort(404)
    w_str = f"{w.name}\n"
    for i in w.comment:
        comment = w.comment[i]
        w_str += f"  {comment.part}\n  {comment.english}\n  {comment.chinese}\n"
        for a in comment.eg:
            e, c = a.split("##")
            w_str += f"    {e}\n    {c}\n"
    response = make_response(w_str)
    response.headers["Content-Disposition"] = f"attachment;filename={word}.henglish.txt"
    return response
