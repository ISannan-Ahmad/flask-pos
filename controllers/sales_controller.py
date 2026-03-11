from models import Order, Product, OrderItem, CustomerTransaction, CashTransaction, StockMovement, PKT
from extensions import db
from datetime import datetime, timedelta, timezone
from controllers.audit_controller import AuditController
from flask_login import current_user

class SalesController:
    @staticmethod
    def create_order(data, current_user_id, is_admin=False):
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
        
        # Customer info fields
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')
        customer_email = data.get('customer_email', '')
            
        new_order = Order(
            created_by=current_user_id,
            status='draft',
            order_type=order_type,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            customer_email=customer_email,
            total_amount=0.0,
            total_profit=0.0,
            amount_paid=0.0
        )
        
        if order_type == 'credit_sale':
            new_order.due_date = datetime.now(PKT) + timedelta(days=30)
        
        db.session.add(new_order)
        db.session.flush()

        for product, qty in parsed_items:
            price_value = data.get(f'price_{product.id}')
            item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=qty,
                price=float(price_value) if price_value else None
            )
            db.session.add(item)

        # Admin direct-confirm: approve immediately
        if is_admin:
            total = 0
            total_profit = 0
            
            for item in new_order.items:
                if not item.price:
                    # Admin must provide prices via price_{product_id} fields
                    db.session.rollback()
                    return False, "All items must have a selling price set."
                
                product = db.session.get(Product, item.product_id, with_for_update={"of": Product})
                if product.stock_quantity < item.quantity:
                    db.session.rollback()
                    return False, f"Not enough stock for {product.name}. Available: {product.stock_quantity}"
                
                total += float(item.price) * item.quantity
                profit = (float(item.price) - float(product.cost_price or 0)) * item.quantity
                total_profit += profit
                
                qty_before = product.stock_quantity
                product.stock_quantity -= item.quantity
                
                stock_movement = StockMovement(
                    product_id=product.id,
                    quantity_change=-item.quantity,
                    quantity_before=qty_before,
                    quantity_after=product.stock_quantity,
                    reference_type='sale',
                    reference_id=new_order.id,
                    user_id=current_user_id
                )
                db.session.add(stock_movement)
            
            new_order.total_amount = total
            new_order.total_profit = total_profit
            new_order.status = 'approved'
            new_order.approved_by = current_user_id
            new_order.cam_number = data.get('cam_number')
            new_order.checked_by = data.get('checked_by')
            
            try:
                amount_paid = float(data.get('amount_paid', 0))
                if amount_paid < 0:
                    amount_paid = 0
            except (ValueError, TypeError):
                amount_paid = 0.0
            
            payment_method = data.get('payment_method', 'cash')
            
            if order_type == 'sale' and amount_paid == 0:
                amount_paid = float(total)
            if amount_paid > float(total):
                amount_paid = float(total)
            
            new_order.amount_paid = amount_paid
            
            # Handle Ledgers
            if new_order.customer_id and order_type == 'credit_sale':
                receivable_tx = CustomerTransaction(
                    customer_id=new_order.customer_id,
                    order_id=new_order.id,
                    transaction_type='receivable',
                    amount=total,
                    reference=f"Invoice #{new_order.id}",
                    created_by=current_user_id
                )
                db.session.add(receivable_tx)
                
                if amount_paid > 0:
                    payment_tx = CustomerTransaction(
                        customer_id=new_order.customer_id,
                        order_id=new_order.id,
                        transaction_type='payment',
                        amount=amount_paid,
                        payment_method=payment_method,
                        reference=f"Payment for Order #{new_order.id}",
                        created_by=current_user_id
                    )
                    db.session.add(payment_tx)
            
            if amount_paid > 0:
                cash_tx = CashTransaction(
                    transaction_type='in',
                    amount=amount_paid,
                    source='sales',
                    reference_id=new_order.id,
                    description=f"Payment for Order #{new_order.id}",
                    created_by=current_user_id
                )
                db.session.add(cash_tx)
            
            AuditController.log(
                user_id=current_user_id,
                action='Create & Approve Order',
                table_name='order',
                record_id=new_order.id,
                old_value=None,
                new_value={'status': 'approved', 'total': float(total), 'amount_paid': amount_paid}
            )
            
            db.session.commit()
            return True, f"Order #{new_order.id} created and approved!", new_order.id

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
        
        # Handle payment from approval form
        try:
            amount_paid = float(data.get('amount_paid', 0))
            if amount_paid < 0:
                return False, "Payment amount cannot be negative."
        except (ValueError, TypeError):
            amount_paid = 0.0
        
        payment_method = data.get('payment_method', 'cash')
        
        # For cash sales, default to fully paid if no amount specified
        if order.order_type == 'sale' and amount_paid == 0:
            amount_paid = float(total)
        
        # Cap payment at total
        if amount_paid > float(total):
            amount_paid = float(total)
            
        order.amount_paid = amount_paid
        order.cam_number = data.get('cam_number')
        order.checked_by = data.get('checked_by')
        
        # Handle Ledgers:
        if order.customer_id and order.order_type == 'credit_sale':
            # Increase customer debt (receivable)
            receivable_tx = CustomerTransaction(
                customer_id=order.customer_id,
                order_id=order.id,
                transaction_type='receivable',
                amount=total,
                reference=f"Invoice #{order.id}",
                created_by=current_user_id
            )
            db.session.add(receivable_tx)
            
            if amount_paid > 0:
                # Record payment against customer account
                payment_tx = CustomerTransaction(
                    customer_id=order.customer_id,
                    order_id=order.id,
                    transaction_type='payment',
                    amount=amount_paid,
                    payment_method=payment_method,
                    reference=f"Payment for Order #{order.id}",
                    created_by=current_user_id
                )
                db.session.add(payment_tx)

        if amount_paid > 0:
            # Add to Cash Book
            cash_tx = CashTransaction(
                transaction_type='in',
                amount=amount_paid,
                source='sales',
                reference_id=order.id,
                description=f"Payment for Order #{order.id}",
                created_by=current_user_id
            )
            db.session.add(cash_tx)
        
        AuditController.log(
            user_id=current_user_id,
            action='Approve Order',
            table_name='order',
            record_id=order.id,
            old_value={'status': 'draft'},
            new_value={'status': 'approved', 'total': float(total), 'amount_paid': amount_paid, 'payment_method': payment_method}
        )
        
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
    def get_all_orders(order_type='all', start_date=None, end_date=None, status=None):
        query = Order.query
        
        if order_type != 'all':
            query = query.filter_by(order_type=order_type)
            
        if status:
            query = query.filter_by(status=status)
        
        if start_date:
            query = query.filter(Order.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Order.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        orders = query.order_by(Order.created_at.desc()).all()
        
        # Summary totals (from filtered approved orders only)
        approved = [o for o in orders if o.status == 'approved']
        cash_total = sum(float(o.total_amount) for o in approved if o.order_type == 'sale')
        credit_total = sum(float(o.total_amount) for o in approved if o.order_type == 'credit_sale')
        cash_count = sum(1 for o in approved if o.order_type == 'sale')
        credit_count = sum(1 for o in approved if o.order_type == 'credit_sale')
        
        return {
            'orders': orders,
            'cash_total': cash_total,
            'credit_total': credit_total,
            'grand_total': cash_total + credit_total,
            'cash_count': cash_count,
            'credit_count': credit_count,
            'total_count': cash_count + credit_count,
        }

    @staticmethod
    def cancel_order(order_id, current_user_id):
        order = Order.query.get(order_id)
        if not order:
            return False, "Order not found."
        if order.status != 'draft':
            return False, "Only draft orders can be cancelled."
        
        order.status = 'cancelled'
        AuditController.log(
            user_id=current_user_id,
            action='Cancel Order',
            table_name='order',
            record_id=order.id,
            old_value={'status': 'draft'},
            new_value={'status': 'cancelled'}
        )
        db.session.commit()
        return True, f"Order #{order.id} has been cancelled."

    @staticmethod
    def remove_order_item(order_id, item_id, current_user_id):
        from controllers.audit_controller import AuditController
        
        order = Order.query.get(order_id)
        if not order:
            return False, "Order not found."
            
        if order.status != 'draft':
            return False, "Only draft orders can be modified."
            
        item = db.session.get(OrderItem, item_id)
        if not item or item.order_id != order.id:
            return False, "Item not found in this order."
            
        product_name = item.product.name
        
        if len(order.items) <= 1:
            order.status = 'cancelled'
            AuditController.log(
                user_id=current_user_id,
                action='Cancel Order (Last Item Removed)',
                table_name='order',
                record_id=order.id,
                old_value={'status': 'draft'},
                new_value={'status': 'cancelled'}
            )
            db.session.delete(item)
            db.session.commit()
            return True, f"Last item removed. Order #{order.id} has been automatically cancelled."
            
        db.session.delete(item)
        db.session.commit()
        return True, f"Item {product_name} has been removed from the order."
