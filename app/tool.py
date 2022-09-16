from functools import wraps
from flask import abort, g
from flask_wtf import FlaskForm
from typing import ClassVar, Optional, Callable
from wtforms.fields import StringField, PasswordField
from wtforms.validators import DataRequired, Length, Regexp


class AuthForm(FlaskForm):
    name = StringField("User name", description="User name",
                       validators=[DataRequired(message="Must enter user name"),
                                   Length(1, 10, message="Length: 1 - 10"),
                                   Regexp(r"^[a-zA-Z0-9_]+$", message="Only letters and numbers and _ are accepted")])
    passwd = PasswordField("Password", description="Password",
                           validators=[DataRequired(message="Must enter password"),
                                       Length(4, 32, "Length: 4 - 32")])


def form_required(form: ClassVar[FlaskForm], callback: Optional[Callable] = None, **kw):
    def required(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            f = form()
            if not f.validate_on_submit():
                if callback is None:
                    return abort(404)
                return callback(form=f, **kw, **kwargs)
            g.form = f  # 使用g传递form参数
            return func(*args, **kwargs)
        return new_func
    return required
