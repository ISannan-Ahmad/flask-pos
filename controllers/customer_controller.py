from models import Customer, CustomerTransaction, CashTransaction
from extensions import db
from flask_login import current_user

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
            
        customer = Customer(
            name=name,
            phone=data.get('phone'),
            address=data.get('address'),
            credit_limit=limit
        )
        db.session.add(customer)
        db.session.commit()
        return True, "Customer created successfully"

    @staticmethod
    def apply_account_payment(customer_id, amount, payment_method, notes):
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return False, "Customer not found"
            
        try:
            amount = float(amount)
            if amount <= 0:
                return False, "Amount must be greater than zero"
        except ValueError:
            return False, "Invalid amount"
            
        # Log to Customer Ledger
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
        
        # Log to Cash Book
        cash_tx = CashTransaction(
            transaction_type='in',
            amount=amount,
            source='customer_payment',
            description=f"Account Payment from {customer.name}",
            created_by=current_user.id
        )
        db.session.add(cash_tx)
        
        # FIFO Allocation to unpaid orders
        unpaid_orders = [o for o in customer.orders if o.status == 'approved' and float(o.total_amount) > float(o.amount_paid)]
        # Sort oldest first
        unpaid_orders.sort(key=lambda x: x.created_at)
        
        remaining_payment = amount
        for order in unpaid_orders:
            if remaining_payment <= 0:
                break
                
            due_on_order = float(order.total_amount) - float(order.amount_paid)
            if remaining_payment >= due_on_order:
                # Pay off this order completely
                order.amount_paid = float(order.amount_paid) + due_on_order
                remaining_payment -= due_on_order
            else:
                # Partial payment on this order
                order.amount_paid = float(order.amount_paid) + remaining_payment
                remaining_payment = 0
                
        db.session.commit()
        return True, "Payment applied successfully"
