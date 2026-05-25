from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
import asyncio

from . import models

logger = logging.getLogger(__name__)

class LessonScheduler:
    def __init__(self, telegram_bot, db_session):
        self.scheduler = BackgroundScheduler()
        self.telegram_bot = telegram_bot
        self.db_session = db_session
        
    def add_lesson_reminder(self, lesson: models.Lesson, student: models.Student):
        """Добавление напоминания для урока"""
        reminder_time = lesson.lesson_datetime - timedelta(minutes=30)
        now = datetime.utcnow()
        
        # Если время напоминания уже прошло — отправляем сразу
        if reminder_time <= now:
            logger.warning(f"️ Время напоминания для урока {lesson.id} уже прошло, отправляем сразу")
            asyncio.run(self._send_reminder_sync(lesson.id, student.telegram_id))
            return None
        
        job = self.scheduler.add_job(
            self._send_reminder,
            'date',
            run_date=reminder_time,
            args=[lesson.id, student.telegram_id],
            id=f"lesson_{lesson.id}",
            replace_existing=True
        )
        
        logger.info(f"⏰ Напоминание для урока {lesson.id} запланировано на {reminder_time}")
        return job
    
    async def _send_reminder_sync(self, lesson_id: int, telegram_id: str):
        """Синхронная обёртка для отправки"""
        db = self.db_session()
        try:
            lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
            if not lesson or lesson.reminder_sent:
                return
            
            lesson_info = {
                'subject': lesson.subject,
                'datetime': lesson.lesson_datetime,
                'platform': lesson.platform,
                'link': lesson.meeting_link
            }
            
            success = await self.telegram_bot.send_lesson_reminder(telegram_id, lesson_info)
            
            if success:
                lesson.reminder_sent = True
                db.commit()
                logger.info(f"✅ Напоминание для урока {lesson_id} отправлено")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке напоминания {lesson_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _send_reminder(self, lesson_id: int, telegram_id: str):
        """Отправка напоминания (вызывается планировщиком)"""
        db = self.db_session()
        try:
            lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
            if not lesson or lesson.reminder_sent:
                return
            
            lesson_info = {
                'subject': lesson.subject,
                'datetime': lesson.lesson_datetime,
                'platform': lesson.platform,
                'link': lesson.meeting_link
            }
            
            # Запускаем асинхронный код
            success = asyncio.run(self.telegram_bot.send_lesson_reminder(telegram_id, lesson_info))
            
            if success:
                lesson.reminder_sent = True
                db.commit()
                logger.info(f"✅ Напоминание для урока {lesson_id} отправлено")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке напоминания {lesson_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        logger.info("📅 Планировщик запущен")
    
    def shutdown(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()