from aiogram import Router, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
router = Router()


@router.message(Command('help'))
async def bot_help(message: types.Message):
    channel = [
        [InlineKeyboardButton(text="📢 Turan O'quv markazi", url="https://t.me/turankonsalting")],
        [InlineKeyboardButton(text="👩🏻‍💻 Turan Admin", url="https://t.me/Turan_talim")],
        [InlineKeyboardButton(text="📍 Manzil", url="https://maps.app.goo.gl/yu1S1VaGT6BNmkDDA")],
        [InlineKeyboardButton(text="📷 Instagram", url="https://www.instagram.com/turan_talim")],
        [InlineKeyboardButton(text="🎥 YouTube", url="https://www.youtube.com/@turansevdigimyerdeyim")],
        [InlineKeyboardButton(text="🚀 Facebook", url="https://www.facebook.com/share/14xjEBMrHKt/")]
    ]
    channel_markup = InlineKeyboardMarkup(inline_keyboard=channel)
    text = ("Bot haqida: ",
            "Ushbu bot Turan <b> O'quv markazi </b> uchun maxsus yaratilgan AI Suniy Intelekt botidir.",
            "Bot kommandalari: ",
            "/start - 🔄️ Botni ishga tushirish",
            "/change_language - 🌐 Tilni o'zgartirish",
            "/chat - 🤖 Yangi chat", 
            "/chat - ❌ Chatni to'xtatish",
            "Bizning ijtimoiy tarmoqlarga obuna bo'lishni unutmang ;) "
            )
    await message.answer(text="\n".join(text), reply_markup=channel_markup)
