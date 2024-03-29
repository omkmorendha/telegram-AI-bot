from telebot import TeleBot
from sqlalchemy import create_engine
import json
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("URL")
engine = create_engine(DATABASE_URL)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = TeleBot(BOT_TOKEN)

with open("messages_eng.json", "r") as json_file:
    strings_eng = json.load(json_file)


def get_message(language, key):
    if language == "eng":
        return strings_eng.get(key, "")
    else: 
        return ""


def get_user_language(id):
    pass


@bot.message_handler(commands=['start', 'restart'])
def start(message):
    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "start_message")
    bot.send_message(message.chat.id, message_to_send)


@bot.message_handler(commands=['menu'])
def menu(message):
    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "menu_message")
    bot.send_message(message.chat.id, "message_to_send")


if __name__ == '__main__':
    bot.infinity_polling()