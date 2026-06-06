from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
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
        TYUMEN_TZ = timezone(timedelta(hours=5))
        lesson_time_naive = lesson.lesson_datetime.replace(tzinfo=None)
        reminder_time = lesson_time_naive - timedelta(minutes=30)
        now_utc = datetime.utcnow()
        reminder_time_utc = reminder_time - timedelta(hours=5)
        
        if reminder_time_utc <= now_utc:
            logger.warning(f"Время напоминания для урока {lesson.id} уже прошло ({reminder_time_utc}). Отправляем напоминание немедленно.")
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._send_reminder_sync(lesson.id, student.telegram_id))
                else:
                    asyncio.run(self._send_reminder_sync(lesson.id, student.telegram_id))
            except RuntimeError:
                asyncio.run(self._send_reminder_sync(lesson.id, student.telegram_id))
            return None

        job = self.scheduler.add_job(
            self._send_reminder,
            'date',
            run_date=reminder_time_utc, 
            args=[lesson.id, student.telegram_id],
            id=f"lesson_{lesson.id}",
            replace_existing=True
        )
        
        logger.info(f"Напоминание для урока {lesson.id} запланировано на {reminder_time_utc} (UTC)")
        return job
    
    async def _send_reminder_sync(self, lesson_id: int, telegram_id: str):
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
                logger.info(f"Напоминание для урока {lesson_id} отправлено")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания {lesson_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _send_reminder(self, lesson_id: int, telegram_id: str):
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
            
            success = asyncio.run(self.telegram_bot.send_lesson_reminder(telegram_id, lesson_info))
            if success:
                lesson.reminder_sent = True
                db.commit()
                logger.info(f"Напоминание для урока {lesson_id} отправлено")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания {lesson_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def start(self):
        self.scheduler.start()
        logger.info("Планировщик запущен")
    
    def shutdown(self):
        self.scheduler.shutdown()