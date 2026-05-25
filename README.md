# Tutor Telegram Scheduler

Система автоматических напоминаний об уроках для репетиторов.

## Технологии

- **Backend**: FastAPI + SQLAlchemy
- **Frontend**: Streamlit
- **Database**: SQLite
- **Scheduler**: APScheduler
- **Telegram**: python-telegram-bot (MOCK_MODE для демо)

## Установка

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Архитектура

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│   SQLite    │
│  Frontend   │◀────│   Backend   │◀────│   Database  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   APSched   │
                    │  Scheduler  │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Telegram  │
                    │  Bot (Mock) │
                    └─────────────┘
