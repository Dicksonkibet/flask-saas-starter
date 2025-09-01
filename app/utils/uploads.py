
import os
import secrets
from PIL import Image
from flask import current_app, request
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename, allowed_extensions=ALLOWED_EXTENSIONS):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_filename(filename):
    """Generate unique filename to prevent conflicts"""
    name, ext = os.path.splitext(secure_filename(filename))
    unique_name = f"{name}_{secrets.token_hex(8)}{ext}"
    return unique_name

def save_uploaded_file(file, folder='general'):
    """Save uploaded file and return file info"""
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type"
    
    # Create upload directory if it doesn't exist
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Generate unique filename
    filename = generate_unique_filename(file.filename)
    file_path = os.path.join(upload_path, filename)
    
    try:
        file.save(file_path)
        
        # If it's an image, create thumbnail
        if allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            create_thumbnail(file_path)
        
        return {
            'filename': filename,
            'original_name': file.filename,
            'path': file_path,
            'url': f"/uploads/{folder}/{filename}",
            'size': os.path.getsize(file_path)
        }, None
        
    except Exception as e:
        return None, f"Failed to save file: {str(e)}"

def create_thumbnail(image_path, size=(300, 300)):
    """Create thumbnail for uploaded images"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            name, ext = os.path.splitext(image_path)
            thumbnail_path = f"{name}_thumb{ext}"
            img.save(thumbnail_path, optimize=True, quality=85)
            
            return thumbnail_path
    except Exception as e:
        current_app.logger.error(f"Failed to create thumbnail: {str(e)}")
        return None
