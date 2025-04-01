import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from utils.pdf_processor import extract_text_from_pdf
from utils.summarizer import generate_summary
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render the main page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process for summarization"""
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    # Check if user submitted an empty form
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    # Check if file is allowed and process it
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Extract text from PDF
            text = extract_text_from_pdf(filepath)
            
            # Generate summary
            summary, key_points = generate_summary(text)
            
            # Store results in session for display
            session['summary'] = summary
            session['key_points'] = key_points
            session['filename'] = filename
            
            # Clean up the uploaded file
            os.remove(filepath)
            
            return redirect(url_for('show_results'))
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(url_for('index'))

@app.route('/results')
def show_results():
    """Display summarization results"""
    # Check if results exist in session
    if 'summary' not in session or 'key_points' not in session:
        flash('No results to display. Please upload a PDF first.')
        return redirect(url_for('index'))
    
    return render_template(
        'results.html',
        filename=session.get('filename', 'Unknown file'),
        summary=session.get('summary', 'No summary available'),
        key_points=session.get('key_points', [])
    )

if __name__ == '__main__':
    app.run(debug=True)