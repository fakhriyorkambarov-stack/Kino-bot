import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Message,
)

# --- SOZLAMALAR ---
BOT_TOKEN = "8536381410:AAGeAR1zVR-HFimOuhFJ4JP65Lu6keYZcQY"  # BotFather bergan tokeningizni yozing
CHANNEL_ID = -1004421497278
CHANNEL_LINK = "https://t.me/+GrLHZyzoSywwOTUy"
ADMIN_IDS = [5682264149]  # Sizning Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Ma'lumotlar bazasini yaratish
def init_db():
  conn = sqlite3.connect("movies.db")
  cursor = conn.cursor()
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS movies (
                    code TEXT PRIMARY KEY,
                    file_id TEXT,
                    file_type TEXT,
                    caption TEXT
                )"""
  )
  conn.commit()
  conn.close()


init_db()


# Admin kino qo'shishi uchun holatlar (FSM)
class AddMovie(StatesGroup):
  code = State()
  media = State()


# Obunani tekshirish funksiyasi
async def check_sub(user_id: int) -> bool:
  if user_id in ADMIN_IDS:
    return True  # Adminlar uchun majburiy obuna shart emas
  try:
    member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception:
    pass
  return False


# /start buyrug'i
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
  if not await check_sub(message.from_user.id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga obuna bo'lish", url=CHANNEL_LINK)],
            [
                InlineKeyboardButton(
                    text="Obunani tekshirish 🔄", callback_data="check_sub"
                )
            ],
        ]
    )
    await message.answer(
        "Iltimos, botdan foydalanish uchun avval kanalimizga obuna bo'ling:",
        reply_markup=keyboard,
    )
    return

  # Admin bo'lsangiz maxsus tugma chiqadi
  if message.from_user.id in ADMIN_IDS:
    admin_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎬 Kino qo'shish")]], resize_keyboard=True
    )
    await message.answer(
        "Xush kelibsiz, Admin! Kino kodini yuboring yoki quyidagi tugmani"
        " bosing:",
        reply_markup=admin_kb,
    )
  else:
    await message.answer(
        "Xush kelibsiz! Ko'rmoqchi bo'lgan kinongiz kodini yuboring (masalan:"
        " 123)."
    )


# Obuna bo'ldim tugmasi bosilganda
@dp.callback_query(F.data == "check_sub")
async def verify_sub(call: CallbackQuery):
  if await check_sub(call.from_user.id):
    await call.message.edit_text(
        "Rahmat! Obuna tasdiqlandi. Endi kino kodini yuborishingiz mumkin."
    )
  else:
    await call.answer(
        "Siz hali kanalga obuna bo'lmadingiz!", show_alert=True
    )


# --- ADMIN PANEL ---


@dp.message(F.text == "🎬 Kino qo'shish")
async def start_add_movie(message: Message, state: FSMContext):
  if message.from_user.id not in ADMIN_IDS:
    return
  await state.set_state(AddMovie.code)
  await message.answer(
      "Yangi kino uchun **kod** yuboring (masalan: `123`):", parse_mode="Markdown"
  )


@dp.message(AddMovie.code)
async def process_movie_code(message: Message, state: FSMContext):
  await state.update_data(code=message.text.strip())
  await state.set_state(AddMovie.media)
  await message.answer(
      "Endi shu kod uchun **videoni yoki faylni** yuboring:"
  )


@dp.message(AddMovie.media)
async def process_movie_media(message: Message, state: FSMContext):
  data = await state.get_data()
  code = data["code"]

  file_id = None
  file_type = None
  caption = message.caption or ""

  if message.video:
    file_id = message.video.file_id
    file_type = "video"
  elif message.document:
    file_id = message.document.file_id
    file_type = "document"
  elif message.photo:
    file_id = message.photo[-1].file_id
    file_type = "photo"
  else:
    await message.answer("Iltimos, video, rasm yoki hujjat yuboring!")
    return

  conn = sqlite3.connect("movies.db")
  cursor = conn.cursor()
  cursor.execute(
      "REPLACE INTO movies (code, file_id, file_type, caption) VALUES (?, ?, ?,"
      " ?)",
      (code, file_id, file_type, caption),
  )
  conn.commit()
  conn.close()

  await state.clear()
  await message.answer(
      f"✅ **{code}**-kodli kino muvaffaqiyatli saqlandi!", parse_mode="Markdown"
  )


# --- FOYDALANUVCHILAR UCHUN KINO QIDIRISH ---


@dp.message()
async def get_movie(message: Message):
  if not await check_sub(message.from_user.id):
    await message.answer("Avval kanalga obuna bo'ling! /start ni bosing.")
    return

  code = message.text.strip()

  conn = sqlite3.connect("movies.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT file_id, file_type, caption FROM movies WHERE code = ?", (code,)
  )
  movie = cursor.fetchone()
  conn.close()

  if not movie:
    await message.answer("❌ Bunday kodli kino topilmadi.")
    return

  file_id, file_type, caption = movie

  if file_type == "video":
    await message.answer_video(
        video=file_id, caption=caption or f"🎬 Kino kodi: {code}"
    )
  elif file_type == "document":
    await message.answer_document(
        document=file_id, caption=caption or f"🎬 Kino kodi: {code}"
    )
  elif file_type == "photo":
    await message.answer_photo(
        photo=file_id, caption=caption or f"🎬 Kino kodi: {code}"
    )


async def main():
  print("Bot ishga tushdi...")
  await dp.start_polling(bot)


if __name__ == '__main__':
    print("Bot ishga tushdi...")
    asyncio.run(main())
