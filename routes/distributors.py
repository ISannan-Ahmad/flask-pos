from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils import role_required
from controllers.distributors_controller import DistributorsController

distributors_bp = Blueprint('distributors', __name__)

@distributors_bp.route('/')
@login_required
@role_required('admin')
def list_distributors():
    all_distributors = DistributorsController.get_all_distributors()
    return render_template('distributors.html', distributors=all_distributors)

@distributors_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_distributor():
    if request.method == 'POST':
        success, message = DistributorsController.add_distributor(request.form)
        if success:
             flash(message, "success")
             return redirect(url_for('distributors.list_distributors'))
    
    return render_template('add_distributor.html')

@distributors_bp.route('/<int:id>')
@login_required
@role_required('admin')
def distributor_detail(id):
    success, message, distributor, products, purchase_orders, transactions = DistributorsController.get_distributor_details(id)
    if not success:
        flash(message, "danger")
        return redirect(url_for('distributors.list_distributors'))
    
    return render_template('distributor_detail.html', 
                         distributor=distributor,
                         products=products,
                         purchase_orders=purchase_orders,
                         transactions=transactions)

@distributors_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_distributor(id):
    success, message, distributor, products, purchase_orders, transactions = DistributorsController.get_distributor_details(id)
    if not success:
        flash(message, "danger")
        return redirect(url_for('distributors.list_distributors'))
        
    if request.method == 'POST':
        success, message = DistributorsController.edit_distributor(id, request.form)
        if success:
             flash(message, "success")
             return redirect(url_for('distributors.list_distributors'))
        else:
             flash(message, "danger")
    
    return render_template('edit_distributor.html', distributor=distributor)

@distributors_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_distributor(id):
    success, message = DistributorsController.delete_distributor(id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('distributors.list_distributors'))
