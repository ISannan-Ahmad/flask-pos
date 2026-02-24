from .auth import auth_bp
from .main import main_bp
from .products import products_bp
from .distributors import distributors_bp
from .purchases import purchases_bp
from .sales import sales_bp
from .expenses import expenses_bp
from .customers import customers_bp
from .analytics import analytics_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(distributors_bp, url_prefix='/distributors')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(expenses_bp, url_prefix='/expenses')
    app.register_blueprint(customers_bp, url_prefix='/customers')
