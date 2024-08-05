from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import PyPDF2
import google.generativeai as genai

# Configure Google Gemini API with your API key
genai.configure(api_key='AIzaSyBhec2S7TJ_fC2YwRZn7XjLXLipdnH-sYs')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.expanduser('~/uploads')
app.secret_key = 'supersecretkey'  # Replace with a real secret key

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    if 'logged_in' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form  # Use request.form to handle form data
        email = data.get('email')
        password = data.get('password')
        # Dummy authentication logic
        if email == 'test@example.com' and password == '123':
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"})
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Extract text from PDF
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfFileReader(f)
                pdf_text = ''
                for page_num in range(reader.numPages):
                    pdf_text += reader.getPage(page_num).extract_text()
            app.config['pdf_text'] = pdf_text
            return jsonify({"success": True, "message": "File uploaded and processed"})
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify({"error": "File upload failed"})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    if not question or 'pdf_text' not in app.config:
        return jsonify({"error": "Question and PDF text are required."})

    pdf_text = app.config['pdf_text']

    # Create a prompt string for the Gemini API
    prompt = (
        "You are a helpful assistant who reads PDFs and answers questions based on the PDF content. "
        "You will also use the conversation history to be context-aware.\n\n"
        f"PDF content: {pdf_text}\n\n"
        f"User question: {question}"
    )

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        bot_response = response.text
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
