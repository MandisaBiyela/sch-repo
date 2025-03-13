import os
import uuid
from werkzeug.utils import secure_filename
from google.cloud import storage

# Set the environment variable to the path of your service account key JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'golden-rush-440703-f9-d99ae1b17466.json'

# Create a storage client
storage_client = storage.Client()

# Define your bucket name
BUCKET_NAME = 'groupbookstoreproject'

# Define the allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_book_image(file):
    """
    Upload a book cover image to Google Cloud Storage
    
    Args:
        file: The file object from request.files
    
    Returns:
        string: The public URL of the uploaded image, or None if upload fails
    """
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        # Get the bucket
        bucket = storage_client.get_bucket(BUCKET_NAME)
        
        # Create a unique filename to avoid collisions
        original_filename = secure_filename(file.filename)
        unique_filename = f"book_covers/{uuid.uuid4()}_{original_filename}"
        
        # Create a blob and upload the file
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        
        # With uniform bucket-level access enabled, we don't use make_public()
        # Instead, we construct the URL directly
        image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_filename}"
        
        return image_url
        
    except Exception as e:
        print(f"Error uploading to Google Cloud Storage: {e}")
        return None

def delete_book_image(image_url):
    """
    Delete a book cover image from Google Cloud Storage
    
    Args:
        image_url: The public URL of the image to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Extract the blob name from the URL
        # URL format: https://storage.googleapis.com/groupbookstoreproject/book_covers/filename
        if not image_url or 'groupbookstoreproject' not in image_url:
            return False
            
        # Parse the URL to get the blob name
        blob_name = image_url.split('groupbookstoreproject/')[1]
        
        # Get the bucket and delete the blob
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.delete()
        
        return True
        
    except Exception as e:
        print(f"Error deleting from Google Cloud Storage: {e}")
        return False