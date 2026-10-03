import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@testshola232")
ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip()]

if not BOT_TOKEN:
    raise ValueError("Не найден токен бота! Проверьте переменные окружения.")

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

pending_posts: dict[int, dict] = {}

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        " Привет! Я бот канала <b>«Подслушано Школа 32»</b>.\n\n"
        "Напиши мне любое сообщение — оно анонимно появится у модераторов."
    )

@router.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_user_message(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"
    
    header = (
        f"📩 <b>Новое сообщение</b>\n"
        f" {user.full_name}\n"
        f"🆔 {username} (<code>{user.id}</code>)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject"),
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            header_msg = await bot.send_message(admin_id, header, reply_markup=kb)
            copied = await message.copy_to(chat_id=admin_id)
            
            post_data = {
                "admin_id": admin_id,
                "header_msg_id": header_msg.message_id,
                "content_msg_id": copied.message_id,
                "user_id": user.id,
            }
            
            pending_posts[header_msg.message_id] = post_data
            pending_posts[copied.message_id] = post_data
            
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

    await message.answer("✅ Сообщение отправлено на модерацию!")

@router.callback_query(F.data.in_({"publish", "reject"}))
async def moderate_callback(callback: CallbackQuery):
    post = pending_posts.pop(callback.message.message_id, None)
    if not post:
        await callback.answer("⚠️ Уже обработано", show_alert=True)
        return

    pending_posts.pop(post.get("content_msg_id"), None)

    if callback.data == "publish":
        try:
            await bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=post["admin_id"],
                message_id=post["content_msg_id"]
            )
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ <b>Опубликовано</b>"
            )
            await callback.answer("Готово!")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
    else:
        await callback.message.edit_text(
            callback.message.text + "\n\n <b>Отклонено</b>"
        )
        await callback.answer("Отклонено")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def run_web_server():
    app = web.Application()
    async def handle(request):
        return web.Response(text="Bot is alive!")
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web server started on port 8080")
    # Держим сервер живым
    await asyncio.Event().wait()

# --- ИСПРАВЛЕННЫЙ ЗАПУСК ---
async def main():
    print("🤖 Бот запущен...")
    # Создаем задачи и запускаем их параллельно
    bot_task = asyncio.create_task(dp.start_polling(bot))
    server_task = asyncio.create_task(run_web_server())
    
    # Ждем завершения любой из задач (обычно бот работает вечно)
    await asyncio.gather(bot_task, server_task)

if __name__ == "__main__":
    asyncio.run(main())
