from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required
from controllers.auth_controller import AuthController

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        success, message = AuthController.login_user_with_credentials(
            request.form['username'], request.form['password']
        )
        if success:
            return redirect(url_for('main.dashboard'))
        flash(message, "danger")
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
