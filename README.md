# GateLens – API Protection Gateway

GateLens is a lightweight, security‑focused API gateway built with **Python (FastAPI)** and a **React/HTML dashboard**.  
It sits between clients and backend APIs, enforcing **JWT authentication**, **API key validation**, **rate‑limiting**, and basic **SQL injection / XSS filtering**, while logging all traffic for real‑time monitoring.

---

## Overview

GateLens protects exposed APIs by adding a unified security layer that:

- Intercepts all incoming API requests before they reach the backend.  
- Validates **JWT tokens** and **API keys** for each request.  
- Applies **rate‑limiting per IP** (for example, 10 requests per minute).  
- Logs essential request details: IP address, endpoint, method, status, and timestamp.  
- Forwards valid and allowed requests to the backend API and returns responses.  
- Visualizes traffic and events in a real‑time **dashboard** (frontend UI).

---

## Technologies Used

- **Backend**: Python + FastAPI (asynchronous, type‑hinted API framework).  
- **Server**: Uvicorn (ASGI server).  
- **Authentication**: JWT (JSON Web Tokens).  
- **API Security**: API key validation.  
- **Rate Limiting**: SlowAPI / custom middleware (e.g., 10 requests per minute per IP).  
- **Logging**: JSON‑based, structured request logs.  
- **Frontend**: React.js (or HTML/CSS/JavaScript) dashboard UI.  
- **Deployment**: Cloud platforms such as Render or similar.

---

## Getting Started

### Prerequisites

- Python 3.8+  
- Node.js (if using React frontend)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/gate-lens-api-gateway.git
cd gate-lens-api-gateway
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the FastAPI gateway

```bash
uvicorn backend.main:app --reload
```

### 4. Run the frontend

For React:

```bash
cd frontend
npm install
npm start
```

For simple HTML/JS:

```bash
cd frontend
python -m http.server 8000
```

Then open `http://localhost:8000` in the browser.

---

## Purpose & Use Case

GateLens is designed to help developers, startups, and students secure their APIs without relying on heavy enterprise tools.  
It demonstrates practical API security patterns—authentication, rate‑limiting, and logging—in a lightweight, hackathon‑friendly prototype that is easy to understand, extend, and present.
