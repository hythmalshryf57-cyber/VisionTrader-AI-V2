import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import uuid
from config import settings
from database import get_db
from models import InviteCode
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class PaymentStates(StatesGroup):
    waiting_for_payment_proof = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "مرحباً بك في بوت VisionTrader AI! 🎯\n\n"
        "للحصول على التطبيق:\n"
        "1. اضغط /buy لمعرفة طرق الدفع\n"
        "2. أرسل إثبات الدفع\n"
        "3. ستحصل على رمز الدعوة\n\n"
        "استخدم /help للمساعدة"
    )

@dp.message_handler(commands=['buy'])
async def buy(message: types.Message):
    await message.reply(
        "طرق الدفع المتاحة:\n\n"
        "💰 حوالة بنكية: [تفاصيل الحساب]\n"
        "₿ USDT: [عنوان المحفظة]\n\n"
        "بعد الدفع، أرسل صورة إثبات الدفع هنا.\n"
        "سيتم مراجعتها خلال 24 ساعة."
    )

@dp.message_handler(commands=['payment_methods'])
async def payment_methods(message: types.Message):
    await message.reply(
        "طرق الدفع:\n\n"
        "1. حوالة بنكية\n"
        "2. USDT (TRC20)\n"
        "3. PayPal\n\n"
        "السعر: 50 دولار للشهر الواحد"
    )

@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.reply(
        "أسئلة شائعة:\n\n"
        "❓ كيف أحصل على التطبيق؟\n"
        "أرسل إثبات الدفع بعد /buy\n\n"
        "❓ كم يستغرق المراجعة؟\n"
        "24 ساعة كحد أقصى\n\n"
        "❓ مشكلة في الدفع؟\n"
        "اتصل بالدعم: @support"
    )

@dp.message_handler(content_types=['photo'])
async def handle_payment_proof(message: types.Message):
    if message.from_user is None:
        return

    # Forward to admin
    admin_keyboard = InlineKeyboardMarkup()
    admin_keyboard.add(
        InlineKeyboardButton("تأكيد", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("رفض", callback_data=f"reject_{message.from_user.id}")
    )

    await bot.send_photo(
        chat_id=settings.ADMIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=f"إثبات دفع جديد:\n"
                f"المستخدم: {message.from_user.full_name}\n"
                f"اليوزر: @{message.from_user.username}\n"
                f"المعرف: {message.from_user.id}\n"
                f"التاريخ: {message.date}",
        reply_markup=admin_keyboard
    )

    await message.reply("تم استلام إثبات الدفع! سيتم مراجعته خلال 24 ساعة.")

@dp.callback_query_handler(lambda c: c.data.startswith('approve_'))
async def approve_payment(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])

    # Generate invite code
    invite_code = str(uuid.uuid4())[:8].upper()

    db: Session = next(get_db())
    new_code = InviteCode(code=invite_code, created_by_admin=True)
    db.add(new_code)
    db.commit()

    # Send to user
    await bot.send_message(
        chat_id=user_id,
        text=f"✅ تم تأكيد الدفع!\n\nرمز الدعوة الخاص بك: `{invite_code}`\n\nاستخدمه للتسجيل في التطبيق."
    )

    await callback_query.answer("تم إرسال الرمز للمستخدم")

@dp.callback_query_handler(lambda c: c.data.startswith('reject_'))
async def reject_payment(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])

    await bot.send_message(
        chat_id=user_id,
        text="❌ تم رفض الدفع.\n\nراجع طريقة الدفع الصحيحة وأعد المحاولة."
    )

    await callback_query.answer("تم رفض الدفع")

async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())