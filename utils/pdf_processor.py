import os
import PyPDF2
from dotenv import load_dotenv
import re
import nltk
from nltk.tokenize import sent_tokenize
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Try to download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using PyPDF2
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content from the PDF
    """
    logger.info(f"Processing PDF file: {file_path}")
    
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            text = ""
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        
        # Clean up the text
        text = clean_text(text)
        
        if not text.strip():
            logger.warning("No text was extracted from the PDF")
            return "No text could be extracted from this PDF. The file might be scanned or have security restrictions."
        
        logger.info(f"Successfully extracted {len(text)} characters of text")
        return text
    
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return f"Error extracting text from PDF: {str(e)}"

def clean_text(text):
    """
    Clean up extracted text by removing extra whitespace and fixing common issues
    
    Args:
        text (str): Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple newlines with double newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove excessive spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Fix broken sentences (where sentences are split across lines)
    sentences = sent_tokenize(text)
    text = ' '.join(sentences)
    text = re.sub(r' \.', '.', text)  # Fix space before periods
    
    return text

def summarize_text(text, max_length=500):
    """
    Create a simple summary of the text
    
    Args:
        text (str): The text to summarize
        max_length (int): Maximum length of summary
        
    Returns:
        str: Summarized text
    """
    if not text or len(text) < max_length:
        return text
    
    # Split into sentences
    sentences = sent_tokenize(text)
    
    # Use the first few sentences as a summary
    summary = sentences[0]
    current_length = len(summary)
    
    for sentence in sentences[1:]:
        if current_length + len(sentence) + 1 > max_length:
            break
        summary += " " + sentence
        current_length += len(sentence) + 1
    
    return summary + "..."

def extract_key_points(text, num_points=5):
    """
    Extract key points from text
    
    Args:
        text (str): The text to analyze
        num_points (int): Number of key points to extract
        
    Returns:
        list: Key points from the text
    """
    if not text:
        return []
    
    # Split into sentences
    sentences = sent_tokenize(text)
    
    # Use heuristics to find important sentences
    important_sentences = []
    
    # Look for sentences with key indicators
    indicators = ["important", "key", "significant", "essential", "critical", 
                  "conclusion", "therefore", "thus", "in summary", "to summarize"]
    
    for sentence in sentences:
        lower_sent = sentence.lower()
        # Check if sentence contains any indicators
        if any(indicator in lower_sent for indicator in indicators):
            important_sentences.append(sentence)
    
    # If not enough important sentences found, use first sentences from paragraphs
    if len(important_sentences) < num_points:
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            if para.strip() and len(important_sentences) < num_points:
                first_sentence = sent_tokenize(para)[0] if sent_tokenize(para) else ""
                if first_sentence and first_sentence not in important_sentences:
                    important_sentences.append(first_sentence)
    
    # If still not enough, add some sentences from the beginning and end
    if len(important_sentences) < num_points:
        remaining = num_points - len(important_sentences)
        beginning_sentences = sentences[:remaining//2] if sentences else []
        ending_sentences = sentences[-remaining//2:] if sentences else []
        
        for sent in beginning_sentences + ending_sentences:
            if sent not in important_sentences and len(important_sentences) < num_points:
                important_sentences.append(sent)
    
    # Return the selected points, limited to num_points
    return important_sentences[:num_points]

def process_pdf(file_path):
    """
    Process a PDF file and return extracted text, summary, and key points
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        dict: Dictionary containing extracted text, summary, and key points
    """
    text = extract_text_from_pdf(file_path)
    
    if text and not text.startswith("Error"):
        summary = summarize_text(text)
        key_points = extract_key_points(text)
        
        return {
            "text": text,
            "summary": summary,
            "key_points": key_points
        }
    else:
        return {
            "text": text,
            "summary": "Could not generate summary due to extraction error.",
            "key_points": []
        }

# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            result = process_pdf(file_path)
            print("\n--- SUMMARY ---")
            print(result["summary"])
            print("\n--- KEY POINTS ---")
            for i, point in enumerate(result["key_points"], 1):
                print(f"{i}. {point}")
        else:
            print(f"File not found: {file_path}")
    else:
        print("Please provide a PDF file path as an argument")