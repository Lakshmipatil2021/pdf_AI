from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import PyPDF2
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth
import pinecone
from sentence_transformers import SentenceTransformer # type: ignore

# Configure Google Gemini API with your API key
genai.configure(api_key='AIzaSyBhec2S7TJ_fC2YwRZn7XjLXLipdnH-sYs')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.expanduser('~/uploads')
app.secret_key = 'supersecretkey'  # Replace with a real secret key

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize Firebase Admin SDK
cred = credentials.Certificate('C:/Users/drkir/Downloads/pdfai-a4d51-firebase-adminsdk-evca6-510c6c3a14.json')
firebase_admin.initialize_app(cred)

# Initialize Pinecone
pinecone.init(api_key="0b9d3337-0d0c-4c06-9d38-1215fa674604", environment="YOUR_PINECONE_ENVIRONMENT")
index = pinecone.Index("pdf-index")

# Load sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        id_token = data.get('idToken')
        try:
            decoded_token = auth.verify_id_token(id_token)
            user_id = decoded_token['uid']
            session['user'] = user_id
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
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
            # Create text chunks and store embeddings in Pinecone
            chunks = [pdf_text[i:i+512] for i in range(0, len(pdf_text), 512)]
            embeddings = model.encode(chunks)
            for i, embedding in enumerate(embeddings):
                index.upsert([(f'{filename}_chunk_{i}', embedding.tolist(), {'text': chunks[i]})])
            return jsonify({"success": True, "message": "File uploaded and processed"})
        except Exception as e:
            return jsonify({"error": str(e)})
    return jsonify({"error": "File upload failed"})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({"error": "Question is required."})

    # Create embedding for the question
    question_embedding = model.encode([question])[0]

    # Query Pinecone for relevant PDF chunks
    query_response = index.query(question_embedding.tolist(), top_k=5, include_metadata=True)
    pdf_text = ' '.join([match['metadata']['text'] for match in query_response['matches']])

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






