from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Admin panel confirmation buttons
inline_keyboard = [[
    InlineKeyboardButton(text="✅ Ha", callback_data='yes'),
    InlineKeyboardButton(text="❌ Yo'q", callback_data='no')
]]
are_you_sure_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# Main admin menu buttons
admins_menu = [
    [InlineKeyboardButton(text="📤 Reklama yuborish", callback_data="reklama"), 
     InlineKeyboardButton(text="📊 Statistika", callback_data="statistics")],
    [InlineKeyboardButton(text="📃 Ma'lumotlar bazasini yuklab olish (Excel)", callback_data="allusers")],
    [InlineKeyboardButton(text="🗑️ Bazani tozalash", callback_data="cleandb")],
    [InlineKeyboardButton(text="👥 Adminlar ro'yxati", callback_data="list_admins"),
     InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin")],
    [InlineKeyboardButton(text="➖ Adminni o'chirish", callback_data="remove_admin")]
]

admin_menu_markup = InlineKeyboardMarkup(inline_keyboard=admins_menu)