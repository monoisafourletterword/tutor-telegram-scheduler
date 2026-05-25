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
        # ✅ Читаем настройки из .env
        self.mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
        self.proxy_url = os.getenv("PROXY_URL")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            f"👋 Привет, {update.effective_user.first_name}!\n\n"
            "Я бот для напоминаний об уроках.\n"
            "Ты получишь уведомление за 30 минут до занятия."
        )
    
    async def send_lesson_reminder(self, chat_id: str, lesson_info: dict):
        """Отправка напоминания об уроке"""
        message = (
            f"📚 *Напоминание об уроке*\n\n"
            f" Предмет: {lesson_info.get('subject', 'Не указан')}\n"
            f"⏰ Время: {lesson_info['datetime'].strftime('%d.%m.%Y в %H:%M')}\n"
            f"💻 Платформа: {lesson_info.get('platform', 'Не указана')}\n\n"
            f"🔗 Ссылка: {lesson_info.get('link', 'Не предоставлена')}\n\n"
            f"До встречи на уроке! 👋"
        )
        
        # ✅ Режим демо: только логирование
        if self.mock_mode:
            logger.info(f"🧪 [MOCK MODE] Отправка сообщения пользователю {chat_id}:\n{message}")
            return True
        
        try:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Напоминание отправлено пользователю {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения {chat_id}: {e}")
            return False
    
    def run_polling(self):
        """Запуск бота в режиме polling"""
        # ✅ Не запускаем polling в режиме демо
        if self.mock_mode:
            logger.info("🧪 [MOCK MODE] Бот запущен в демо-режиме (без реальных запросов к Telegram)")
            return
        
        # Настройка прокси если есть
        builder = Application.builder().token(self.token)
        if self.proxy_url:
            builder = builder.proxy_url(self.proxy_url)
            logger.info(f"🔗 Используем прокси: {self.proxy_url}")
        
        self.app = builder.build()
        self.app.add_handler(CommandHandler("start", self.start_command))
        logger.info("🤖 Telegram бот запущен...")
        
        try:
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")