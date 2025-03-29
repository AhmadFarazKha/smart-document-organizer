import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import PyPDF2
import google.generativeai as genai
import io
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

# Get Google API key from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Configure Google Generative AI with API key
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Determine paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Google OAuth2 configuration
SCOPES = ['https://www.googleapis.com/auth/drive']  # Full drive access for uploads
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF using PyMuPDF for better extraction"""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text with PyMuPDF: {str(e)}")
        # Fallback to PyPDF2 if PyMuPDF fails
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e2:
            print(f"Error extracting text with PyPDF2: {str(e2)}")
            return f"Error extracting text: {str(e2)}"

def summarize_text(text, max_length=1500):
    """Truncate text to prepare for summarization"""
    # Check if text is too long, truncate if necessary
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text

def generate_summary(text):
    """Generate summary using Google's Generative AI"""
    if not GOOGLE_API_KEY:
        return "API key not found. Please set GOOGLE_API_KEY in .env file."
    
    try:
        # Use Google's generative AI for summarization
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Please provide a concise summary of the following document in bullet points format. 
        Focus on the key points, decisions, action items, and important details.
        Format as meeting minutes with clear sections.
        
        Document text:
        {text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return f"Error generating summary: {str(e)}"

def get_google_auth_flow():
    """Create and return Google OAuth2 flow"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:5000/oauth2callback'
    )
    return flow

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Initiate Google OAuth2 login"""
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback"""
    state = session['state']
    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    
    # Save credentials for future use
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    
    return redirect(url_for('list_documents'))

def get_drive_service():
    """Create Google Drive service"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None
    
    return build('drive', 'v3', credentials=creds)

@app.route('/list-documents')
def list_documents():
    """List documents from Google Drive"""
    service = get_drive_service()
    if not service:
        return redirect(url_for('login'))
    
    try:
        results = service.files().list(
            pageSize=50, 
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()
        files = results.get('files', [])
        return render_template('documents.html', files=files)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route('/search-documents', methods=['POST'])
def search_documents():
    """Search documents in Google Drive"""
    service = get_drive_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401
    
    query = request.form.get('query', '')
    try:
        results = service.files().list(
            q=f"name contains '{query}'",
            pageSize=50, 
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()
        files = results.get('files', [])
        return render_template('documents.html', files=files)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route('/upload-file', methods=['GET', 'POST'])
def upload_file():
    """Handle file uploads"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    service = get_drive_service()
    if not service:
        return redirect(url_for('login'))
    
    # Check if the post request has a file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    uploaded_files = []
    
    for file in files:
        # If user does not select file, browser might submit an empty file
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # For PDF files, generate summary
            summary = None
            if filename.lower().endswith('.pdf'):
                # Extract text from PDF
                pdf_text = extract_text_from_pdf(file_path)
                # Truncate text if needed
                truncated_text = summarize_text(pdf_text)
                # Generate summary using Google's API
                summary = generate_summary(truncated_text)
            
            # Upload file to Google Drive
            try:
                file_metadata = {
                    'name': filename
                }
                
                media = MediaFileUpload(
                    file_path, 
                    resumable=True
                )
                
                uploaded_file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,mimeType,webViewLink'
                ).execute()
                
                # Add summary to the uploaded file info if available
                if summary:
                    uploaded_file['summary'] = summary
                
                uploaded_files.append(uploaded_file)
                
                # Clean up local file after upload
                os.remove(file_path)
            except Exception as e:
                flash(f"Error uploading {filename}: {str(e)}")
    
    if uploaded_files:
        return render_template('upload_success.html', files=uploaded_files)
    else:
        flash('No files were uploaded')
        return redirect(request.url)

@app.route('/upload-ajax', methods=['POST'])
def upload_ajax():
    """Handle AJAX file uploads (for drag and drop)"""
    service = get_drive_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Check if the post request has a file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser might submit an empty file
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # For PDF files, generate summary
        summary = None
        if filename.lower().endswith('.pdf'):
            # Extract text from PDF
            pdf_text = extract_text_from_pdf(file_path)
            # Truncate text if needed
            truncated_text = summarize_text(pdf_text)
            # Generate summary using Google's API
            summary = generate_summary(truncated_text)
        
        # Upload file to Google Drive
        try:
            file_metadata = {
                'name': filename
            }
            
            media = MediaFileUpload(
                file_path, 
                resumable=True
            )
            
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,webViewLink'
            ).execute()
            
            # Clean up local file after upload
            os.remove(file_path)
            
            response_data = {
                'success': True,
                'file': {
                    'id': uploaded_file.get('id'),
                    'name': uploaded_file.get('name'),
                    'mimeType': uploaded_file.get('mimeType'),
                    'webViewLink': uploaded_file.get('webViewLink')
                }
            }
            
            # Add summary to response if available
            if summary:
                response_data['file']['summary'] = summary
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/view-summary/<file_id>')
def view_summary(file_id):
    """View detailed summary of a document"""
    service = get_drive_service()
    if not service:
        return redirect(url_for('login'))
    
    try:
        # Get file metadata
        file = service.files().get(fileId=file_id, fields='id,name,mimeType,webViewLink').execute()
        
        # Check if file is a PDF
        if file.get('mimeType') == 'application/pdf':
            # Create a temporary file to download the PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = temp_file.name
            
            # Download file content
            request = service.files().get_media(fileId=file_id)
            with open(temp_path, 'wb') as f:
                downloader = MediaFileUpload(temp_path)
                downloader.resumable = True
                f.write(request.execute())
            
            # Extract text from PDF
            pdf_text = extract_text_from_pdf(temp_path)
            # Remove temporary file
            os.unlink(temp_path)
            
            # Truncate text if needed
            truncated_text = summarize_text(pdf_text)
            # Generate summary
            summary = generate_summary(truncated_text)
            
            return render_template('summary.html', file=file, summary=summary)
        else:
            flash('Only PDF files can be summarized')
            return redirect(url_for('list_documents'))
    except Exception as e:
        flash(f"Error generating summary: {str(e)}")
        return redirect(url_for('list_documents'))

if __name__ == '__main__':
    app.run(debug=True)