from functools import wraps
from flask import abort, current_app
from flask_login import current_user
import os
import glob
from werkzeug.utils import secure_filename

def role_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, 'role', None) != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return wrapper

def get_product_image_url(product_name):
    base_name = f"{secure_filename(product_name)}_img"
    
    try:
        static_folder = current_app.static_folder
        images_dir = os.path.join(static_folder, 'product_images')
        if not os.path.exists(images_dir):
            return None
        
        pattern = os.path.join(images_dir, f"{base_name}.*")
        matches = glob.glob(pattern)
        if matches:
            filename = os.path.basename(matches[0])
            return f"product_images/{filename}"
    except RuntimeError:
        # Working outside of application context
        pass
    return None
