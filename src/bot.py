import telebot
from telebot import types
import sqlite3
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен бота. Установите переменную окружения BOT_TOKEN")

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  title TEXT,
                  content TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()

# Словарь для хранения временных данных пользователей
user_states = {}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📝 Добавить заметку"))
    markup.add(types.KeyboardButton("📋 Список заметок"))
    markup.add(types.KeyboardButton("🔍 Поиск заметок"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я бот для управления заметками. Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📝 Добавить заметку")
def add_note_start(message):
    user_states[message.chat.id] = {'state': 'waiting_title'}
    bot.send_message(message.chat.id, "Введите заголовок заметки:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_title')
def add_note_title(message):
    user_states[message.chat.id] = {'state': 'waiting_content', 'title': message.text}
    bot.send_message(message.chat.id, "Теперь введите содержание заметки:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_content')
def add_note_content(message):
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('''INSERT INTO notes (user_id, title, content, created_at)
                 VALUES (?, ?, ?, ?)''',
              (message.chat.id,
               user_states[message.chat.id]['title'],
               message.text,
               datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    del user_states[message.chat.id]
    bot.send_message(message.chat.id, "Заметка успешно сохранена!", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📋 Список заметок")
def list_notes(message):
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT id, title, created_at FROM notes WHERE user_id = ?', (message.chat.id,))
    notes = c.fetchall()
    conn.close()
    
    if not notes:
        bot.send_message(message.chat.id, "У вас пока нет заметок.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for note in notes:
        markup.add(types.InlineKeyboardButton(
            text=f"{note[1]} ({note[2]})",
            callback_data=f"view_{note[0]}"
        ))
    
    bot.send_message(message.chat.id, "Ваши заметки:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔍 Поиск заметок")
def search_notes_start(message):
    user_states[message.chat.id] = {'state': 'waiting_search'}
    bot.send_message(message.chat.id, "Введите ключевое слово для поиска:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_search')
def search_notes(message):
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    search_term = f"%{message.text}%"
    c.execute('''SELECT id, title, created_at FROM notes 
                 WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)''',
              (message.chat.id, search_term, search_term))
    notes = c.fetchall()
    conn.close()
    
    if not notes:
        bot.send_message(message.chat.id, "Заметки не найдены.", reply_markup=get_main_keyboard())
        return
    
    markup = types.InlineKeyboardMarkup()
    for note in notes:
        markup.add(types.InlineKeyboardButton(
            text=f"{note[1]} ({note[2]})",
            callback_data=f"view_{note[0]}"
        ))
    
    bot.send_message(message.chat.id, "Найденные заметки:", reply_markup=markup)
    del user_states[message.chat.id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_note(call):
    note_id = int(call.data.split('_')[1])
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT title, content, created_at FROM notes WHERE id = ? AND user_id = ?',
              (note_id, call.message.chat.id))
    note = c.fetchone()
    conn.close()
    
    if note:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{note_id}"))
        markup.add(types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{note_id}"))
        
        bot.edit_message_text(
            f"📌 {note[0]}\n\n{note[1]}\n\nСоздано: {note[2]}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
def edit_note_start(call):
    note_id = int(call.data.split('_')[1])
    user_states[call.message.chat.id] = {'state': 'waiting_edit_title', 'note_id': note_id}
    bot.send_message(call.message.chat.id, "Введите новый заголовок заметки:")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_note(call):
    note_id = int(call.data.split('_')[1])
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('DELETE FROM notes WHERE id = ? AND user_id = ?',
              (note_id, call.message.chat.id))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, "Заметка удалена!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_edit_title')
def edit_note_title(message):
    user_states[message.chat.id]['title'] = message.text
    user_states[message.chat.id]['state'] = 'waiting_edit_content'
    bot.send_message(message.chat.id, "Введите новое содержание заметки:")

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_edit_content')
def edit_note_content(message):
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('''UPDATE notes 
                 SET title = ?, content = ? 
                 WHERE id = ? AND user_id = ?''',
              (user_states[message.chat.id]['title'],
               message.text,
               user_states[message.chat.id]['note_id'],
               message.chat.id))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "Заметка обновлена!", reply_markup=get_main_keyboard())
    del user_states[message.chat.id]

if __name__ == '__main__':
    init_db()  # Инициализация базы данных при запуске
    print("Бот запущен...")
    bot.infinity_polling() 