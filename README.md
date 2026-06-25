<<<<<<< HEAD
# 🔍 AI Code Reviewer

An intelligent Python code analysis tool that checks your code for **time complexity**, **space complexity**, **optimality**, and **errors**.

Built with **Flask** (backend API) + **Streamlit** (frontend UI) — communicates via **JSON**.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Flask API (Terminal 1)
```bash
python app.py
```
The API runs on `http://localhost:5000`.

### 3. Start the Streamlit Frontend (Terminal 2)
```bash
streamlit run streamlit_app.py
```
Opens in your browser at `http://localhost:8501`.

---

## 📊 What It Analyzes

| Feature | Description |
|---|---|
| ⏱️ Time Complexity | Big-O notation (O(1), O(n), O(n²), etc.) |
| 💾 Space Complexity | Memory usage analysis |
| 🎯 Optimality | Optimal / Near-Optimal / Moderate / Brute Force |
| 🐛 Error Detection | Syntax errors, unused imports, undefined names |

---

## 🔌 API Usage

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "for i in range(n):\n    print(i)", "language": "python"}'
```

---

## 🏗️ Project Structure

```
AI_Code_Reviewer/
├── app.py              # Flask backend API
├── analyzer.py         # AST-based code analysis engine
├── streamlit_app.py    # Streamlit frontend
├── requirements.txt    # Dependencies
└── README.md           # This file
```
=======
# AI-Code-Reviewer
AI-powered Python code analysis tool that detects errors, evaluates time and space complexity, and rates code optimality through an interactive Streamlit interface.
>>>>>>> bbb02f939c96e76e1aa4bbaf2a08a0f309731513
