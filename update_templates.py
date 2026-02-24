import os
import re

template_dir = r"f:\Programming\Arc_Innovata_projects\flask_pos\templates"

# Mapping of old endpoint name to new blueprint.endpoint name
replacements = {
    r"url_for\('dashboard'\)": "url_for('main.dashboard')",
    r"url_for\('login'\)": "url_for('auth.login')",
    r"url_for\('logout'\)": "url_for('auth.logout')",
    r"url_for\('products'\)": "url_for('products.products')",
    r"url_for\('manage_products'\)": "url_for('products.manage_products')",
    
    # regex for url_for with args
    r"url_for\('delete_product'": "url_for('products.delete_product'",
    r"url_for\('edit_product'": "url_for('products.edit_product'",
    r"url_for\('distributors'\)": "url_for('distributors.list_distributors')",
    r"url_for\('add_distributor'\)": "url_for('distributors.add_distributor')",
    r"url_for\('distributor_detail'": "url_for('distributors.distributor_detail'",
    r"url_for\('purchase_orders'\)": "url_for('purchases.purchase_orders')",
    r"url_for\('create_purchase_order'\)": "url_for('purchases.create_purchase_order')",
    r"url_for\('purchase_order_detail'": "url_for('purchases.purchase_order_detail'",
    r"url_for\('receive_purchase_order'": "url_for('purchases.receive_purchase_order'",
    r"url_for\('add_purchase_payment'": "url_for('purchases.add_purchase_payment'",
    r"url_for\('create_order'\)": "url_for('sales.create_order')",
    r"url_for\('order_detail'": "url_for('sales.order_detail'",
    r"url_for\('add_order_payment'": "url_for('sales.add_order_payment'",
    r"url_for\('receipt'": "url_for('sales.receipt'",
    r"url_for\('analytics'\)": "url_for('analytics.analytics')",
    r"url_for\('analytics',": "url_for('analytics.analytics',",
    r"url_for\('aging_report'\)": "url_for('analytics.aging_report')",
    r"url_for\('ledger'\)": "url_for('analytics.ledger')",
    r"url_for\('ledger',": "url_for('analytics.ledger',"
}

for filename in os.listdir(template_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(template_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        for old, new in replacements.items():
            content = re.sub(old, new, content)
            
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {filename}")
