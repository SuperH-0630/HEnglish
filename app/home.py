from flask import blueprints, url_for, request, redirect, render_template, flash, current_app, abort, g
from flask_login import login_user, current_user, login_required, logout_user
from wtforms import PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from app.user import load_user, create_user, check_template, get_template, have_user
from app.tool import form_required, AuthForm


home = blueprints.Blueprint("home", __name__)


class LoginForm(AuthForm):
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")

    def __init__(self):
        super(LoginForm, self).__init__()
        self.remember.data = True


class RegisterForm(AuthForm):
    template = SelectField("Template", choices=get_template(), coerce=str,
                           validators=[DataRequired(message="Template must be selected")])
    passwd_again = PasswordField("Passwd again",
                                 validators=[DataRequired(message="Must enter password again"),
                                             EqualTo("passwd", message="The password entered twice is different")])
    submit = SubmitField("register")

    def __init__(self):
        super(RegisterForm, self).__init__()
        self.template.data = "base"

    def validate_name(self, field):
        if have_user(field.data):
            raise ValidationError("User is already exist")

    def validate_template(self, field):
        if not check_template(field.data):
            raise ValidationError("Template does not exist")


def __load_index(login_form: LoginForm, register_form: RegisterForm):
    if not current_user.is_anonymous:
        return redirect(url_for("test.question"))
    return render_template("index.html", login_form=login_form, register_form=register_form)


@home.route("/", methods=["GET"])
def index():
    if not current_user.is_anonymous:
        return redirect(url_for("test.question"))
    return __load_index(LoginForm(), RegisterForm())


@home.route("/login", methods=["POST"])
@form_required(LoginForm, lambda form: __load_index(form, RegisterForm()))
def login():
    if not current_user.is_anonymous:
        current_app.logger.debug(f"re-login and abort(304)")
        flash(f"You are login as {current_user.user}")
        abort(304)

    login_form: LoginForm = g.form
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
@form_required(RegisterForm, lambda form: __load_index(LoginForm(), form))
def register():
    if not current_user.is_anonymous:
        current_app.logger.debug(f"re-login and register(304)")
        flash(f"You are login as {current_user.user}")
        abort(304)

    register_form: RegisterForm = g.form
    flat, user = create_user(register_form.template.data, register_form.name.data, register_form.passwd.data)
    if user is not None:
        current_app.logger.debug(f"{register_form.name.data} with {register_form.template.data} register success")
        flash("Register success")
    else:
        current_app.logger.debug(
            f"{register_form.name.data} with {register_form.template.data} register fail [{flat}]")
        flash("User is already exist")
    return redirect(url_for("home.index"))


@home.route('/logout')
@login_required
def logout():
    logout_user()
    flash("User logout")
    return redirect(url_for("home.index"))
