import os
from google.cloud import language_v1
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_summary(text):
    """
    Generate a concise summary and extract key points from the text
    using Google Natural Language API
    
    Args:
        text (str): Text content to summarize
        
    Returns:
        tuple: (summary, list of key points)
    """
    # Initialize the Natural Language API client
    client = language_v1.LanguageServiceClient()
    
    # Create a document object with the text
    document = language_v1.Document(
        content=text,
        type_=language_v1.Document.Type.PLAIN_TEXT
    )
    
    # Analyze entities to find key topics
    entity_response = client.analyze_entities(
        document=document,
        encoding_type=language_v1.EncodingType.UTF8
    )
    
    # Extract key entities with high salience
    key_entities = []
    for entity in entity_response.entities:
        if entity.salience > 0.1:  # Only include significant entities
            key_entities.append(entity.name)
    
    # Analyze document sentiment
    sentiment_response = client.analyze_sentiment(
        document=document,
        encoding_type=language_v1.EncodingType.UTF8
    )
    document_sentiment = sentiment_response.document_sentiment
    
    # Analyze the document syntax
    syntax_response = client.analyze_syntax(
        document=document,
        encoding_type=language_v1.EncodingType.UTF8
    )
    
    # Analyze document classifications
    try:
        classification_response = client.classify_text(document=document)
        categories = [category.name for category in classification_response.categories]
    except Exception:
        # Text might be too short for classification
        categories = []
    
    # Generate summary based on content analysis
    if len(text) > 10000:
        # For long documents, use content categorization and key entities
        summary = f"This document focuses on {', '.join(categories[:3] if categories else key_entities[:5])}. "
        summary += generate_extractive_summary(text, 5)
    else:
        # For shorter documents, use a simpler approach
        summary = generate_extractive_summary(text, 3)
    
    # Extract key points (important sentences)
    key_points = extract_key_points(text, entity_response.entities)
    
    return summary, key_points

def generate_extractive_summary(text, num_sentences=3):
    """
    Create an extractive summary by selecting important sentences
    
    Args:
        text (str): The text to summarize
        num_sentences (int): Number of sentences to include
        
    Returns:
        str: Extractive summary
    """
    # Split text into sentences
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    
    if len(sentences) <= num_sentences:
        return text
    
    # Simple algorithm: take first sentence, last sentence, and some from the middle
    important_sentences = [sentences[0]]
    
    # Add some sentences from the middle
    middle_count = min(num_sentences - 2, len(sentences) - 2)
    if middle_count > 0:
        step = (len(sentences) - 2) // (middle_count + 1)
        for i in range(1, middle_count + 1):
            idx = i * step
            if idx < len(sentences):
                important_sentences.append(sentences[idx])
    
    # Add the last sentence
    if len(sentences) > 1:
        important_sentences.append(sentences[-1])
    
    return '. '.join(important_sentences) + '.'

def extract_key_points(text, entities, max_points=10):
    """
    Extract key points from the text based on important entities
    
    Args:
        text (str): The document text
        entities (list): Entities from the Natural Language API
        max_points (int): Maximum number of key points to extract
        
    Returns:
        list: Key points extracted from the text
    """
    # Split text into sentences
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    
    # Find sentences containing important entities
    important_sentences = []
    high_salience_entities = [entity.name for entity in entities if entity.salience > 0.05]
    
    for sentence in sentences:
        for entity in high_salience_entities:
            if entity in sentence and sentence not in important_sentences:
                important_sentences.append(sentence)
                break
    
    # Limit the number of key points
    key_points = important_sentences[:max_points]
    
    # If we couldn't find enough key points, add some sentences from the beginning
    if len(key_points) < min(3, max_points) and len(sentences) > 0:
        for sentence in sentences:
            if sentence not in key_points:
                key_points.append(sentence)
                if len(key_points) >= min(3, max_points):
                    break
    
    return key_points