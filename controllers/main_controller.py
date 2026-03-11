from sqlalchemy import func, extract
from extensions import db
from models import (Order, PurchaseOrder, Product, Customer,
                     CustomerTransaction, EmployeePayment, Expense, PKT)
from datetime import datetime, timedelta


class MainController:
    @staticmethod
    def get_admin_dashboard_data():
        now = datetime.now(PKT)
        year, month = now.year, now.month

        orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        pending_purchase_orders = PurchaseOrder.query.filter_by(status='pending').count()
        pending_orders = Order.query.filter_by(status='draft').count()

        # ── Financial summary for current month ──
        sales_q = Order.query.filter(
            Order.status == 'approved',
            extract('year', Order.created_at) == year,
            extract('month', Order.created_at) == month)

        revenue = float(sales_q.with_entities(func.sum(Order.total_amount)).scalar() or 0)

        cash_sales = float(
            sales_q.filter(Order.order_type == 'sale')
            .with_entities(func.sum(Order.total_amount)).scalar() or 0)
        credit_sales = float(
            sales_q.filter(Order.order_type == 'credit_sale')
            .with_entities(func.sum(Order.total_amount)).scalar() or 0)
            
        returns_q = sales_q.filter(Order.order_type == 'return')
        total_returns_amount = float(returns_q.with_entities(func.sum(func.abs(Order.total_amount))).scalar() or 0)
        total_returns_count = returns_q.count()
            
        total_orders_month = sales_q.filter(Order.order_type != 'return').count()

        purchases = float(
            PurchaseOrder.query.filter(
                PurchaseOrder.status == 'received',
                extract('year', PurchaseOrder.created_at) == year,
                extract('month', PurchaseOrder.created_at) == month
            ).with_entities(func.sum(PurchaseOrder.total_amount)).scalar() or 0)

        expenses = float(
            Expense.query.filter(
                extract('year', Expense.expense_date) == year,
                extract('month', Expense.expense_date) == month
            ).with_entities(func.sum(Expense.amount)).scalar() or 0)

        staff_expenses = float(
            EmployeePayment.query.filter(
                extract('year', EmployeePayment.date) == year,
                extract('month', EmployeePayment.date) == month
            ).with_entities(func.sum(EmployeePayment.amount)).scalar() or 0)

        gross_profit = float(sales_q.with_entities(func.sum(Order.total_profit)).scalar() or 0)
        net_profit = gross_profit - expenses - staff_expenses

        # Receipts collected this month
        receipts = float(
            CustomerTransaction.query.filter(
                CustomerTransaction.transaction_type == 'payment',
                extract('year', CustomerTransaction.created_at) == year,
                extract('month', CustomerTransaction.created_at) == month
            ).with_entities(func.sum(CustomerTransaction.amount)).scalar() or 0)

        outstanding_credit = credit_sales - receipts

        # ── All-time balances ──
        total_receivables = float(
            db.session.query(func.sum(Order.total_amount - Order.amount_paid))
            .filter(Order.status == 'approved',
                    Order.total_amount > Order.amount_paid).scalar() or 0)

        total_payables = float(
            db.session.query(func.sum(PurchaseOrder.total_amount - PurchaseOrder.amount_paid))
            .filter(PurchaseOrder.payment_status != 'paid').scalar() or 0)

        # ── Alerts ──
        low_stock_products = Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level,
            Product.is_active == True
        ).count()

        low_stock_items = Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level,
            Product.is_active == True
        ).order_by(Product.stock_quantity.asc()).limit(10).all()

        credit_reminders = MainController.get_credit_due_reminders()

        unpaid_supplier_invoices = PurchaseOrder.query.filter(
            PurchaseOrder.payment_status != 'paid',
            PurchaseOrder.status == 'received',
            PurchaseOrder.total_amount > PurchaseOrder.amount_paid
        ).order_by(PurchaseOrder.created_at.desc()).limit(10).all()

        return {
            'orders': orders,
            'pending_purchase_orders': pending_purchase_orders,
            'pending_orders': pending_orders,
            # Financial
            'revenue': revenue,
            'purchases': purchases,
            'expenses': expenses,
            'staff_expenses': staff_expenses,
            'net_profit': net_profit,
            # Sales
            'cash_sales': cash_sales,
            'credit_sales': credit_sales,
            'total_orders_month': total_orders_month,
            'total_returns_amount': total_returns_amount,
            'total_returns_count': total_returns_count,
            'receipts': receipts,
            'outstanding_credit': outstanding_credit,
            # Balances
            'total_receivables': total_receivables,
            'total_payables': total_payables,
            # Alerts
            'low_stock_products': low_stock_products,
            'low_stock_items': low_stock_items,
            'credit_reminders': credit_reminders,
            'unpaid_supplier_invoices': unpaid_supplier_invoices,
        }

    @staticmethod
    def get_low_stock_products():
        return Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level,
            Product.is_active == True
        ).order_by(Product.stock_quantity.asc()).all()

    @staticmethod
    def get_credit_due_reminders():
        """Get customers with payments approaching or past due date."""
        now = datetime.now(PKT)
        reminder_window = now + timedelta(days=7)

        overdue_orders = Order.query.filter(
            Order.order_type == 'credit_sale',
            Order.status == 'approved',
            Order.total_amount > Order.amount_paid,
            Order.due_date.isnot(None),
            Order.due_date <= reminder_window
        ).order_by(Order.due_date.asc()).limit(20).all()

        reminders = []
        for order in overdue_orders:
            remaining = float(order.total_amount) - float(order.amount_paid)
            is_overdue = order.due_date.replace(tzinfo=None) < now.replace(tzinfo=None)
            reminders.append({
                'order_id': order.id,
                'customer_name': order.customer_name or 'Unknown',
                'customer_phone': order.customer_phone or '',
                'remaining': remaining,
                'due_date': order.due_date,
                'is_overdue': is_overdue,
                'days_remaining': (order.due_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days
            })
        return reminders

    @staticmethod
    def get_staff_dashboard_data(current_user_id):
        orders = Order.query.filter_by(created_by=current_user_id)\
            .order_by(Order.created_at.desc()).limit(10).all()

        return {
            'orders': orders
        }

    @staticmethod
    def get_pending_orders():
        """Get all draft orders that need admin approval."""
        orders = Order.query.filter_by(status='draft').order_by(Order.created_at.desc()).all()
        return orders
        
    @staticmethod
    def check_new_orders(last_check_time=None):
        """Count how many new draft orders were created since last_check_time."""
        query = Order.query.filter_by(status='draft')
        if last_check_time:
            try:
                # Convert ISO string to datetime object
                if isinstance(last_check_time, str):
                    last_check_time = datetime.fromisoformat(last_check_time.replace('Z', '+00:00'))
                    last_check_time = last_check_time.replace(tzinfo=None)
                query = query.filter(Order.created_at > last_check_time)
            except (ValueError, TypeError):
                pass # Fall back to total count if time format is invalid
                
        # We return both the count and the current server time to use for the next ping
        current_time = datetime.now(PKT).isoformat()
        count = query.count()
        return {'new_count': count, 'timestamp': current_time}
