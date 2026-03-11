from models import Order, OrderItem, Product, StockMovement, CustomerTransaction, CashTransaction, PKT, PurchaseOrder, PurchaseOrderItem, SupplierTransaction
from extensions import db
from datetime import datetime

class ReturnController:
    @staticmethod
    def get_customer_returns():
        return Order.query.filter_by(order_type='return').order_by(Order.created_at.desc()).all()

    @staticmethod
    def get_supplier_returns():
        return PurchaseOrder.query.filter_by(status='returned').order_by(PurchaseOrder.created_at.desc()).all()

    @staticmethod
    def get_defective_inventory():
        return StockMovement.query.filter_by(reference_type='customer_return_defective').order_by(StockMovement.timestamp.desc()).all()

    @staticmethod
    def process_customer_return(data, current_user_id):
        order_id = data.get('order_id')
        product_id = data.get('product_id')
        qty_returned = int(data.get('quantity', 0))
        reason = data.get('reason', '')
        
        if qty_returned <= 0:
            return False, "Quantity must be greater than zero.", None
            
        try:
            order_id = int(order_id)
            product_id = int(product_id)
        except (TypeError, ValueError):
            return False, "Invalid Order ID or Product ID.", None
            
        original_order = db.session.get(Order, order_id)
        if not original_order or original_order.status != 'approved':
            return False, "Valid approved original order not found.", None
            
        # Find item in original order to get price
        original_item = next((item for item in original_order.items if item.product_id == int(product_id)), None)
        if not original_item:
            return False, "Product not found in the original order.", None
            
        if qty_returned > original_item.quantity:
            return False, f"Cannot return more than originally sold ({original_item.quantity}).", None
            
        # If reason is missing
        if not reason:
            return False, "A reason must be selected.", None
            
        product = db.session.get(Product, product_id)
        return_value = float(original_item.price) * qty_returned
        
        # Ensure we have notes
        note = data.get('notes', '')
        
        # Create a negative order to represent the return
        return_order = Order(
            created_by=current_user_id,
            approved_by=current_user_id,
            customer_id=original_order.customer_id,
            customer_name=original_order.customer_name,
            customer_phone=original_order.customer_phone,
            status='approved',
            order_type='return',
            total_amount=-return_value,  # Negative so it deducts from total sales sum
            total_profit=-( (float(original_item.price) - float(product.cost_price or 0)) * qty_returned ),
            amount_paid=-return_value, # Automatically "refunded" or adjusted
            cam_number=f"Return Ref: Order #{original_order.id}",
            checked_by=f"Reason: {reason} | {note}"
        )
        db.session.add(return_order)
        db.session.flush()
        
        return_item = OrderItem(
            order_id=return_order.id,
            product_id=product.id,
            quantity=qty_returned,
            price=original_item.price
        )
        db.session.add(return_item)
        
        # Inventory Logic
        qty_before = product.stock_quantity
        is_defective = reason == 'Defective Product'
        
        if not is_defective:
            # Add back to normal inventory
            product.stock_quantity += qty_returned
            ref_type = 'customer_return'
        else:
            # Do NOT add back to inventory. It's defective.
            ref_type = 'customer_return_defective'
            
        stock_movement = StockMovement(
            product_id=product.id,
            quantity_change=qty_returned, # Representing goods coming back
            quantity_before=qty_before,
            quantity_after=product.stock_quantity, # Will be same as before if defective!
            reference_type=ref_type,
            reference_id=return_order.id,
            user_id=current_user_id
        )
        db.session.add(stock_movement)
        
        # Financial Logic
        # If the original sale was on credit, we reduce their receivable balance.
        if original_order.customer_id:
            # We add a negative receivable transaction to reduce balance
            customer_tx = CustomerTransaction(
                customer_id=original_order.customer_id,
                order_id=return_order.id,
                transaction_type='receivable',
                amount=-return_value,
                reference=f"Return from Order #{original_order.id} - {reason}",
                created_by=current_user_id
            )
            db.session.add(customer_tx)
            
        # Logging Audit
        from controllers.audit_controller import AuditController
        AuditController.log(
            user_id=current_user_id,
            action='Process Customer Return',
            table_name='order',
            record_id=return_order.id,
            old_value=None,
            new_value={'reason': reason, 'refund': return_value, 'defective': is_defective}
        )
        
        db.session.commit()
        return True, f"Return processed successfully. Receipt #{return_order.id}", return_order.id

    @staticmethod
    def process_supplier_return(data, current_user_id):
        po_id = data.get('purchase_order_id')
        product_id = data.get('product_id')
        qty_returned = int(data.get('quantity', 0))
        reason = data.get('reason', '')
        
        if qty_returned <= 0:
            return False, "Quantity must be greater than zero.", None
            
        try:
            po_id = int(po_id)
            product_id = int(product_id)
        except (TypeError, ValueError):
            return False, "Invalid Purchase Order ID or Product ID.", None
            
        original_po = db.session.get(PurchaseOrder, po_id)
        if not original_po or original_po.status != 'received':
            return False, "Valid received purchase order not found.", None
            
        original_item = next((item for item in original_po.items if item.product_id == int(product_id)), None)
        if not original_item:
            return False, "Product not found in original purchase order.", None
            
        if qty_returned > original_item.quantity:
            return False, f"Cannot return more than originally purchased ({original_item.quantity}).", None
            
        product = db.session.get(Product, product_id)
        if product.stock_quantity < qty_returned:
             return False, "Not enough current stock to return to supplier.", None
             
        if not reason:
             return False, "A reason must be given.", None
             
        return_value = float(original_item.unit_cost) * qty_returned
        
        note = data.get('notes', '')
        
        # Create negative PO for supplier return
        return_po = PurchaseOrder(
            distributor_id=original_po.distributor_id,
            created_by=current_user_id,
            status='returned',
            total_amount=-return_value,
            amount_paid=0.0, # Handled via payable reduction
            invoice_number=f"Return Ref: PO #{original_po.id}",
            notes=f"Supplier Return. Reason: {reason} | {note}",
            received_at=datetime.now(PKT)
        )
        db.session.add(return_po)
        db.session.flush()
        
        return_item = PurchaseOrderItem(
            purchase_order_id=return_po.id,
            product_id=product.id,
            quantity=qty_returned,
            unit_cost=original_item.unit_cost,
            total_cost=-return_value
        )
        db.session.add(return_item)
        
        # Deduct from Inventory
        qty_before = product.stock_quantity
        product.stock_quantity -= qty_returned
        
        stock_movement = StockMovement(
            product_id=product.id,
            quantity_change=-qty_returned,
            quantity_before=qty_before,
            quantity_after=product.stock_quantity,
            reference_type='supplier_return',
            reference_id=return_po.id,
            user_id=current_user_id
        )
        db.session.add(stock_movement)
        
        # Adjust Supplier Balance (reduce the payable)
        supplier_tx = SupplierTransaction(
            distributor_id=original_po.distributor_id,
            purchase_order_id=return_po.id,
            transaction_type='payable',
            amount=-return_value,
            reference=f"Return to supplier - PO #{original_po.id}",
            notes=reason,
            created_by=current_user_id
        )
        db.session.add(supplier_tx)
        
        db.session.commit()
        return True, f"Supplier return processed successfully. Reference #{return_po.id}", return_po.id
