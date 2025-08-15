# main.py
import telebot
from telebot import types
import schedule
import threading
import time
from datetime import datetime, timedelta
from config import BOT_TOKEN
from database import Database
from card_system import CardSystem
from bonus_system import BonusSystem


# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()
card_system = CardSystem(db)
bonus_system = BonusSystem(db)

WEBHOOK_HOST = 'PehenyshkaCookie.pythonanywhere.com' 
WEBHOOK_PATH = '/webhook'

app = Flask(__name__)

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK'
    else:
        return 'Bad Request', 403

# Команды бота
@bot.message_handler(commands=['start'])
def start_command(message):
	user_id = message.from_user.id
	username = message.from_user.username
	time_sended = message.date

	# Регистрируем пользователя
	db.register_user(user_id, username, time_sended)

	welcome_text = f"""
**Добро пожаловать в мир One Piece Cards!**
Привет, {message.from_user.first_name}!
Тебя ждет увлекательное приключение по сбору карточек персонажей One Piece!
🎴 **Что ты можешь делать:**
• /card - Получить карточку (раз в 2 часа)
• /collection - Посмотреть свою коллекцию
• /top - Топ игроков
• /daily - Ежедневные бонусы
• /profile - Твоя статистика
• /help - Помощь
⭐ **Редкость карточек:**
{chr(11088) * 5} Мифическая (0.5%)
{chr(11088) * 4} Легендарная (2.5%)
{chr(11088) * 3} Эпическая (9%)
{chr(11088) * 2} Редкая (28%)
{chr(11088) * 1} Обычная (60%)
Начни с команды /card для получения первой карточки! 🎯
"""
	bot.reply_to(message, welcome_text, parse_mode='Markdown')
@bot.message_handler(commands=['card'])
def drop_card_command(message):
    user_id = message.from_user.id
    time_to_drop = message.date

    # Проверяем, есть ли у пользователя хоть одна карта
    user_cards = db.get_user_cards(user_id)
    if not user_cards:
        # Первый дроп всегда разрешён
        card = card_system.drop_card_for_user(user_id, time_to_drop)
        if card:
            card_info = card_system.format_card_info(card)
            image_path = card[4]
            if image_path:
                try:
                    with open(f"cards/{image_path}", 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=card_info, parse_mode='Markdown')
                except FileNotFoundError:
                    bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
            else:
                bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Ошибка при получении карточки. Попробуйте позже.")
        return

    # Проверяем, может ли пользователь получить карточку
    if not db.can_drop_card(user_id, time_to_drop):
        # Попытка использовать дополнительную попытку (бонус)
        if bonus_system.use_extra_drop(user_id):
            card = card_system.drop_card_for_user(user_id, time_to_drop)
            if card:
                card_info = card_system.format_card_info(card)
                image_path = card[4] # image_path
                if image_path:
                    try:
                        with open(f"cards/{image_path}", 'rb') as photo:
                            bot.send_photo(message.chat.id, photo, caption=card_info, parse_mode='Markdown')
                    except FileNotFoundError:
                        bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
            else:
                bot.reply_to(message, "❌ Ошибка при получении карточки. Попробуйте позже.")
            return  # Важно! Не продолжаем дальше
        # Если нет бонуса — стандартное сообщение ожидания
        user = db.get_user(user_id)
        if user and user[3]: # last_card_drop
            if isinstance(user[3], int):
                last_drop_time = datetime.fromtimestamp(user[3])
            else:
                last_drop_time = datetime.strptime(str(user[3]), '%Y-%m-%d %H:%M:%S')
            last_drop = last_drop_time
            next_drop = last_drop + timedelta(hours=2)
            wait_time =  next_drop - datetime.fromtimestamp(time_to_drop)

            hours = int(wait_time.total_seconds() // 3600)
            minutes = int((wait_time.total_seconds() % 3600) // 60)

            bot.reply_to(message, f"⏰ Вы сможете получить следующую карточку через {hours}ч {minutes}мин")
        return

    # Выпадение карточки (обычная попытка)
    card = card_system.drop_card_for_user(user_id, time_to_drop)

    if card:
        card_info = card_system.format_card_info(card)
        image_path = card[4] # image_path
        if image_path:
            try:
                with open(f"cards/{image_path}", 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption=card_info, parse_mode='Markdown')
            except FileNotFoundError:
                bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🎉 **Новая карточка!**\n{card_info}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Ошибка при получении карточки. Попробуйте позже.")
@bot.message_handler(commands=['collection'])
def collection_command(message):
	user_id = message.from_user.id

	# Инлайн-клавиатура для навигации
	markup = types.InlineKeyboardMarkup()
	markup.row(
		types.InlineKeyboardButton("📊 Общая информация", callback_data="collection_summary"),
		types.InlineKeyboardButton("🎴 Все карточки", callback_data="collection_all")
	)
	markup.row(
		types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="collection_5"),
		types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="collection_4"),
		types.InlineKeyboardButton("⭐⭐⭐", callback_data="collection_3")
	)
	markup.row(
		types.InlineKeyboardButton("⭐⭐", callback_data="collection_2"),
		types.InlineKeyboardButton("⭐", callback_data="collection_1")
	)

	bot.reply_to(message, "📚 **Ваша коллекция карточек:**\nВыберите, что посмотреть:",
				 reply_markup=markup, parse_mode='Markdown')
@bot.callback_query_handler(func=lambda call: call.data.startswith('collection_'))
def collection_callback(call):
    user_id = call.from_user.id
    action = call.data.split('_')[1]

    def get_collection_menu_markup():
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📊 Общая информация", callback_data="collection_summary"),
            types.InlineKeyboardButton("🎴 Все карточки", callback_data="collection_all")
        )
        markup.row(
            types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="collection_5"),
            types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="collection_4"),
            types.InlineKeyboardButton("⭐⭐⭐", callback_data="collection_3")
        )
        markup.row(
            types.InlineKeyboardButton("⭐⭐", callback_data="collection_2"),
            types.InlineKeyboardButton("⭐", callback_data="collection_1")
        )
        return markup

    if action == "summary":
        summary = card_system.get_user_collection_summary(user_id)
        # Добавляем кнопку "Вернуться"
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🔙 Вернуться", callback_data="collection_menu"))
        bot.edit_message_text(summary, call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown', reply_markup=markup)

    elif action == "all":
        cards = db.get_user_cards(user_id)
        if not cards:
            bot.answer_callback_query(call.id, "У вас еще нет карточек!", show_alert=True)
            return

        card_counter = {}
        for card in cards:
            name = card[1]
            if name in card_counter:
                card_counter[name]["count"] += 1
            else:
                card_counter[name] = {"stars": card[2], "count": 1}

        cards_text = "🎴 **Все ваши карточки:**\n\n"
        for i, (name, info) in enumerate(list(card_counter.items())[:20]):
            stars = "⭐" * info["stars"]
            count = info["count"]
            cards_text += f"{i+1}. {name} {stars} x{count}\n"

        if len(card_counter) > 20:
            cards_text += f"\n... и еще {len(card_counter) - 20} уникальных карточек"

        # Добавляем кнопку "Вернуться"
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🔙 Вернуться", callback_data="collection_menu"))
        bot.edit_message_text(cards_text, call.message.chat.id, call.message.message_id,
                            parse_mode='Markdown', reply_markup=markup)

    elif action.isdigit():
        rarity = int(action)
        cards = [card for card in db.get_user_cards(user_id) if card[2] == rarity]

        if not cards:
            bot.answer_callback_query(call.id, f"У вас нет карточек {rarity}★ уровня!", show_alert=True)
            return

        card_counter = {}
        for card in cards:
            name = card[1]
            if name in card_counter:
                card_counter[name]["count"] += 1
            else:
                card_counter[name] = {
                    "total_power": card[5] + card[6] + card[7] + card[8],
                    "count": 1
                }

        stars = "⭐" * rarity
        cards_text = f"🎴 **Карточки {stars} уровня:**\n\n"

        for i, (name, info) in enumerate(list(card_counter.items())[:20]):
            cards_text += f"{i+1}. {name} (💪{info['total_power']}) x{info['count']}\n"

        if len(card_counter) > 20:
            cards_text += f"\n... и еще {len(card_counter) - 20} уникальных карточек"

        # Добавляем кнопку "Вернуться"
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("🔙 Вернуться", callback_data="collection_menu"))
        bot.edit_message_text(cards_text, call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown', reply_markup=markup)

    elif action == "menu":
        # Показываем главное меню коллекции
        bot.edit_message_text(
            "📚 **Ваша коллекция карточек:**\nВыберите, что посмотреть:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=get_collection_menu_markup()
        )
@bot.message_handler(commands=['top'])
def top_command(message):
	leaderboard = db.get_leaderboard(10)

	if not leaderboard:
		bot.reply_to(message, "❌ Пока нет игроков в рейтинге!")
		return

	top_text = "🏆 **Топ-10 игроков:**\n\n"

	medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

	for i, player in enumerate(leaderboard):
		username = player[1] or f"Игрок {player[0]}"
		username = escape_markdown(username)
		total_cards = player[2] or 0
		total_power = player[3] or 0
		rare_cards = player[4] or 0

		top_text += f"{medals[i]} **{username}**\n"
		top_text += f" 🎴 Карточек: {total_cards} | 💪 Сила: {total_power} | ⭐ Редких: {rare_cards}\n\n"

	bot.reply_to(message, top_text, parse_mode='Markdown')
@bot.message_handler(commands=['daily'])
def bonus_command(message):
	user_id = message.from_user.id

	if bonus_system.can_claim_daily_bonus(user_id):
		# Показываем варианты бонусов
		bonuses = bonus_system.get_daily_bonus_options()

		markup = types.InlineKeyboardMarkup()
		for bonus in bonuses:
			markup.row(types.InlineKeyboardButton(
				f"{bonus['emoji']} {bonus['name']}",
				callback_data=f"bonus_{bonus['type']}"
			))

		bot.reply_to(message,
					 "🎁 **Ежедневный бонус доступен!**\nВыберите один из вариантов:",
					 reply_markup=markup, parse_mode='Markdown')
	else:
		# Показываем статус бонусов
		status = bonus_system.get_bonus_status(user_id)
		bot.reply_to(message, status, parse_mode='Markdown')
@bot.callback_query_handler(func=lambda call: call.data.startswith('bonus_'))
def bonus_callback(call):
    user_id = call.from_user.id
    bonus_type = call.data[len('bonus_'):]  # Исправлено!

    if bonus_system.claim_daily_bonus(user_id, bonus_type):
        bonuses = bonus_system.get_daily_bonus_options()
        bonus_info = next((b for b in bonuses if b['type'] == bonus_type), None)

        if bonus_info:
            # Экранируем спецсимволы для Markdown
            name = escape_markdown(bonus_info['name'])
            description = escape_markdown(bonus_info['description'])
            emoji = escape_markdown(bonus_info['emoji'])
            success_text = f"✅ *Бонус активирован!*\n\n{emoji} {name}\n{description}"
            bot.edit_message_text(success_text, call.message.chat.id, call.message.message_id,
                                 parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка активации бонуса", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Вы уже получили ежедневный бонус!", show_alert=True)
@bot.message_handler(commands=['profile'])
def stats_command(message):
	user_id = message.from_user.id
	stats = db.get_user_stats(user_id)
	user = db.get_user(user_id)

	if not stats or not user:
		bot.reply_to(message, "❌ Статистика недоступна")
		return

	total_cards = stats[0] or 0
	total_power = stats[1] or 0
	legendary_cards = stats[2] or 0
	epic_cards = stats[3] or 0

	registration_date = user[2]
	last_drop = datetime.fromtimestamp(user[3]) # last_card_drop
	if not last_drop:
		return True

	# Подсчет дней с регистрации
	if registration_date:
		reg_date = datetime.strptime(registration_date, '%Y-%m-%d %H:%M:%S')
		days_playing = (datetime.now() - reg_date).days
	else:
		days_playing = 0

	stats_text = f"""
📊 **Ваша статистика:**
👤 **Общее:**
🗓 Дней в игре: {days_playing}
🎴 Всего карточек: {total_cards}
💪 Общая сила: {total_power}
⭐ **Редкие карты:**
🌟 5★ карточек: {legendary_cards}
🔥 4★ карточек: {epic_cards}
⏰ **Последний дроп:** {last_drop or 'Никогда'}
"""

	bot.reply_to(message, stats_text, parse_mode='Markdown')
@bot.message_handler(commands=['help'])
def help_command(message):
	help_text = """
🆘 **Справка по командам:**
🎴 **Основные команды:**
• /card - Получить новую карточку (каждые 2 часа)
• /collection - Посмотреть свою коллекцию
• /profile - Ваша подробная статистика
• /top - Рейтинг лучших игроков
🎁 **Бонусы:**
• /daily - Ежедневные бонусы и их статус
ℹ️ **Информация:**
• /help - Эта справка
• /start - Перезапуск бота
🎯 **Советы:**
• Карточки выпадают с разной редкостью
• Используйте ежедневные бонусы для лучших шансов
• Собирайте редкие карты для топовых позиций
• Активность вознаграждается особыми бонусами
Удачи в сборе коллекции! 🍀
"""

	bot.reply_to(message, help_text, parse_mode='Markdown')
# Фоновые задачи
def schedule_jobs():
	"""Планирование фоновых задач"""
	schedule.every().day.at("00:00").do(bonus_system.reset_daily_bonuses)

	while True:
		schedule.run_pending()
		time.sleep(60) # Проверка каждую минуту

# Запуск планировщика в отдельном потоке
scheduler_thread = threading.Thread(target=schedule_jobs)
scheduler_thread.daemon = True
scheduler_thread.start()

# Обработка ошибок
@bot.message_handler(func=lambda message: True)
def unknown_command(message):
	bot.reply_to(message, "❓ Неизвестная команда. Используйте /help для просмотра доступных команд.")

def escape_markdown(text):
    """Экранирует спецсимволы Markdown v2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + c if c in escape_chars else c for c in str(text)])

if __name__ == "__main__":

    app.run() 
    # print("🤖 Бот запущен!")
    # print("📚 База данных инициализирована")
    # print("⏰ Планировщик запущен")
    # print("🎴 Система карточек готова")

	# #Запуск бота
    # bot.infinity_polling(none_stop=True)
