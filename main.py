from telebot import TeleBot
import json
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_KEY")

bot = TeleBot(BOT_TOKEN)

with open("messages_eng.json", "r") as json_file:
    strings_eng = json.load(json_file)


@bot.message_handler(commands=['start', 'restart'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to the AI BOT")


@bot.message_handler(commands=['menu'])
def menu(message):
    bot.send_message(message.chat.id, "Welcome to the AI BOT")


if __name__ == '__main__':
    bot.infinity_polling()