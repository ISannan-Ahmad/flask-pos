from models import PurchaseOrder, Distributor, Product, PurchaseOrderItem, SupplierTransaction, StockMovement, CashTransaction
from extensions import db
from datetime import datetime
from flask_login import current_user

class PurchasesController:
    @staticmethod
    def get_all_purchases():
        return PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()

    @staticmethod
    def create_purchase_order(data, current_user_id):
        distributor_id = data.get('distributor_id')
        if not distributor_id:
             return False, "Please select a distributor", None
             
        purchase_order = PurchaseOrder(
            distributor_id=distributor_id,
            created_by=current_user_id,
            invoice_number=data.get('invoice_number'),
            notes=data.get('notes')
        )
        db.session.add(purchase_order)
        db.session.flush()
        
        total_amount = 0
        product_ids = data.getlist('product_id[]')
        quantities = data.getlist('quantity[]')
        unit_costs = data.getlist('unit_cost[]')
        
        has_items = False
        for i in range(len(product_ids)):
            if product_ids[i] and quantities[i] and unit_costs[i]:
                qty = int(quantities[i])
                cost = float(unit_costs[i])
                total = qty * cost
                
                item = PurchaseOrderItem(
                    purchase_order_id=purchase_order.id,
                    product_id=int(product_ids[i]),
                    quantity=qty,
                    unit_cost=cost,
                    total_cost=total
                )
                db.session.add(item)
                total_amount += total
                has_items = True
        
        if has_items:
            purchase_order.total_amount = total_amount
            db.session.commit()
            return True, "Purchase order created successfully!", purchase_order
        else:
            db.session.rollback()
            return False, "Purchase order must have at least one item", None

    @staticmethod
    def get_purchase_order(order_id):
        return db.session.get(PurchaseOrder, order_id)

    @staticmethod
    def receive_purchase_order(order_id):
        purchase = db.session.get(PurchaseOrder, order_id)
        if not purchase:
             return False, "Purchase order not found."
             
        if purchase.status == 'received':
             return False, "Purchase order already received"
             
        # Create Payable Transaction for received goods
        payable_tx = SupplierTransaction(
            distributor_id=purchase.distributor_id,
            purchase_order_id=purchase.id,
            transaction_type='payable',
            amount=purchase.total_amount,
            reference=f"Purchase Order #{purchase.id}",
            created_by=current_user.id
        )
        db.session.add(payable_tx)

        for item in purchase.items:
            product = db.session.get(Product, item.product_id, with_for_update={"of": Product})
            if product:
                qty_before = product.stock_quantity
                
                # Calculate Weighted Average Cost
                current_value = qty_before * float(product.cost_price or 0)
                new_value = item.total_cost
                total_qty = qty_before + item.quantity
                wac = (current_value + float(new_value)) / total_qty if total_qty > 0 else float(item.unit_cost)
                
                product.cost_price = wac
                product.stock_quantity = total_qty
                
                # Write StockMovement log
                stock_movement = StockMovement(
                    product_id=product.id,
                    quantity_change=item.quantity,
                    quantity_before=qty_before,
                    quantity_after=total_qty,
                    reference_type='purchase_receipt',
                    reference_id=purchase.id,
                    user_id=current_user.id
                )
                db.session.add(stock_movement)
        
        purchase.status = 'received'
        purchase.received_at = datetime.utcnow()
        
        if purchase.amount_paid > 0:
            purchase.payment_status = 'partial' if purchase.remaining_amount > 0 else 'paid'
        
        db.session.commit()
        return True, "Purchase order received and stock updated!"

    @staticmethod
    def add_purchase_payment(order_id, data, current_user_id):
        purchase = db.session.get(PurchaseOrder, order_id)
        if not purchase:
             return False, "Purchase order not found."
             
        amount = float(data['amount'])
        payment_method = data['payment_method']
        
        if amount <= 0:
             return False, "Invalid payment amount"
             
        # Log to Supplier Ledger
        transaction = SupplierTransaction(
            distributor_id=purchase.distributor_id,
            purchase_order_id=purchase.id,
            transaction_type='payment',
            amount=amount,
            payment_method=payment_method,
            reference=f"Payment for PO #{purchase.id}",
            notes=data.get('notes', ''),
            created_by=current_user_id
        )
        db.session.add(transaction)
        
        # Log to Cash Book
        cash_tx = CashTransaction(
            transaction_type='out',
            amount=amount,
            source='supplier_payment',
            reference_id=purchase.id,
            description=f"Payment for PO #{purchase.id}",
            created_by=current_user_id
        )
        db.session.add(cash_tx)
        
        purchase.amount_paid = float(purchase.amount_paid) + amount
        
        if purchase.amount_paid >= purchase.total_amount:
            purchase.payment_status = 'paid'
        else:
            purchase.payment_status = 'partial'
        
        db.session.commit()
        return True, f"Payment of Rs. {amount:,.2f} recorded"
