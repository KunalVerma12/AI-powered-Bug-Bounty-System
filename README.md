# AI-Multi-Agent-Bug-Bounty-Hunter
An AI-powered full-stack cybersecurity platform that automates GitHub repository security analysis using a multi-agent architecture. The platform authenticates users through GitHub OAuth, imports repositories using the GitHub REST API, performs static code analysis with **Semgrep** and **Bandit**, stores scan history in **MongoDB**, and presents AI-assisted vulnerability reports through a modern React dashboard.

---

## 🚀 Features

- 🔐 GitHub OAuth Authentication
- 📂 Import and synchronize GitHub repositories
- 🤖 Multi-Agent Security Pipeline
  - Recon Agent
  - Scanner Agent
  - AI Analyst Agent
  - Fix Recommendation Agent
- 🔍 Static code analysis using Semgrep
- 🛡️ Python security scanning with Bandit
- 🧠 AI-generated vulnerability explanations and remediation suggestions
- 📊 Interactive dashboard with scan history and analytics
- 📈 Repository security posture scoring
- 🚨 Severity-based vulnerability classification
- 📜 Detailed vulnerability reports
- ⚡ Real-time scan progress tracking
- 🌙 Light & Dark Mode support

---

# 🏗️ Architecture

```text
                           GitHub
                              │
                  GitHub OAuth & REST API
                              │
                              ▼
                     FastAPI Backend
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   Recon Agent          Scanner Agent         AI Analyst
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
              Semgrep                 Bandit
                              │
                              ▼
                         MongoDB
                              │
                              ▼
                 React + Vite Dashboard
```

---

# 🛠️ Tech Stack

### Frontend

- React.js
- Vite
- Tailwind CSS
- Axios

### Backend

- FastAPI
- Python

### Database

- MongoDB

### Authentication

- GitHub OAuth

### Security Analysis

- Semgrep
- Bandit

### APIs

- GitHub REST API

---

# ✨ Key Capabilities

- Authenticate users securely using GitHub OAuth
- Import repositories directly from GitHub
- Perform automated repository security scans
- Detect vulnerabilities using Semgrep and Bandit
- Generate AI-powered vulnerability explanations
- Recommend remediation strategies
- Store scan history and results in MongoDB
- Visualize findings through an interactive dashboard
- Track repository security posture over time

---

# 📂 Project Structure

```text
AI-powered-Bug-Bounty-System
│
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── agents/
│   ├── utils/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── database/
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

---

# ⚙️ Installation

## Clone the Repository

```bash
git clone https://github.com/KunalVerma12/AI-powered-Bug-Bounty-System.git

cd AI-powered-Bug-Bounty-System
```

---

## Backend Setup

```bash
python -m venv venv

source venv/bin/activate

pip install -r backend/requirements.txt

uvicorn backend.main:app --reload
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

```env
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/github/callback
FRONTEND_URL=http://localhost:5173
```

---

# 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scan` | Initiate a repository scan |
| GET | `/api/results` | Retrieve all scan results |
| GET | `/api/results/{scan_id}` | Retrieve detailed scan information |
| GET | `/api/vulnerabilities` | Retrieve detected vulnerabilities |
| GET | `/api/dashboard/summary` | Retrieve dashboard statistics |

---

# 🎯 Future Enhancements

- Docker support
- GitHub Actions integration
- WebSocket-based live scan updates
- CVE database integration
- OWASP Top 10 mapping
- PDF security report generation
- SARIF export support
- Multi-user collaboration
- Kubernetes deployment

---

# 📸 Screenshots

> Add screenshots here for:
>
> - Login Page
> - Dashboard
> - Repository Selection
> - Scan Progress
> - Vulnerability Reports
> - Analytics

---

# 👨‍💻 Author

**Kunal Verma**

- GitHub: https://github.com/KunalVerma12

---

## ⭐ If you found this project interesting, consider giving it a star!