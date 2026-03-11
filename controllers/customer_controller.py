from models import Customer, CustomerTransaction, CashTransaction, Order, OrderItem, Product, PKT
from extensions import db
from flask_login import current_user
from sqlalchemy import func, extract

class CustomerController:
    @staticmethod
    def get_all_customers():
        return Customer.query.order_by(Customer.created_at.desc()).all()

    @staticmethod
    def get_customer(customer_id):
        return db.session.get(Customer, customer_id)

    @staticmethod
    def create_customer(data):
        name = data.get('name')
        if not name:
            return False, "Customer name is required"
            
        try:
            limit = float(data.get('credit_limit', 0))
        except ValueError:
            limit = 0.0

        try:
            credit_days = int(data.get('credit_days', 30))
        except ValueError:
            credit_days = 30
            
        customer = Customer(
            name=name,
            phone=data.get('phone'),
            address=data.get('address'),
            email=data.get('email'),
            credit_limit=limit,
            credit_days=credit_days
        )
        db.session.add(customer)
        db.session.commit()
        return True, "Customer created successfully"

    @staticmethod
    def get_customer_analytics(customer_id):
        """Purchase analytics: totals, yearly breakdown, product breakdown."""
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return None

        # Total purchases
        total_purchases = db.session.query(func.sum(Order.total_amount))\
            .filter(Order.customer_id == customer_id, Order.status == 'approved').scalar() or 0
        total_orders = Order.query.filter_by(customer_id=customer_id, status='approved').count()

        # Yearly breakdown
        yearly = db.session.query(
            extract('year', Order.created_at).label('year'),
            func.sum(Order.total_amount).label('total'),
            func.count(Order.id).label('count')
        ).filter(Order.customer_id == customer_id, Order.status == 'approved')\
         .group_by(extract('year', Order.created_at))\
         .order_by(extract('year', Order.created_at).desc()).all()

        # Product breakdown (top 10)
        product_data = db.session.query(
            Product.name,
            func.sum(OrderItem.quantity).label('qty'),
            func.sum(OrderItem.price * OrderItem.quantity).label('total')
        ).join(OrderItem, OrderItem.product_id == Product.id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .filter(Order.customer_id == customer_id, Order.status == 'approved')\
         .group_by(Product.name)\
         .order_by(func.sum(OrderItem.price * OrderItem.quantity).desc())\
         .limit(10).all()

        return {
            'total_purchases': float(total_purchases),
            'total_orders': total_orders,
            'yearly': [{'year': int(y.year), 'total': float(y.total), 'count': y.count} for y in yearly],
            'products': [{'name': p.name, 'qty': int(p.qty), 'total': float(p.total)} for p in product_data]
        }

    @staticmethod
    def apply_account_payment(customer_id, amount, payment_method, notes, payment_destination='business', supplier_id=None):
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return False, "Customer not found", None
            
        try:
            amount = float(amount)
            if amount <= 0:
                return False, "Amount must be greater than zero", None
        except ValueError:
            return False, "Invalid amount", None
            
        transaction = CustomerTransaction(
            customer_id=customer.id,
            transaction_type='payment',
            amount=amount,
            payment_method=payment_method,
            reference="Account Payment (FIFO)",
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(transaction)
        
        from models import Distributor, SupplierTransaction
        if payment_destination == 'supplier':
            if not supplier_id:
                return False, "Supplier must be selected for third-party payment", None
            supplier = db.session.get(Distributor, supplier_id)
            if not supplier:
                return False, "Supplier not found", None
                
            supplier_tx = SupplierTransaction(
                distributor_id=supplier.id,
                transaction_type='payment',
                amount=amount,
                payment_method=payment_method,
                reference=f"Third-Party Payment from Customer {customer.name}",
                notes=f"Customer settled account directly to supplier. Note: {notes}",
                created_by=current_user.id
            )
            db.session.add(supplier_tx)
            transaction.reference = f"Third-Party Payment to {supplier.name}"
            transaction.notes = f"Paid directly to supplier {supplier.name}. {notes or ''}"
        else:
            cash_tx = CashTransaction(
                transaction_type='in',
                amount=amount,
                source='customer_payment',
                description=f"Account Payment from {customer.name}",
                created_by=current_user.id
            )
            db.session.add(cash_tx)
        
        unpaid_orders = [o for o in customer.orders if o.status == 'approved' and float(o.total_amount) > float(o.amount_paid)]
        unpaid_orders.sort(key=lambda x: x.created_at)
        
        remaining_payment = amount
        for order in unpaid_orders:
            if remaining_payment <= 0:
                break
                
            due_on_order = float(order.total_amount) - float(order.amount_paid)
            if remaining_payment >= due_on_order:
                order.amount_paid = float(order.amount_paid) + due_on_order
                remaining_payment -= due_on_order
            else:
                order.amount_paid = float(order.amount_paid) + remaining_payment
                remaining_payment = 0
                
        db.session.commit()
        return True, "Payment applied successfully", transaction.id

