# AI Code Review & Rewrite Agent 🤖

An AI-powered web application that provides intelligent code reviews and automated rewriting using Groq's Llama 3.3 model.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green)

## ✨ Features

- **Multi-Language Support**: Python, JavaScript, Java, C++, and more.
- **Deep Analysis**: Detects bugs, security vulnerabilities, performance issues, and best practices.
- **Automated Rewriting**: One-click fix to generate production-ready code.
- **Modern UI**: Dark gradient theme, syntax highlighting, and side-by-side diffs.
- **Real-time Streaming**: (Simulated via fast Groq inference) for quick feedback.

## 📁 Project Structure

```
AI-Code-Review-Agent/
├── backend/
│   ├── main.py            # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment variables (API Key)
├── frontend/
│   ├── index.html         # Main application interface
│   └── login.html         # Login page
└── README.md              # Documentation
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Groq API Key (Get one at [console.groq.com](https://console.groq.com))

### Installation

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Open `.env` and paste your Groq API Key:
    ```env
    GROQ_API_KEY=your_actual_api_key_here
    ```

### Running the App

1.  **Start the server:**
    ```bash
    python -m uvicorn main:app --reload
    ```

2.  **Open in Browser:**
    Go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

3.  **Login:**
    - Email: `demo@example.com`
    - Password: `demo123`

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn, Python-Dotenv
- **AI Engine**: Groq SDK (Llama-3.3-70b-versatile)
- **Frontend**: HTML5, Vanilla JS, Tailwind CSS
- **Utilities**: Marked.js (Markdown), Highlight.js (Syntax Highlighting)

## 📸 Usage

1.  **Select Language**: Choose the programming language of your code.
2.  **Paste Code**: Enter the source code in the left panel.
3.  **Select Focus**: Check boxes for Bugs, Security, Performance, etc.
4.  **Review**: Click "Review Code" for a detailed report.
5.  **Rewrite**: Click "Fix & Rewrite" to get an optimized version.


