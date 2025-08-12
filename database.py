# database.py
import sqlite3
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Створення всіх необхідних таблиць"""
        # Таблиця користувачів
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_card_drop TIMESTAMP,
        daily_bonus_claimed DATE,
        bonus_card_chance REAL DEFAULT 0.0,
        bonus_extra_drops INTEGER DEFAULT 0
        )
        ''')

    # Таблиця карточок
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rarity INTEGER NOT NULL,
        description TEXT,
        image_path TEXT,
        health INTEGER DEFAULT 100,
        melee_weapon INTEGER DEFAULT 10,
        ranged_weapon INTEGER DEFAULT 10,
        devil_fruit INTEGER DEFAULT 0
        )
        ''')

        # Таблиця колекцій користувачів
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_id INTEGER,
        obtained_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (card_id) REFERENCES cards (id)
        )
        ''')

        self.conn.commit()
        self.populate_initial_cards()




    def register_user(self, user_id, username=None, time_sended=None):
        """Реєстрація нового користувача"""
        self.cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, last_card_drop)
        VALUES (?, ?, ?)
        ''', (user_id, username, time_sended))
        self.conn.commit()






    def get_user(self, user_id):
        """Отримання інформації про користувача"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()







    def can_drop_card(self, user_id, time_to_drop):
        """Перевірка чи може користувач отримати карточку"""
        user = self.get_user(user_id)
        if not user:
            return False

        last_drop = user[3] # last_card_drop
        if not last_drop:
            return True

        if isinstance(last_drop, int):
            last_drop_time = datetime.fromtimestamp(last_drop)
            print(last_drop_time, type(last_drop_time))
        else:
            last_drop_time = datetime.strptime(str(last_drop), '%Y-%m-%d %H:%M:%S')
            print(last_drop_time, type(last_drop_time))
        # last_drop_time = datetime.strptime(last_drop, '%Y-%m-%d %H:%M:%S')
        current_drop_time = datetime.fromtimestamp(time_to_drop)
        print(current_drop_time)
        return current_drop_time - last_drop_time >= timedelta(hours=0)





    def update_last_drop(self, user_id, time_to_drop):
        """Оновлення часу останнього отримання карточки"""
        # time_to_drop має бути у форматі 'YYYY-MM-DD HH:MM:SS'
        self.cursor.execute('''
        UPDATE users SET last_card_drop = ?
        WHERE user_id = ?
        ''', (time_to_drop, user_id))
        self.conn.commit()

    def add_card_to_user(self, user_id, card_id):
        """Додавання карточки до колекції користувача"""
        self.cursor.execute('''
        INSERT INTO user_cards (user_id, card_id)
        VALUES (?, ?)
        ''', (user_id, card_id))
        self.conn.commit()

    def get_user_cards(self, user_id):
        """Отримання всіх карточок користувача"""
        self.cursor.execute('''
        SELECT c.*, uc.obtained_date
        FROM cards c
        JOIN user_cards uc ON c.id = uc.card_id
        WHERE uc.user_id = ?
        ORDER BY c.rarity DESC, uc.obtained_date DESC
        ''', (user_id,))
        return self.cursor.fetchall()

    def get_card_by_id(self, card_id):
        """Отримання карточки за ID"""
        self.cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
        return self.cursor.fetchone()

    def get_cards_by_rarity(self, rarity):
        """Отримання карточок за рідкістю"""
        self.cursor.execute('SELECT * FROM cards WHERE rarity = ?', (rarity,))
        return self.cursor.fetchall()

    def get_user_stats(self, user_id):
        """Отримання статистики користувача"""
        self.cursor.execute('''
        SELECT
        COUNT(*) as total_cards,
        SUM(c.health + c.melee_weapon + c.ranged_weapon + c.devil_fruit) as total_power,
        COUNT(CASE WHEN c.rarity = 5 THEN 1 END) as legendary_cards,
        COUNT(CASE WHEN c.rarity = 4 THEN 1 END) as epic_cards
        FROM user_cards uc
        JOIN cards c ON uc.card_id = c.id
        WHERE uc.user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()

    def get_leaderboard(self, limit=10):
        """Отримання топ гравців"""
        self.cursor.execute('''
        SELECT
        u.user_id,
        u.username,
        COUNT(uc.card_id) as total_cards,
        SUM(c.health + c.melee_weapon + c.ranged_weapon + c.devil_fruit) as total_power,
        COUNT(CASE WHEN c.rarity >= 4 THEN 1 END) as rare_cards
        FROM users u
        LEFT JOIN user_cards uc ON u.user_id = uc.user_id
        LEFT JOIN cards c ON uc.card_id = c.id
        GROUP BY u.user_id
        ORDER BY rare_cards DESC, total_power DESC
        LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    # Система бонусів
    def can_claim_daily_bonus(self, user_id):
        """Перевірка чи може користувач отримати щоденний бонус"""
        user = self.get_user(user_id)
        if not user:
            return False

        last_bonus = user[4] # daily_bonus_claimed
        if not last_bonus:
            return True

        today = datetime.now().date()
        last_bonus_date = datetime.strptime(last_bonus, '%Y-%m-%d').date()
        return today > last_bonus_date

    def claim_daily_bonus(self, user_id, bonus_type):
        """Отримання щоденного бонусу"""
        today = datetime.now().date().strftime('%Y-%m-%d')

        if bonus_type == "rare_chance":
            self.cursor.execute('''
            UPDATE users SET
            daily_bonus_claimed = ?,
            bonus_card_chance = 10.0
            WHERE user_id = ?
            ''', (today, user_id))
        elif bonus_type == "extra_drop":
            self.cursor.execute('''
            UPDATE users SET
            daily_bonus_claimed = ?,
            bonus_extra_drops = 1
            WHERE user_id = ?
            ''', (today, user_id))

        self.conn.commit()

    def populate_initial_cards(self):
        """Заповнення початкових карточок"""
        # Перевіряємо чи вже є карточки
        self.cursor.execute('SELECT COUNT(*) FROM cards')
        if self.cursor.fetchone()[0] > 0:
            return

    # 5★ МИФИЧЕСКИЕ
        legendary_cards = [
            ("Гол Д. Роджер", 5, "Король пиратов", "5_star/roger.jpg", 210, 110, 95, 120),
            ("Эдвард Ньюгейт", 5, "Белоус, сильнейший человек в мире", "5_starwhitebeard.jpg", 230, 120, 80, 110),
            ("Шанкс", 5, "Император моря", "5_star/shanks.jpg", 195, 105, 110, 100),
            ("Кайдо", 5, "Король зверей", "5_star/kaido.jpg", 250, 130, 75, 130),
            ("Биг Мам", 5, "Могучая императрица", "5_star/bigmom.jpg", 210, 90, 100, 120),
            ("Им Сама", 5, "Повелительница мира", "5_star/im.jpg", 220, 115, 110, 130),
            ("Джой Бой", 5, "Легенда прошлого", "5_star/joyboy.jpg", 215, 112, 105, 125),
            ("Зунеша", 5, "Гигантский слон", "5_star/zunesha.jpg", 270, 85, 70, 140),
            ("Рокс Д. Шебек", 5, "Легендарный капитан пиратов Рокс", "5_star/rocks.jpg", 225, 120, 110, 135)
        ]

        # 4★ ЛЕГЕНДАРНЫЕ
        epic_cards = [
            ("Монки Д. Луффи", 4, "Будущий король пиратов", "4_star/luffy.jpg", 170, 95, 80, 95),
            ("Черная Борода", 4, "Обладатель двух плодов", "4_star/blackbeard.jpg", 180, 90, 100, 110),
            ("Ророноа Зоро", 4, "Охотник на пиратов", "4_star/zoro.jpg", 160, 110, 70, 80),
            ("Трафальгар Ло", 4, "Хирург смерти", "4_star/law.jpg", 155, 80, 90, 100),
            ("Дофламинго", 4, "Король нитей", "4_star/doflamingo.jpg", 158, 85, 95, 95),
            ("Михоук", 4, "Лучший мечник", "4_star/mihawk.jpg", 165, 120, 70, 80),
            ("Рейли", 4, "Правая рука Роджера", "4_star/rayleigh.jpg", 155, 95, 80, 90),
            ("Сэнгоку", 4, "Бывший адмирал флота", "4_star/sengoku.jpg", 160, 100, 75, 90),
            ("Марко", 4, "Феникс", "4_star/marco.jpg", 168, 90, 85, 105),
            ("Гарп", 4, "Герой дозора", "4_star/garp.jpg", 175, 110, 70, 80),
            ("Кудзан", 4, "Бывший адмирал", "4_star/kuzan.jpg", 158, 80, 100, 90),
            ("Кизару", 4, "Световой адмирал", "4_star/kizaru.jpg", 162, 90, 110, 80),
            ("Сакадзуки", 4, "Адмирал флота Акаину", "4_star/akainu.jpg", 170, 115, 80, 95),
            ("Бен Бекман", 4, "Правая рука Шанкса", "4_star/beckman.jpg", 155, 105, 90, 95)
        ]

        # 3★ ЭПИЧЕСКИЕ
        rare_cards = [
            ("Санджи", 3, "Мистер Принц", "3_star/sanji.jpg", 135, 85, 75, 70),
            ("Ямато", 3, "Дочь Кайдо", "3_star/yamato.jpg", 140, 80, 80, 80),
            ("Юстас Кид", 3, "Худшее поколение", "3_star/kid.jpg", 138, 80, 85, 75),
            ("Боа Хэнкок", 3, "Королева амазонок", "3_star/hancock.jpg", 125, 70, 90, 90),
            ("Катакури", 3, "Конфетный генерал", "3_star/katakuri.jpg", 145, 90, 80, 95),
            ("Джинбей", 3, "Рыба-человек", "3_star/jinbe.jpg", 142, 85, 75, 70),
            ("Киллер", 3, "Маска", "3_star/killer.jpg", 130, 95, 80, 65),
            ("Бартоломео", 3, "Барьер", "3_star/bartolomeo.jpg", 128, 75, 85, 80),
            ("Перона", 3, "Призраки", "3_star/perona.jpg", 120, 70, 95, 85),
            ("Кавендиш", 3, "Дуалист", "3_star/cavendish.jpg", 132, 90, 80, 65),
            ("Бэдж", 3, "Капитан крепость", "3_star/bege.jpg", 140, 80, 75, 70),
            ("Хоукинс", 3, "Маг", "3_star/hawkins.jpg", 125, 75, 90, 80),
            ("Х Дрейк", 3, "Динозавр", "3_star/xdrake.jpg", 137, 85, 80, 75),
            ("Урудж", 3, "Монах", "3_star/urouge.jpg", 145, 95, 70, 65),
            ("Джек", 3, "Стихийный бедствий", "3_star/jack.jpg", 148, 92, 78, 85)
        ]

        # 2★ РЕДКИЕ
        common_cards = [
            ("Нами", 2, "Навигатор", "2_star/nami.jpg", 105, 50, 80, 70),
            ("Нико Робин", 2, "Археолог", "2_star/robin.jpg", 110, 55, 75, 75),
            ("Брук", 2, "Скелет-музыкант", "2_star/brook.jpg", 108, 65, 60, 65),
            ("Крокодайл", 2, "Мистер 0", "2_star/crocodile.jpg", 120, 70, 65, 90),
            ("Багги", 2, "Клоун", "2_star/buggy.jpg", 95, 40, 55, 60),
            ("Френки", 2, "Киборг", "2_star/franky.jpg", 110, 60, 75, 50),
            ("Смокер", 2, "Дым", "2_star/smoker.jpg", 115, 65, 65, 70),
            ("Ташиги", 2, "Мечница", "2_star/tashigi.jpg", 105, 75, 60, 65),
            ("Пел", 2, "Сокол", "2_star/pell.jpg", 108, 60, 75, 65),
            ("Морган", 2, "Топор", "2_star/morgan.jpg", 100, 70, 55, 60),
            ("Хина", 2, "Клетка", "2_star/hina.jpg", 112, 62, 70, 68),
            ("Джанг", 2, "Гипноз", "2_star/jango.jpg", 98, 55, 75, 62),
            ("Калгара", 2, "Воин Шандии", "2_star/kalgara.jpg", 115, 65, 60, 65),
            ("Мисс Валентайн", 2, "Легкая как пух", "2_star/valentine.jpg", 105, 58, 70, 65),
            ("Шу", 2, "Пожиратель мечей", "2_star/shu.jpg", 100, 62, 60, 65),
            ("Дорри", 2, "Гигант воин", "2_star/dorry.jpg", 120, 70, 50, 60),
            ("Броги", 2, "Капитан блюгори", "2_star/brody.jpg", 110, 65, 58, 62),
            ("Кокоро", 2, "Женщина-русалка", "2_star/kokoro.jpg", 105, 50, 75, 65),
        ]

        # 1★ ОБЫЧНЫЕ
        basic_cards = [
            ("Виви", 1, "Принцесса", "1_star/vivi.jpg", 80, 35, 40, 45),
            ("Бони", 1, "Обжора", "1_star/bonney.jpg", 77, 38, 42, 48),
            ("Бон Клей", 1, "Мимикрия", "1_star/bonclay.jpg", 83, 42, 40, 50),
            ("Чоппер", 1, "Доктор", "1_star/chopper.jpg", 85, 45, 35, 55),
            ("Усопп", 1, "Король снайперов", "1_star/usopp.jpg", 75, 45, 80, 50),
            ("Коби", 1, "Моряк", "1_star/kobi.jpg", 75, 70, 40, 50),
            ("Ребекка", 1, "Гладиатор", "1_star/rebecca.jpg", 80, 65, 48, 48),
            ("Ган Фолл", 1, "Рыцарь неба", "1_star/gunfoll.jpg", 83, 68, 40, 45),
            ("Дадан", 1, "Опекун", "1_star/dadan.jpg", 77, 60, 45, 45),
            ("Кару", 1, "Утка", "1_star/karoo.jpg", 73, 30, 35, 40),
            ("Момоносукэ", 1, "Мальчик-дракон", "1_star/momonosuke.jpg", 78, 38, 40, 42),
            ("Кейми", 1, "Русалка", "1_star/keimi.jpg", 74, 32, 37, 43),
            ("Хельмеппо", 1, "Сын капитана", "1_star/helmeppo.jpg", 76, 36, 39, 41),
            ("Каппа", 1, "Водяной дух", "1_star/kappa.jpg", 77, 38, 35, 38),
            ("Тама", 1, "Девочка с дарами", "1_star/tama.jpg", 75, 32, 38, 42),
            ("Паппаг", 1, "Морская звезда", "1_star/papagu.jpg", 73, 30, 37, 40),
            ("Банкина", 1, "Мать Усоппа", "1_star/banchina.jpg", 75, 30, 35, 40),
            ("Макино", 1, "Барменша", "1_star/makino.jpg", 78, 35, 40, 45)
        ]

        # Додаємо карточки до бази даних
        
        all_cards = legendary_cards + epic_cards + rare_cards + common_cards + basic_cards

        self.cursor.executemany('''
        INSERT INTO cards (name, rarity, description, image_path, health, melee_weapon, ranged_weapon, devil_fruit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', all_cards)

        self.conn.commit()
        print("Початкові карточки додано до бази даних!")

print(datetime.now())