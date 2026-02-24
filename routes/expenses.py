from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils import role_required
from controllers.expenses_controller import ExpensesController

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def list_expenses():
    expenses, total_expenses = ExpensesController.get_all_expenses()
    return render_template('expenses.html', expenses=expenses, total=total_expenses)

@expenses_bp.route('/add', methods=['POST'])
@login_required
@role_required('admin')
def add_expense():
    success, message, _ = ExpensesController.add_expense(request.form, current_user.id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('expenses.list_expenses'))

@expenses_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_expense(id):
    expense = ExpensesController.get_expense(id)
    if not expense:
        flash("Expense not found", "danger")
        return redirect(url_for('expenses.list_expenses'))
        
    if request.method == 'POST':
        success, message = ExpensesController.edit_expense(id, request.form)
        if success:
            flash(message, "success")
            return redirect(url_for('expenses.list_expenses'))
        else:
            flash(message, "danger")
            
    return render_template('edit_expense.html', expense=expense)

@expenses_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_expense(id):
    success, message = ExpensesController.delete_expense(id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('expenses.list_expenses'))
