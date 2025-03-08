from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import db
from componets.messages import messages

inline_keyboard = [[
    InlineKeyboardButton(text="✅ Yes", callback_data='yes'),
    InlineKeyboardButton(text="❌ No", callback_data='no')
]]
are_you_sure_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)



# languages = [[
#     InlineKeyboardButton("🇺🇿 O'zbek", callback_data='uz'),
#     InlineKeyboardButton("🇷🇺 Русский", callback_data='ru'),
#     InlineKeyboardButton('🇺🇸 English', callback_data='eng')
# ]]

# languages_markup = InlineKeyboardMarkup(inline_keyboard=languages)

async def get_social_links(link_type=None):
    """Get social media links from database, optionally filtered by type"""
    if link_type:
        query = "SELECT id, name, url, link_type FROM social_links WHERE link_type = $1 ORDER BY id"
        return await db.fetch(query, link_type)
    else:
        query = "SELECT id, name, url, link_type FROM social_links ORDER BY id"
        return await db.fetch(query)



async def get_social_media_keyboard(language):
    """Generate inline keyboard with social media links from database"""
    # Get social media links
    social_links = await get_social_links("social")
    admin_links = await get_social_links("admin")
    location_links = await get_social_links("location")
    
    # Build keyboard
    keyboard = []
    
    # Add social media links (2 per row)
    social_row = []
    for i, link in enumerate(social_links):
        social_row.append(InlineKeyboardButton(text=link["name"], url=link["url"]))
        if len(social_row) == 2 or i == len(social_links) - 1:
            keyboard.append(social_row)
            social_row = []
    
    # Add admin links
    for link in admin_links:
        keyboard.append([InlineKeyboardButton(
            text=messages[language].get("admin_contact", link["name"]), 
            url=link["url"]
        )])
    
    # Add location links
    for link in location_links:
        keyboard.append([InlineKeyboardButton(
            text=messages[language].get("location_gps", link["name"]), 
            url=link["url"]
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)