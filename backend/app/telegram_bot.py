import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"👋 Привет, {update.effective_user.first_name}!\n\n"
            "Я бот для напоминаний об уроках с Никитой.\n"
            "Ты получишь уведомление за 30 минут до занятия.\n\n"
            "Используй команды:\n"
            "/help — список всех команд\n"
            "/schedule — ближайшее расписание\n"
            "/contact — связь с репетитором"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам"""
        help_text = (
            "📖 *Помощь*\n\n"
            "/start — Запустить бота\n"
            "/help — Показать эту справку\n"
            "/schedule — Посмотреть ближайшие уроки\n"
            "/contact — Контакты репетитора\n\n"
            "💡 Напоминания приходят автоматически за 30 мин до урока."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать ближайшее расписание"""
        chat_id = str(update.effective_user.id)
        
        from .database import SessionLocal
        from . import models
        from datetime import datetime
        
        db = SessionLocal()
        try:
            student = db.query(models.Student).filter(
                models.Student.telegram_id == chat_id
            ).first()
            
            if not student:
                await update.message.reply_text(
                    "❌ Не удалось найти твои уроки. Убедись, что ты добавил свой Telegram ID у репетитора."
                )
                return
            
            now = datetime.utcnow()
            upcoming_lessons = db.query(models.Lesson).filter(
                models.Lesson.student_id == student.id,
                models.Lesson.lesson_datetime >= now
            ).order_by(models.Lesson.lesson_datetime).limit(3).all()
            
            if not upcoming_lessons:
                await update.message.reply_text("📅 Ближайших уроков пока нет.")
                return
            
            text = "📅 *Ближайшие уроки:*\n\n"
            for lesson in upcoming_lessons:
                dt = lesson.lesson_datetime.strftime('%d.%m %H:%M')
                subj = lesson.subject or 'Без предмета'
                plat = lesson.platform or '?'
                text += f"• {dt} — {subj} ({plat})\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка в /schedule: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка при загрузке расписания.")
        finally:
            db.close()
    
    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Контакты репетитора"""
        contact_text = (
            "📞 *Контакты репетитора Никиты*\n\n"
            "Telegram: @monoisafourletterword\n" 
            "Пиши по любым вопросам:\n"
            "• Перенос урока\n"
            "• Технические проблемы\n"
            "• Домашние задания"
        )
        await update.message.reply_text(contact_text, parse_mode='Markdown')
    
    async def send_lesson_reminder(self, chat_id: str, lesson_info: dict):
        message = (
            f" *Напоминание об уроке*\n\n"
            f" Предмет: {lesson_info.get('subject', 'Не указан')}\n"
            f"⏰ Время: {lesson_info['datetime'].strftime('%d.%m.%Y в %H:%M')}\n"
            f"💻 Платформа: {lesson_info.get('platform', 'Не указана')}\n\n"
            f" Ссылка: {lesson_info.get('link', 'Не предоставлена')}\n\n"
            f"До встречи на уроке! 👋"
        )
        
        if self.mock_mode:
            logger.info(f"🧪 [MOCK MODE] Сообщение для {chat_id}:\n{message}")
            return True
        
        try:
            await self.app.bot.send_message(
                chat_id=chat_id, text=message, parse_mode='Markdown'
            )
            logger.info(f"✅ Напоминание отправлено пользователю {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки {chat_id}: {e}")
            return False
    
    def run_polling(self):
        if self.mock_mode:
            logger.info("🧪 [MOCK MODE] Демо-режим")
            return
            
        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("schedule", self.schedule_command))
        self.app.add_handler(CommandHandler("contact", self.contact_command))
        
        logger.info("🤖 Telegram бот запущен...")
        
        try:
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")