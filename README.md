ML Chatbot scaffold

Stack: React frontend + FastAPI backend

Quick start (backend):

1. Create a virtualenv and install requirements:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

2. Run the API:

```bash
uvicorn backend.main:app --reload --port 8000
```

Quick start (frontend):

```bash
cd frontend
npm install
npm start
```

Notes:
- API endpoints: `/upload`, `/eda/{file_id}`, `/train/{file_id}`, `/hypothesis/{file_id}`
- Upload Parquet or CSV files. The backend stores files in `uploads/`.
- The training endpoint uses numeric features only and chooses model automatically.
 - To enable LLM-backed chat forwarding, create a `.env` file in the project root with your API key. See `.env.example`.

Environment variables (create `.env`):

```
OPENAI_API_KEY=your_api_key_here
# Optional: OPENAI_API_URL and OPENAI_MODEL
```

New endpoints:
- `/chat` — POST: route actions (`eda`, `train`, `hypothesis`) or forward `messages` to the LLM. Example payloads:
	- `{"action":"eda","file_id":"..."}`
	- `{"action":"text","messages":[{"role":"user","content":"Hello"}]}`
This project was refocused to a local pipeline (no API server). Use the scripts in `pipeline/` to run EDA, train models, and perform hypothesis tests locally.

Quick local pipeline usage:

1. Create and activate a Python virtual environment and install backend requirements:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

2. Run EDA:

```powershell
python pipeline/eda.py path/to/data.parquet --out eda.json
```

3. Train a model:

```powershell
python pipeline/train.py path/to/data.csv --target target_column --out-model model.joblib
```

4. Hypothesis test:

```powershell
python pipeline/hypothesis.py path/to/data.csv --column value_column --test ttest --group-column group_col
```

If you want the API/server restored later, tell me and I will re-add a minimal FastAPI wrapper around these scripts.
