from telebot import TeleBot
from langchain_openai import OpenAI, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = TeleBot(BOT_TOKEN)

with open("messages_eng.json", "r") as json_file:
    strings_eng = json.load(json_file)


def get_message(language, key):
    if language == "eng":
        return strings_eng.get(key, "")
    else:
        return ""


def create_users_table():
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id VARCHAR,
            language VARCHAR,
            credits INTEGER
        )
    """
    )
    conn.commit()
    cursor.close()
    conn.close()


def drop_tables():
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    cursor.close()
    conn.close()
    print("Tables dropped successfully.")


def add_user(telegram_id, initial_credits=15, initial_language="eng"):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (telegram_id, credits, language)
            VALUES (%s, %s, %s)
        """,
            (str(telegram_id), initial_credits, initial_language),
        )
        conn.commit()
        print("User added successfully!")
    except Exception as e:
        print(f"Error adding user: {e}")
    finally:
        cursor.close()
        conn.close()


def user_exists(telegram_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM users WHERE telegram_id = %s)", (str(telegram_id),)
    )
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return result


def get_user_language(telegram_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT language FROM users WHERE telegram_id = %s", (str(telegram_id),)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0]
    else:
        return "eng"


@bot.message_handler(commands=["start", "restart"])
def start(message):
    if not user_exists(message.chat.id):
        add_user(message.chat.id)

    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "start_message")

    bot.send_message(message.chat.id, message_to_send)


@bot.message_handler(commands=["menu"])
def menu(message):
    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "menu_message")
    bot.send_message(message.chat.id, message_to_send)


@bot.message_handler(commands=["chat"])
def start_chat(message):
    user_language = get_user_language(message.chat.id)
    chat_message = get_message(user_language, "chat_message")
    bot.send_message(message.chat.id, chat_message)
    bot.register_next_step_handler(message, continue_chat)


def continue_chat(message):
    if message.text.lower() == "/stop":
        bot.send_message(message.chat.id, "Conversation stopped.")
        return
    chat = ChatOpenAI(temperature=0.5) 
    messages = [HumanMessage(content=message.text)]
    response = chat.invoke(messages)
    bot.send_message(message.chat.id, response.content)
    bot.register_next_step_handler(message, continue_chat)


if __name__ == "__main__":
    # drop_tables()
    # create_users_table()
    bot.infinity_polling()
