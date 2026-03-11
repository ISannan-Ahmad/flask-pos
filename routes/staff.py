from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils import role_required
from controllers.staff_controller import StaffController

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

@staff_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def staff_list():
    if request.method == 'POST':
        success, msg = StaffController.create_employee(request.form)
        flash(msg, 'success' if success else 'danger')
        return redirect(url_for('staff.staff_list'))

    employees = StaffController.get_all_employees()
    return render_template('staff.html', employees=employees)

@staff_bp.route('/<int:employee_id>')
@login_required
@role_required('admin')
def staff_detail(employee_id):
    emp = StaffController.get_employee(employee_id)
    if not emp:
        flash('Employee not found.', 'danger')
        return redirect(url_for('staff.staff_list'))

    payment_type = request.args.get('payment_type', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    payments = StaffController.get_payment_history(
        employee_id,
        payment_type=payment_type or None,
        start_date=start_date or None,
        end_date=end_date or None
    )
    return render_template('staff_detail.html', employee=emp, payments=payments,
                           payment_type=payment_type, start_date=start_date, end_date=end_date)

@staff_bp.route('/<int:employee_id>/pay', methods=['POST'])
@login_required
@role_required('admin')
def record_payment(employee_id):
    success, msg = StaffController.record_payment(employee_id, request.form)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('staff.staff_detail', employee_id=employee_id))
