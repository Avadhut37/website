# Linktree Clone

Create a Linktree clone. It should have a main page that displays a list of links. There should be an admin page where a user can add, edit, and delete links. The links should be stored in a database.

## Project Structure

```
├── backend/           # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── frontend/          # React frontend
│   ├── src/
│   ├── package.json
│   └── ...
└── README.md
```

## Getting Started

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
