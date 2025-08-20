## Final-Project: AI-Assisted Pathology Report Analyzer & Prescription Generator

This project ingests a pathology PDF, extracts key patient/test details, uses OpenAI to generate analysis/recommendations/medications, and produces a prescription-styled PDF. A React frontend talks to a FastAPI backend.

### Tech Stack
- Backend: FastAPI, Uvicorn, pdfplumber, reportlab, OpenAI API
- Frontend: React (Create React App), Bootstrap, Axios

### Directory Structure
- `back-end/`: FastAPI app, PDF parsing and prescription generation
- `front-end/`: React app UI

### Prerequisites
- Python 3.10+
- Node.js 18+
- An OpenAI API key (set as `OPENAI_API_KEY`)

### Quick Start
1) Backend
```
cd back-end
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=YOUR_KEY_HERE
uvicorn app:app --reload
```
The server runs on `http://127.0.0.1:8000`.

2) Frontend
```
cd front-end
npm install
npm start
```
The app runs on `http://localhost:3000` and calls the backend at `http://localhost:8000`.

### Backend Endpoints
- `POST /upload`: multipart PDF upload; extracts info and runs analysis
- `GET /results`: returns last processed results
- `POST /update_profile`: update patient info (JSON body)
- `POST /update_analysis`: pass selected tests (JSON array) to refresh analysis
- `POST /generate_prescription`: `{ isUpdate: boolean }` -> creates PDF under `back-end/Output-files/`
- `GET /download?file_path=...`: download the generated PDF
- `WS /ws`: simple chat endpoint

### Environment Variables
- `OPENAI_API_KEY` (backend): Your OpenAI API key. Not required for app to boot, but required for analysis/prescription generation to work.

### Notes
- Do not commit real secrets. The backend now reads the key from the environment; see above.
- Make sure ports `3000` (frontend) and `8000` (backend) are free.

### License
Proprietary/All rights reserved unless otherwise specified by the author.


