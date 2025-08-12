# card_system.py
import random
from config import RARITY_CHANCES, RARITY_NAMES, STAR_EMOJI
class CardSystem:
    def __init__(self, database):
        self.db = database

    def get_random_rarity(self, bonus_chance=0.0):
        """Получение случайной редкости с учетом бонусов"""
        # Базовые шансы
        chances = RARITY_CHANCES.copy()

        # Добавляем бонус к редким картам (4★ и 5★)
        if bonus_chance > 0:
            chances[5] += bonus_chance * 0.3 # 30% бонуса идет на 5★
            chances[4] += bonus_chance * 0.7 # 70% бонуса идет на 4★

        # Уменьшаем шансы обычных карт
        total_bonus = bonus_chance
        chances[1] -= total_bonus * 0.6
        chances[2] -= total_bonus * 0.3
        chances[3] -= total_bonus * 0.1

        # Формируем список редкостей с весами
        rarity_list = []
        for rarity, chance in chances.items():
            rarity_list.extend([rarity] * int(chance * 100))

        return random.choice(rarity_list)

    def get_random_card(self, rarity):
        """Получение случайной карточки заданной редкости"""
        cards = self.db.get_cards_by_rarity(rarity)
        if not cards:
            return None
        return random.choice(cards)

    def drop_card_for_user(self, user_id, time_to_drop):
        """Выпадение карточки для пользователя"""
        user = self.db.get_user(user_id)
        if not user:
            return None

        # Получаем бонусный шанс пользователя
        bonus_chance = user[5] # bonus_card_chance

        # Определяем редкость
        rarity = self.get_random_rarity(bonus_chance)

        # Получаем карточку
        card = self.get_random_card(rarity)
        if not card:
            return None

        # Добавляем карточку пользователю
        self.db.add_card_to_user(user_id, card[0]) # card id

        # Обновляем время последнего выпадения
        self.db.update_last_drop(user_id, time_to_drop)

        # Сбрасываем бонусный шанс после использования
        if bonus_chance > 0:
            self.db.cursor.execute('''
                UPDATE users SET bonus_card_chance = 0.0 WHERE user_id = ?
            ''', (user_id,))
            self.db.conn.commit()

        return card

    def format_card_info(self, card):
        """Форматирование информации о карточке"""
        if not card:
            return "Карточка не найдена"

        name = card[1]
        rarity = card[2]
        description = card[3]
        health = card[5]
        melee = card[6]
        ranged = card[7]
        devil_fruit = card[8]

        stars = STAR_EMOJI * rarity
        rarity_name = RARITY_NAMES.get(rarity, "Неизвестная")
        total_power = health + melee + ranged + devil_fruit

        return f"""
🎴 **{name}** {stars}
🏷 {rarity_name}
📝 {description}
📊 **Характеристики:**
❤️ Жизнь: {health}
⚔️ Ближний бой: {melee}
🏹 Дальний бой: {ranged}
🍎 Дьявольский плод: {devil_fruit}
💪 Общая сила: {total_power}
 """

    def get_user_collection_summary(self, user_id):
        """Получение краткой информации о коллекции пользователя"""
        cards = self.db.get_user_cards(user_id)
        stats = self.db.get_user_stats(user_id)

        if not cards:
            return "У вас пока нет карточек! 😢"

        total_cards = stats[0]
        total_power = stats[1] or 0
        legendary_cards = stats[2] or 0
        epic_cards = stats[3] or 0

        # Подсчет по редкости
        rarity_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for card in cards:
            rarity_count[card[2]] += 1

        summary = f"""
📚 **Ваша коллекция:**
🎴 Всего карточек: {total_cards}
💪 Общая сила: {total_power}
⭐ Распределение по редкости:
{STAR_EMOJI * 5} Мифические: {rarity_count[5]}
{STAR_EMOJI * 4} Легендарные: {rarity_count[4]}
{STAR_EMOJI * 3} Эпические: {rarity_count[3]}
{STAR_EMOJI * 2} Редкие: {rarity_count[2]}
{STAR_EMOJI * 1} Обычные: {rarity_count[1]}
 """

        return summary
