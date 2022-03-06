from flask import blueprints, render_template, current_app, abort, redirect, url_for, flash, make_response, request
from flask import send_file
from flask_login import current_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField, FileField
from wtforms.validators import DataRequired
from app.user import UserWordDataBase
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadData
from threading import Thread
from typing import Optional, List
from core.word import Word
import io

test = blueprints.Blueprint("test", __name__)


class SearchForm(FlaskForm):
    search = StringField("Word", validators=[DataRequired()])
    from_internet = BooleanField("Internet")
    add_to_db = BooleanField("Add")
    submit = SubmitField("Search")


class ResetDeleteForm(FlaskForm):
    name = StringField("User name", validators=[DataRequired()])
    passwd = PasswordField("Passwd", validators=[DataRequired()])
    new_passwd = PasswordField("New passwd")
    submit = SubmitField("Submit")


class UploadFile(FlaskForm):
    file = FileField("File")
    submit = SubmitField("Upload")


def __load_word(word):
    user: UserWordDataBase = current_user
    box, box_distinct, box_sum, box_sum_distinct = user.get_box_count()
    right_count, wrong_count, history = user.get_history_info()
    search_from = SearchForm()
    reset_delete_form = ResetDeleteForm()
    upload_form = UploadFile()
    job: Upload = Upload.upload.get(user.user)
    if Upload.upload.get(user.user) is not None:
        if job.is_alive():
            have_job = True
        else:
            flash("Upload finished")
            have_job = False
            del Upload.upload[user.user]
    else:
        have_job = False

    template_var = dict(word=word, len=len, right_count=right_count, wrong_count=wrong_count, history=history,
                        box=box, box_distinct=box_distinct, box_sum=box_sum, box_sum_distinct=box_sum_distinct,
                        have_job=have_job, search=search_from, reset_delete=reset_delete_form, upload=upload_form)
    if word is None:
        return render_template("test.html", **template_var, have_word=False)
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    word_id = serializer.dumps({"word": word.name})
    return render_template("test.html", **template_var, word_id=word_id, have_word=True)


@test.route("/")
@login_required
def question():
    word = current_user.rand_word()
    return __load_word(word)


@test.route("/right/<string:word_id>")
@login_required
def right(word_id: str):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        word: dict = serializer.loads(word_id, max_age=120)  # 120s内生效
        user: UserWordDataBase = current_user
        user.right_word(word["word"])
    except BadData:
        flash(f"Timeout for confirm word")
        abort(408)
    except KeyError:
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
    except BadData:
        flash(f"Timeout for confirm word")
        abort(408)
    except KeyError:
        abort(404)
    return redirect(url_for("test.question"))


@test.route("/delete/word/<string:word>")
@login_required
def delete(word: str):
    user: UserWordDataBase = current_user
    user.delete_txt(word)
    flash(f"Word '{word}' is deleted.")
    return redirect(url_for("test.question"))


@test.route("/download/word/<string:word>")
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


class Search(Thread):
    def __init__(self, user: UserWordDataBase, word: str, internet: bool, add: bool):
        super(Search, self).__init__()
        self.word: Optional[Word] = None
        self.word_str = word
        self.internet = internet
        self.add = add
        self.user = user
        self.daemon = True

    def run(self):
        self.word = self.user.find_word(self.word_str, self.internet, self.add)

    def wait_event(self) -> Optional[Word]:
        self.join(timeout=5)
        return self.word


@test.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()
    if not form.validate_on_submit():
        word = request.args.get("word", "")
        if len(word) == 0:
            abort(400)
        user = current_user._get_current_object()
        th = Search(user, word, request.args.get("internet", 0) != '0', request.args.get("add", 0) != '0')
        th.start()
        word = th.wait_event()
        if th.is_alive():
            flash("Search timeout")
        return __load_word(word)
    return redirect(url_for("test.search",
                            word=form.search.data, internet=int(form.from_internet.data), add=int(form.add_to_db.data)))


@test.route("/download/table/<string:file_type>")
@login_required
def download_table(file_type: str):
    user: UserWordDataBase = current_user
    try:
        max_eg = int(request.args.get("max_eg", -1))
    except (ValueError, TypeError):
        return abort(400)
    df = user.export_frame(max_eg, file_type == "html")
    if file_type == "csv":
        df_io = io.BytesIO()
        df.to_csv(df_io)
    elif file_type == "xlsx":
        df_io = io.BytesIO()
        df.to_excel(df_io)
    elif file_type == "html":
        df_io = io.StringIO()
        df.to_html(df_io, escape=False)
        df_io = io.BytesIO(df_io.getvalue().encode('utf-8'))
    elif file_type == "json":
        df_io = io.BytesIO()
        df.to_json(df_io)
    elif file_type == "markdown":
        df_io = io.StringIO()
        df.to_markdown(df_io)
        df_io = io.BytesIO(df_io.getvalue().encode('utf-8'))
    elif file_type == "latex":
        df_io = io.StringIO()
        df.to_latex(df_io)
        df_io = io.BytesIO(df_io.getvalue().encode('utf-8'))
    else:
        return abort(400)
    df_io.seek(0, io.SEEK_SET)
    return send_file(df_io, attachment_filename=f"{user.user}.henglish.{file_type}", as_attachment=True)


@test.route("/reset/user", methods=["POST"])
@login_required
def reset_user():
    reset_form = ResetDeleteForm()
    if reset_form.validate_on_submit():
        user: UserWordDataBase = current_user
        if not user.check_passwd(reset_form.passwd.data):
            flash("Passwd error.")
        else:
            flash("User reset")
            user.reset()
        return redirect(url_for("test.question"))
    abort(400)


@test.route("/delete/user", methods=["POST"])
@login_required
def delete_user():
    delete_form = ResetDeleteForm()
    if delete_form.validate_on_submit():
        user: UserWordDataBase = current_user
        if not user.check_passwd(delete_form.passwd.data):
            flash("Passwd error.")
        else:
            flash("User reset")
            logout_user()
            user.delete_user()
        return redirect(url_for("test.question"))
    abort(400)


@test.route("/reset/passwd", methods=["POST"])
@login_required
def reset_passwd():
    reset_form = ResetDeleteForm()
    if reset_form.validate_on_submit():
        if len(reset_form.new_passwd.data) < 4 or len(reset_form.new_passwd.data) > 32:
            flash("Please enter a password of length 4-32")
        else:
            user: UserWordDataBase = current_user
            if not user.check_passwd(reset_form.passwd.data):
                flash("Passwd error.")
            else:
                flash("User passwd reset")
                user.set_passwd(reset_form.new_passwd.data)
                logout_user()
                return redirect(url_for("home.index"))
        return redirect(url_for("test.question"))
    abort(400)


class Upload(Thread):
    upload = {}

    def __init__(self, user: UserWordDataBase, file: List[str]):
        super(Upload, self).__init__()
        self.user: UserWordDataBase = user
        self.file = file
        self.upload[user.user] = self
        self.daemon = True

    def run(self):
        for i in self.file:
            self.user.import_txt(i)


@test.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files["file"]
    user = current_user._get_current_object()
    job: Upload = Upload.upload.get(user.user)
    if Upload.upload.get(user.user) is not None and job.is_alive():
        flash("Please wait for the current task to complete")
        return abort(423)
    Upload(user, file.stream.read().decode('utf-8').split('\n')).start()
    flash("File is being processed")
    return redirect(url_for("test.question"))


@test.route("/introduce")
def introduce():
    return render_template("introduce.html")
