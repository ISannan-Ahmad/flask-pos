from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, 'role', None) != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return wrapper
