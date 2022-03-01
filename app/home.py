from flask import blueprints, url_for, request, redirect, render_template, flash, current_app, abort
from flask_login import login_user, current_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo
from app.user import load_user, create_user, check_template, get_template
from typing import ClassVar


class LoginForm(FlaskForm):
    name = StringField("User name", validators=[DataRequired(), Length(1, 32)])
    passwd = PasswordField("Passwd", validators=[DataRequired(), Length(4, 32)])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")


def register_form() -> ClassVar:
    class Form(FlaskForm):
        name = StringField("User name", validators=[DataRequired(), Length(1, 32)])
        template = SelectField("Template", choices=get_template())
        passwd = PasswordField("Passwd", validators=[DataRequired(),
                                                     EqualTo("passwd_again", message="两次输入密码不相同"),
                                                     Length(4, 32)])
        passwd_again = PasswordField("Passwd again", validators=[DataRequired()])
        submit = SubmitField("register")
    return Form()


home = blueprints.Blueprint("home", __name__)


@home.route("/", methods=["GET"])
def index():
    if not current_user.is_anonymous:
        return redirect(url_for("test.question"))
    return render_template("index.html", login_form=LoginForm(), register_form=register_form())


@home.route("/login", methods=["POST"])
def login():
    if not current_user.is_anonymous:
        current_app.logger.debug(f"re-login and abort(304)")
        flash(f"You are login as {current_user.user}")
        abort(304)

    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = load_user(login_form.name.data, login_form.passwd.data)
        if user is not None:
            login_user(user, login_form.remember.data)
            next_page = request.args.get("next")
            if next_page is None or not next_page.startswith('/'):
                next_page = url_for('home.index')
            flash("Login success")
            current_app.logger.info(f"{login_form.name.data} login success")
            return redirect(next_page)
        flash("Login fail")
        current_app.logger.debug(f"{login_form.name.data} login fail")
    return redirect(url_for("home.index"))


@home.route("/register", methods=["POST"])
def register():
    if not current_user.is_anonymous:
        current_app.logger.debug(f"re-login and register(304)")
        flash(f"You are login as {current_user.user}")
        abort(304)

    register_ = register_form()
    if register_.validate_on_submit():
        template = register_.template.data
        if len(template) == 0:
            template = "base"
        if not check_template(template):
            flash(f"Template '{template}' not exist")
            abort(400)
        flat, user = create_user(template, register_.name.data, register_.passwd.data)
        if user is not None:
            current_app.logger.debug(f"{register_.name.data} with {register_.template.data} register success")
            flash("Register success")
        else:
            current_app.logger.debug(
                f"{register_.name.data} with {register_.template.data} register fail [{flat}]")
            flash("User is already exist")
    return redirect(url_for("home.index"))


@home.route('/logout')
@login_required
def logout():
    logout_user()
    flash("User logout")
    return redirect(url_for("home.index"))
