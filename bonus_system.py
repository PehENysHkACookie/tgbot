# bonus_system.py
import random
from datetime import datetime

class BonusSystem:
    def __init__(self, database):
        self.db = database

    def get_daily_bonus_options(self):
        """Получение вариантов ежедневных бонусов"""
        bonuses = [
            {
                "type": "rare_chance",
                "name": " Удача на карты 🍀",
                "description": "Увеличивает шанс выпадения редких карт на 10% на весь день",
                "emoji": "🍀"
            },
            {
                "type": "extra_drop", 
                "name": " Дополнительная карта ⚡",
                "description": "Дает возможность получить одну дополнительную карту сегодня",
                "emoji": "⚡"
            }
        ]
        return bonuses

    def can_claim_daily_bonus(self, user_id):
        """Проверка возможности получения ежедневного бонуса"""
        return self.db.can_claim_daily_bonus(user_id)

    def claim_daily_bonus(self, user_id, bonus_type):
        """Получение ежедневного бонуса"""
        if not self.can_claim_daily_bonus(user_id):
            return False
        self.db.claim_daily_bonus(user_id, bonus_type)
        return True

    def get_bonus_status(self, user_id):
        """Получение статуса активных бонусов пользователя"""
        user = self.db.get_user(user_id)
        if not user:
            return "Пользователь не найден"
        bonus_chance = user[5] # bonus_card_chance
        extra_drops = user[6] # bonus_extra_drops
        status = "🎁 **Активные бонусы:**\n"
        if bonus_chance > 0:
            status += f"🍀 Повышенный шанс редких карт: +{bonus_chance}%\n"
        if extra_drops > 0:
            status += f"⚡ Дополнительные попытки получения карт: {extra_drops}\n"
        if bonus_chance == 0 and extra_drops == 0:
            status += "❌ Нет активных бонусов\n"
        status += f"\n🗓 Ежедневный бонус: {'✅ Доступен' if self.can_claim_daily_bonus(user_id) else '❌ Уже получен'}"
        return status

    def use_extra_drop(self, user_id):
        """Использование дополнительной попытки"""
        user = self.db.get_user(user_id)
        if not user or user[6] <= 0: # extra_drops
            return False
        self.db.cursor.execute('''
            UPDATE users SET bonus_extra_drops = bonus_extra_drops - 1 
            WHERE user_id = ?
        ''', (user_id,))
        self.db.conn.commit()
        return True

    def reset_daily_bonuses(self):
        """Сброс ежедневных бонусов (вызывается каждую ночь)"""
        self.db.cursor.execute('''
            UPDATE users SET 
                bonus_card_chance = 0.0,
                bonus_extra_drops = 0
            WHERE daily_bonus_claimed != DATE('now')
        ''')
        self.db.conn.commit()

    # def get_weekly_bonus(self, user_id):
    #     """Еженедельный бонус для активных игроков"""
    #     # Подсчет карт за последнюю неделю
    #     self.db.cursor.execute('''
    #         SELECT COUNT(*) FROM user_cards 
    #         WHERE user_id = ? AND obtained_date >= DATE('now', '-7 days')
    #     ''', (user_id,))
    #     weekly_cards = self.db.cursor.fetchone()[0]
    #     if weekly_cards >= 10: # Если получено 10+ карт за неделю
    #         return {
    #             "eligible": True,
    #             "reward": "legendary_chance",
    #             "description": "🎉 Вы получили гарантированную 4★+ карту за активность!"
    #         }
    #     return {"eligible": False}