from aiogram import Router, types
from aiogram.enums.parse_mode import ParseMode
from componets.messages import buttons, messages
from loader import db



router = Router()


channel = [
        [types.InlineKeyboardButton(text="📢 Turan O'quv markazi", url="https://t.me/turankonsalting")],
        [types.InlineKeyboardButton(text="👩🏻‍💻 Turan Admin", url="https://t.me/Turan_talim")],
        [types.InlineKeyboardButton(text="📍 Manzil", url="https://maps.app.goo.gl/yu1S1VaGT6BNmkDDA")],
        [types.InlineKeyboardButton(text="📷 Instagram", url="https://www.instagram.com/turan_talim")],
        [types.InlineKeyboardButton(text="🎥 YouTube", url="https://www.youtube.com/@turansevdigimyerdeyim")],
        [types.InlineKeyboardButton(text="🚀 Facebook", url="https://www.facebook.com/share/14xjEBMrHKt/")]
    ]
channel_markup = types.InlineKeyboardMarkup(inline_keyboard=channel)


@router.message(lambda message: message.text == buttons["uz"]["btn_aboutus"] or
                       message.text == buttons["tr"]["btn_aboutus"])
async def handle_about_center(message: types.Message):
    """Handle information requests about Turan Education Center"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    
    about_text = {
        "uz": (
            "<b>TURAN TA'LIM – FARG‘ONADAGI YAGONA TURK TILI MARKAZI</b>\n\n"
            "Turan O‘quv Markazi – Farg‘ona shahridagi yagona <b>Turk tili markazi</b> bo‘lib, "
            "o‘quvchilarga sifatli ta’lim berish va ularning kelajagiga yo‘l ochishni maqsad qilgan. "
            "Markazimiz 2 yil oldin tashkil etilgan bo‘lib, <b>Turan Kansalting</b> va <b>Turan Til Markazi</b> "
            "asoschisi <b>Tamer Tunç</b> tomonidan ochilgan.\n\n"
            "<b>📚 O‘tiladigan fanlar:</b>\n"
            "✔️ Turk tili\n"
            "✔️ TYS imtihoniga tayyorgarlik\n"
            "✔️ Matematika va Mantiq\n"
            "✔️ Tarix\n"
            "✔️ Huquq\n\n"
            "<b>📍 Manzilimiz:</b> Farg‘ona shahri, 'Ixlos savdo majmuasi', 3-qavat\n"
            "📞 <b>Telefon:</b> +998 90 846 81 88\n"
            "📲 <b>Telegram:</b> <a href='https://t.me/Turan_talim'>t.me/Turan_talim</a>"
        ),
        "tr": (
            "<b>TURAN TA'LIM – FERGANA'DAKİ TEK TÜRKÇE MERKEZİ</b>\n\n"
            "Turan Eğitim Merkezi, Fergana’daki tek <b>Türkçe merkezi</b> olup, "
            "öğrencilere kaliteli eğitim sunmayı ve onların geleceğine yön vermeyi amaçlamaktadır. "
            "Merkezimiz 2 yıl önce kurulmuş olup, <b>Turan Danışmanlık</b> ve <b>Turan Dil Merkezi</b> "
            "kurucusu <b>Tamer Tunç</b> tarafından açılmıştır.\n\n"
            "<b>📚 Verilen Dersler:</b>\n"
            "✔️ Türkçe\n"
            "✔️ TYS Sınav Hazırlık\n"
            "✔️ Matematik ve Mantık\n"
            "✔️ Tarih\n"
            "✔️ Hukuk\n\n"
            "<b>📍 Adresimiz:</b> Fergana şehri, 'Ixlos ticaret kompleksi', 3. kat\n"
            "📞 <b>Telefon:</b> +998 90 846 81 88\n"
            "📲 <b>Telegram:</b> <a href='https://t.me/Turan_talim'>t.me/Turan_talim</a>"
        )
    }
    video_url = "https://t.me/turan_mediafiles/5"
    await message.answer_video(
        video=video_url,
        caption=about_text.get(language, about_text["uz"]),
        parse_mode=ParseMode.HTML,
        reply_markup=channel_markup
    )
