import asyncio
import os
import subprocess

import speech_recognition as sr
from aiogram import F, Router
from aiogram.types import Message

router = Router()


def run_ffmpeg_conversion(input_path: str, output_path: str) -> bool:
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_path,
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                "16000",
                output_path,
                "-y",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def transcribe_audio(file_path: str) -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="ru-RU")
    except sr.UnknownValueError:
        return "Нᴇ ʏдᴀлось ᴘᴀзобᴘᴀть ᴘᴇчь 🔇"
    except sr.RequestError as e:
        return f"Ошибка сервиса распознавания: {e}"
    except Exception as e:
        return f"Ошибка при обработке аудио: {e}"


async def process_voice_or_video(message: Message, file_id: str, is_video: bool = False):
    bot = message.bot
    action = "upload_document" if is_video else "record_voice"
    await bot.send_chat_action(chat_id=message.chat.id, action=action)

    temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    ext = ".mp4" if is_video else ".ogg"
    input_file = os.path.join(temp_dir, f"{file_id}{ext}")
    output_file = os.path.join(temp_dir, f"{file_id}.wav")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, input_file)

        success = await asyncio.to_thread(run_ffmpeg_conversion, input_file, output_file)
        if not success:
            await message.reply("⚠️ Ошибкᴀ: нᴇ ʏдᴀлось обᴘᴀботᴀть ᴀʏдио-фоᴘмᴀт!")
            return

        transcription = await asyncio.to_thread(transcribe_audio, output_file)
        if transcription.strip():
            await message.reply(f"📝 *Расшифровка:* \n\n_«{transcription}»_", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при транскрибации голосового сообщения: {e}")
    finally:
        for path in [input_file, output_file]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


@router.message(F.voice)
async def handle_voice_message(message: Message):
    await process_voice_or_video(message, message.voice.file_id, is_video=False)


@router.message(F.video_note)
async def handle_video_note_message(message: Message):
    await process_voice_or_video(message, message.video_note.file_id, is_video=True)
