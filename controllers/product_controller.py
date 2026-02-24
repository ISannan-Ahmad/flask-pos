from models import Product, Distributor, OrderItem, PurchaseOrderItem, PurchaseOrder, SupplierTransaction, StockMovement, CashTransaction
from extensions import db
from datetime import datetime
from flask_login import current_user

class ProductController:
    @staticmethod
    def get_all_products():
        return Product.query.filter_by(is_active=True).all()

    @staticmethod
    def get_all_distributors():
        return Distributor.query.all()
        
    @staticmethod
    def get_product_by_id(product_id):
        product = db.session.get(Product, product_id)
        if product and product.is_active:
            return product
        return None

    @staticmethod
    def create_product(data):
        name = data.get('name')
        stock = data.get('stock')
        cost = data.get('cost')
        sell = data.get('sell')

        if not all([name, stock, cost, sell]):
            return False, "Name, stock, cost price, and selling price are required."

        # Generate SKU if not provided
        sku = data.get('sku')
        if not sku:
            dist_code = data.get('distributor_id', 'GEN')
            name_part = name[:3].upper()
            sku = f"{dist_code}-{name_part}-{datetime.now().strftime('%y%m')}"
        
        try:
            product = Product(
                name=name,
                description=data.get('description', ''),
                sku=sku,
                stock_quantity=int(stock),
                cost_price=float(cost),
                selling_price=float(sell),
                distributor_id=data.get('distributor_id') or None,
                vehicle_type=data.get('vehicle_type'),
                vehicle_model=data.get('vehicle_model'),
                part_number=data.get('part_number'),
                min_stock_level=int(data.get('min_stock', 5)),
                is_active=True
            )
            db.session.add(product)
            db.session.flush()

            if product.stock_quantity > 0:
                stock_movement = StockMovement(
                    product_id=product.id,
                    quantity_change=product.stock_quantity,
                    quantity_before=0,
                    quantity_after=product.stock_quantity,
                    reference_type='manual_adjustment',
                    user_id=current_user.id
                )
                db.session.add(stock_movement)

            db.session.commit()
            return True, "Product added successfully!"
        except ValueError:
            return False, "Invalid numeric value provided for stock or price."

    @staticmethod
    def delete_product(product_id):
        product = db.session.get(Product, product_id)
        if not product:
            return False, "Product not found."
            
        product.is_active = False
        db.session.commit()
        return True, "Product deleted successfully!"
        
    @staticmethod
    def update_product(product_id, data):
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
             return False, "Product not found."
             
        try:
            product.name = data.get('name', product.name)
            product.description = data.get('description', '')
            product.sku = data.get('sku', product.sku)
            stock_qty = int(data.get('stock', product.stock_quantity))
            
            if stock_qty != product.stock_quantity:
                 qty_change = stock_qty - product.stock_quantity
                 stock_movement = StockMovement(
                    product_id=product.id,
                    quantity_change=qty_change,
                    quantity_before=product.stock_quantity,
                    quantity_after=stock_qty,
                    reference_type='manual_adjustment',
                    user_id=current_user.id
                )
                 db.session.add(stock_movement)
                 product.stock_quantity = stock_qty
                 
            product.cost_price = float(data.get('cost', product.cost_price))
            product.selling_price = float(data.get('sell', product.selling_price))
            product.distributor_id = data.get('distributor_id') or None
            product.vehicle_type = data.get('vehicle_type')
            product.vehicle_model = data.get('vehicle_model')
            product.part_number = data.get('part_number')
            product.min_stock_level = int(data.get('min_stock', 5))
            
            db.session.commit()
            return True, "Product updated successfully!"
        except (ValueError, TypeError):
             return False, "Invalid data provided."
             
    @staticmethod
    def get_product_details(product_id):
         product = db.session.get(Product, product_id)
         if not product or not product.is_active:
              return False, None, None, None, "Product not found."
         # Get recent order history for this product
         recent_sales = OrderItem.query.filter_by(product_id=product_id).order_by(OrderItem.id.desc()).limit(10).all()
         recent_purchases = PurchaseOrderItem.query.filter_by(product_id=product_id).order_by(PurchaseOrderItem.id.desc()).limit(10).all()
         
         return True, product, recent_sales, recent_purchases
         
    @staticmethod
    def restock_product(product_id, data):
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return False, "Product not found.", product
            
        try:
            qty_to_add = int(data.get('quantity', 0))
            new_cost = float(data.get('cost_price', product.cost_price or 0))
            new_sell = float(data.get('selling_price', product.selling_price or 0))
            amount_paid = float(data.get('amount_paid', 0))
            
            if qty_to_add > 0:
                current_qty = product.stock_quantity
                current_value = current_qty * float(product.cost_price or 0)
                new_value = qty_to_add * new_cost
                total_qty = current_qty + qty_to_add
                
                # Weighted Average Cost calculation
                wac = (current_value + new_value) / total_qty if total_qty > 0 else new_cost
                
                product.stock_quantity = total_qty
                product.cost_price = wac
                product.selling_price = new_sell
                
                stock_movement = StockMovement(
                    product_id=product.id,
                    quantity_change=qty_to_add,
                    quantity_before=current_qty,
                    quantity_after=product.stock_quantity,
                    reference_type='restock',
                    user_id=current_user.id
                )
                db.session.add(stock_movement)

                if product.distributor_id:
                    total_cost = qty_to_add * new_cost
                    payment_status = 'paid'
                    if amount_paid == 0:
                        payment_status = 'pending'
                    elif amount_paid < total_cost:
                        payment_status = 'partial'
                                            
                    po = PurchaseOrder(
                        distributor_id=product.distributor_id,
                        created_by=current_user.id,
                        status='received',
                        total_amount=total_cost,
                        amount_paid=amount_paid,
                        payment_status=payment_status,
                        notes="Direct restock from product page"
                    )
                    po.received_at = datetime.utcnow()
                    db.session.add(po)
                    db.session.flush()
                    
                    po_item = PurchaseOrderItem(
                        purchase_order_id=po.id,
                        product_id=product.id,
                        quantity=qty_to_add,
                        unit_cost=new_cost,
                        total_cost=total_cost
                    )
                    db.session.add(po_item)
                    
                    stock_movement.reference_id = po.id
                    
                    if total_cost > 0:
                        ctx_purchase = SupplierTransaction(
                            distributor_id=product.distributor_id,
                            transaction_type='payable',
                            amount=total_cost,
                            purchase_order_id=po.id,
                            reference=f"Direct Restock PO #{po.id}",
                            created_by=current_user.id
                        )
                        db.session.add(ctx_purchase)
                        
                        if amount_paid > 0:
                            ctx_pay = SupplierTransaction(
                                distributor_id=product.distributor_id,
                                transaction_type='payment',
                                amount=amount_paid,
                                purchase_order_id=po.id,
                                reference=f"Payment for Restock PO #{po.id}",
                                created_by=current_user.id
                            )
                            db.session.add(ctx_pay)
                            
                            cash_tx = CashTransaction(
                                transaction_type='out',
                                amount=amount_paid,
                                source='supplier_payment',
                                reference_id=po.id,
                                description=f"Payment for Restock PO #{po.id}",
                                created_by=current_user.id
                             )
                            db.session.add(cash_tx)
                            
                db.session.commit()
                return True, f"Successfully restocked {qty_to_add} units. New log saved.", product
            else:
                return False, "Quantity must be greater than 0.", product
        except ValueError:
            return False, "Please enter valid numeric amounts.", product
