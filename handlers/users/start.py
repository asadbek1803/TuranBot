from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.enums.parse_mode import ParseMode
from keyboards.reply.buttons import get_keyboard, language_keyboard
from aiogram.client.session.middlewares.request_logging import logger
from loader import db, bot
from aiogram.fsm.context import FSMContext
from data.config import ADMINS
from componets.messages import messages, buttons
from datetime import datetime

router = Router()

# Tilni tanlash uchun ReplyKeyboardMarkup



@router.message(CommandStart())
async def do_start(message: types.Message):
    """Foydalanuvchini tekshirish va u tanlagan til bo'yicha xabar yuborish."""
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    user = await db.select_user(telegram_id=telegram_id)

    if user:
        language = user.get("language", "uz")
        text = messages[language]["start_command"].format(name=full_name)
        video_url = "https://t.me/turan_mediafiles/2"
        await message.answer_video(
            caption=text,
            video=video_url,
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )
    else:
        text = f"Assalomu alaykum, <b>{full_name}</b>! 👋\n{messages['uz']['choose_lang']}"
        video_url = "https://t.me/turan_mediafiles/3"
        await message.answer_video(
            caption=text,
            video=video_url,
            reply_markup=language_keyboard(),
            parse_mode=ParseMode.HTML
        )


@router.message(Command("change_language"))
@router.message(lambda message: message.text == buttons["uz"]["btn_change_lang"] or
                             message.text == buttons["tr"]["btn_change_lang"]
                                )
async def get_lang_keyboards(message: types.Message):
    msg = await message.answer_video(
        caption="🌍 Iltimos, yangi tilni tanlang:\n\n🇺🇿 O‘zbekcha |  🇹🇷 Türkçe",
        reply_markup=language_keyboard(),
        video="https://t.me/turan_mediafiles/3"
    )

@router.message(lambda message: message.text in ["🇺🇿 O'zbek",  "🇹🇷 Türkçe"])
async def create_or_update_account(message: types.Message):
    """Foydalanuvchini bazaga qo'shish yoki tilini yangilash."""
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    language_map = {"🇺🇿 O'zbek": "uz",  "🇹🇷 Türkçe": "tr"}
    language = language_map[message.text]

    welcome_messages = {
        "uz": ("Akkaunt muvaffaqiyatli yaratildi ✅", 
               f"Assalomu alaykum <b>{full_name}</b>! Bizning Turan AI botga xush kelibsiz 😊"),
        
        "tr": ("Hesap başarıyla oluşturuldu ✅",
               f"Merhaba <b>{full_name}</b>! Turan AI botumuza hoş geldiniz 😊")
    }

    update_messages = {
        "uz": "Til muvaffiqiyatli yangilandi ✅",
        "tr": "Dil başarıyla güncellendi ✅"
    }
    try:
        user = await db.select_user(telegram_id=telegram_id)
        if user:
            await db.update_user_language(telegram_id, language)
            await message.answer(text=update_messages[language], reply_markup=get_keyboard(language))
        else:
            await db.add_user(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                language=language
            )
            success_msg, welcome_msg = welcome_messages[language]
            await message.answer(text=success_msg)
            video_url = "https://t.me/turan_mediafiles/2"
            await message.answer_video(
                caption=welcome_msg,
                video=video_url,
                parse_mode=ParseMode.HTML,
                reply_markup=get_keyboard(language)
            )
            for admin in ADMINS:
                try:
                    admin_message = f"🆕 Yangi foydalanuvchi qo'shildi:\n👤 Ism: {full_name}\n🔹 Username: @{username}\n🆔 Telegram ID: {telegram_id}\n📅 Qo'shilgan vaqt: {created_at}"
                    await bot.send_message(chat_id=admin, text=admin_message, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Adminga xabar yuborishda xatolik: {e}")
    except Exception as e:
        await message.answer(text=f"Serverda xatolik yuz berdi ❌\n\n\n/start buyrug'ini yuboring!")

