from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import openai
import numpy as np
import re
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'join_date': self.join_date.isoformat(),
            'last_login': self.last_login.isoformat()
        }

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Check if user exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.email == email:
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        else:
            return jsonify({'success': False, 'message': 'Username already taken'}), 400
    
    # Create new user
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password, password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': user.to_dict()
    })




# Load and preprocess dataset
try:
    dataset = pd.read_csv("C:\\Users\\HP\\Downloads\\vit_college_queries.csv")
    dataset.fillna("", inplace=True)
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = pd.DataFrame(columns=["question", "answer"])

# Initialize OpenAI API key
openai.api_key = "YOUR_OPENAI_API_KEY"  # Replace with your OpenAI API key

# Initialize sentence transformer model
model = SentenceTransformer('paraphrase-mpnet-base-v2')  # Using a better model than MiniLM

# VIT-specific synonyms and abbreviations dictionary
vit_synonyms = {
    "vit": "vellore institute of technology",
    "hostel": "dormitory",
    "hod": "head of department",
    "cse": "computer science engineering",
    "ece": "electronics and communication engineering",
    "mech": "mechanical engineering",
    "ffcs": "fully flexible credit system",
    "da": "digital assignment",
    "cat": "continuous assessment test",
    "fat": "final assessment test",

}

# Simple list of common English stopwords
stopwords = {"a", "an", "the", "in", "on", "at", "for", "to", "of", "with", "by", 
             "is", "are", "am", "was", "were", "be", "been", "being", 
             "and", "or", "but", "if", "then", "else", "when", "so", "than",
             "that", "this", "these", "those", "i", "you", "he", "she", "it", 
             "we", "they", "who", "whom", "whose", "which", "what", "how"}

# Function to preprocess text
def comprehensive_preprocess(text):
    if not text or not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace VIT-specific terms with their expanded forms
    for abbr, full in vit_synonyms.items():
        text = re.sub(r'\b' + abbr + r'\b', full, text)
    
    # Remove punctuation and split into words
    words = re.findall(r'\b\w+\b', text)
    
    # Remove stopwords
    filtered_words = [word for word in words if word not in stopwords]
    
    return " ".join(filtered_words)

# Preprocess dataset questions
preprocessed_questions = [comprehensive_preprocess(q) for q in dataset["question"].fillna("").tolist()]
original_questions = dataset["question"].fillna("").tolist()

# Generate embeddings for preprocessed questions
question_embeddings = model.encode(preprocessed_questions)

def exact_match(user_input):
    processed_input = comprehensive_preprocess(user_input)
    
    for i, (proc_q, orig_q) in enumerate(zip(preprocessed_questions, original_questions)):
        if processed_input == proc_q:
            return dataset.iloc[i]["answer"], 1.0  # Return answer and confidence score
    
    return None, 0.0

def fuzzy_match(user_input, threshold=80):
    processed_input = comprehensive_preprocess(user_input)
    
    # Use RapidFuzz process to find the best match
    best_match = process.extractOne(
        processed_input, 
        preprocessed_questions,
        scorer=fuzz.token_sort_ratio  # Better for differently ordered words
    )
    
    if best_match and best_match[1] >= threshold:
        index = preprocessed_questions.index(best_match[0])
        return dataset.iloc[index]["answer"], best_match[1] / 100  # Normalize to 0-1
    
    return None, 0.0

def semantic_match(user_input, threshold=0.75):
    processed_input = comprehensive_preprocess(user_input)
    user_embedding = model.encode([processed_input])
    
    similarities = cosine_similarity(user_embedding, question_embeddings)[0]
    max_index = similarities.argmax()
    max_similarity = similarities[max_index]
    
    if max_similarity >= threshold:
        return dataset.iloc[max_index]["answer"], max_similarity
    
    return None, max_similarity

def query_expansion(user_input):
    """Generate expanded versions of the query to increase matching chances"""
    expanded_queries = [user_input]
    
    # Add a query without question words
    question_words = ["what", "how", "when", "where", "who", "why", "is", "are", "can", "do", "does"]
    tokens = user_input.lower().split()
    if any(word in question_words for word in tokens):
        filtered_tokens = [token for token in tokens if token not in question_words]
        expanded_queries.append(" ".join(filtered_tokens))
    
    # Add keywords-only query 
    processed = comprehensive_preprocess(user_input)
    if processed and processed != user_input:
        expanded_queries.append(processed)
    
    return expanded_queries

def ensemble_matching(user_input):
    """Combine multiple matching techniques with weights"""
    expanded_queries = query_expansion(user_input)
    
    # Weight for each method 
    weights = {
        "exact": 1.0,
        "fuzzy": 0.8,
        "semantic": 0.9
    }
    
    best_score = 0
    best_answer = None
    
    # Try each expanded query
    for query in expanded_queries:
        # Get results from each method
        exact_answer, exact_score = exact_match(query)
        fuzzy_answer, fuzzy_score = fuzzy_match(query)
        semantic_answer, semantic_score = semantic_match(query)
        
        # Calculate weighted scores
        candidates = {
            exact_answer: exact_score * weights["exact"],
            fuzzy_answer: fuzzy_score * weights["fuzzy"],
            semantic_answer: semantic_score * weights["semantic"]
        }
        
        # Remove None answers
        candidates = {k: v for k, v in candidates.items() if k is not None}
        
        # Find the best answer from this query
        if candidates:
            top_answer = max(candidates.items(), key=lambda x: x[1])
            if top_answer[1] > best_score:
                best_score = top_answer[1]
                best_answer = top_answer[0]
    
    confidence_threshold = 0.7  # Minimum confidence required
    
    if best_answer and best_score >= confidence_threshold:
        return best_answer
    
    return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "").strip()
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    
    # Try to find answer in dataset using enhanced matching
    custom_answer = ensemble_matching(user_input)
    
    if custom_answer:
        return jsonify({"response": custom_answer})
    
    # Fall back to OpenAI API
    try:
        # Include dataset context in the prompt for better results
        system_prompt = """
        You are a helpful VIT college assistant. You provide information about Vellore Institute of Technology.
        Answer questions clearly and concisely based on accurate information about VIT.
        If you don't know the answer, say so politely.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=200,
            temperature=0.6  # Lower temperature for more focused responses
        )
        
        chatbot_reply = response["choices"][0]["message"]["content"].strip()
        return jsonify({"response": chatbot_reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

