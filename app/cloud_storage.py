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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_book_image(file):
    """
    Upload a book cover image to Google Cloud Storage.
    
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
        
        # Secure filename and create unique path
        original_filename = secure_filename(file.filename)
        unique_filename = f"book_covers/{uuid.uuid4()}_{original_filename}"
        
        # Create a blob and upload the file
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Construct the public URL
        image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_filename}"
        
        return image_url
        
    except Exception as e:
        print(f"Error uploading image to Google Cloud Storage: {e}")
        return None

def upload_book_file(file):
    """
    Upload a book file (PDF or image) to Google Cloud Storage.
    
    Args:
        file: The file object from request.files
    
    Returns:
        string: The public URL of the uploaded file, or None if upload fails
    """
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        # Get the bucket
        bucket = storage_client.get_bucket(BUCKET_NAME)
        
        # Determine file type and folder
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        
        if file_extension in {'png', 'jpg', 'jpeg', 'gif'}:
            folder = "book_covers"
        elif file_extension == "pdf":
            folder = "book_pdfs"
        else:
            return None  # Just in case
        
        # Create a unique filename to avoid collisions
        unique_filename = f"{folder}/{uuid.uuid4()}_{original_filename}"
        
        # Create a blob and upload the file
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Construct the public URL
        file_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_filename}"
        
        return file_url
        
    except Exception as e:
        print(f"Error uploading file to Google Cloud Storage: {e}")
        return None

def delete_book_file(file_url):
    """
    Delete a book cover image or a PDF from Google Cloud Storage.
    
    Args:
        file_url: The public URL of the file to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Extract the blob name from the URL
        if not file_url or BUCKET_NAME not in file_url:
            return False
            
        # Parse the URL to get the blob name
        blob_name = file_url.split(f"{BUCKET_NAME}/")[1]
        
        # Get the bucket and delete the blob
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.delete()
        
        return True
        
    except Exception as e:
        print(f"Error deleting from Google Cloud Storage: {e}")
        return False