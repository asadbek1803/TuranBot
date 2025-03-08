import asyncio
import os
import json
from typing import Optional
import aiohttp
from collections import defaultdict
from datetime import datetime, timedelta
import re
from langdetect import detect
import tempfile
from gtts import gTTS
from keyboards.reply.buttons import get_keyboard
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums.parse_mode import ParseMode
from loader import bot, db
from data.config import API_KEY, ASSEMBLYAI_API_KEY  # DEEPGRAM_API_KEY o'rniga ASSEMBLYAI_API_KEY ishlatiladi
from componets.messages import buttons, messages
import google.generativeai as ai

# Configure AI models
ai.configure(api_key=API_KEY)
model = ai.GenerativeModel("gemini-2.0-flash")

router = Router()

# Session management
user_sessions = {}
user_last_request_time = {}



def format_text(text):
    """Convert text to HTML format"""
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text

async def safe_delete_message(message: types.Message):
    """Safely delete a message, catching any deletion errors"""
    try:
        await message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")
        pass

# Rate limiting configuration
class VoiceRateLimiter:
    def __init__(self):
        self.active_users = defaultdict(int)
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=5)
        self.max_concurrent_users = 3
        self.cooldown_period = timedelta(minutes=2)
        self.user_cooldowns = {}

    def cleanup_old_entries(self):
        """Remove old entries from tracking"""
        if datetime.now() - self.last_cleanup > self.cleanup_interval:
            current_time = datetime.now()
            self.user_cooldowns = {
                user: time for user, time in self.user_cooldowns.items()
                if current_time - time < self.cooldown_period
            }
            self.last_cleanup = current_time

    async def check_rate_limit(self, user_id: int) -> tuple[bool, Optional[timedelta]]:
        """Check if user should be rate limited"""
        self.cleanup_old_entries()
        current_time = datetime.now()

        if user_id in self.user_cooldowns:
            wait_time = self.cooldown_period - (current_time - self.user_cooldowns[user_id])
            if wait_time > timedelta(0):
                return True, wait_time
            else:
                del self.user_cooldowns[user_id]

        if len(self.active_users) >= self.max_concurrent_users:
            self.user_cooldowns[user_id] = current_time
            return True, self.cooldown_period

        self.active_users[user_id] = current_time
        return False, None

    def release_user(self, user_id: int):
        """Release user from active processing"""
        if user_id in self.active_users:
            del self.active_users[user_id]

rate_limiter = VoiceRateLimiter()

class VoiceProcessor:
    """Voice processing helper class using AssemblyAI API"""

    @staticmethod
    async def cleanup_files(*file_paths: str):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up file {file_path}: {e}")

    @staticmethod
    async def upload_to_assemblyai(file_path: str) -> Optional[str]:
        """Upload audio file to AssemblyAI and get upload_url"""
        try:
            headers = {"authorization": ASSEMBLYAI_API_KEY}
            async with aiohttp.ClientSession() as session:
                # Read file in chunks for efficient upload
                with open(file_path, 'rb') as audio_file:
                    async with session.post(
                        url="https://api.assemblyai.com/v2/upload",
                        headers=headers,
                        data=audio_file
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"AssemblyAI upload error: {response.status}, {error_text}")
                        
                        upload_result = await response.json()
                        return upload_result.get("upload_url")
            
            return None
        except Exception as e:
            print(f"AssemblyAI upload error: {str(e)}")
            return None

    @staticmethod
    async def transcribe_voice(file_path: str, language: str) -> Optional[str]:
        """Transcribe voice to text using AssemblyAI API"""
        try:
            # Upload file to AssemblyAI
            upload_url = await VoiceProcessor.upload_to_assemblyai(file_path)
            if not upload_url:
                raise Exception("Failed to upload audio to AssemblyAI")
            
            # Prepare language setting
            language_code = "en"
            if language == "ru":
                language_code = "ru"
            elif language == "uz":
                language_code = "en"
            else:
                language_code = "tr"  
                
                
                
            # AssemblyAI might not support Uzbek, fallback to English
            
            # Create transcription request
            headers = {
                "authorization": ASSEMBLYAI_API_KEY,
                "content-type": "application/json"
            }
            
            payload = {
                "audio_url": upload_url,
                "language_code": language_code
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit transcription request
                async with session.post(
                    url="https://api.assemblyai.com/v2/transcript",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"AssemblyAI transcription error: {response.status}, {error_text}")
                    
                    transcript_response = await response.json()
                    transcript_id = transcript_response.get("id")
                    
                    if not transcript_id:
                        raise Exception("No transcript ID returned from AssemblyAI")
                    
                    # Poll for completion
                    polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                    
                    # Maximum polling attempts (30 seconds at 1s intervals)
                    max_polls = 30
                    polls = 0
                    
                    while polls < max_polls:
                        await asyncio.sleep(1)
                        async with session.get(polling_endpoint, headers=headers) as poll_response:
                            if poll_response.status != 200:
                                error_text = await poll_response.text()
                                raise Exception(f"AssemblyAI polling error: {poll_response.status}, {error_text}")
                            
                            polling_result = await poll_response.json()
                            status = polling_result.get("status")
                            
                            if status == "completed":
                                return polling_result.get("text")
                            elif status == "error":
                                raise Exception(f"AssemblyAI transcription failed: {polling_result.get('error')}")
                            
                            polls += 1
                    
                    raise Exception("Transcription timed out")
            
        except Exception as e:
            print(f"Voice transcription error: {str(e)}")
            return None
        
        finally:
            await VoiceProcessor.cleanup_files(file_path)


# Message Handlers
@router.message(Command("chat"))
@router.message(lambda message: message.text and any(message.text == buttons[lang]["btn_new_chat"] for lang in ["uz", "tr"]))
async def start_chat(message: types.Message):
    """Start AI chatbot with user."""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"

    # Reset session if exists
    if telegram_id in user_sessions:
        del user_sessions[telegram_id]

    user_sessions[telegram_id] = {
        "chat": model.start_chat(),
        "message_count": 0,
        "language": language
    }

    await message.answer(
        text=messages[language]["start"],
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(language)
    )

@router.message(Command("stop"))
@router.message(lambda message: message.text and any(message.text == buttons[lang]["btn_stop"] for lang in ["uz", "tr"]))
async def stop_chat(message: types.Message):
    """Stop the chat session."""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"

    if telegram_id in user_sessions:
        del user_sessions[telegram_id]
        await message.answer(
            text=messages[language]["stop"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )
    else:
        await message.answer(
            text=messages[language]["not_started"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )

@router.message(F.voice)
async def handle_voice(message: types.Message):
    """Handle voice messages"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    
    if telegram_id not in user_sessions:
        await message.answer(
            text=messages[language]["not_started"],
            parse_mode=ParseMode.HTML
        )
        return
    
    is_limited, wait_time = await rate_limiter.check_rate_limit(telegram_id)
    if is_limited:
        wait_minutes = round(wait_time.total_seconds() / 60, 1)
        await message.answer(
            text=messages[language]["time_waiter"].format(minutes=wait_minutes),
            parse_mode=ParseMode.HTML
        )
        return
    
    thinking_msg = await message.answer(
        text=messages[language]["voice_processing"],
        parse_mode=ParseMode.HTML
    )
    
    voice_path = None
    temp_audio_path = None
    
    try:
        if not message.voice or not message.voice.file_id:
            raise Exception("Invalid voice message")

        voice = await bot.get_file(message.voice.file_id)
        voice_path = f"temp_voice_{message.message_id}_{telegram_id}.ogg"
        await bot.download_file(voice.file_path, voice_path)
        
        if not os.path.exists(voice_path) or os.path.getsize(voice_path) < 100:
            raise Exception("Voice file download failed")
        
        voice_text = await VoiceProcessor.transcribe_voice(voice_path, language)
        print(f"Transcription result: {voice_text}")
        
        if not voice_text or not voice_text.strip():
            raise Exception("Could not recognize speech in audio")
        
        await safe_delete_message(thinking_msg)
        await message.answer(
            text=messages[language]["voice_recognized"].format(text=voice_text),
            parse_mode=ParseMode.HTML
        )
        
        # Process the message and get AI response
        session = user_sessions.get(telegram_id)
        
        # Response processing
        processing_msg = await message.answer(
            text=messages[language]["thinking"],
            parse_mode=ParseMode.HTML
        )
        
        try:
            response = session["chat"].send_message(voice_text)
            session["message_count"] += 1
            
            formatted_response = format_text(response.text)
            
            # Detect the language of the AI response
            try:
                detected_lang = detect(response.text)
                
                # Map detected language codes to gTTS compatible codes
                tts_lang_map = {
                    "en": "en",  # English
                    "ru": "ru",  # Russian
                    "uz": "tr",  # Uzbek (fallback to Turkish)
                    "tr": "tr",  # Turkish
                    "ar": "ar",  # Arabic
                    "es": "es",  # Spanish
                    "fr": "fr",  # French
                    "de": "de",  # German
                    "it": "it",  # Italian
                    "ja": "ja",  # Japanese
                    "ko": "ko",  # Korean
                    "zh-cn": "zh-CN",  # Chinese (Simplified)
                    "pt": "pt",  # Portuguese
                    "hi": "hi",  # Hindi
                    # Add more language mappings as needed
                }
                
                # Get appropriate TTS language code, default to English if not found
                tts_lang = tts_lang_map.get(detected_lang, "en")
                
                # Special case for Uzbek - if response is in Uzbek, use Turkish as fallback
                if detected_lang == "uz":
                    tts_lang = "tr"
                    
            except Exception as lang_error:
                print(f"Language detection error: {lang_error}")
                # Fallback to English if language detection fails
                tts_lang = "en"
            
            # Create a temporary file for the audio
            temp_fd, temp_audio_path = tempfile.mkstemp(suffix='.mp3')
            os.close(temp_fd)
                
            # Generate speech from text using detected language
            tts = gTTS(text=response.text, lang=tts_lang, slow=False)
            tts.save(temp_audio_path)
            
            # Send voice message and text response
            await safe_delete_message(processing_msg)
            
            # Send text response
            await message.answer(
                text=formatted_response,
                parse_mode=ParseMode.HTML,
                reply_markup=get_keyboard(language)
            )
            
            # Send audio response using FSInputFile
            voice_file = types.FSInputFile(temp_audio_path)
            
            # Provide information about the language used for TTS
            language_names = {
                "en": "English",
                "ru": "Russian",
                "tr": "Turkish",
                "ar": "Arabic",
                "es": "Spanish",
                "fr": "French",
                "de": "German",
                "it": "Italian",
                "ja": "Japanese",
                "ko": "Korean",
                "zh-CN": "Chinese",
                "pt": "Portuguese",
                "hi": "Hindi",
                # Add more language names as needed
            }
            
            voice_caption = f"🔊 {language_names.get(tts_lang, tts_lang)} audio response"
            
            # Show special message for Uzbek language since we use Turkish as fallback
            if detected_lang == "uz":
                hint = "⚠️ Ai o'zbek tilida ravon gaplasha olmaydi. Ovozli Qo'llab quvvatlash faqat 🇹🇷 Turk tili uchun. \n\n😞 Noqulaylik uchun uzur so'raymiz!"
                await bot.send_message(chat_id=telegram_id, text=hint)
            
            sent_voice_message = await message.answer_voice(
                voice=voice_file,
                caption=voice_caption
            )
            
                
                # After sending, schedule message deletion if needed
                # Uncomment the next line if you want to delete the voice message after some time
                # await asyncio.sleep(60)  # Wait 60 seconds
                # await bot.delete_message(chat_id=message.chat.id, message_id=sent_voice_message.message_id)
            
        except Exception as e:
            print(f"Error processing voice message: {e}")
            await safe_delete_message(processing_msg)
            await message.answer(
                text=messages[language]["error"],
                parse_mode=ParseMode.HTML,
                reply_markup=get_keyboard(language)
            )
        
    except Exception as e:
        error_msg = str(e)
        print(f"Voice processing error: {error_msg}")
        await safe_delete_message(thinking_msg)
        await message.answer(
            text=f"{messages[language]['voice_error']}\n{error_msg}",
            parse_mode=ParseMode.HTML
        )
    finally:
        rate_limiter.release_user(telegram_id)
        # Clean up temporary files
        if voice_path and os.path.exists(voice_path):
            await VoiceProcessor.cleanup_files(voice_path)
        if temp_audio_path and os.path.exists(temp_audio_path):
            await VoiceProcessor.cleanup_files(temp_audio_path)



@router.message(F.text)
async def handle_text(message: types.Message):
    """Handle text messages"""
    telegram_id = message.from_user.id
    
    # Skip processing for command buttons
    if any(message.text == buttons[lang][btn] for lang in ["uz", "tr"] 
           for btn in ["btn_new_chat", "btn_stop","btn_location", "btn_aboutus", "btn_change_lang"]):
        return
    
    await process_message(message)

async def process_message(message: types.Message, text: Optional[str] = None):
    """Process messages (both voice and text)"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    
    session = user_sessions.get(telegram_id)
    if not session:
        await message.answer(
            text=messages[language]["not_started"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )
        return
    
    # Check message limit
    if session["message_count"] >= 20:
        del user_sessions[telegram_id]
        await message.answer(
            text=messages[language]["limit_reached"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )
        return
    
    # Check rate limiting for text messages
    current_time = datetime.now()
    last_request_time = user_last_request_time.get(telegram_id)
    if last_request_time and (current_time - last_request_time).total_seconds() < 1:
        await message.answer(
            text=messages[language]["too_fast"],
            parse_mode=ParseMode.HTML
        )
        return
    
    user_last_request_time[telegram_id] = current_time
    
    thinking_msg = await message.answer(
        text=messages[language]["thinking"],
        parse_mode=ParseMode.HTML
    )
    
    try:
        input_text = text if text else message.text
        response = session["chat"].send_message(input_text)
        session["message_count"] += 1
        
        formatted_response = format_text(response.text)
        
        await safe_delete_message(thinking_msg)
        await message.answer(
            text=formatted_response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )
    except Exception as e:
        print(f"Error processing message: {e}")
        await safe_delete_message(thinking_msg)
        await message.answer(
            text=messages[language]["error"],
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(language)
        )

@router.message(F.video)
async def handle_video(message: types.Message):
    """Handle video messages"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    
    await message.answer(
        text=messages[language]["not_supported_media"],
        parse_mode=ParseMode.HTML
    )

@router.message(F.photo)
async def handle_image(message: types.Message):
    """Handle image/photo messages"""
    telegram_id = message.from_user.id
    user = await db.select_user(telegram_id=telegram_id)
    language = user["language"] if user else "uz"
    
    await message.answer(
        text=messages[language]["not_supported_media"],
        parse_mode=ParseMode.HTML
    )



