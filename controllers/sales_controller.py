from models import Order, Product, OrderItem, CustomerTransaction, CashTransaction, StockMovement
from extensions import db
from datetime import datetime, timedelta
from flask_login import current_user

class SalesController:
    @staticmethod
    def create_order(data, current_user_id):
        product_ids = data.getlist('product_id[]')
        quantities = data.getlist('quantity[]')
        
        insufficient_stock = []
        parsed_items = []
        
        for i in range(len(product_ids)):
            if product_ids[i] and quantities[i]:
                pid = int(product_ids[i])
                qty = int(quantities[i])
                if qty > 0:
                    product = db.session.get(Product, pid)
                    if product:
                        if qty > product.stock_quantity:
                            insufficient_stock.append(f"{product.name} (available: {product.stock_quantity})")
                        else:
                            parsed_items.append((product, qty))

        if insufficient_stock:
            return False, f"Insufficient stock for: {', '.join(insufficient_stock)}"
            
        if not parsed_items:
            return False, "Order must contain at least one valid item."

        order_type = data.get('order_type', 'sale')
        customer_id = data.get('customer_id') or None
        
        # for cash sales without explicit customer record
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        
        try:
            amount_paid = float(data.get('amount_paid', 0))
        except ValueError:
            amount_paid = 0.0
            
        # Optional: ensure staff can't set amount paid
        if current_user.role != 'admin':
            amount_paid = 0.0
            
        new_order = Order(
            created_by=current_user_id,
            status='draft',
            order_type=order_type,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            total_amount=0.0,
            total_profit=0.0,
            amount_paid=amount_paid
        )
        
        if order_type == 'credit_sale' and amount_paid == 0:
            new_order.due_date = datetime.utcnow() + timedelta(days=30)
        
        db.session.add(new_order)
        db.session.flush()

        for product, qty in parsed_items:
            # We don't set price here, it is set by admin on approval
            item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=qty,
                price=None 
            )
            db.session.add(item)

        db.session.commit()
        return True, "Draft Order created successfully!"

    @staticmethod
    def get_order_by_id(order_id):
        return db.session.get(Order, order_id)

    @staticmethod
    def approve_order(order_id, data, current_user_id):
        # We process approval inside a database transaction explicitly handled by SQLAlchemy.
        # But we could also use with_for_update() to lock the rows.
        
        order = db.session.get(Order, order_id)
        if not order:
             return False, "Order not found."
             
        if order.status == 'approved':
             return False, "Order is already approved. Cannot modify."
             
        total = 0
        total_profit = 0

        for item in order.items:
            price_value = data.get(f'price_{item.id}')
            if not price_value:
                return False, "All items must have a selling price set by Admin."

            price = float(price_value)
            item.price = price
            
            # Lock the product row
            product = db.session.get(Product, item.product_id, with_for_update={"of": Product})

            if product.stock_quantity < item.quantity:
                db.session.rollback()
                return False, f"Not enough stock for {product.name}. Available: {product.stock_quantity}"

            total += price * item.quantity
            profit = (price - float(product.cost_price or 0)) * item.quantity
            total_profit += profit
            
            # Stock reduction and movement log
            qty_before = product.stock_quantity
            product.stock_quantity -= item.quantity
            
            stock_movement = StockMovement(
                product_id=product.id,
                quantity_change=-item.quantity,
                quantity_before=qty_before,
                quantity_after=product.stock_quantity,
                reference_type='sale',
                reference_id=order.id,
                user_id=current_user_id
            )
            db.session.add(stock_movement)

        order.total_amount = total
        order.total_profit = total_profit
        order.status = 'approved'
        order.approved_by = current_user_id
        
        # Handle Ledgers:
        if order.customer_id:
            # Increase customer debt
            receivable_tx = CustomerTransaction(
                customer_id=order.customer_id,
                order_id=order.id,
                transaction_type='receivable',
                amount=total,
                reference=f"Invoice #{order.id}",
                created_by=current_user_id
            )
            db.session.add(receivable_tx)
            
            if order.amount_paid > 0:
                # Immediate partial payment on credit sale / cash sale
                payment_tx = CustomerTransaction(
                    customer_id=order.customer_id,
                    order_id=order.id,
                    transaction_type='payment',
                    amount=order.amount_paid,
                    payment_method='cash',
                    reference=f"Initial payment for Order #{order.id}",
                    created_by=current_user_id
                )
                db.session.add(payment_tx)

        if order.amount_paid > 0:
            # Add to Cash Book
            cash_tx = CashTransaction(
                transaction_type='in',
                amount=order.amount_paid,
                source='sales',
                reference_id=order.id,
                description=f"Initial payment for Order #{order.id}",
                created_by=current_user_id
            )
            db.session.add(cash_tx)
        
        db.session.commit()
        return True, "Order approved and finalized successfully!"
        
    @staticmethod
    def add_order_payment(order_id, data, current_user_id):
        order = db.session.get(Order, order_id)
        if not order:
             return False, "Order not found."

        if order.status != 'approved':
             return False, "Payments can only be added to approved orders."
             
        amount = float(data['amount'])
        payment_method = data['payment_method']
        
        if amount <= 0 or amount > order.remaining_amount:
             return False, "Invalid payment amount"
             
        if order.customer_id:
            transaction = CustomerTransaction(
                customer_id=order.customer_id,
                order_id=order.id,
                transaction_type='payment',
                amount=amount,
                payment_method=payment_method,
                reference=f"Payment for Order #{order.id}",
                notes=data.get('notes', ''),
                created_by=current_user_id
            )
            db.session.add(transaction)
            
        cash_tx = CashTransaction(
            transaction_type='in',
            amount=amount,
            source='customer_payment',
            reference_id=order.id,
            description=f"Payment for Order #{order.id}",
            created_by=current_user_id
        )
        db.session.add(cash_tx)
        
        order.amount_paid = float(order.amount_paid) + amount
        
        db.session.commit()
        return True, f"Payment of Rs. {amount:,.2f} received"

    @staticmethod
    def get_all_orders():
         return Order.query.order_by(Order.created_at.desc()).all()
