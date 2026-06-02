import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import uuid
from config import settings
from database import get_db, SessionLocal
from models import InviteCode, JournalEntry
from sqlalchemy.orm import Session
from services.auto_scanner import auto_scanner
from services.voting_engine import voting_engine
import models

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class PaymentStates(StatesGroup):
    waiting_for_payment_proof = State()


class InviteStates(StatesGroup):
    waiting_for_name = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "أهلاً! أنا بوت VisionTrader AI. أقدر أعطيك رمز دعوة للمنصة. اكتب /invite عشان تحصل على رمزك.\n\n"
        "للمساعدة: استخدم /help"
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
        "بوت VisionTrader AI جاهز للعمل.\n\n"
        "الأوامر المدعومة:\n"
        "/start - ابدأ المحادثة\n"
        "/invite - اطلب رمز دعوة\n"
        "/status - حالة الماسح الضوئي\n"
        "/scan <رمز> - فحص سريع لسوق محدد\n"
        "/top - أفضل 3 فرص حالياً\n"
        "/performance - أداء التداول الأخير\n"
        "/daily - تقرير الأداء اليومي\n"
        "\nللدفع: /buy"
    )


@dp.message_handler(commands=['invite'])
async def invite(message: types.Message):
    await message.reply("جميل — ايش اسمك؟")
    await InviteStates.waiting_for_name.set()


@dp.message_handler(state=InviteStates.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def receive_name(message: types.Message, state: FSMContext):
    name = (message.text or '').strip()
    if not name:
        await message.reply('الرجاء إدخال اسم صالح.')
        return

    invite_code = str(uuid.uuid4())[:8].upper()

    db: Session = next(get_db())
    new_code = InviteCode(code=invite_code, created_by_admin=False)
    db.add(new_code)
    db.commit()

    await message.reply(
        f"أهلاً {name}! هذا رمز الدعوة الخاص بك:\n\n{invite_code}\n\n"
        f"استخدم هذا الرمز في صفحة إنشاء الحساب: {invite_code}"
    )
    await state.finish()


@dp.message_handler()
async def fallback(message: types.Message):
    await message.reply(
        "الأوامر المتاحة:\n/start - ابدأ\n/invite - اطلب رمز دعوة\n/buy - طرق الدفع\n/help - مساعدة"
    )

@dp.message_handler(commands=['status'])
async def status(message: types.Message):
    is_running = getattr(auto_scanner, 'is_running', False)
    await message.reply(f"حالة الماسح الضوئي: {'قيد التشغيل' if is_running else 'متوقف'}")

@dp.message_handler(commands=['top'])
async def top_opportunities(message: types.Message):
    opportunities = auto_scanner.get_top_opportunities()
    if not opportunities:
        await message.reply("لا توجد فرص مميزة حالياً.")
        return
    lines = ["أفضل 3 فرص حالياً:"]
    for item in opportunities:
        lines.append(
            f"{item['market']}: {item['recommendation']} ({item['confidence']}%)\n"
            f"Entry: {item['entry']} SL: {item['sl']} TP: {item['tp']}"
        )
    await message.reply("\n\n".join(lines))

@dp.message_handler(commands=['scan'])
async def scan(message: types.Message):
    args = message.get_args().strip() if hasattr(message, 'get_args') else ''
    symbol = args.split()[0].upper() if args else ''
    if not symbol:
        await message.reply("يرجى استخدام /scan <رمز>. مثال: /scan XAUUSD")
        return

    if symbol not in auto_scanner.MARKETS:
        await message.reply(f"السوق '{symbol}' غير مدعوم. استخدم رمز واحد من: {', '.join(auto_scanner.MARKETS)}")
        return

    try:
        simulated_visual = [{"description": f"Manual scan for {symbol}."}]
        result = voting_engine.analyze(simulated_visual)
        rec = result.get('recommendation', 'محايد')
        conf = int(result.get('confidence', 0))

        if rec not in ['شراء', 'بيع'] or conf < 60:
            await message.reply(f"لا يوجد إشارة قوية على {symbol} الآن. ({rec} - {conf}%)")
            return

        levels = auto_scanner._build_trade_levels(symbol, rec)
        await message.reply(
            f"🔎 نتيجة الفحص السريع لـ {symbol}:\n"
            f"توصية: {rec}\n"
            f"ثقة: {conf}%\n"
            f"السعر الحالي: {levels['entry']}\n"
            f"SL: {levels['sl']}\n"
            f"TP: {levels['tp']}"
        )
    except Exception as e:
        await message.reply(f"فشل الفحص السريع: {e}")

def _build_trading_stats(period_days: int):
    session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        entries = session.query(JournalEntry).filter(JournalEntry.date >= cutoff).all()
        total = len(entries)
        wins = len([e for e in entries if str(e.result).lower() == 'win'])
        losses = len([e for e in entries if str(e.result).lower() == 'loss'])
        pnl = sum((e.profit_loss or 0.0) for e in entries)
        return {
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': int((wins / total * 100) if total else 0),
            'pnl': pnl,
        }
    finally:
        session.close()

@dp.message_handler(commands=['performance'])
async def performance(message: types.Message):
    weekly = _build_trading_stats(7)
    monthly = _build_trading_stats(30)
    await message.reply(
        f"📊 أداء التداول:\n"
        f"هذا الأسبوع: {weekly['total']} صفقات، {weekly['wins']} رابحة، {weekly['losses']} خاسرة، نسبة نجاح {weekly['win_rate']}%، PnL {weekly['pnl']:.2f}$\n"
        f"هذا الشهر: {monthly['total']} صفقات، {monthly['wins']} رابحة، {monthly['losses']} خاسرة، نسبة نجاح {monthly['win_rate']}%، PnL {monthly['pnl']:.2f}$"
    )

@dp.message_handler(commands=['daily'])
async def daily_report(message: types.Message):
    session = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=1)
        entries = session.query(JournalEntry).filter(JournalEntry.date >= since).all()
        if not entries:
            await message.reply("لا توجد بيانات تداول خلال الـ 24 ساعة الماضية.")
            return
        total = len(entries)
        wins = len([e for e in entries if str(e.result).lower() == 'win'])
        losses = len([e for e in entries if str(e.result).lower() == 'loss'])
        pnl = sum((e.profit_loss or 0.0) for e in entries)
        await message.reply(
            f"📅 تقرير يومي:\n"
            f"الصفقات: {total}\n"
            f"رابحة: {wins}\n"
            f"خاسرة: {losses}\n"
            f"PnL: {pnl:.2f}$"
        )
    finally:
        session.close()

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