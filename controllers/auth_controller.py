from werkzeug.security import check_password_hash
from flask_login import login_user
from models import User

class AuthController:
    @staticmethod
    def login_user_with_credentials(username, password):
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return True, "Login successful"
        return False, "Invalid credentials"
