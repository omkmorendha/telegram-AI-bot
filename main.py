from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from langchain_openai import OpenAI, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URLl")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = TeleBot(BOT_TOKEN)

with open("messages_eng.json", "r") as json_file:
    strings_eng = json.load(json_file)


model_settings = {
    "gpt-3.5-turbo" : 1,
    "gpt-4" : 5,
}


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
            credits INTEGER,
            model VARCHAR
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


def add_user(telegram_id, initial_credits=15, initial_language="eng", model="gpt-3.5-turbo"):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (telegram_id, credits, language, model)
            VALUES (%s, %s, %s, %s)
        """,
            (str(telegram_id), initial_credits, initial_language, model),
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


def get_user_model(telegram_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT model FROM users WHERE telegram_id = %s", (str(telegram_id),)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0]
    else:
        return "gpt-3.5-turbo"


def reduce_credits(chat_id, reduce_by):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET credits = GREATEST(0, credits - %s)
            WHERE telegram_id = %s
        """,
            (reduce_by, str(chat_id)),
        )
        conn.commit()
        print("Credits reduced successfully!")
    except Exception as e:
        print(f"Error reducing credits: {e}")
    finally:
        cursor.close()
        conn.close()


def check_credits(chat_id, required_credits):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT credits
            FROM users
            WHERE telegram_id = %s
            """,
            (str(chat_id),)
        )
        credits = cursor.fetchone()[0]
        if credits >= required_credits:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking credits: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


@bot.message_handler(commands=["credits"])
def show_credits(message):
    user_language = get_user_language(message.chat.id)
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT credits
            FROM users
            WHERE telegram_id = %s
            """,
            (str(message.chat.id),)
        )
        credits = cursor.fetchone()[0]
        credits_message = get_message(user_language, "credits_message").format(credits=credits)
        bot.send_message(message.chat.id, credits_message)
    
    except Exception as e:
        print(f"Error fetching credits: {e}")
        failure_message = get_message(user_language, "failure_message")
        bot.send_message(message.chat.id, failure_message)
    
    finally:
        cursor.close()
        conn.close()

def process_recharge(message):
    user_language = get_user_language(message.chat.id)
    
    try:
        amount = 15
        if amount <= 0:
            bot.send_message(message.chat.id, "Invalid amount. Please enter a positive number.")
            return

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET credits = credits + %s
            WHERE telegram_id = %s
            """,
            (amount, str(message.chat.id))
        )
        conn.commit()
        cursor.close()
        conn.close()

        success_message = get_message(user_language, "recharge_success_message").format(amount=amount)
        bot.send_message(message.chat.id, success_message)

    except Exception as e:
        print(f"Error processing recharge: {e}")
        failure_message = get_message(user_language, "failure_message")
        bot.send_message(message.chat.id, failure_message)


@bot.message_handler(commands=["recharge"])
def recharge_credits(message):
    user_language = get_user_language(message.chat.id)
    recharge_message = get_message(user_language, "recharge_message")
    bot.send_message(message.chat.id, recharge_message)
    bot.register_next_step_handler(message, process_recharge(message))


@bot.message_handler(commands=["start", "restart"])
def start(message):
    if not user_exists(message.chat.id):
        add_user(message.chat.id)

    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "start_message")
    menu_message = get_message(user_language, "menu_message")

    bot.send_message(message.chat.id, message_to_send, parse_mode= 'Markdown')
    bot.send_message(message.chat.id, menu_message, parse_mode= 'Markdown')


@bot.message_handler(commands=["menu"])
def menu(message):
    user_language = get_user_language(message.chat.id)
    message_to_send = get_message(user_language, "menu_message")
    bot.send_message(message.chat.id, message_to_send, parse_mode= 'Markdown')


@bot.message_handler(commands=["recharge"])
def recharge_credits(message):
    user_language = get_user_language(message.chat.id)
    recharge_message = get_message(user_language, "recharge_message")
    bot.send_message(message.chat.id, recharge_message)


@bot.message_handler(commands=["chat"])
def start_chat(message):
    user_language = get_user_language(message.chat.id)
    model = get_user_model(message.chat.id)
    token = model_settings[model]
    
    if check_credits(message.chat.id, 1):
        chat = ChatOpenAI(temperature=0.5, model=model)
        chat_message = get_message(user_language, "chat_message")
        bot.send_message(message.chat.id, chat_message)
        bot.register_next_step_handler(message, lambda msg: continue_chat(msg, chat, user_language, token))
    
    else:
        insufficient_credits_message = get_message(user_language, "insufficient_credits_message")
        bot.send_message(message.chat.id, insufficient_credits_message)


def continue_chat(message, chat, user_language, token):
    try: 
        if message.text.lower().startswith("/"):
            bot.send_message(message.chat.id, "Conversation stopped.")
            return

        if check_credits(message.chat.id, token):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Go Back to Menu', callback_data='show-menu'))
            
            messages = [HumanMessage(content=message.text)]
            response = chat.invoke(messages)
            reduce_credits(message.chat.id, token)
                
            bot.send_message(message.chat.id, response.content, reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(message, lambda msg: continue_chat(msg, chat, user_language, token))
        
        else:
            insufficient_credits_message = get_message(user_language, "insufficient_credits_message")
            bot.send_message(message.chat.id, insufficient_credits_message)
        
    except:
        failure_message = get_message(user_language, "failure_message")
        bot.send_message(message.chat.id, failure_message)


@bot.callback_query_handler(func=lambda call: call.data == 'show-menu')
def stop_callback(call):
    if call.data == 'show-menu':
        user_language = get_user_language(call.message.chat.id)
        menu_message = get_message(user_language, "menu_message")
        conversation_end = get_message(user_language, "conversation_end")
        
        bot.send_message(call.message.chat.id, conversation_end)
        bot.send_message(call.message.chat.id, menu_message, parse_mode= 'Markdown')


def update_user_model(chat_id, model):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET model = %s
            WHERE telegram_id = %s
        """,
            (model, str(chat_id)),
        )
        conn.commit()
        print("Model changed successfully!")
    except Exception as e:
        print(f"Error changing model: {e}")
    finally:
        cursor.close()
        conn.close()
    

@bot.message_handler(commands=["settings"])
def settings_message(message):
    user_language = get_user_language(message.chat.id)
    model = get_user_model(message.chat.id)
    
    settings_message = get_message(user_language, "settings_message")

    keyboard = InlineKeyboardMarkup()
    button_gpt_35_turbo = InlineKeyboardButton("GPT-3.5-Turbo", callback_data="gpt_3.5_turbo")
    button_gpt_4 = InlineKeyboardButton("GPT-4", callback_data="gpt_4")
    keyboard.row(button_gpt_35_turbo, button_gpt_4)

    bot.send_message(message.chat.id, settings_message.format(model=model), reply_markup=keyboard, parse_mode='Markdown')
    
    message_to_send = get_message(user_language, "menu_message")
    bot.send_message(message.chat.id, message_to_send, parse_mode= 'Markdown')


@bot.callback_query_handler(func=lambda call: call.data in ["gpt_3.5_turbo", "gpt_4"])
def settings_callback(call):
    update_user_model(call.message.chat.id, call.data.replace('_', '-'))
    
    user_language = get_user_language(call.message.chat.id)
    model = get_user_model(call.message.chat.id)
    model_update_message = get_message(user_language, "model_update_message")
    
    bot.send_message(call.message.chat.id, model_update_message.format(model=model), parse_mode='Markdown')
    bot.register_next_step_handler(call.message, menu)


if __name__ == "__main__":
    # drop_tables()
    # create_users_table()
    bot.infinity_polling()
