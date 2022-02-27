from flask import blueprints, url_for, request, redirect, render_template, flash, current_app, abort
from flask_login import login_user, current_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo
from app.user import load_user, create_user, check_template


class LoginForm(FlaskForm):
    name = StringField("User name", validators=[DataRequired(), Length(1, 32)])
    passwd = PasswordField("Passwd", validators=[DataRequired(), Length(4, 32)])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")


class RegisterForm(FlaskForm):
    name = StringField("User name", validators=[DataRequired(), Length(1, 32)])
    template = StringField("Template name", validators=[Length(0, 32)])
    passwd = PasswordField("Passwd", validators=[DataRequired(),
                                                 EqualTo("passwd_again", message="两次输入密码不相同"),
                                                 Length(4, 32)])
    passwd_again = PasswordField("Passwd again", validators=[DataRequired()])
    submit = SubmitField("register")

    def validate_name(self, field):
        if load_user(field.data, None) is not None:
            raise ValidationError("User is already exist")

    def validate_template(self, field):
        if not check_template(field.data):
            raise ValidationError("Template not exist")


home = blueprints.Blueprint("home", __name__)


@home.route("/", methods=["GET"])
def index():
    if not current_user.is_anonymous:
        return redirect(url_for("test.question"))
    return render_template("index.html", login_form=LoginForm(), register_form=RegisterForm())


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

    register_form = RegisterForm()
    if register_form.validate_on_submit():
        template = register_form.template.data
        if len(template) == 0:
            template = "base"
        flat, user = create_user(template, register_form.name.data, register_form.passwd.data)
        if user is not None:
            current_app.logger.debug(f"{register_form.name.data} with {register_form.template.data} register success")
            flash("Register success")
        else:
            current_app.logger.debug(
                f"{register_form.name.data} with {register_form.template.data} register fail [{flat}]")
            flash("Register fail")
    return redirect(url_for("home.index"))


@home.route('/logout')
@login_required
def logout():
    logout_user()
    flash("User logout")
    return redirect(url_for("home.index"))
