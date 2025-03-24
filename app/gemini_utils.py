import os
from google.generativeai import GenerativeModel
import google.generativeai as genai
from flask import current_app

def initialize_gemini():
    """Initialize the Gemini API client with the API key from environment variables."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        current_app.logger.error("GEMINI_API_KEY not found in environment variables")
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Gemini API: {str(e)}")
        return False

def generate_book_description(title, author):
    """
    Generate a book description using Gemini AI based on the title and author.
    
    Args:
        title (str): The title of the book
        author (str): The author of the book
        
    Returns:
        str: Generated book description or None if there was an error
    """
    if not title or not author:
        return None
    
    try:
        # Initialize the Gemini Pro model
        model = GenerativeModel('gemini-1.5-flash')
        
        # Craft a prompt that will generate a good book description

        prompt = f"""
        Write a compelling and persuasive book description for "{title}" by {author}.
        If you are familiar with the book, use only real details based on the actual book. Do not invent any characters, plot points, or themes.
        Make the description engaging and emotional, making the reader eager to buy the book.
        Keep it between 3-5 sentences and highlight why this book is a must-read.
        If you're unfamiliar with the book, do not attempt to invent a description. Instead, state that you have not heard of it and cannot provide a description.
        """


        # Generate the description
        response = model.generate_content(prompt)
        
        # Return the generated text
        if response.text:
            return response.text.strip()
        return None
    
    except Exception as e:
        current_app.logger.error(f"Error generating book description: {str(e)}")
        return None