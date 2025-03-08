from aiogram import Router, types
from aiogram.enums.parse_mode import ParseMode
from componets.messages import buttons, messages
from loader import db



router = Router()




@router.message(lambda message: message.text == buttons["uz"]["btn_location"] or
                       message.text == buttons["tr"]["btn_location"])
async def handle_address_request(message: types.Message):
    """Handle education center address requests"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    video_url = "https://t.me/turan_mediafiles/6"
    location = [[types.InlineKeyboardButton(text = "📌 Xarita orqali ko'rish", url="https://maps.app.goo.gl/3hKwUrWuz2xAnQTX6")]]
    await message.answer_video(
        video = video_url,
        caption=messages[language]["education_center_address"],
        parse_mode=ParseMode.HTML,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard = location)
    )