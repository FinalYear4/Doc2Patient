# app/translate.py

import requests
from flask import current_app

def translate_text(text, target_language, source_language='en'):
    """Translates text using the LibreTranslate API."""
    if not text:
        return ""
    
    # We will use a free, public instance of LibreTranslate
    api_url = "https://translate.argosopentech.com/translate"
    
    payload = {
        'q': text,
        'source': source_language,
        'target': target_language
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        json_response = response.json()
        return json_response.get('translatedText', text)
    
    except requests.exceptions.RequestException as e:
        # If the API call fails for any reason, log the error and return the original text
        current_app.logger.error(f"Translation API error: {e}")
        return text