# 🎓AI-Powered-College-Query-Resolver

An intelligent chatbot designed to answer student queries related to college processes, facilities, academics, and more. It uses a hybrid approach by searching a custom dataset and falling back to OpenAI's GPT-3.5 Turbo model when needed. Built with a Flask backend and an interactive frontend.

---

## 🔧 Features

- 📁 **Custom Dataset Support** – Answers questions using college-specific CSV data.
- 🤖 **GPT-3.5 Turbo Integration** – Provides responses for questions not found in the dataset.
- 💬 **Chat Interface** – Clean and responsive UI for real-time interaction.
-👤 **User Auth** – Basic login and registration pages.
- 🧠 **Semantic Search** –  Uses sentence similarity for better dataset matching.
---

---

## 🚀 Getting Started

### 📦 Prerequisites

- Python 3.8+
- Flask
- OpenAI API Key
- Pandas
- SentenceTransformers 
- PyTorch

### 🔨 Installation

1. **Clone the repository**
git clone https://github.com/yourusername/college-query-chatbot.git
cd college-query-chatbot
2.**Install dependencies**

pip install flask flask-cors pandas openai sentence-transformers torch
3.**Configure API Key Replace your OpenAI key in server.py**
openai.api_key = "your_openai_api_key"
4.**Run the server**
python server.py
5.**Open in Browser Navigate to: http://127.0.0.1:5000**

### 📸 UI Preview
![Screenshot (419)](https://github.com/user-attachments/assets/f668f942-e601-4042-94b8-0a34b63df9c6)
