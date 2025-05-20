# Создание Telegram бота для заметок

Пошаговое руководство по созданию бота для управления заметками в Telegram.

## Что умеет бот

- 📝 Создание заметок с заголовком и содержанием
- 📋 Просмотр списка всех заметок
- 🔍 Поиск заметок по ключевым словам
- ✏️ Редактирование существующих заметок
- 🗑 Удаление заметок
- 💾 Сохранение заметок в базу данных

## Шаг 1: Создание бота в Telegram

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Введите имя бота (например, "My Notes Bot")
4. Введите username бота (должен заканчиваться на 'bot', например "my_notes_bot")
5. Сохраните полученный токен - он понадобится для настройки бота

## Шаг 2: Подготовка окружения

1. Установите Python (если еще не установлен)
2. Создайте новую директорию для проекта
3. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```
4. Установите необходимую библиотеку:
```bash
pip install pyTelegramBotAPI
```

## Шаг 3: Создание базы данных

Создайте файл `bot.py` и добавьте код для работы с базой данных:

```python
import sqlite3

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
```

## Шаг 4: Основная структура бота

Добавьте в `bot.py` базовую структуру бота:

```python
import telebot
from telebot import types
import datetime

# Инициализация бота
TOKEN = 'ваш_токен_от_botfather'
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения состояний пользователей
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
```

## Шаг 5: Добавление функционала

### Создание заметки
```python
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
```

### Просмотр заметок
```python
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
```

### Поиск заметок
```python
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
```

## Шаг 6: Запуск бота

Добавьте в конец файла `bot.py`:

```python
if __name__ == '__main__':
    init_db()  # Инициализация базы данных
    print("Бот запущен...")
    bot.infinity_polling()
```

Запустите бота:
```bash
python bot.py
```

## Дополнительные возможности для улучшения

1. Добавление категорий для заметок
2. Добавление тегов
3. Экспорт заметок в различные форматы
4. Добавление напоминаний
5. Добавление возможности прикрепления файлов
6. Добавление возможности делиться заметками с другими пользователями

## Советы по безопасности

1. Не публикуйте токен бота в публичных репозиториях
2. Регулярно делайте резервные копии базы данных
3. Добавьте ограничение на размер заметок
4. Добавьте валидацию вводимых данных
5. Используйте переменные окружения для хранения токена 

## Полезные ресурсы

### Документация и API
- [Официальная документация pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- [Документация Telegram Bot API](https://core.telegram.org/bots/api)
- [Документация SQLite3 в Python](https://docs.python.org/3/library/sqlite3.html)

### Учебные материалы
- [Руководство по созданию Telegram ботов](https://core.telegram.org/bots/tutorial)
- [Примеры использования pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI/tree/master/examples)
- [Учебник по SQLite в Python](https://www.sqlitetutorial.net/sqlite-python/)

### Инструменты и сервисы
- [BotFather](https://t.me/botfather) - создание и управление ботами
- [Telegram Bot API](https://t.me/BotAPI) - новости и обновления API
- [Telegram Bot Support](https://t.me/BotSupport) - поддержка разработчиков ботов

### Сообщества
- [Telegram Bot Developers](https://t.me/botdevelopers) - сообщество разработчиков
- [Python Telegram Bot Developers](https://t.me/pythontelegrambotgroup) - группа разработчиков на Python
- [Stack Overflow](https://stackoverflow.com/questions/tagged/telegram-bot) - вопросы и ответы по разработке ботов

### Дополнительные библиотеки
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - альтернативная библиотека для создания ботов
- [aiogram](https://github.com/aiogram/aiogram) - асинхронная библиотека для создания ботов
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM для работы с базами данных (альтернатива sqlite3) 