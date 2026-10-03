import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
# ВАЖНО: Импортируем DefaultBotProperties для новой версии
from aiogram.client.default import DefaultBotProperties 
from aiogram.enums import ParseMode

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8229879973:AAHHMgDTmgKXmV4RffneBckGki-JwKQqefA"
CHANNEL_ID = "@testshola232" 
ADMIN_IDS = [5888064962] # Замените на ваш ID
# ===================================

logging.basicConfig(level=logging.INFO)

# ИСПРАВЛЕННАЯ СТРОКА (именно она вызывала ошибку ранее):
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
        "👋 Привет! Я бот канала <b>«Подслушано Школа 32»</b>.\n\n"
        "Напиши мне любое сообщение — оно анонимно появится у модераторов."
    )

@router.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_user_message(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"
    
    header = (
        f"📩 <b>Новое сообщение</b>\n"
        f"👤 {user.full_name}\n"
        f" {username} (<code>{user.id}</code>)\n"
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
            callback.message.text + "\n\n❌ <b>Отклонено</b>"
        )
        await callback.answer("Отклонено")

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
