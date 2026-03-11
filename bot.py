import os
import logging
import asyncio
import tempfile
from telegram import Update, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp
from video_processor import VideoProcessor
from quiz_generator import QuizGenerator

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")

video_processor = VideoProcessor(OPENAI_API_KEY)
quiz_generator = QuizGenerator(OPENAI_API_KEY)

# Store ongoing quizzes per chat
active_quizzes = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = (
        "🎬 *English With Movies Bot*'ga xush kelibsiz!\n\n"
        "Bu bot filmlar orqali ingliz tilini o'rganishga yordam beradi.\n\n"
        "📌 *Qanday ishlaydi:*\n"
        "1️⃣ Menga video yuboring\n"
        "2️⃣ Bot videodagi nutqni matnga aylantiradi\n"
        "3️⃣ Muhim so'zlar (vocabulary) ajratiladi\n"
        "4️⃣ 10 ta quiz savol tuziladi\n"
        "5️⃣ Bilimingizni sinab ko'ring! 🎯\n\n"
        "Boshlash uchun video yuboring! 🎥"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "ℹ️ *Yordam*\n\n"
        "🎥 Video yuborish: Telegram orqali video fayl yuboring\n"
        "📝 /start - Botni qayta ishga tushirish\n"
        "❓ /help - Yordam\n\n"
        "⚠️ *Eslatma:* Video 50MB dan kichik bo'lishi kerak."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video files"""
    chat_id = update.message.chat_id
    
    # Notify user that processing has started
    processing_msg = await update.message.reply_text(
        "⏳ Video qabul qilindi! Qayta ishlanmoqda...\n"
        "Bu bir necha daqiqa vaqt olishi mumkin."
    )
    
    try:
        # Get video file
        video = update.message.video or update.message.document
        
        if not video:
            await processing_msg.edit_text("❌ Video topilmadi. Iltimos, video yuboring.")
            return
        
        # Check file size (50MB limit)
        if video.file_size > 50 * 1024 * 1024:
            await processing_msg.edit_text(
                "❌ Video hajmi juda katta (50MB dan oshmasligi kerak).\n"
                "Iltimos, kichikroq video yuboring."
            )
            return
        
        await processing_msg.edit_text("📥 Video yuklanmoqda...")
        
        # Download video
        video_file = await context.bot.get_file(video.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        await video_file.download_to_drive(tmp_path)
        
        await processing_msg.edit_text("🎙️ Audio ajratilmoqda va matnga aylantirilmoqda...")
        
        # Transcribe video
        transcript = await video_processor.transcribe_video(tmp_path)
        
        if not transcript or len(transcript.strip()) < 20:
            await processing_msg.edit_text(
                "❌ Videoda yetarli nutq topilmadi.\n"
                "Iltimos, ingliz tilida gap bo'lgan video yuboring."
            )
            os.unlink(tmp_path)
            return
        
        await processing_msg.edit_text("📚 Vocabulary ajratilmoqda...")
        
        # Extract vocabulary
        vocabulary = await quiz_generator.extract_vocabulary(transcript)
        
        await processing_msg.edit_text("🧠 Quiz savollar tuzilmoqda...")
        
        # Generate quiz questions
        questions = await quiz_generator.generate_quiz(transcript, vocabulary)
        
        # Send transcript (first 500 chars)
        transcript_preview = transcript[:800] + "..." if len(transcript) > 800 else transcript
        
        await update.message.reply_text(
            f"✅ *Transkriptsiya:*\n\n_{transcript_preview}_",
            parse_mode="Markdown"
        )
        
        # Send vocabulary
        vocab_text = "📖 *Muhim so'zlar (Vocabulary):*\n\n"
        for item in vocabulary[:10]:
            vocab_text += f"🔹 *{item['word']}* - {item['definition']}\n"
            if item.get('example'):
                vocab_text += f"   _{item['example']}_\n"
            vocab_text += "\n"
        
        await update.message.reply_text(vocab_text, parse_mode="Markdown")
        
        # Delete processing message
        await processing_msg.delete()
        
        # Start quiz
        await update.message.reply_text(
            "🎯 *Quiz boshlandi!*\n\n"
            "10 ta savol bo'ladi. Har bir savolda 4 ta javob varianti bor.\n"
            "Bilimingizni sinab ko'ring! 💪",
            parse_mode="Markdown"
        )
        
        # Store quiz data
        active_quizzes[chat_id] = {
            "questions": questions,
            "current": 0,
            "score": 0,
            "total": len(questions)
        }
        
        # Send first question
        await send_quiz_question(update, context, chat_id)
        
        # Cleanup
        os.unlink(tmp_path)
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await processing_msg.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, qayta urinib ko'ring."
        )


async def send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Send a quiz question with inline keyboard"""
    if chat_id not in active_quizzes:
        return
    
    quiz_data = active_quizzes[chat_id]
    current_idx = quiz_data["current"]
    
    if current_idx >= len(quiz_data["questions"]):
        await finish_quiz(update, context, chat_id)
        return
    
    question = quiz_data["questions"][current_idx]
    question_num = current_idx + 1
    total = quiz_data["total"]
    
    # Create inline keyboard with options
    keyboard = []
    options = question["options"]
    
    for i, option in enumerate(options):
        letter = ["A", "B", "C", "D"][i]
        keyboard.append([
            InlineKeyboardButton(
                f"{letter}) {option}",
                callback_data=f"quiz_{chat_id}_{current_idx}_{i}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    question_text = (
        f"❓ *Savol {question_num}/{total}*\n\n"
        f"{question['question']}"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz answer callback"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: quiz_{chat_id}_{question_idx}_{answer_idx}
    data = query.data.split("_")
    if len(data) != 4 or data[0] != "quiz":
        return
    
    chat_id = int(data[1])
    question_idx = int(data[2])
    answer_idx = int(data[3])
    
    if chat_id not in active_quizzes:
        await query.edit_message_text("❌ Quiz topilmadi. Video yuboring.")
        return
    
    quiz_data = active_quizzes[chat_id]
    
    # Check if this is the current question
    if question_idx != quiz_data["current"]:
        return
    
    question = quiz_data["questions"][question_idx]
    correct_idx = question["correct_answer"]
    options = question["options"]
    
    letters = ["A", "B", "C", "D"]
    
    if answer_idx == correct_idx:
        quiz_data["score"] += 1
        result_text = f"✅ *To'g'ri!*\n\n"
    else:
        result_text = f"❌ *Noto'g'ri!*\n\n"
        result_text += f"To'g'ri javob: *{letters[correct_idx]}) {options[correct_idx]}*\n\n"
    
    # Add explanation if available
    if question.get("explanation"):
        result_text += f"💡 {question['explanation']}"
    
    await query.edit_message_text(result_text, parse_mode="Markdown")
    
    # Move to next question
    quiz_data["current"] += 1
    
    # Small delay before next question
    await asyncio.sleep(1)
    
    if quiz_data["current"] < quiz_data["total"]:
        await send_quiz_question(update, context, chat_id)
    else:
        await finish_quiz(update, context, chat_id)


async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Show quiz results"""
    if chat_id not in active_quizzes:
        return
    
    quiz_data = active_quizzes[chat_id]
    score = quiz_data["score"]
    total = quiz_data["total"]
    percentage = (score / total) * 100 if total > 0 else 0
    
    # Determine emoji based on score
    if percentage >= 90:
        emoji = "🏆"
        comment = "Ajoyib! Siz zo'r ingliz tili bilimiga egasiz!"
    elif percentage >= 70:
        emoji = "🌟"
        comment = "Yaxshi! Davom eting, siz yaxshi o'rganmoqdasiz!"
    elif percentage >= 50:
        emoji = "👍"
        comment = "Yomon emas! Ko'proq mashq qiling."
    else:
        emoji = "💪"
        comment = "Davom eting! Mashq qilish orqali yaxshilanasiz."
    
    result_text = (
        f"{emoji} *Quiz tugadi!*\n\n"
        f"📊 *Natija:* {score}/{total} ({percentage:.0f}%)\n\n"
        f"{'🟩' * score}{'🟥' * (total - score)}\n\n"
        f"_{comment}_\n\n"
        "Yangi video yuboring va yana o'rganing! 🎬"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=result_text,
        parse_mode="Markdown"
    )
    
    # Clear quiz data
    del active_quizzes[chat_id]


def main():
    """Main function to run the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video)
    )
    application.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern="^quiz_"))
    
    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
