import os
import logging
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.admin import IsBotAdminFilter
from data.config import ADMINS
from loader import bot, db
from keyboards.inline.buttons import are_you_sure_markup
from keyboards.inline.admin_menu import admin_menu_markup
from utils.pgtoexcel import export_to_excel

router = Router()

class AdminState(StatesGroup):
    ask_ad_content = State()
    are_you_sure = State()

class AdminAddState(StatesGroup):
    waiting_for_user_id = State()
    confirm_add_admin = State()

# --------- Admin Panel Commands ---------

@router.message(Command('admin'), IsBotAdminFilter(ADMINS))
async def welcome_to_admin(message: types.Message):
    await message.answer(text="Assalomu alaykum Admin 😊\nAdmin Panel bilan tanishing 👇👇👇", reply_markup=admin_menu_markup)


# --------- User Management ---------

@router.message(Command('allusers'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "allusers", IsBotAdminFilter(ADMINS))
async def all_users(event: types.Message | types.CallbackQuery):
    users = await db.select_all_users()
    file_path = "data/users_list.xlsx"

    if isinstance(event, types.CallbackQuery):
        await event.answer("Tayyorlanmoqda ⌛")
        target_message = event.message
    else:
        await event.answer("Tayyorlanmoqda ⌛")
        target_message = event

    await export_to_excel(users, ['ID', 'Full Name', 'Username', 'Telegram ID', "Created at", "Language"], file_path)
    
    await target_message.answer_document(types.FSInputFile(file_path))


@router.callback_query(lambda c: c.data == "statistics", IsBotAdminFilter(ADMINS))
async def show_statistics(call: types.CallbackQuery):
    users_count = await db.count_users()
    await call.message.answer(f"Bot foydalanuvchilari soni: {users_count} ta")
    await call.answer()


# --------- Marketing ---------

@router.message(Command('reklama'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "reklama", IsBotAdminFilter(ADMINS))
async def ask_ad_content(event: types.Message | types.CallbackQuery, state: FSMContext):
    if isinstance(event, types.CallbackQuery):
        await event.message.answer("Reklama uchun post yuboring")
        await event.answer()
    else:
        await event.answer("Reklama uchun post yuboring")
    
    await state.set_state(AdminState.ask_ad_content)


@router.message(AdminState.ask_ad_content, IsBotAdminFilter(ADMINS))
async def send_ad_to_users(message: types.Message, state: FSMContext):
    users = await db.select_all_users()
    count = 0
    
    # Send status message first
    status_msg = await message.answer("Reklama yuborilmoqda...")
    
    for user in users:
        user_id = user[3]
        try:
            await message.send_copy(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as error:
            logging.info(f"Ad did not send to user: {user_id}. Error: {error}")
    
    await status_msg.edit_text(f"Reklama {count} ta foydalanuvchiga muvaffaqiyatli yuborildi.")
    await state.clear()


# --------- Database Management ---------

@router.message(Command('cleandb'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "cleandb", IsBotAdminFilter(ADMINS))
async def ask_are_you_sure(event: types.Message | types.CallbackQuery, state: FSMContext):
    if isinstance(event, types.CallbackQuery):
        msg = await event.message.reply("Haqiqatdan ham bazani tozalab yubormoqchimisiz?", reply_markup=are_you_sure_markup)
        await event.answer()
    else:
        msg = await event.reply("Haqiqatdan ham bazani tozalab yubormoqchimisiz?", reply_markup=are_you_sure_markup)
    
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AdminState.are_you_sure)


@router.callback_query(AdminState.are_you_sure, IsBotAdminFilter(ADMINS))
async def clean_db(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get('msg_id')
    
    if call.data == 'yes':
        await db.delete_users()
        text = "Baza tozalandi!"
    elif call.data == 'no':
        text = "Bekor qilindi."
    
    await bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=msg_id)
    await state.clear()


# --------- Social Links ---------

async def add_social_link(name, url, link_type="social"):
    """Add or update a social media link in the database"""
    query = """
    INSERT INTO social_links (name, url, link_type) 
    VALUES ($1, $2, $3) 
    ON CONFLICT (name) 
    DO UPDATE SET url = $2, link_type = $3
    RETURNING id
    """
    return await db.execute(query, name, url, link_type)


@router.message(Command("add_social_link"), IsBotAdminFilter(ADMINS))
async def add_social_link_handler(message: types.Message):
    """Handler for adding social media links by admins"""
    # Parse command arguments: /add_social_link Instagram https://instagram.com/turan_edu
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Usage: /add_social_link [name] [url]\nExample: /add_social_link Instagram https://instagram.com/turan_edu"
        )
        return
    
    name = args[1]
    url = args[2]
    
    # Add to database
    try:
        await add_social_link(name, url)
        await message.answer(f"Social media link '{name}' added successfully!")
    except Exception as e:
        await message.answer(f"Error adding social media link: {str(e)}")


@router.message(Command("add_special_link"), IsBotAdminFilter(ADMINS))
async def add_special_link_handler(message: types.Message):
    """Handler for adding admin contact or location by admins"""
    # Parse command arguments: /add_special_link admin https://t.me/turan_admin
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.answer(
            "Usage: /add_special_link [type] [name] [url]\n"
            "Example: /add_special_link admin Admin https://t.me/turan_admin\n"
            "Example: /add_special_link location GPS https://maps.google.com/?q=41.2950,69.2044"
        )
        return
    
    link_type = args[1]
    name = args[2]
    url = args[3]
    
    # Add to database
    try:
        await add_social_link(name, url, link_type)
        await message.answer(f"Special link '{name}' of type '{link_type}' added successfully!")
    except Exception as e:
        await message.answer(f"Error adding special link: {str(e)}")


# --------- Admin Management ---------

@router.message(Command('add_admin'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "add_admin", IsBotAdminFilter(ADMINS))
async def ask_for_admin_id(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Command to start the process of adding a new admin"""
    if isinstance(event, types.CallbackQuery):
        await event.message.answer("Yangi admin qo'shish uchun Telegram ID raqamini kiriting:")
        await event.answer()
    else:
        await event.answer("Yangi admin qo'shish uchun Telegram ID raqamini kiriting:")
    
    await state.set_state(AdminAddState.waiting_for_user_id)


@router.message(AdminAddState.waiting_for_user_id, IsBotAdminFilter(ADMINS))
async def confirm_add_admin(message: types.Message, state: FSMContext):
    """Validate user ID and ask for confirmation"""
    user_id = message.text.strip()
    
    # Validate that input is a number
    if not user_id.isdigit():
        await message.answer("Noto'g'ri format. Iltimos, raqamlardan iborat Telegram ID kiriting.")
        return
    
    # Check if already an admin
    if user_id in ADMINS:
        await message.answer("Bu foydalanuvchi allaqachon admin hisoblanadi!")
        await state.clear()
        return
    
    # Store the ID and ask for confirmation
    await state.update_data(new_admin_id=user_id)
    
    # Try to get user info
    try:
        user_info = await bot.get_chat(user_id)
        user_detail = f"👤 {user_info.full_name}"
        if user_info.username:
            user_detail += f" (@{user_info.username})"
    except Exception as e:
        logging.error(f"Error getting user info: {e}")
        user_detail = f"ID: {user_id} (Foydalanuvchi topilmadi yoki bot bilan bog'lanmagan)"
    
    await message.answer(
        f"Quyidagi foydalanuvchini admin qilishni tasdiqlaysizmi?\n\n{user_detail}",
        reply_markup=are_you_sure_markup
    )
    await state.set_state(AdminAddState.confirm_add_admin)


@router.callback_query(AdminAddState.confirm_add_admin, IsBotAdminFilter(ADMINS))
async def process_add_admin(call: types.CallbackQuery, state: FSMContext):
    """Process the admin addition based on confirmation"""
    await call.answer()
    
    if call.data == 'yes':
        # Get the stored admin ID
        data = await state.get_data()
        new_admin_id = data.get('new_admin_id')
        
        try:
            # Update .env file
            env_path = os.path.join(os.getcwd(), '.env')
            updated = False
            
            # Read the current .env content
            if os.path.exists(env_path):
                with open(env_path, 'r') as file:
                    lines = file.readlines()
                
                # Find and update ADMINS line
                with open(env_path, 'w') as file:
                    for line in lines:
                        if line.startswith('ADMINS='):
                            current_value = line.strip().split('=', 1)[1]
                            # Remove quotes if present
                            if (current_value.startswith('"') and current_value.endswith('"')) or \
                               (current_value.startswith("'") and current_value.endswith("'")):
                                current_value = current_value[1:-1]
                            
                            # Parse and update admin list
                            admin_list = current_value.split(',')
                            admin_list.append(new_admin_id)
                            new_admin_str = ','.join(admin_list)
                            
                            # Write updated line
                            file.write(f'ADMINS={new_admin_str}\n')
                            updated = True
                        else:
                            file.write(line)
            
            # If ADMINS line wasn't found, append it
            if not updated:
                with open(env_path, 'a') as file:
                    # If file is empty or doesn't end with newline, add one
                    if os.path.exists(env_path) and os.path.getsize(env_path) > 0:
                        with open(env_path, 'rb+') as f:
                            f.seek(-1, os.SEEK_END)
                            last_char = f.read(1)
                            if last_char != b'\n':
                                file.write('\n')
                    
                    # Append the new ADMINS line
                    current_admins = ','.join(ADMINS)
                    if new_admin_id not in ADMINS:
                        if current_admins:
                            file.write(f'ADMINS={current_admins},{new_admin_id}\n')
                        else:
                            file.write(f'ADMINS={new_admin_id}\n')
            
            # Update ADMINS in the current session
            ADMINS.append(new_admin_id)
            
            # Try to notify the new admin
            try:
                await bot.send_message(
                    chat_id=new_admin_id,
                    text="🎉 Tabriklaymiz! Siz botning administratori etib tayinlandingiz. /admin buyrug'i orqali admin paneliga kirishingiz mumkin."
                )
            except Exception as e:
                logging.error(f"Error sending notification to new admin: {e}")
            
            await call.message.edit_text("✅ Admin muvaffaqiyatli qo'shildi! Bot qayta ishga tushirilganda yangi admin huquqlari to'liq kuchga kiradi.")
            
        except Exception as e:
            logging.error(f"Error adding admin: {e}")
            await call.message.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
    else:
        await call.message.edit_text("❌ Admin qo'shish bekor qilindi.")
    
    await state.clear()


@router.message(Command('list_admins'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "list_admins", IsBotAdminFilter(ADMINS))
async def list_admins(event: types.Message | types.CallbackQuery):
    """List all current admin IDs"""
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
        
    if not ADMINS:
        await message.answer("Adminlar ro'yxati bo'sh.")
        return
    
    admin_list = []
    for admin_id in ADMINS:
        try:
            user_info = await bot.get_chat(admin_id)
            admin_name = f"👤 {user_info.full_name}"
            if user_info.username:
                admin_name += f" (@{user_info.username})"
            admin_list.append(f"{admin_name}\nID: {admin_id}")
        except Exception:
            admin_list.append(f"ID: {admin_id}")
    
    await message.answer("Bot adminlari ro'yxati:\n\n" + "\n\n".join(admin_list))


@router.message(Command('remove_admin'), IsBotAdminFilter(ADMINS))
@router.callback_query(lambda c: c.data == "remove_admin", IsBotAdminFilter(ADMINS))
async def ask_for_admin_removal(event: types.Message | types.CallbackQuery):
    """Command to remove an admin"""
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
        
    if len(ADMINS) <= 1:
        await message.answer("⚠️ Kamida bitta admin qolishi kerak. Adminni o'chirib bo'lmaydi.")
        return
    
    admin_buttons = []
    
    for i, admin_id in enumerate(ADMINS):
        # Skip the first admin (owner)
        if i == 0:
            continue
            
        try:
            user_info = await bot.get_chat(admin_id)
            button_text = f"{user_info.full_name}"
            if user_info.username:
                button_text += f" (@{user_info.username})"
        except Exception:
            button_text = f"ID: {admin_id}"
            
        admin_buttons.append([types.InlineKeyboardButton(text=button_text, callback_data=f"remove_admin_{admin_id}")])
    
    # Add cancel button
    admin_buttons.append([types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin_removal")])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=admin_buttons)
    await message.answer("Adminlikdan olib tashlamoqchi bo'lgan foydalanuvchini tanlang:", reply_markup=markup)


@router.callback_query(lambda c: c.data.startswith("remove_admin_"), IsBotAdminFilter(ADMINS))
async def confirm_remove_admin(call: types.CallbackQuery):
    """Ask for confirmation to remove an admin"""
    admin_id = call.data.split("_")[-1]
    
    try:
        user_info = await bot.get_chat(admin_id)
        admin_name = f"{user_info.full_name}"
        if user_info.username:
            admin_name += f" (@{user_info.username})"
    except Exception:
        admin_name = f"ID: {admin_id}"
    
    confirm_buttons = [
        [
            types.InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_remove_admin_{admin_id}"),
            types.InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_admin_removal")
        ]
    ]
    confirm_markup = types.InlineKeyboardMarkup(inline_keyboard=confirm_buttons)
    
    await call.message.edit_text(
        f"Haqiqatan ham {admin_name} ni adminlikdan olib tashlamoqchimisiz?",
        reply_markup=confirm_markup
    )
    
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("confirm_remove_admin_"), IsBotAdminFilter(ADMINS))
async def process_remove_admin(call: types.CallbackQuery):
    """Process admin removal after confirmation"""
    admin_id = call.data.split("_")[-1]
    
    try:
        # Update .env file
        env_path = os.path.join(os.getcwd(), '.env')
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as file:
                lines = file.readlines()
            
            with open(env_path, 'w') as file:
                for line in lines:
                    if line.startswith('ADMINS='):
                        current_value = line.strip().split('=', 1)[1]
                        # Remove quotes if present
                        if (current_value.startswith('"') and current_value.endswith('"')) or \
                           (current_value.startswith("'") and current_value.endswith("'")):
                            current_value = current_value[1:-1]
                        
                        # Parse and update admin list
                        admin_list = current_value.split(',')
                        if admin_id in admin_list:
                            admin_list.remove(admin_id)
                        new_admin_str = ','.join(admin_list)
                        
                        # Write updated line
                        file.write(f'ADMINS={new_admin_str}\n')
                    else:
                        file.write(line)
        
        # Update ADMINS in the current session
        if admin_id in ADMINS:
            ADMINS.remove(admin_id)
        
        # Try to notify the removed admin
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="ℹ️ Sizning admin huquqlaringiz olib tashlandi."
            )
        except Exception as e:
            logging.error(f"Error sending notification to removed admin: {e}")
        
        await call.message.edit_text("✅ Admin muvaffaqiyatli olib tashlandi! Bot qayta ishga tushirilganda o'zgarishlar to'liq kuchga kiradi.")
        
    except Exception as e:
        logging.error(f"Error removing admin: {e}")
        await call.message.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await call.answer()


@router.callback_query(lambda c: c.data == "cancel_admin_removal", IsBotAdminFilter(ADMINS))
async def cancel_admin_removal(call: types.CallbackQuery):
    """Cancel admin removal"""
    await call.message.edit_text("❌ Admin olib tashlash bekor qilindi.")
    await call.answer()