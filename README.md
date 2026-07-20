# Autonomous Multi-Agent Bug Bounty Hunter

An full-stack cybersecurity dashboard that scans GitHub repositories with a mock multi-agent pipeline and presents vulnerabilities.

## Stack

- Frontend: React, Vite, Tailwind CSS, Axios
- Backend: FastAPI
- Storage: in-memory mock repository with seeded scans/results

## Features

- GitHub repository scan submission
- Simulated multi-agent workflow: Recon Agent, Scanner Agent, AI Analyst, Fix Agent
- Feed-style dashboard for vulnerability reports
- Activity history with scan progress
- Profile screen with key metrics
- Vulnerability detail modal with explanation, snippet, and fix suggestion
- Light/dark mode toggle

## Run backend

```bash
cd /Users/kunal/bug-bounty-hunter
./venv/bin/uvicorn backend.main:app --reload
```

## Run frontend

```bash
cd /Users/kunal/bug-bounty-hunter/frontend
npm install
npm run dev
```

## API

- `POST /api/scan`
- `GET /api/results`
- `GET /api/results/{scan_id}`
- `GET /api/vulnerabilities`
- `GET /api/dashboard/summary`
