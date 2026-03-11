from models import Product, Distributor, OrderItem, PurchaseOrderItem, PurchaseOrder, SupplierTransaction, StockMovement, CashTransaction, PKT
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
    def _handle_image_upload(product_name, files):
        if not files or 'image' not in files:
            return
            
        image_file = files.get('image')
        if not image_file or not image_file.filename:
            return
            
        import os
        import glob
        from flask import current_app
        from werkzeug.utils import secure_filename
        
        _, ext = os.path.splitext(image_file.filename)
        base_name = f"{secure_filename(product_name)}_img"
        filename = f"{base_name}{ext}"
        
        images_dir = os.path.join(current_app.static_folder, 'product_images')
        os.makedirs(images_dir, exist_ok=True)
        
        pattern = os.path.join(images_dir, f"{base_name}.*")
        for old_file in glob.glob(pattern):
            try:
                os.remove(old_file)
            except OSError:
                pass
                
        file_path = os.path.join(images_dir, filename)
        image_file.save(file_path)

    @staticmethod
    def _rename_product_image(old_name, new_name):
        import os
        import glob
        from flask import current_app
        from werkzeug.utils import secure_filename
        
        images_dir = os.path.join(current_app.static_folder, 'product_images')
        old_base = f"{secure_filename(old_name)}_img"
        new_base = f"{secure_filename(new_name)}_img"
        
        for old_file in glob.glob(os.path.join(images_dir, f"{old_base}.*")):
            _, ext = os.path.splitext(old_file)
            try:
                os.rename(old_file, os.path.join(images_dir, f"{new_base}{ext}"))
            except OSError:
                pass

    @staticmethod
    def create_product(data, files=None):
        name = data.get('name')
        stock = data.get('stock')
        sell = data.get('sell')

        # New cost structure
        purchase_price_raw = data.get('purchase_price') or data.get('cost') or '0'
        additional_expenses_raw = data.get('additional_expenses', '0') or '0'

        if not all([name, stock, sell]):
            return False, "Name, stock, and selling price are required.", None

        # Generate SKU if not provided
        sku = data.get('sku')
        if not sku:
            dist_code = data.get('distributor_id', 'GEN')
            name_part = name[:3].upper()
            sku = f"{dist_code}-{name_part}-{datetime.now().strftime('%y%m')}"
        
        try:
            purchase_price = float(purchase_price_raw)
            additional_expenses = float(additional_expenses_raw)
            cost_price = purchase_price + additional_expenses

            desc = data.get('description', '')
            unit_type = data.get('unit_type')
            qty_per_unit = data.get('qty_per_unit')
            if unit_type and qty_per_unit:
                import json
                meta = json.dumps({"type": unit_type, "qty": qty_per_unit})
                desc = f"{desc}\n---UNIT_META---\n{meta}"

            product = Product(
                name=name,
                description=desc,
                sku=sku,
                brand=data.get('brand') or None,
                target_vehicle=data.get('target_vehicle') or None,
                stock_quantity=int(stock),
                purchase_price=purchase_price,
                additional_expenses=additional_expenses,
                cost_price=cost_price,
                selling_price=float(sell),
                distributor_id=data.get('distributor_id') or None,
                part_number=data.get('part_number'),
                min_stock_level=int(data.get('min_stock', 5)),
                is_active=True
            )
            db.session.add(product)
            db.session.flush()

            ProductController._handle_image_upload(product.name, files)

            po_id = None
            if product.stock_quantity > 0:
                if product.distributor_id:
                    # Generate Purchase Order Invoice
                    total_cost = product.stock_quantity * cost_price
                    po = PurchaseOrder(
                        distributor_id=product.distributor_id,
                        created_by=current_user.id,
                        status='received',
                        total_amount=total_cost,
                        amount_paid=0.0,
                        payment_status='pending',
                        cam_number=data.get('cam_number'),
                        checked_by=data.get('checked_by'),
                        notes="Initial stock on product creation"
                    )
                    po.received_at = datetime.now(PKT)
                    db.session.add(po)
                    db.session.flush()
                    po_id = po.id
                    
                    po_item = PurchaseOrderItem(
                        purchase_order_id=po.id,
                        product_id=product.id,
                        quantity=product.stock_quantity,
                        unit_cost=cost_price,
                        total_cost=total_cost
                    )
                    db.session.add(po_item)
                    
                    if total_cost > 0:
                        ctx_purchase = SupplierTransaction(
                            distributor_id=product.distributor_id,
                            transaction_type='payable',
                            amount=total_cost,
                            purchase_order_id=po.id,
                            reference=f"Initial Stock PO #{po.id}",
                            created_by=current_user.id
                        )
                        db.session.add(ctx_purchase)
                        
                    stock_movement = StockMovement(
                        product_id=product.id,
                        quantity_change=product.stock_quantity,
                        quantity_before=0,
                        quantity_after=product.stock_quantity,
                        reference_type='purchase_receipt',
                        reference_id=po.id,
                        user_id=current_user.id
                    )
                    db.session.add(stock_movement)
                else:
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
            return True, "Product added successfully!", po_id
        except ValueError:
            return False, "Invalid numeric value provided for stock or price.", None

    @staticmethod
    def delete_product(product_id):
        product = db.session.get(Product, product_id)
        if not product:
            return False, "Product not found."
            
        product.is_active = False
        db.session.commit()
        return True, "Product deleted successfully!"
        
    @staticmethod
    def update_product(product_id, data, files=None):
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
             return False, "Product not found."
             
        try:
            old_name = product.name
            product.name = data.get('name', product.name)
            
            if old_name != product.name:
                ProductController._rename_product_image(old_name, product.name)
                
            ProductController._handle_image_upload(product.name, files)
            
            desc = data.get('description', '')
            unit_type = data.get('unit_type')
            qty_per_unit = data.get('qty_per_unit')
            if unit_type and qty_per_unit:
                import json
                meta = json.dumps({"type": unit_type, "qty": qty_per_unit})
                desc = f"{desc}\n---UNIT_META---\n{meta}"
                
            product.description = desc
            product.sku = data.get('sku', product.sku)
            product.brand = data.get('brand') or product.brand
            product.target_vehicle = data.get('target_vehicle') or product.target_vehicle

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

            # New cost structure
            purchase_price = float(data.get('purchase_price', product.purchase_price or 0))
            additional_expenses = float(data.get('additional_expenses', product.additional_expenses or 0))
            product.purchase_price = purchase_price
            product.additional_expenses = additional_expenses
            product.cost_price = purchase_price + additional_expenses

            product.selling_price = float(data.get('sell', product.selling_price))
            product.distributor_id = data.get('distributor_id') or None
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
         recent_sales = OrderItem.query.filter_by(product_id=product_id).order_by(OrderItem.id.desc()).limit(10).all()
         recent_purchases = PurchaseOrderItem.query.filter_by(product_id=product_id).order_by(PurchaseOrderItem.id.desc()).limit(10).all()
         
         return True, product, recent_sales, recent_purchases
         
    @staticmethod
    def restock_product(product_id, data):
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return False, "Product not found.", product, None
            
        try:
            qty_to_add = int(data.get('quantity', 0))
            new_purchase_price = float(data.get('purchase_price') or data.get('cost_price', product.purchase_price or 0))
            new_additional = float(data.get('additional_expenses', 0))
            new_cost = new_purchase_price + new_additional
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
                product.purchase_price = new_purchase_price
                product.additional_expenses = new_additional
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

                po_id = None
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
                    po.received_at = datetime.now(PKT)
                    db.session.add(po)
                    db.session.flush()
                    po_id = po.id
                    
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
                return True, f"Successfully restocked {qty_to_add} units. New log saved.", product, po_id
            else:
                return False, "Quantity must be greater than 0.", product, None
        except ValueError:
            return False, "Please enter valid numeric amounts.", product, None
