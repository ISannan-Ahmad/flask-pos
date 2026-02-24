from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils import role_required
from controllers.product_controller import ProductController

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
@login_required
def products():
    all_products = ProductController.get_all_products()
    distributors = ProductController.get_all_distributors()
    return render_template('products.html', products=all_products, distributors=distributors)

@products_bp.route('/admin', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_products():
    if request.method == 'POST':
        success, message = ProductController.create_product(request.form)
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")
        return redirect(url_for('products.manage_products'))

    products = ProductController.get_all_products()
    distributors = ProductController.get_all_distributors()
    return render_template('manage_products.html', products=products, distributors=distributors)

@products_bp.route('/admin/delete/<int:id>')
@login_required
@role_required('admin')
def delete_product(id):
    success, message = ProductController.delete_product(id)
    if success:
         flash(message, "success")
    else:
         flash(message, "danger")
    return redirect(url_for('products.manage_products'))

@products_bp.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_product(id):
    product = ProductController.get_product_by_id(id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.manage_products'))
    
    if request.method == 'POST':
        success, message = ProductController.update_product(id, request.form)
        if success:
             flash(message, "success")
             return redirect(url_for('products.manage_products'))
        else:
             flash(message, "danger")
             distributors = ProductController.get_all_distributors()
             return render_template('edit_product.html', product=product, distributors=distributors)
    
    distributors = ProductController.get_all_distributors()
    return render_template('edit_product.html', product=product, distributors=distributors)

@products_bp.route('/<int:id>')
@login_required
def product_detail(id):
    found, product, recent_sales, recent_purchases, *error = ProductController.get_product_details(id)
    
    if not found:
        message = error[0] if error else "Product not found."
        flash(message, "danger")
        return redirect(url_for('products.products'))
        
    return render_template('product_detail.html', product=product, recent_sales=recent_sales, recent_purchases=recent_purchases)

@products_bp.route('/<int:id>/restock', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def restock_product(id):
    product = ProductController.get_product_by_id(id)
    
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.products'))
        
    if request.method == 'POST':
        success, message, updated_product = ProductController.restock_product(id, request.form)
        if success:
             flash(message, "success")
             return redirect(url_for('products.product_detail', id=id))
        else:
             flash(message, "danger" if "Please enter" in message else "warning")
             
    return render_template('restock_product.html', product=product)

