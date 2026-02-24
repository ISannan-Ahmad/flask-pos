from sqlalchemy import func
from extensions import db
from models import Order, PurchaseOrder, Product

class MainController:
    @staticmethod
    def get_admin_dashboard_data():
        orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        pending_purchase_orders = PurchaseOrder.query.filter_by(status='pending').count()
        
        total_receivables = db.session.query(func.sum(Order.total_amount - Order.amount_paid))\
            .filter(Order.status == 'approved')\
            .filter(Order.total_amount > Order.amount_paid).scalar() or 0
            
        total_payables = db.session.query(func.sum(PurchaseOrder.total_amount - PurchaseOrder.amount_paid))\
            .filter(PurchaseOrder.payment_status != 'paid').scalar() or 0
            
        low_stock_products = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).count()
        
        return {
            'orders': orders,
            'pending_purchase_orders': pending_purchase_orders,
            'total_receivables': total_receivables,
            'total_payables': total_payables,
            'low_stock_products': low_stock_products
        }

    @staticmethod
    def get_staff_dashboard_data(current_user_id):
        orders = Order.query.filter_by(created_by=current_user_id)\
            .order_by(Order.created_at.desc()).limit(10).all()
        
        return {
            'orders': orders
        }
