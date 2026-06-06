from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import threading
from . import models
from . import schemas
from .database import engine, get_db, SessionLocal
from .telegram_bot import TelegramBot
from .scheduler import LessonScheduler
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

telegram_bot = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_bot, scheduler
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        telegram_bot = TelegramBot(bot_token)
        bot_thread = threading.Thread(target=telegram_bot.run_polling, daemon=True)
        bot_thread.start()
        
        scheduler = LessonScheduler(telegram_bot, SessionLocal)
        scheduler.start()
        logger.info("Telegram бот и планировщик инициализированы")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN не найден в .env")
    
    yield
    
    if scheduler:
        scheduler.shutdown()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Бот-секретарь для репетитора Никиты",
    description="API для управления уроками и рассылкой уведомлений",
    version="1.0.0",
    lifespan=lifespan
)

# для учеников
@app.post("/students/", response_model=schemas.StudentResponse)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = models.Student(**student.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/students/", response_model=List[schemas.StudentResponse])
def read_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    students = db.query(models.Student).offset(skip).limit(limit).all()
    return students

@app.get("/students/{student_id}", response_model=schemas.StudentResponse)
def read_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

# для уроков
@app.post("/lessons/", response_model=schemas.LessonResponse)
def create_lesson(lesson: schemas.LessonCreate, db: Session = Depends(get_db)):
    db_lesson = models.Lesson(**lesson.model_dump())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson

@app.get("/lessons/", response_model=List[schemas.LessonResponse])
def read_lessons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    lessons = db.query(models.Lesson).offset(skip).limit(limit).all()
    return lessons

@app.post("/lessons/{lesson_id}/schedule-reminder")
async def schedule_reminder(lesson_id: int, db: Session = Depends(get_db)):
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    student = db.query(models.Student).filter(models.Student.id == lesson.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    scheduler.add_lesson_reminder(lesson, student)
    
    return {"status": "scheduled", "lesson_id": lesson_id}

@app.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")
    
    if scheduler and f"lesson_{lesson_id}" in [job.id for job in scheduler.scheduler.get_jobs()]:
        scheduler.scheduler.remove_job(f"lesson_{lesson_id}")
        logger.info(f"Отменено напоминание для удаленного урока {lesson_id}")
    
    db.delete(lesson)
    db.commit()
    
    return {"status": "deleted", "lesson_id": lesson_id, "message": "Урок успешно удален"}

@app.post("/test/send-message")
async def test_send_message():
    if not telegram_bot:
        raise HTTPException(status_code=500, detail="Telegram bot not initialized")
    
    # тест
    YOUR_CHAT_ID = "630099003"
    
    test_info = {
        'subject': 'Тестовый урок',
        'datetime': datetime.utcnow(),
        'platform': 'Test Platform',
        'link': 'https://test.com'
    }
    
    success = await telegram_bot.send_lesson_reminder(YOUR_CHAT_ID, test_info)
    
    if success:
        return {"status": "success", "message": "Сообщение отправлено!"}
    else:
        raise HTTPException(status_code=500, detail="Не удалось отправить сообщение")

# проверка
@app.get("/")
def read_root():
    return {"message": "Tutor Scheduler API is running!", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.patch("/students/{student_id}/toggle-active")
def toggle_student_active(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.is_active = not student.is_active
    db.commit()
    db.refresh(student)
    
    status = "активен" if student.is_active else "неактивен"
    return {"id": student.id, "name": student.name, "is_active": student.is_active, "message": f"Студент теперь {status}"}

@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    lessons_to_delete = db.query(models.Lesson).filter(
        models.Lesson.student_id == student_id
    ).all()
    
    for lesson in lessons_to_delete:
        if scheduler and f"lesson_{lesson.id}" in [job.id for job in scheduler.scheduler.get_jobs()]:
            scheduler.scheduler.remove_job(f"lesson_{lesson.id}")
            logger.info(f"Отменено напоминание для урока {lesson.id} при удалении студента")
        db.delete(lesson)
    
    db.delete(student)
    db.commit()
    
    return {
        "status": "deleted", 
        "student_id": student_id, 
        "name": student.name,
        "lessons_deleted": len(lessons_to_delete),
        "message": f"Студент '{student.name}' и {len(lessons_to_delete)} связанных уроков успешно удалены"
    }