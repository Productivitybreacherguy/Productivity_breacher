import pygame
import sys
import time
import psutil
import threading
import random
import math
import socket
import json
import os
import numpy as np
import secrets
import random
import socket as _socket

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pb_session.json")

def get_or_create_session():
    """Читает или создаёт pb_session.json с портом и токеном."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
            if "port" in data and "token" in data:
                return data["port"], data["token"]
        except Exception:
            pass
    
    # Создаём новый
    port = random.randint(20000, 60000)
    token = secrets.token_hex(16)
    data = {"port": port, "token": token}
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[SESSION] Ошибка сохранения: {e}")
    return port, token

SESSION_PORT, SESSION_TOKEN = get_or_create_session()

# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

W, H = 500, 700
screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("[BETA] Productivity Breacher")

# ============================================================
# ЦВЕТА
# ============================================================

WHITE       = (255, 255, 255)
WHITE_DARK  = (230, 230, 230)
GRAY_SOFT   = (240, 240, 240)
GRAY_TEXT   = (100, 100, 100)
BLACK       = (0, 0, 0)
RED         = (220, 50, 50)
ORANGE      = (255, 140, 0)
YELLOW      = (230, 200, 40)
GREEN       = (100, 220, 100)
BORDER      = 10

# ============================================================
# ШРИФТЫ
# ============================================================

font_big   = pygame.font.Font(None, 48)
font_mid   = pygame.font.Font(None, 36)
font_small = pygame.font.Font(None, 30)
font_tiny  = pygame.font.Font(None, 24)
pending_request = None   # None, "discard", "free_day"

# ============================================================
# ТЕМЫ
# ============================================================

BASE_THEMES = {
    "Классика":   (255, 215, 0),
    "Фиолетовая": (180, 100, 255),
    "Зелёная":    (100, 220, 120),
    "Синяя":      (100, 160, 255),
}

CODE_THEMES = {
    "Snakey":         (50, 205, 50),
    "PartyLaws":      (139, 69, 19),
    "MyMommaStrict":  (20, 20, 20),
    "CameFromGithub": (60, 60, 60),
}

current_theme = "Классика"
ACCENT = BASE_THEMES[current_theme]

# ============================================================
# ЦВЕТА ТЕКСТА
# ============================================================

TEXT_COLORS = {
    "Чёрный":            (0, 0, 0),
    "Серый":             (100, 100, 100),
    "Тёмно-синий":       (20, 40, 90),
    "Тёмно-фиолетовый":  (70, 30, 110),
}
current_text_color = "Чёрный"
TEXT_COLOR = TEXT_COLORS[current_text_color]

# ============================================================
# УЗОРЫ ФОНА
# ============================================================

PATTERNS = ["Шахматка", "Полосы", "Точки", "Ромбы", "Пусто"]
current_pattern  = "Шахматка"
invert_pattern   = False
animate_pattern  = False
anim_offset      = 0.0
filler_variable = True

# ============================================================
# ЯЗЫКИ
# ============================================================

LANGUAGES = ["Русский", "English", "Deutsch", "Français", "Español"]
current_language = "Русский"

# ============================================================
# ЗВУКОВЫЕ ТЕМЫ
# ============================================================

SOUND_THEMES = ["Классика", "Джаз", "Марио", "Тишина", "Дождь", "Оркестр"]
current_sound_theme = "Классика"
sound_scroll = 0
# Карта: тема → имя файла в папке music/
SOUND_FILES = {
    "Классика": "ClassicPB.mp3",
    "Джаз":     "JazzPB.mp3",
    "Марио":    "MarioPB.mp3",
    "Дождь":    "RainPB.mp3",
    "Оркестр":  "OrchestraPB.mp3",
    # "Тишина" — без файла
}

current_music_file = None   # какой трек сейчас играет


def play_background_music(theme_name):
    """Запускает фоновую музыку для выбранной темы. Если 'Тишина' — выключает."""
    global current_music_file

    # Тишина — просто стоп
    if theme_name == "Тишина" or theme_name not in SOUND_FILES:
        pygame.mixer.music.stop()
        current_music_file = None
        return

    filename = SOUND_FILES[theme_name]
    if filename == current_music_file:
        return  # уже играет — не перезапускаем

    music_path = resource_path(os.path.join("music", filename))
    if not os.path.exists(music_path):
        print(f"[MUSIC] Не найден файл: {music_path}")
        return

    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(volume / 100)
        pygame.mixer.music.play(-1)  # -1 = бесконечный loop
        current_music_file = filename
        print(f"[MUSIC] Играет: {filename}")
    except Exception as e:
        print(f"[MUSIC] Ошибка загрузки: {e}")
ach_scroll = 0

# ============================================================
# FREE DAY
# ============================================================

free_day_active          = False
free_day_date            = ""
free_day_request_pending = False
free_day_popup_until     = 0.0

# ============================================================
# ЗАМЕТКА
# ============================================================

note_text    = ""
note_active  = False
note_slide   = 0.0
current_note = ""
note_used    = False

# ============================================================
# КРЕСТ (анимация конца таймера)
# ============================================================

cross_phase               = "idle"
cross_scale               = 0.0
cross_alpha               = 255
cross_shake               = 0
cross_start               = 0.0
pending_state_after_cross = None

# ============================================================
# МНОЖИТЕЛИ (от кодов)
# ============================================================

timer_speed_mult    = 1.0
cooldown_speed_mult = 1.0
cooldown_flat_bonus = 0

# ============================================================
# КВЕСТЫ
# ============================================================

QUESTS_POOL = [
    ("Set up 3 timers",       "timers_count",   3),
    ("Get an app killed",     "app_killed",     1),
    ("Set a new color theme", "color_changed",  1),
    ("Set a new sound theme", "sound_changed",  1),
    ("Check your history",    "history_opened", 1),
]
daily_quests   = []
quest_progress = {}
quests_date    = ""

# ============================================================
# КОДЫ
# ============================================================

ACTIVATED_CODES = []
code_input = ""
code_message = ""
code_message_ok = False
code_message_until = 0.0

# ============================================================
# ПЕРЕВОДЫ
# ============================================================

TRANSLATIONS = {
    "Русский": {
        "settings": "Настройки", "sound": "Звук", "themes": "Темы", "text": "Текст",
        "patterns": "Узоры", "langs": "Языки", "volume": "Громкость",
        "choose_theme": "Выберите тему", "choose_text": "Цвет текста",
        "choose_pattern": "Узор фона", "inversion": "Инверсия", "animation": "Анимация",
        "language": "Язык", "options": "Меню", "history": "История", "quests": "Квесты",
        "codes": "Коды",
        "timer_label": "Ставьте свой таймер!", "too_much": "это слишком много времени!",
        "max_2h": "не более 2 часов!", "cooldown": "Перезарядка!",
        "no_play": "играть пока нельзя!", "start": "Старт!",
        "closing1": "Закрываешь меня?", "closing2a": "Думаешь можешь",
        "closing2b": "сам контролировать себя?", "closing3": "ладно, удачи!",
    },
    "English": {
        "settings": "Settings", "sound": "Sound", "themes": "Themes", "text": "Text",
        "patterns": "Patterns", "langs": "Languages", "volume": "Volume",
        "choose_theme": "Choose theme", "choose_text": "Text color",
        "choose_pattern": "Background pattern", "inversion": "Inversion",
        "animation": "Animation", "language": "Language", "options": "Options",
        "history": "History", "quests": "Quests", "codes": "Codes",
        "timer_label": "Set your timer!", "too_much": "that's too much time!",
        "max_2h": "no more than 2 hours!", "cooldown": "Cooldown!",
        "no_play": "you can't play yet!", "start": "Start!",
        "closing1": "Closing me?", "closing2a": "You think you can",
        "closing2b": "control yourself?", "closing3": "well, good luck!",
    },
    "Deutsch": {
        "settings": "Einstellungen", "sound": "Ton", "themes": "Themen", "text": "Text",
        "patterns": "Muster", "langs": "Sprachen", "volume": "Lautstärke",
        "choose_theme": "Thema wählen", "choose_text": "Textfarbe",
        "choose_pattern": "Hintergrundmuster", "inversion": "Inversion",
        "animation": "Animation", "language": "Sprache", "options": "Optionen",
        "history": "Verlauf", "quests": "Quests", "codes": "Codes",
        "timer_label": "Stelle deinen Timer!", "too_much": "das ist zu viel Zeit!",
        "max_2h": "nicht mehr als 2 Stunden!", "cooldown": "Abklingzeit!",
        "no_play": "du kannst noch nicht spielen!", "start": "Start!",
        "closing1": "Schließt du mich?", "closing2a": "Denkst du, du kannst",
        "closing2b": "dich selbst kontrollieren?", "closing3": "na dann, viel Glück!",
    },
    "Français": {
        "settings": "Paramètres", "sound": "Son", "themes": "Thèmes", "text": "Texte",
        "patterns": "Motifs", "langs": "Langues", "volume": "Volume",
        "choose_theme": "Choisir un thème", "choose_text": "Couleur du texte",
        "choose_pattern": "Motif de fond", "inversion": "Inversion",
        "animation": "Animation", "language": "Langue", "options": "Options",
        "history": "Historique", "quests": "Quêtes", "codes": "Codes",
        "timer_label": "Réglez votre minuteur!", "too_much": "c'est trop de temps!",
        "max_2h": "pas plus de 2 heures!", "cooldown": "Recharge!",
        "no_play": "tu ne peux pas encore jouer!", "start": "Démarrer!",
        "closing1": "Tu me fermes?", "closing2a": "Tu penses pouvoir",
        "closing2b": "te contrôler?", "closing3": "eh bien, bonne chance!",
    },
    "Español": {
        "settings": "Ajustes", "sound": "Sonido", "themes": "Temas", "text": "Texto",
        "patterns": "Patrones", "langs": "Idiomas", "volume": "Volumen",
        "choose_theme": "Elige tema", "choose_text": "Color del texto",
        "choose_pattern": "Patrón de fondo", "inversion": "Inversión",
        "animation": "Animación", "language": "Idioma", "options": "Opciones",
        "history": "Historial", "quests": "Misiones", "codes": "Códigos",
        "timer_label": "¡Pon tu temporizador!", "too_much": "¡eso es demasiado tiempo!",
        "max_2h": "¡no más de 2 horas!", "cooldown": "¡Recarga!",
        "no_play": "¡aún no puedes jugar!", "start": "¡Empezar!",
        "closing1": "¿Me estás cerrando?", "closing2a": "¿Crees que puedes",
        "closing2b": "controlarte a ti mismo?", "closing3": "bueno, ¡buena suerte!",
    },
}

def t(key):
    """Возвращает перевод ключа для текущего языка."""
    return TRANSLATIONS[current_language].get(key, key)

# ============================================================
# ГРОМКОСТЬ
# ============================================================

volume = 75

# ============================================================
# ФАКТЫ
# ============================================================

FACTS = [
    "А вы знали, что Roblox изначально должен был быть симулятором физики?",
    "А вы знали, что первая версия Minecraft была создана за 6 дней?",
    "А вы знали, что Python назван в честь шоу «Летающий цирк Монти Пайтона»?",
    "А вы знали, что первый компьютерный баг был настоящей молью?",
    "А вы знали, что слово «робот» придумал чешский писатель Карел Чапек?",
    "А вы знали, что Тетрис был создан в СССР в 1984 году?",
    "А вы знали, что самая долгая игра в Minecraft длится более 10 лет?",
    "А вы знали, что в игре Roblox есть скрытая лошадь, которую вырезали?",
    "А вы знали, что в Roblox есть игра Doors, где есть сущность по имени Sally?",
    "А вы знали, что в Roblox есть игра Forsaken, где есть персонаж по имени Chance?",
    "А вы знали, что первая компьютерная мышь была сделана из дерева?",
    "А вы знали, что интернет изначально назывался ARPANET?",
    "А вы знали, что первый сайт в мире всё ещё работает?",
    "А вы знали, что создатель Minecraft Нотч написал игру за одну неделю?",
    "А вы знали, что в Python есть пасхалка «import this»?",
    "А вы знали, что у клавиатуры QWERTY раскладка создана для медленной печати?",
    "А вы знали, что первая видеоигра была создана в 1958 году?",
    "А вы знали, что Тетрис изначально был создан для советских компьютеров?",
    "А вы знали, что слово «пиксель» происходит от «picture element»?",
    "А вы знали, что самый первый компьютер весил 27 тонн?",
    "А вы знали, что в Roblox есть игра Tower Defense Simulator?",
    "А вы знали, что в Roblox есть игра Adopt Me, где можно заводить питомцев?",
    "А вы знали, что в Roblox есть игра Brookhaven, где можно строить дома?",
    "А вы знали, что в Roblox есть игра Piggy, похожая на хоррор?",
    "А вы знали, что в Roblox есть игра Murder Mystery 2?",
    "А вы знали, что в Roblox есть игра Arsenal, где можно стрелять?",
    "А вы знали, что в Roblox есть игра Blox Fruits, где можно стать пиратом?",
    "А вы знали, что в Roblox есть игра BedWars, где надо защищать кровать?",
    "А вы знали, что в Roblox есть игра Natural Disaster Survival?",
    "А вы знали, что в Roblox есть игра Work at a Pizza Place?",
]

# ============================================================
# БЛОКИРОВКА ПРИЛОЖЕНИЙ
# ============================================================

BLOCKED_APPS = ["Roblox", "Minecraft", "YouTube", "Discord", "ChatGPT", "OpenAI"]
BLOCKED_SITES = [
    "youtube.com", "youtu.be", "m.youtube.com",
    "tiktok.com", "www.tiktok.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "x.com",
    "reddit.com", "www.reddit.com",
    "twitch.tv", "www.twitch.tv",
    "netflix.com", "www.netflix.com",
    "discord.com", "www.discord.com",
]

can_play       = False
socket_conn    = None
password       = "CL0SE"
cooldown_active = False

# ============================================================
# ФАЙЛЫ ДАННЫХ
# ============================================================

def resource_path(relative_path):
    """Возвращает путь к ресурсу — работает и в .py, и в собранном .app."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIMERS_FILE      = os.path.join(BASE_DIR, "timers.json")
HISTORY_TXT_FILE = os.path.join(BASE_DIR, "history.txt")
QUESTS_FILE      = os.path.join(BASE_DIR, "quests.json")
CODES_FILE       = os.path.join(BASE_DIR, "codes.json")

# ============================================================
# СОСТОЯНИЕ ПРИЛОЖЕНИЯ
# ============================================================

state           = "input"
timer_input     = ""
timer_start     = 0
timer_seconds   = 0
cooldown_end    = 0
cooldown_seconds = 0
error_until     = 0
current_fact    = ""
close_start     = 0
menu_state      = "closed"
slider_drag     = False
timer_history   = []

# Request Discard
request_btn_visible  = False
request_btn_slide    = 0.0
request_btn_rect     = None
request_phase        = "idle"
request_phase_time   = 0.0
request_used         = False
cooldown_start_time  = 0.0

# ============================================================
# ФАЙЛЫ: timers.json
# ============================================================

def ensure_timers_file():
    if not os.path.exists(TIMERS_FILE):
        with open(TIMERS_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
    else:
        filler_variable = True

def get_available_themes():
    """Возвращает базовые темы + те кодовые, что разблокированы."""
    result = dict(BASE_THEMES)
    for code, color in CODE_THEMES.items():
        if code in ACTIVATED_CODES:
            result[code] = color
    return result

def load_history():
    if not os.path.exists(TIMERS_FILE):
        return []
    try:
        with open(TIMERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history):
    if len(history) > 30:
        history = history[-30:]
    try:
        with open(TIMERS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError as e:
        filler_variable = True


def get_history_stats():
    """Возвращает статистику по истории таймеров."""
    empty = {"total": 0, "avg": "0s", "most_common": "none", "most_count": 0, "total_seconds": 0}
    if not timer_history:
        return empty

    total = len(timer_history)
    total_seconds = 0
    counts = {}

    for entry in timer_history:
        d = entry.get("duration", "0s")
        counts[d] = counts.get(d, 0) + 1
        try:
            num = int(d[:-1])
            unit = d[-1].lower()
            secs = num if unit == "s" else num * 60 if unit == "m" else num * 3600
            total_seconds += secs
        except Exception:
            pass

    avg = total_seconds // total if total > 0 else 0
    if avg >= 3600:
        avg_str = f"{avg // 3600}h {(avg % 3600) // 60}m"
    elif avg >= 60:
        avg_str = f"{avg // 60}m {avg % 60}s"
    else:
        avg_str = f"{avg}s"

    most_common = max(counts, key=counts.get) if counts else "none"
    return {
        "total": total,
        "avg": avg_str,
        "most_common": most_common,
        "most_count": counts.get(most_common, 0),
        "total_seconds": total_seconds,
    }


def export_history_txt():
    try:
        with open(HISTORY_TXT_FILE, "w", encoding="utf-8") as f:
            f.write("PB&J - Timer History\n")
            f.write("=" * 30 + "\n\n")
            for i, entry in enumerate(timer_history, 1):
                duration = entry.get("duration", "?")
                tm       = entry.get("time", "?")
                source   = entry.get("source", "self")
                note     = entry.get("note", "")
                if note:
                    f.write(f"{i}. {duration}  -  {tm}  ({source})  [{note}]\n")
                else:
                    f.write(f"{i}. {duration}  -  {tm}  ({source})\n")
            f.write("\n" + "=" * 30 + "\n")
            f.write(f"Total: {len(timer_history)} timers\n")
        filler_variable = True
    except OSError as e:
        filler_variable = True

# ============================================================
# ФАЙЛЫ: quests.json
# ============================================================

def load_quests():
    global daily_quests, quest_progress, quests_date
    today = time.strftime("%d.%m.%Y")

    if not os.path.exists(QUESTS_FILE):
        daily_quests = []
        quest_progress = {}
        quests_date = ""
        return

    try:
        with open(QUESTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") == today:
            daily_quests   = data.get("quests", [])
            quest_progress = data.get("progress", {})
            quests_date    = today
        else:
            daily_quests = []
            quest_progress = {}
            quests_date = ""
    except (json.JSONDecodeError, OSError):
        daily_quests = []
        quest_progress = {}
        quests_date = ""


def save_quests():
    try:
        with open(QUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"date": quests_date, "quests": daily_quests, "progress": quest_progress},
                f, ensure_ascii=False, indent=2
            )
    except OSError as e:
        filler_variable = True


def generate_quests():
    global daily_quests, quest_progress, quests_date
    today = time.strftime("%d.%m.%Y")
    if quests_date == today and daily_quests:
        return
    daily_quests = random.sample(QUESTS_POOL, 3)
    quest_progress = {q[1]: 0 for q in daily_quests}
    quests_date = today
    save_quests()
    filler_variable = True


def progress_quest(key):
    global quest_progress
    if not daily_quests:
        return
    for q in daily_quests:
        if q[1] == key:
            if quest_progress.get(key, 0) < q[2]:
                quest_progress[key] = quest_progress.get(key, 0) + 1
                save_quests()
            return

# ============================================================
# ФАЙЛЫ: codes.json
# ============================================================

def load_codes():
    global ACTIVATED_CODES
    if not os.path.exists(CODES_FILE):
        ACTIVATED_CODES = []
        return
    try:
        with open(CODES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ACTIVATED_CODES = data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        ACTIVATED_CODES = []


def save_codes():
    try:
        with open(CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(ACTIVATED_CODES, f, ensure_ascii=False, indent=2)
    except OSError as e:
        filler_variable = True


# Список всех валидных кодов
VALID_CODES = ["Snakey", "PartyLaws", "MyMommaStrict", "CameFromGithub", "IHateThis"]
# ============================================================
# ДОСТИЖЕНИЯ
# ============================================================

ACHIEVEMENTS_FILE = os.path.join(BASE_DIR, "achievements.json")
SIGNATURES_FILE = os.path.join(BASE_DIR, "signatures.json")

# База сигнатур: {"Roblox": {"name": "robloxplayer", "exe": "/path/to/roblox"}, ...}
known_signatures = {}
# Триггер: изменилась ли сигнатура с прошлого раза
signature_changed = False

# Каждое достижение: (id, название, цитата, описание, можно_получить_автоматически)
ACHIEVEMENTS = [
    # --- АВТОМАТИЧЕСКИЕ ---
    ("welcome",         "Welcome!",
     "did I just get hacked?",
     "Enter Productivity Breacher for the first time.", True),

    ("first_timer",     "Time-managing.",
     "Tick tock goes the clock...",
     "Set up your first timer.", True),

    ("first_cooldown",  "Stop right there!",
     "aw man this suckz",
     "Enter your first cooldown state.", True),

    ("app_killed_cd",   "Locked and loaded.",
     "PAY US TO GET YOUR FILES BACK!11!1!!1",
     "Have an app get killed via entering cooldown.", True),

    ("app_killed_free", "Damn it!",
     "unfortunate, yeah.",
     "Get an app killed via trying to open it without a timer.", True),

    ("new_looks",       "New looks.",
     "there are skins here???",
     "Make a unique color, music & background combo.", True),

    ("hunters_dream",   "A Hunter's dream.",
     "did you hear anything?",
     "Set sound settings on \"silent\" and the sound Volume to 0.", True),

    ("sensory_overload","Sensory overload",
     "Secret way secret way",
     "Get a custom color/sound theme/background via events, codes or the devs.", True),

    ("pomodoro",        "Pomodoro would be proud",
     "Again & again & again",
     "Set up your 100th timer.", True),

    ("hidden_cameras",  "Hidden cameras",
     "I was stalked?!",
     "Check your history for the first time.", True),

    ("code_of_doom",    "The code of doom and despair",
     "GOD DAMN IT!",
     "Try to access a banned app through a rename/reposition.", True),

    ("buzzkill",        "Buzzkill!",
     "and how does that benefit me exactly?",
     "Set a timer for one second.", True),

    ("free_time",       "Free time",
     "im pretty sure I can play now",
     "Have a parent grant you a free day.", True),

    ("badass_parents",  "Badass parents",
     "THEY UNBLOCKED IT?",
     "Have a parent grant you access to a blocked app via \"unblock\".", True),

    ("cheat_code",      "Cheat code",
     "im tubers93!",
     "Close the app via main password.", True),

    # --- НЕДОСТУПНЫЕ (пока что) ---
    ("bug_spray",       "Bug spray",
     "yeah man the President knows my name!",
     "Find a bug, report it to the Dev and hope for this to be given to you. (UNOBTAINABLE)", False),

    ("one_more_game",   "One more game",
     "she agreed! Open roblox!",
     "Have your parent discard a cooldown for you. (UNOBTAINABLE)", False),

    ("twentyfour",      "24 times right?",
     "I can finally see it after obtaining this body.",
     "Successfully play a blocked game and send the footage to a dev. (UNOBTAINABLE)", False),

    ("oh_baby_triple",  "Oh baby a triple!",
     "im just that good",
     "Get a clip of you winning, finishing or pulling a stunt in game with the timer running out right after you did it barely letting you win, then submit it into the official Productivity Breacher discord server. (UNOBTAINABLE)", False),

    ("how_unfortunate","How unfortunate...",
     "I was SO CLOSE!",
     "Be at the very end of a hard game, then get your app killed, then submit the clip to the official discord server. (UNOBTAINABLE)", False),

    ("limited_omni",    "Limited omnipotence",
     "I've been through worse.",
     "Win EVERY event that was ever announced in the history of PB. (UNOBTAINABLE)", False),

    ("unholy_spirits",  "Unholy spirits",
     "is this place haunted?",
     "Complete the Halloween event of 2026. (UNOBTAINABLE)", False),

    ("weather_fright",  "Weather frightful, fire delightful.",
     "its TIIII..... IIME!",
     "Complete the 2026 new year event. (UNOBTAINABLE)", False),

    ("ufo",             "It's a bird.. It's a plane... It's a UFO!",
     "and out of the sky... Like a flash..",
     "Complete the 2026 frog invasion event. (UNOBTAINABLE)", False),

    ("old_school",      "Old school.",
     "back to the future, huh?",
     "Have a developer grant you access to the oldest versions of the app. (UNOBTAINABLE)", False),
]

# Какие достижения уже разблокированы
unlocked_achievements = []

# Всплывашка при разблокировке
achievement_popup_queue = []       # очередь достижений на показ
achievement_popup_current = None   # какое показывается сейчас
achievement_popup_start = 0.0      # когда началась показ
achievement_popup_duration = 3.5   # сколько секунд висит


def load_achievements():
    """Загружает список разблокированных достижений из файла."""
    global unlocked_achievements
    if not os.path.exists(ACHIEVEMENTS_FILE):
        unlocked_achievements = []
        return
    try:
        with open(ACHIEVEMENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        unlocked_achievements = data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        unlocked_achievements = []

def load_signatures():
    """Загружает сохранённые сигнатуры процессов."""
    global known_signatures
    if not os.path.exists(SIGNATURES_FILE):
        known_signatures = {}
        return
    try:
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        known_signatures = data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        known_signatures = {}


def save_signatures():
    """Сохраняет сигнатуры процессов в файл."""
    try:
        with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
            json.dump(known_signatures, f, ensure_ascii=False, indent=2)
    except OSError as e:
        filler_variable = True

def save_achievements():
    """Сохраняет список разблокированных достижений в файл."""
    try:
        with open(ACHIEVEMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(unlocked_achievements, f, ensure_ascii=False, indent=2)
    except OSError as e:
        filler_variable = True


def get_achievement(ach_id):
    """Возвращает кортеж достижения по id или None."""
    for ach in ACHIEVEMENTS:
        if ach[0] == ach_id:
            return ach
    return None


def unlock_achievement(ach_id):
    """Разблокирует достижение (если ещё не разблокировано). Показывает попап."""
    global achievement_popup_queue

    if ach_id in unlocked_achievements:
        return False

    ach = get_achievement(ach_id)
    if ach is None:
        filler_variable = True
        return False

    # Проверка на (UNOBTAINABLE) — их нельзя получить автоматически
    if not ach[4]:
        filler_variable = True
        return False

    unlocked_achievements.append(ach_id)
    save_achievements()

    # Добавляем в очередь на показ
    achievement_popup_queue.append(ach_id)

    filler_variable = True
    return True


def try_activate_code(code):
    """Пытается активировать код. Возвращает True при успехе."""
    global ACCENT, current_theme, timer_speed_mult, cooldown_speed_mult

    if code not in VALID_CODES:
        return False
    if code in ACTIVATED_CODES:
        return False

    ACTIVATED_CODES.append(code)
    save_codes()

    if code in CODE_THEMES:
        current_theme = code
        ACCENT = CODE_THEMES[code]

    if code == "IHateThis":
        timer_speed_mult = 0.9
        cooldown_speed_mult = 1.1

    filler_variable = True
    return True

# ============================================================
# FREE DAY
# ============================================================

def check_free_day():
    global free_day_active, free_day_date, can_play
    today = time.strftime("%d.%m.%Y")
    if free_day_active and free_day_date != today:
        free_day_active = False
        free_day_date = ""
        can_play = False
        filler_variable = True

# ============================================================
# WATCHDOG (блокировка приложений)
# ============================================================

import subprocess

def get_safari_url():
    """Возвращает URL активной вкладки Safari или None."""
    script = 'tell application "Safari" to get URL of current tab of front window'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def is_blocked_site(url):
    """Проверяет, есть ли запрещённый сайт в URL."""
    if not url:
        return False
    url_lower = url.lower()
    return any(site in url_lower for site in BLOCKED_SITES)


def close_safari_tab():
    """Закрывает активную вкладку Safari."""
    script = 'tell application "Safari" to close current tab of front window'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
        print("[WEBSITE] Вкладка закрыта")
    except Exception as e:
        print(f"[WEBSITE] Ошибка закрытия: {e}")

def is_app_open():
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = (proc.info['name'] or "").lower()
            exe = (proc.info['exe'] or "").lower()
            if any(app.lower() in name or app.lower() in exe for app in BLOCKED_APPS):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def check_signatures():
    """Проверяет, изменились ли сигнатуры заблокированных процессов.
    Возвращает True, если найдено изменение (rename/reposition)."""
    global known_signatures, signature_changed

    if not can_play:
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                name = (proc.info['name'] or "").lower()
                exe = (proc.info['exe'] or "").lower()
                if not name:
                    continue

                # Ищем, к какому заблокированному приложению относится процесс
                matched_app = None
                for app in BLOCKED_APPS:
                    if app.lower() in name or app.lower() in exe:
                        matched_app = app
                        break

                if matched_app is None:
                    continue

                current_sig = {"name": name, "exe": exe}

                # Если для этого приложения ещё нет базы — записываем и пропускаем
                if matched_app not in known_signatures:
                    known_signatures[matched_app] = current_sig
                    save_signatures()
                    continue

                # Сравниваем с базой
                old_sig = known_signatures[matched_app]
                if old_sig.get("name") != name or old_sig.get("exe") != exe:
                    # Сигнатура изменилась → rename или reposition
                    signature_changed = True
                    filler_variable = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return signature_changed

def kill_apps():
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = (proc.info['name'] or "").lower()
            exe = (proc.info['exe'] or "").lower()
            if any(app.lower() in name or app.lower() in exe for app in BLOCKED_APPS):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def watchdog():
    global signature_changed

    while True:
        check_free_day()
        if not can_play:
            check_signatures()

            if is_app_open():
                was_changed = signature_changed

                kill_apps()
                progress_quest("app_killed")

                if cooldown_active:
                    unlock_achievement("app_killed_cd")
                else:
                    unlock_achievement("app_killed_free")

                if was_changed:
                    unlock_achievement("code_of_doom")
                    signature_changed = False

            # --- Проверка сайтов в Safari ---
            current_url = get_safari_url()
            if current_url and is_blocked_site(current_url):
                print(f"[WEBSITE] Заблокирован: {current_url}")
                close_safari_tab()
                progress_quest("app_killed")

        time.sleep(2)  # было 1, стало 2 (чтобы не спамить osascript)

# ============================================================
# SOCKET SERVER
# ============================================================

def handle_socket_command(data, conn):
    """Обрабатывает одну команду сокета. Возвращает True, если соединение нужно закрыть."""
    global socket_conn, timer_input, state, timer_start, timer_seconds
    global can_play, current_fact, password, BLOCKED_APPS
    global cooldown_active, cooldown_end, timer_history
    global free_day_active, free_day_date
    global pending_request

    # --- LOCK:<время> ---
    if data.startswith("LOCK:"):
        new_timer = data.split(":", 1)[1].strip()
        timer_input = new_timer
        try:
            num = int(new_timer[:-1])
            unit = new_timer[-1].lower()
            secs = num if unit == "s" else num * 60 if unit == "m" else num * 3600
            if 0 < secs <= 7200:
                state = "timer"
                timer_start = time.time()
                timer_seconds = secs
                can_play = True
                cooldown_active = False
                current_fact = random.choice(FACTS)
                timer_history.append({
                    "duration": new_timer,
                    "time": time.strftime("%H:%M"),
                    "note": "",
                })
                save_history(timer_history)
                progress_quest("timers_count")
                filler_variable = True
            else:
                filler_variable = True
        except Exception as e:
            filler_variable = True

    # --- SETPASSWORD:<пароль> ---
    elif data.startswith("SETPASSWORD:"):
        password = data.split(":", 1)[1]
        filler_variable = True

    # --- CLOSE:<пароль> ---
    elif data.startswith("CLOSE:"):
        entered = data.split(":", 1)[1]
        if entered == password:
            filler_variable = True
            pygame.quit()
            sys.exit()
        else:
            filler_variable = True

    # --- BLOCK:<имя приложения> ---
    elif data.startswith("BLOCK:"):
        app_name = data.split(":", 1)[1].strip()
        if app_name and app_name not in BLOCKED_APPS:
            BLOCKED_APPS.append(app_name)
        filler_variable = True

    # --- UNBLOCK:<имя приложения> ---
    elif data.startswith("UNBLOCK:"):
        app_name = data.split(":", 1)[1].strip()
        if app_name in BLOCKED_APPS:
            BLOCKED_APPS.remove(app_name)
        filler_variable = True
        unlock_achievement("badass_parents")

    elif data == "GET_PENDING":
        print(f"[SOCKET] GET_PENDING, pending_request={pending_request}")
        if pending_request:
            conn.sendall(f"PENDING:{pending_request}".encode())
        else:
            conn.sendall(b"PENDING:NONE")

    # --- GET_HISTORY ---
    elif data == "GET_HISTORY":
        lines = ["HISTORY_START"]
        for entry in timer_history:
            lines.append(f"{entry['duration']}|{entry.get('time', '?')}")
        lines.append("HISTORY_END")
        response = "\n".join(lines)
        conn.sendall(response.encode())

    # --- DISCARD ---
    elif data == "DISCARD":
        cooldown_end = 0
        cooldown_active = False
        if state == "cooldown":
            state = "input"
            timer_input = ""
            current_fact = ""
        print("[SOCKET] Кулдаун сброшен.")

    elif data == "GET_PENDING":
        if pending_request:
            conn.sendall(f"PENDING:{pending_request}".encode())
        else:
            conn.sendall(b"PENDING:NONE")

    elif data == "DISCARD_ACCEPT":
        # Родитель одобрил сброс кулдауна
        cooldown_end = 0
        cooldown_active = False
        if state == "cooldown":
            state = "input"
            timer_input = ""
            current_fact = ""
        pending_request = None
        print("[SOCKET] Родитель одобрил discard.")

    elif data == "DISCARD_DENY":
        pending_request = None
        print("[SOCKET] Родитель отклонил discard.")

    elif data == "FREE_DAY_ACCEPT":
        free_day_active = True
        free_day_date = time.strftime("%d.%m.%Y")
        can_play = True
        pending_request = None
        print("[SOCKET] Родитель одобрил Free Day.")
        unlock_achievement("free_time")

    elif data == "FREE_DAY_DENY":
        pending_request = None
        print("[SOCKET] Родитель отклонил Free Day.")

    # --- FREE_DAY ---
    elif data == "FREE_DAY":
        free_day_active = True
        free_day_date = time.strftime("%d.%m.%Y")
        can_play = True
        filler_variable = True
        unlock_achievement("free_time")

    return False


def socket_server():
    """Принимает команды от родительского приложения (controller)."""
    global socket_conn

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", SESSION_PORT))
    srv.listen(1)
    print(f"[SOCKET] Сервер запущен на 127.0.0.1:{SESSION_PORT}")

    while True:
        conn, addr = srv.accept()
        socket_conn = conn

        # --- АВТОРИЗАЦИЯ ---
        try:
            auth_data = conn.recv(1024).decode()
            # Может прийти несколько строк: AUTH\nCOMMAND
            lines = auth_data.split("\n")
            auth_msg = lines[0].strip()

            if auth_msg != f"AUTH:{SESSION_TOKEN}":
                print(f"[SOCKET] Неверный токен: '{auth_msg}', отключаю")
                conn.close()
                socket_conn = None
                continue

            # Если в буфере уже есть команда — обрабатываем её сразу
            for extra in lines[1:]:
                extra = extra.strip()
                if extra:
                    handle_socket_command(extra, conn)
        except Exception as e:
            print(f"[SOCKET] Ошибка авторизации: {e}")
            conn.close()
            socket_conn = None
            continue

        # --- ОСНОВНОЙ ЦИКЛ ---
        try:
            while True:
                data = conn.recv(1024).decode().strip()
                if not data:
                    break
                handle_socket_command(data, conn)
        except Exception as e:
            print(f"[SOCKET] Ошибка: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
            socket_conn = None

# ============================================================
# ЗВУК
# ============================================================

def play_tone(freq, duration, vol=0.5, wave_type="sine"):
    if freq <= 0:
        time.sleep(duration)
        return

    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t_arr = np.arange(n_samples) / sample_rate

    if wave_type == "sine":
        wave = np.sin(2 * np.pi * freq * t_arr)
    elif wave_type == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t_arr))
    elif wave_type == "saw":
        wave = 2 * (t_arr * freq - np.floor(t_arr * freq + 0.5))
    else:
        wave = np.sin(2 * np.pi * freq * t_arr)

    # Плавное появление / затухание, чтобы не было щелчков
    envelope = np.ones(n_samples)
    fade = int(sample_rate * 0.02)
    if fade > 0 and n_samples > fade * 2:
        envelope[:fade] = np.linspace(0, 1, fade)
        envelope[-fade:] = np.linspace(1, 0, fade)

    buf = (wave * envelope * vol * (volume / 100) * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(np.column_stack((buf, buf)))
    sound.play()


# Каждая звуковая тема = список нот для конца таймера и для конца кулдауна
SOUND_PATTERNS = {
    "Классика": {
        "timer":    [(523, 0.25, 0.30, "square"), (659, 0.25, 0.30, "square"), (784, 0.25, 0.30, "square")],
        "cooldown": [(523, 0.20, 0.35, "saw"), (659, 0.20, 0.35, "saw"), (784, 0.20, 0.35, "saw"), (1047, 0.20, 0.35, "saw")],
    },
    "Джаз": {
        "timer":    [(440, 0.40, 0.25, "sine"), (494, 0.40, 0.25, "sine"), (523, 0.40, 0.25, "sine"), (587, 0.40, 0.25, "sine"), (659, 0.40, 0.25, "sine")],
        "cooldown": [(784, 0.35, 0.25, "sine"), (659, 0.35, 0.25, "sine"), (523, 0.35, 0.25, "sine"), (440, 0.35, 0.25, "sine")],
    },
    "Марио": {
        "timer":    [(659, 0.12, 0.30, "square"), (659, 0.12, 0.30, "square"), (0, 0.12, 0, "sine"), (659, 0.12, 0.30, "square"), (0, 0.12, 0, "sine"), (523, 0.12, 0.30, "square"), (659, 0.12, 0.30, "square"), (784, 0.12, 0.30, "square")],
        "cooldown": [(523, 0.10, 0.30, "square"), (0, 0.10, 0, "sine"), (523, 0.10, 0.30, "square"), (0, 0.10, 0, "sine"), (523, 0.10, 0.30, "square"), (659, 0.10, 0.30, "square"), (784, 0.10, 0.30, "square")],
    },
    "Дождь": {
        "timer":    "rain_timer",
        "cooldown": "rain_cooldown",
    },
    "Оркестр": {
        "timer":    [(262, 0.30, 0.35, "saw"), (330, 0.30, 0.35, "saw"), (392, 0.30, 0.35, "saw"), (523, 0.30, 0.35, "saw"), (659, 0.30, 0.35, "saw"), (784, 0.30, 0.35, "saw")],
        "cooldown": [(196, 0.35, 0.40, "saw"), (262, 0.35, 0.40, "saw"), (330, 0.35, 0.40, "saw"), (392, 0.35, 0.40, "saw"), (523, 0.35, 0.40, "saw")],
    },
}


def _play_rain(loops, freq_min, freq_max, duration, vol):
    for _ in range(loops):
        freq = random.randint(freq_min, freq_max)
        play_tone(freq, duration, vol, "sine")
        time.sleep(0.03)


def sound_timer_end():
    if current_sound_theme == "Тишина":
        return
    pattern = SOUND_PATTERNS.get(current_sound_theme, {}).get("timer")
    if pattern is None:
        return
    if pattern == "rain_timer":
        _play_rain(8, 200, 800, 0.10, 0.10)
        return
    for note in pattern:
        play_tone(*note)
        time.sleep(0.02)


def sound_cooldown_end():
    if current_sound_theme == "Тишина":
        return
    pattern = SOUND_PATTERNS.get(current_sound_theme, {}).get("cooldown")
    if pattern is None:
        return
    if pattern == "rain_cooldown":
        _play_rain(10, 150, 600, 0.12, 0.10)
        return
    for note in pattern:
        play_tone(*note)
        time.sleep(0.02)

# ============================================================
# ЗАГРУЗКА ДАННЫХ И СТАРТ ПОТОКОВ
# ============================================================

ensure_timers_file()
timer_history = load_history()
load_quests()
generate_quests()
load_codes()
load_achievements()
load_signatures()

# Если активирован код темы — применить её при старте
for code in ["Snakey", "PartyLaws", "MyMommaStrict", "CameFromGithub"]:
    if code in ACTIVATED_CODES:
        current_theme = code
        ACCENT = CODE_THEMES[code]
        break

if "IHateThis" in ACTIVATED_CODES:
    timer_speed_mult = 0.9
    cooldown_speed_mult = 1.1

threading.Thread(target=watchdog, daemon=True).start()
threading.Thread(target=socket_server, daemon=True).start()
# Запускаем фоновую музыку текущей темы
play_background_music(current_sound_theme)
# Достижение "Welcome" — при первом запуске
threading.Timer(1.0, lambda: unlock_achievement("welcome")).start()

# ============================================================
# ФУНКЦИИ ОТРИСОВКИ
# ============================================================

def draw_text_with_outline(surface, text, font, center, color, outline_color, outline_width=2):
    base = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    x, y = center
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                surface.blit(outline, outline.get_rect(center=(x + dx, y + dy)))
    surface.blit(base, base.get_rect(center=(x, y)))


def draw_pattern(surface, w, h):
    global anim_offset

    if animate_pattern:
        anim_offset += 0.15

    size = 40

    if current_pattern == "Пусто":
        if animate_pattern:
            pulse = (math.sin(time.time() * 0.5) + 1) / 2
            shade = int(240 + (200 - 240) * pulse)
            surface.fill((shade, shade, shade))
        return

    pattern_color = WHITE if invert_pattern else GRAY_SOFT

    if current_pattern == "Точки":
        if animate_pattern:
            radius = max(1, int(3 + 2 * math.sin(time.time() * 2)))
        else:
            radius = 3
        for x in range(0, w, size):
            for y in range(0, h, size):
                pygame.draw.circle(surface, pattern_color, (x + size // 2, y + size // 2), radius)
        return

    offset = anim_offset % size if animate_pattern else 0

    for x in range(-size, w + size, size):
        for y in range(0, h, size):
            x_shifted = x - offset
            if current_pattern == "Шахматка" and (x // size + y // size) % 2 == 0:
                pygame.draw.rect(surface, pattern_color, (x_shifted, y, size, size))
            elif current_pattern == "Полосы" and (x // size) % 2 == 0:
                pygame.draw.rect(surface, pattern_color, (x_shifted, 0, size, h))
            elif current_pattern == "Ромбы" and (x // size + y // size) % 2 == 0:
                cx = x_shifted + size // 2
                cy = y + size // 2
                pygame.draw.polygon(surface, pattern_color, [
                    (cx, cy - size // 2),
                    (cx + size // 2, cy),
                    (cx, cy + size // 2),
                    (cx - size // 2, cy),
                ])


def draw_fact(surface, w, h, fact):
    if not fact:
        return
    words = fact.split()
    lines, line = [], ""
    for word in words:
        test = line + word + " "
        if font_tiny.size(test)[0] < w - 80:
            line = test
        else:
            lines.append(line)
            line = word + " "
    lines.append(line)

    y = h - 120
    for line in lines:
        text = font_tiny.render(line.strip(), True, GRAY_TEXT)
        surface.blit(text, text.get_rect(center=(w // 2, y)))
        y += 28


def draw_note(surface, w, h, note):
    if not note:
        return
    text = font_small.render(note, True, TEXT_COLOR)
    surface.blit(text, text.get_rect(center=(w // 2, 60)))


def draw_cross(surface, w, h, scale, alpha, shake_x, shake_y):
    size = int(200 * scale)
    if size < 5:
        return
    cross_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    thick = int(size * 0.25)
    offset = int(size * 0.375)
    pygame.draw.rect(cross_surf, (220, 50, 50, alpha), (offset, 0, thick, size))
    pygame.draw.rect(cross_surf, (220, 50, 50, alpha), (0, offset, size, thick))
    cross_surf = pygame.transform.rotate(cross_surf, 45)
    surface.blit(cross_surf, cross_surf.get_rect(center=(w // 2 + shake_x, h // 2 + shake_y)))


def draw_gear(surface, x, y, r, color):
    pygame.draw.circle(surface, color, (x, y), r)
    pygame.draw.circle(surface, WHITE, (x, y), r - 5)
    pygame.draw.circle(surface, color, (x, y), r - 10)
    for i in range(8):
        angle = i * math.pi / 4
        gx = x + int(math.cos(angle) * r)
        gy = y + int(math.sin(angle) * r)
        pygame.draw.circle(surface, color, (gx, gy), 4)


def draw_options_icon(surface, x, y, r, color):
    for i in range(3):
        yy = y - r + i * (r * 0.7) + 4
        pygame.draw.rect(surface, color, (x - r + 4, yy, r * 2 - 8, int(r * 0.5)), border_radius=3)
        pygame.draw.rect(surface, BLACK, (x - r + 4, yy, r * 2 - 8, int(r * 0.5)), 2, border_radius=3)
        pygame.draw.circle(surface, WHITE, (x - r + 8, yy + 3), 2)


def draw_close_button(surface, w):
    cx, cy = w - 55, 105
    pygame.draw.line(surface, BLACK, (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
    pygame.draw.line(surface, BLACK, (cx + 12, cy - 12), (cx - 12, cy + 12), 3)
    return (cx, cy, 20)

running = True
while running:
    w, h = screen.get_size()
    button_center = (w // 2, h // 2 - 150)
    gear_pos = (w - 35, 35)
    gear_radius = 20
    options_pos = (w - 90, 35)
    options_radius = 20

    note_panel_h = 40
    note_panel_total_w = 300
    note_btn_y = h // 2
    note_panel_w = int(note_panel_total_w * note_slide)

    # ========================================================
    # ОБРАБОТКА СОБЫТИЙ
    # ========================================================
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if state == "closing":
                running = False

        # --- ВВОД С КЛАВИАТУРЫ ---
        if event.type == pygame.KEYDOWN:
            if note_active:
                if event.key == pygame.K_BACKSPACE:
                    note_text = note_text[:-1]
                elif event.key == pygame.K_RETURN:
                    note_active = False
                    current_note = note_text
                    note_used = True
                    filler_variable = True
                elif event.key == pygame.K_ESCAPE:
                    note_active = False
                    note_text = ""
                    note_used = True
                elif event.unicode and event.unicode.isprintable() and len(note_text) < 40:
                    note_text += event.unicode
            elif menu_state == "codes":
                if event.key == pygame.K_BACKSPACE:
                    code_input = code_input[:-1]
                elif event.key == pygame.K_RETURN:
                    entered = code_input.strip()
                    if entered:
                        if try_activate_code(entered):
                            code_message = f"Activated: {entered}"
                            code_message_ok = True
                            code_message_until = time.time() + 2.5
                            # Проверка "Sensory overload" — если код дал тему
                            if entered in CODE_THEMES:
                                unlock_achievement("sensory_overload")
                        else:
                            code_message = "Invalid or already used"
                            code_message_ok = False
                            code_message_until = time.time() + 2.5
                    code_input = ""
                elif event.unicode and event.unicode.isprintable() and len(code_input) < 32:
                    code_input += event.unicode
            elif state == "input" and menu_state == "closed":
                if event.key == pygame.K_BACKSPACE:
                    timer_input = timer_input[:-1]
                elif event.unicode and event.unicode.isprintable() and len(timer_input) < 32:
                    timer_input += event.unicode

        # --- КОЛЕСО МЫШИ ---
        if event.type == pygame.MOUSEWHEEL:
            if menu_state == "sound":
                sound_scroll -= event.y * 30
                max_scroll = max(0, len(SOUND_THEMES) * 45 - 190)
                sound_scroll = max(0, min(sound_scroll, max_scroll))
            elif menu_state == "achievements":
                ach_scroll -= event.y * 40
                max_scroll = max(0, len(ACHIEVEMENTS) * 83 - 350)
                ach_scroll = max(0, min(ach_scroll, max_scroll))

        # --- КЛИК МЫШИ ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if state == "input" and menu_state == "closed" and not note_active and not note_used:
                if event.pos[0] > w - 50 and abs(event.pos[1] - note_btn_y) < note_panel_h:
                    note_active = True
                    continue

            if state == "cooldown" and request_btn_rect is not None:
                if request_btn_rect.collidepoint(event.pos):
                    if request_phase == "button":
                        request_phase = "retreating"
                        request_btn_visible = False
                        pending_request = "discard"
                        threading.Thread(target=play_tone, args=(800, 0.1, 0.3, "sine"), daemon=True).start()
                        continue

            if (event.pos[0] - gear_pos[0]) ** 2 + (event.pos[1] - gear_pos[1]) ** 2 <= gear_radius ** 2:
                menu_state = "closed" if menu_state != "closed" else "list"
                sound_scroll = 0

            elif (event.pos[0] - options_pos[0]) ** 2 + (event.pos[1] - options_pos[1]) ** 2 <= options_radius ** 2:
                menu_state = "closed" if menu_state != "closed" else "options_list"

            elif menu_state != "closed":
                close_rect = draw_close_button(screen, w)
                if (event.pos[0] - close_rect[0]) ** 2 + (event.pos[1] - close_rect[1]) ** 2 <= close_rect[2] ** 2:
                    menu_state = "list" if menu_state != "list" else "closed"
                    sound_scroll = 0

                elif menu_state == "options_list":
                    if 60 < event.pos[0] < w - 60 and 180 < event.pos[1] < 235:
                        menu_state = "history"
                        progress_quest("history_opened")
                        unlock_achievement("hidden_cameras")
                    elif 60 < event.pos[0] < w - 60 and 250 < event.pos[1] < 305:
                        free_day_request_pending = True
                        free_day_popup_until = time.time() + 2.0
                        pending_request = "free_day"
                        print("[FREE DAY] Запрос отправлен родителю.")
                    elif 60 < event.pos[0] < w - 60 and 320 < event.pos[1] < 375:
                        menu_state = "quests"
                    elif 60 < event.pos[0] < w - 60 and 390 < event.pos[1] < 445:
                        menu_state = "codes"
                    elif 60 < event.pos[0] < w - 60 and 460 < event.pos[1] < 515:
                        menu_state = "achievements"
                        ach_scroll = 0

                elif menu_state == "list":
                    folders = [("sound", 200), ("themes", 270), ("text", 340), ("patterns", 410), ("langs", 480)]
                    for key, y_pos in folders:
                        if 60 < event.pos[0] < w - 60 and y_pos < event.pos[1] < y_pos + 55:
                            menu_state = key
                            sound_scroll = 0

                elif menu_state == "history":
                    if 60 < event.pos[0] < w - 60 and h - 80 < event.pos[1] < h - 35:
                        export_history_txt()

                elif menu_state == "achievements":
                    if 60 < event.pos[0] < w - 60 and h - 80 < event.pos[1] < h - 35:
                        menu_state = "options_list"

                elif menu_state == "sound":
                    sx, sy, sw = 100, 240, 300
                    if sx - 10 < event.pos[0] < sx + sw + 10 and sy - 20 < event.pos[1] < sy + 20:
                        slider_drag = True
                        volume = max(0, min(100, int((event.pos[0] - sx) / sw * 100)))
                        pygame.mixer.music.set_volume(volume / 100)
                        if current_sound_theme == "Тишина" and volume == 0:
                            unlock_achievement("hunters_dream")
                    else:
                        list_rect = pygame.Rect(60, 320, w - 120, 200)
                        if list_rect.collidepoint(event.pos):
                            list_y = 325 - sound_scroll
                            for name in SOUND_THEMES:
                                if 65 < event.pos[0] < w - 65 and list_y < event.pos[1] < list_y + 40:
                                    if name != current_sound_theme:
                                        progress_quest("sound_changed")
                                    current_sound_theme = name
                                    print(f"[SOUND] Тема: {name}")
                                    threading.Thread(target=play_tone, args=(660, 0.08, 0.2, "sine"), daemon=True).start()

                                    # Меняем фоновую музыку
                                    play_background_music(current_sound_theme)

                                    # --- Достижения ---
                                    if (current_theme != "Классика"
                                        and current_sound_theme != "Классика"
                                        and current_pattern != "Шахматка"):
                                        unlock_achievement("new_looks")

                                    if current_sound_theme == "Тишина" and volume == 0:
                                        unlock_achievement("hunters_dream")
                                list_y += 45

                elif menu_state == "themes":
                    ty = 200
                    available = get_available_themes()
                    for name in available:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 50:
                            if name != current_theme:
                                progress_quest("color_changed")
                            current_theme = name
                            ACCENT = available[name]

                            if name in CODE_THEMES:
                                unlock_achievement("sensory_overload")

                            if (current_theme != "Классика"
                                and current_sound_theme != "Классика"
                                and current_pattern != "Шахматка"):
                                unlock_achievement("new_looks")
                        ty += 65

                elif menu_state == "text":
                    ty = 200
                    for name in TEXT_COLORS:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 50:
                            current_text_color = name
                            TEXT_COLOR = TEXT_COLORS[name]
                        ty += 65

                elif menu_state == "patterns":
                    ty = 200
                    for name in PATTERNS:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 45:
                            current_pattern = name

                            if (current_theme != "Классика"
                                and current_sound_theme != "Классика"
                                and current_pattern != "Шахматка"):
                                unlock_achievement("new_looks")
                        ty += 55
                    if 100 < event.pos[0] < 400 and ty + 10 < event.pos[1] < ty + 55:
                        invert_pattern = not invert_pattern
                    if 100 < event.pos[0] < 400 and ty + 70 < event.pos[1] < ty + 115:
                        animate_pattern = not animate_pattern

                elif menu_state == "langs":
                    ty = 200
                    for name in LANGUAGES:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 45:
                            current_language = name
                        ty += 55

            elif state == "input" and not note_active:
                if (event.pos[0] - button_center[0]) ** 2 + (event.pos[1] - button_center[1]) ** 2 <= 80 ** 2:
                    if timer_input == password:
                        state = "closing"
                        timer_input = ""
                        close_start = time.time()
                        unlock_achievement("cheat_code")
                    elif timer_input:
                        if try_activate_code(timer_input):
                            timer_input = ""
                            if timer_input in CODE_THEMES:
                                unlock_achievement("sensory_overload")
                        else:
                            try:
                                num = int(timer_input[:-1])
                                unit = timer_input[-1]
                                secs = num if unit == "s" else num * 60 if unit == "m" else num * 3600
                                if secs > 7200:
                                    error_until = time.time() + 2
                                    timer_input = ""
                                elif secs > 0:
                                    entered = timer_input
                                    state = "timer"
                                    timer_start = time.time()
                                    timer_seconds = secs
                                    timer_input = ""
                                    can_play = True
                                    cooldown_active = False
                                    current_fact = random.choice(FACTS)
                                    timer_history.append({
                                        "duration": entered,
                                        "time": time.strftime("%H:%M"),
                                        "note": current_note,
                                    })
                                    save_history(timer_history)
                                    progress_quest("timers_count")

                                    # --- Достижения ---
                                    unlock_achievement("first_timer")
                                    if secs == 1:
                                        unlock_achievement("buzzkill")
                                    if len(timer_history) >= 100:
                                        unlock_achievement("pomodoro")
                            except Exception:
                                pass

        if event.type == pygame.MOUSEBUTTONUP:
            slider_drag = False

        if event.type == pygame.MOUSEMOTION and slider_drag and menu_state == "sound":
            sx, sw = 100, 300
            volume = max(0, min(100, int((event.pos[0] - sx) / sw * 100)))
            pygame.mixer.music.set_volume(volume / 100)
            if current_sound_theme == "Тишина" and volume == 0:
                unlock_achievement("hunters_dream")

    # ========================================================
    # ЛОГИКА (НЕ СОБЫТИЯ)
    # ========================================================

    if note_active:
        note_slide = min(1.0, note_slide + 0.15)
    else:
        note_slide = max(0.0, note_slide - 0.15)

    if free_day_request_pending and time.time() > free_day_popup_until:
        free_day_request_pending = False

    # --- Анимация креста ---
    if cross_phase != "idle":
        now_cross = time.time()

        if cross_phase == "falling":
            cross_scale += 0.08
            if cross_scale >= 1.0:
                cross_scale = 1.0
                cross_phase = "shaking"
                cross_start = now_cross
                cross_shake = 10
                threading.Thread(target=play_tone, args=(120, 0.4, 0.5, "saw"), daemon=True).start()
                if pending_state_after_cross is not None:
                    state = pending_state_after_cross
                    pending_state_after_cross = None

        elif cross_phase == "shaking":
            elapsed_shake = now_cross - cross_start
            cross_shake = max(0, int(10 * (1 - elapsed_shake / 0.4)))
            if elapsed_shake >= 0.4:
                cross_phase = "dissolving"
                cross_start = now_cross

        elif cross_phase == "dissolving":
            elapsed_dis = now_cross - cross_start
            cross_alpha = max(0, int(255 * (1 - elapsed_dis / 1.2)))
            if cross_alpha <= 0:
                cross_phase = "idle"
                cross_scale = 0.0
                cross_alpha = 255
                cross_shake = 0

    # --- Таймер: конец -> кулдаун ---
    if state == "timer":
        elapsed = (time.time() - timer_start) * timer_speed_mult
        remaining = max(0, int(timer_seconds - elapsed))
        if remaining <= 0 and cross_phase == "idle":
            base_cooldown = int(timer_seconds * 1.25)
            cooldown_seconds = max(1, int(base_cooldown * cooldown_speed_mult) + cooldown_flat_bonus)
            cooldown_end = time.time() + cooldown_seconds
            can_play = False
            cooldown_active = True
            current_fact = random.choice(FACTS)
            threading.Thread(target=sound_timer_end, daemon=True).start()
            cross_phase = "falling"
            cross_scale = 0.0
            cross_alpha = 255
            pending_state_after_cross = "cooldown"
            note_used = False

            unlock_achievement("first_cooldown")

    # ========================================================
    # ОТРИСОВКА
    # ========================================================

    screen.fill(WHITE)
    draw_pattern(screen, w, h)

    pygame.draw.rect(screen, ACCENT, (0, 0, w, BORDER))
    pygame.draw.rect(screen, ACCENT, (0, h - BORDER, w, BORDER))
    pygame.draw.rect(screen, ACCENT, (0, 0, BORDER, h))
    pygame.draw.rect(screen, ACCENT, (w - BORDER, 0, BORDER, h))

    draw_gear(screen, gear_pos[0], gear_pos[1], gear_radius, ACCENT)
    draw_options_icon(screen, options_pos[0], options_pos[1], options_radius, ACCENT)

    # --- Всплывашка достижения ---
    if achievement_popup_current is None and achievement_popup_queue:
        achievement_popup_current = achievement_popup_queue.pop(0)
        achievement_popup_start = time.time()

    if achievement_popup_current is not None:
        elapsed_pop = time.time() - achievement_popup_start

        if elapsed_pop < 0.4:
            slide = elapsed_pop / 0.4
        elif elapsed_pop < achievement_popup_duration - 0.4:
            slide = 1.0
        elif elapsed_pop < achievement_popup_duration:
            slide = 1.0 - (elapsed_pop - (achievement_popup_duration - 0.4)) / 0.4
        else:
            achievement_popup_current = None
            slide = 0.0

        if achievement_popup_current is not None and slide > 0:
            ach = get_achievement(achievement_popup_current)
            if ach:
                popup_w, popup_h = 320, 80
                popup_x = -popup_w + int((popup_w + 20) * slide)
                popup_y = 20

                popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
                pygame.draw.rect(screen, WHITE, popup_rect, border_radius=10)
                pygame.draw.rect(screen, ACCENT, popup_rect, 3, border_radius=10)

                trophy_x = popup_x + 35
                trophy_y = popup_y + popup_h // 2
                pygame.draw.circle(screen, ACCENT, (trophy_x, trophy_y), 18)
                pygame.draw.circle(screen, WHITE, (trophy_x, trophy_y), 14)
                pygame.draw.circle(screen, ACCENT, (trophy_x, trophy_y), 10)

                head = font_tiny.render("Achievement Unlocked", True, GRAY_TEXT)
                screen.blit(head, (popup_x + 65, popup_y + 10))

                name_t = font_small.render(ach[1], True, BLACK)
                screen.blit(name_t, (popup_x + 65, popup_y + 30))

                quote_t = font_tiny.render(f'"{ach[2]}"', True, GRAY_TEXT)
                screen.blit(quote_t, (popup_x + 65, popup_y + 55))

    # --- Наложения поверх всего ---
    if free_day_request_pending:
        popup_rect = pygame.Rect(60, h // 2 - 40, w - 120, 80)
        pygame.draw.rect(screen, WHITE, popup_rect, border_radius=12)
        pygame.draw.rect(screen, YELLOW, popup_rect, 3, border_radius=12)
        msg1 = font_small.render("Free Day request sent", True, BLACK)
        msg2 = font_tiny.render("Wait for parent approval", True, GRAY_TEXT)
        screen.blit(msg1, msg1.get_rect(center=(w // 2, h // 2 - 10)))
        screen.blit(msg2, msg2.get_rect(center=(w // 2, h // 2 + 20)))

    elif cross_phase != "idle":
        draw_cross(
            screen, w, h, cross_scale, cross_alpha,
            random.randint(-cross_shake, cross_shake),
            random.randint(-cross_shake, cross_shake),
        )

    elif menu_state != "closed":
        pygame.draw.rect(screen, WHITE, (30, 80, w - 60, h - 160), border_radius=12)
        pygame.draw.rect(screen, ACCENT, (30, 80, w - 60, h - 160), 3, border_radius=12)
        draw_close_button(screen, w)

        if menu_state == "list":
            title = font_big.render(t("settings"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 140)))
            folders = [("sound", 200), ("themes", 270), ("text", 340), ("patterns", 410), ("langs", 480)]
            for key, y_pos in folders:
                pygame.draw.rect(screen, WHITE_DARK, (60, y_pos, w - 120, 55), border_radius=8)
                pygame.draw.rect(screen, ACCENT, (60, y_pos, w - 120, 55), 2, border_radius=8)
                text = font_mid.render(t(key), True, BLACK)
                screen.blit(text, text.get_rect(center=(w // 2, y_pos + 28)))

        elif menu_state == "options_list":
            title = font_big.render(t("options"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 120)))

            pygame.draw.rect(screen, WHITE_DARK, (60, 180, w - 120, 55), border_radius=8)
            pygame.draw.rect(screen, ACCENT, (60, 180, w - 120, 55), 2, border_radius=8)
            text = font_mid.render(t("history"), True, BLACK)
            screen.blit(text, text.get_rect(center=(w // 2, 208)))

            pygame.draw.rect(screen, WHITE_DARK, (60, 250, w - 120, 55), border_radius=8)
            if free_day_request_pending:
                fd_color = YELLOW
            elif free_day_active:
                fd_color = GREEN
            else:
                fd_color = ACCENT
            pygame.draw.rect(screen, fd_color, (60, 250, w - 120, 55), 2, border_radius=8)

            if free_day_active:
                fd_label = "Free Day: ACTIVE"
            elif free_day_request_pending:
                fd_label = "Free Day: PENDING"
            else:
                fd_label = "Request Free Day"

            fd_text = font_mid.render(fd_label, True, BLACK)
            screen.blit(fd_text, fd_text.get_rect(center=(w // 2, 278)))

            pygame.draw.rect(screen, WHITE_DARK, (60, 320, w - 120, 55), border_radius=8)
            pygame.draw.rect(screen, ACCENT, (60, 320, w - 120, 55), 2, border_radius=8)
            q_text = font_mid.render(t("quests"), True, BLACK)
            screen.blit(q_text, q_text.get_rect(center=(w // 2, 348)))

            pygame.draw.rect(screen, WHITE_DARK, (60, 390, w - 120, 55), border_radius=8)
            pygame.draw.rect(screen, ACCENT, (60, 390, w - 120, 55), 2, border_radius=8)
            c_text = font_mid.render(t("codes"), True, BLACK)
            screen.blit(c_text, c_text.get_rect(center=(w // 2, 418)))

            pygame.draw.rect(screen, WHITE_DARK, (60, 460, w - 120, 55), border_radius=8)
            pygame.draw.rect(screen, ACCENT, (60, 460, w - 120, 55), 2, border_radius=8)
            a_text = font_mid.render("Achievements", True, BLACK)
            screen.blit(a_text, a_text.get_rect(center=(w // 2, 488)))

        elif menu_state == "achievements":
            title = font_big.render("Achievements", True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 130)))

            total = len(ACHIEVEMENTS)
            got = len(unlocked_achievements)
            counter = font_small.render(f"{got} / {total}", True, GRAY_TEXT)
            screen.blit(counter, counter.get_rect(center=(w // 2, 165)))

            clip_rect = pygame.Rect(30, 190, w - 60, h - 320)
            clip_before = screen.get_clip()
            screen.set_clip(clip_rect)

            y = 200 - ach_scroll
            for ach in ACHIEVEMENTS:
                ach_id, name, quote, desc, obtainable = ach
                unlocked = ach_id in unlocked_achievements

                row_h = 75
                row_rect = pygame.Rect(50, y, w - 100, row_h)

                if y + row_h > 190 and y < h - 130:
                    if unlocked:
                        bg = (230, 255, 230)
                        border = GREEN
                    elif obtainable:
                        bg = WHITE_DARK
                        border = GRAY_TEXT
                    else:
                        bg = (245, 240, 245)
                        border = (200, 180, 200)

                    pygame.draw.rect(screen, bg, row_rect, border_radius=8)
                    pygame.draw.rect(screen, border, row_rect, 2, border_radius=8)

                    name_color = BLACK if (unlocked or obtainable) else GRAY_TEXT
                    name_t = font_small.render(name, True, name_color)
                    screen.blit(name_t, (65, y + 8))

                    quote_t = font_tiny.render(f'"{quote}"', True, GRAY_TEXT)
                    screen.blit(quote_t, (65, y + 32))

                    if unlocked:
                        stat = font_tiny.render("UNLOCKED", True, GREEN)
                    elif obtainable:
                        stat = font_tiny.render("LOCKED", True, GRAY_TEXT)
                    else:
                        stat = font_tiny.render("UNOBTAINABLE", True, (160, 100, 160))
                    screen.blit(stat, stat.get_rect(topright=(w - 65, y + 10)))

                y += row_h + 8

            screen.set_clip(clip_before)

            hint = font_tiny.render("Scroll to see more", True, GRAY_TEXT)
            screen.blit(hint, hint.get_rect(center=(w // 2, h - 100)))

            back_btn = pygame.Rect(60, h - 80, w - 120, 45)
            pygame.draw.rect(screen, ACCENT, back_btn, border_radius=8)
            pygame.draw.rect(screen, BLACK, back_btn, 2, border_radius=8)
            back_t = font_small.render("Back", True, WHITE)
            screen.blit(back_t, back_t.get_rect(center=back_btn.center))

        elif menu_state == "codes":
            title = font_big.render(t("codes"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 130)))

            code_box = pygame.Rect(60, 180, w - 120, 55)
            pygame.draw.rect(screen, WHITE, code_box, border_radius=8)
            pygame.draw.rect(screen, ACCENT, code_box, 3, border_radius=8)

            code_txt = font_small.render(code_input, True, BLACK)
            screen.blit(code_txt, code_txt.get_rect(midleft=(code_box.x + 15, code_box.centery)))

            if (time.time() * 2) % 2 < 1:
                cursor_x = code_box.x + 15 + code_txt.get_width() + 2
                pygame.draw.line(screen, BLACK, (cursor_x, code_box.y + 12), (cursor_x, code_box.bottom - 12), 2)

            if code_message and time.time() < code_message_until:
                msg_color = GREEN if code_message_ok else RED
                msg = font_tiny.render(code_message, True, msg_color)
                screen.blit(msg, msg.get_rect(center=(w // 2, 255)))
            else:
                hint = font_tiny.render("Type code, press Enter", True, GRAY_TEXT)
                screen.blit(hint, hint.get_rect(center=(w // 2, 255)))

            list_title = font_small.render("Activated:", True, BLACK)
            screen.blit(list_title, (60, 290))

            if not ACTIVATED_CODES:
                empty = font_tiny.render("No codes activated yet", True, GRAY_TEXT)
                screen.blit(empty, (60, 320))
            else:
                y = 320
                for code in ACTIVATED_CODES:
                    c_rect = pygame.Rect(60, y, w - 120, 40)
                    pygame.draw.rect(screen, WHITE_DARK, c_rect, border_radius=8)
                    pygame.draw.rect(screen, GREEN, c_rect, 2, border_radius=8)
                    ct = font_small.render(code, True, BLACK)
                    screen.blit(ct, (80, y + 6))
                    y += 50
                    if y > h - 100:
                        break

        elif menu_state == "quests":
            title = font_big.render(t("quests"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 130)))

            date_str = time.strftime("%d.%m.%Y")
            date_text = font_tiny.render(date_str, True, GRAY_TEXT)
            screen.blit(date_text, date_text.get_rect(center=(w // 2, 165)))

            y = 210
            for q in daily_quests:
                label, key, target = q
                prog = quest_progress.get(key, 0)
                done = prog >= target

                q_rect = pygame.Rect(50, y, w - 100, 70)
                pygame.draw.rect(screen, WHITE_DARK, q_rect, border_radius=10)
                if done:
                    pygame.draw.rect(screen, GREEN, q_rect, 3, border_radius=10)
                else:
                    pygame.draw.rect(screen, ACCENT, q_rect, 2, border_radius=10)

                name_t = font_small.render(label, True, BLACK)
                screen.blit(name_t, (65, y + 10))

                prog_text = f"{prog} / {target}"
                if done:
                    prog_text += "  done!"
                prog_s = font_tiny.render(prog_text, True, GRAY_TEXT if not done else GREEN)
                screen.blit(prog_s, (65, y + 42))
                y += 85

        elif menu_state == "history":
            title = font_mid.render(t("history"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 120)))

            stats = get_history_stats()
            stats_rect = pygame.Rect(50, 155, w - 100, 95)
            pygame.draw.rect(screen, WHITE_DARK, stats_rect, border_radius=10)
            pygame.draw.rect(screen, ACCENT, stats_rect, 2, border_radius=10)

            s1 = font_tiny.render(f"Total: {stats['total']} timers", True, BLACK)
            s2 = font_tiny.render(f"Average: {stats['avg']}", True, BLACK)
            s3 = font_tiny.render(f"Most common: {stats['most_common']} ({stats['most_count']}x)", True, BLACK)
            screen.blit(s1, (65, 168))
            screen.blit(s2, (65, 192))
            screen.blit(s3, (65, 216))

            y = 265
            for entry in timer_history[-10:]:
                line = f"{entry.get('duration', '?')}  -  {entry.get('time', '?')}"
                text = font_tiny.render(line, True, TEXT_COLOR)
                screen.blit(text, (60, y))
                y += 26
                if y > h - 110:
                    break

            pygame.draw.rect(screen, ACCENT, (60, h - 80, w - 120, 45), border_radius=8)
            pygame.draw.rect(screen, BLACK, (60, h - 80, w - 120, 45), 2, border_radius=8)
            export_text = font_small.render("Export TXT", True, WHITE)
            screen.blit(export_text, export_text.get_rect(center=(w // 2, h - 58)))

        elif menu_state == "sound":
            title = font_mid.render(t("sound"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 130)))

            lbl = font_small.render(t("volume"), True, BLACK)
            screen.blit(lbl, (60, 200))

            sx, sy, sw = 100, 240, 300
            pygame.draw.rect(screen, WHITE_DARK, (sx, sy - 5, sw, 10), border_radius=5)
            pygame.draw.rect(screen, ACCENT, (sx, sy - 5, int(sw * volume / 100), 10), border_radius=5)
            pygame.draw.circle(screen, ACCENT, (sx + int(sw * volume / 100), sy), 12)
            pygame.draw.circle(screen, BLACK, (sx + int(sw * volume / 100), sy), 12, 2)
            vt = font_tiny.render(f"{volume}", True, BLACK)
            screen.blit(vt, (sx + sw + 20, sy - 10))

            lbl2 = font_small.render("Sound Theme", True, BLACK)
            screen.blit(lbl2, (60, 290))

            list_rect = pygame.Rect(60, 320, w - 120, 200)
            pygame.draw.rect(screen, WHITE_DARK, list_rect, border_radius=8)
            pygame.draw.rect(screen, BLACK, list_rect, 2, border_radius=8)

            clip_before = screen.get_clip()
            screen.set_clip(list_rect)

            list_y = 325 - sound_scroll
            for name in SOUND_THEMES:
                item_rect = pygame.Rect(65, list_y, w - 130, 40)
                if name == current_sound_theme:
                    pygame.draw.rect(screen, ACCENT, item_rect, border_radius=6)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (80, list_y + 8))
                list_y += 45

            screen.set_clip(clip_before)

            hint = font_tiny.render("Scroll to see more", True, GRAY_TEXT)
            screen.blit(hint, hint.get_rect(center=(w // 2, h - 75)))

        elif menu_state == "themes":
            title = font_mid.render(t("themes"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("choose_theme"), True, BLACK)
            screen.blit(lbl, (60, 175))

            ty = 200
            for name, color in get_available_themes().items():
                pygame.draw.rect(screen, WHITE_DARK, (100, ty, 300, 50), border_radius=8)
                if name == current_theme:
                    pygame.draw.rect(screen, ACCENT, (100, ty, 300, 50), 3, border_radius=8)
                pygame.draw.rect(screen, color, (110, ty + 10, 30, 30), border_radius=4)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 12))
                ty += 65

        elif menu_state == "text":
            title = font_mid.render(t("text"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("choose_text"), True, BLACK)
            screen.blit(lbl, (60, 175))

            ty = 200
            for name, color in TEXT_COLORS.items():
                pygame.draw.rect(screen, WHITE_DARK, (100, ty, 300, 50), border_radius=8)
                if name == current_text_color:
                    pygame.draw.rect(screen, ACCENT, (100, ty, 300, 50), 3, border_radius=8)
                pygame.draw.rect(screen, color, (110, ty + 10, 30, 30), border_radius=4)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 12))
                ty += 65

        elif menu_state == "patterns":
            title = font_mid.render(t("patterns"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("choose_pattern"), True, BLACK)
            screen.blit(lbl, (60, 175))

            ty = 200
            for name in PATTERNS:
                pygame.draw.rect(screen, WHITE_DARK, (100, ty, 300, 45), border_radius=8)
                if name == current_pattern:
                    pygame.draw.rect(screen, ACCENT, (100, ty, 300, 45), 3, border_radius=8)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 10))
                ty += 55

            pygame.draw.rect(screen, WHITE_DARK, (100, ty + 10, 300, 45), border_radius=8)
            if invert_pattern:
                pygame.draw.rect(screen, ACCENT, (100, ty + 10, 300, 45), 3, border_radius=8)
            it = font_small.render(t("inversion"), True, BLACK)
            screen.blit(it, (160, ty + 20))

            pygame.draw.rect(screen, WHITE_DARK, (100, ty + 70, 300, 45), border_radius=8)
            if animate_pattern:
                pygame.draw.rect(screen, ACCENT, (100, ty + 70, 300, 45), 3, border_radius=8)
            at = font_small.render(t("animation"), True, BLACK)
            screen.blit(at, (160, ty + 80))

        elif menu_state == "langs":
            title = font_mid.render(t("langs"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("language"), True, BLACK)
            screen.blit(lbl, (60, 175))

            ty = 200
            for name in LANGUAGES:
                pygame.draw.rect(screen, WHITE_DARK, (100, ty, 300, 45), border_radius=8)
                if name == current_language:
                    pygame.draw.rect(screen, ACCENT, (100, ty, 300, 45), 3, border_radius=8)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 10))
                ty += 55

    else:
        if state == "input":
            label = font_big.render(t("timer_label"), True, TEXT_COLOR)
            screen.blit(label, label.get_rect(center=(w // 2, h // 2 + 20)))

            bw, bh = 300, 60
            bx = (w - bw) // 2
            by = h // 2 + 80
            pygame.draw.rect(screen, ACCENT, (bx - 3, by - 3, bw + 6, bh + 6), border_radius=6)
            pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), border_radius=6)

            txt = font_mid.render(timer_input, True, TEXT_COLOR)
            screen.blit(txt, txt.get_rect(midleft=(bx + 15, by + bh // 2)))

            if (time.time() * 2) % 2 < 1:
                cursor_x = bx + 15 + txt.get_width() + 2
                pygame.draw.line(screen, TEXT_COLOR, (cursor_x, by + 10), (cursor_x, by + bh - 10), 2)

            if time.time() < error_until:
                e1 = font_small.render(t("too_much"), True, RED)
                e2 = font_small.render(t("max_2h"), True, RED)
                screen.blit(e1, e1.get_rect(center=(w // 2, h // 2 + 180)))
                screen.blit(e2, e2.get_rect(center=(w // 2, h // 2 + 210)))

            if not note_used:
                panel_rect = pygame.Rect(
                    w - note_panel_w - 30,
                    note_btn_y - note_panel_h // 2,
                    note_panel_w + 30,
                    note_panel_h,
                )
                pygame.draw.rect(screen, WHITE, panel_rect, border_radius=8)
                pygame.draw.rect(screen, YELLOW, panel_rect, 3, border_radius=8)

                if note_panel_w > 100:
                    preview = note_text if note_active and note_text else (current_note if current_note else "Note...")
                    pcol = BLACK if (note_active and note_text) or current_note else GRAY_TEXT
                    ptext = font_tiny.render(preview, True, pcol)
                    screen.blit(ptext, ptext.get_rect(midleft=(panel_rect.x + 15, panel_rect.centery)))

                arrow_pts = [
                    (w - 6, note_btn_y - 12),
                    (w - 6, note_btn_y + 12),
                    (w - 22, note_btn_y),
                ]
                pygame.draw.polygon(screen, YELLOW, arrow_pts)
                pygame.draw.polygon(screen, BLACK, arrow_pts, 2)

        elif state == "timer":
            elapsed = (time.time() - timer_start) * timer_speed_mult
            remaining = max(0, int(timer_seconds - elapsed))

            hh = remaining // 3600
            mm = (remaining % 3600) // 60
            ss = remaining % 60
            time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

            if remaining > 60:
                timer_color = TEXT_COLOR
                shake = 0
            elif remaining > 30:
                timer_color = YELLOW
                shake = 0
            elif remaining > 10:
                timer_color = ORANGE
                shake = 0
            else:
                timer_color = RED
                shake = random.randint(-2, 2)

            txt = font_big.render(time_str, True, timer_color)
            screen.blit(txt, txt.get_rect(center=(w // 2 + shake, h // 2 - 20 + shake)))

            draw_fact(screen, w, h, current_fact)
            draw_note(screen, w, h, current_note)

        elif state == "cooldown":
            cooldown_active = True
            remaining = max(0, int(cooldown_end - time.time()))

            if cooldown_start_time == 0:
                cooldown_start_time = time.time()

            now = time.time()

            if request_phase == "idle" and not request_used and now - cooldown_start_time >= 5:
                request_phase = "button"
                request_phase_time = now
                request_btn_visible = True
                request_used = True

            if request_btn_visible and request_btn_slide < 1.0:
                request_btn_slide = min(1.0, request_btn_slide + 0.03)
            elif not request_btn_visible and request_btn_slide > 0.0:
                request_btn_slide = max(0.0, request_btn_slide - 0.03)

            if request_phase == "retreating" and request_btn_slide <= 0.0:
                request_phase = "waiting"
                request_phase_time = now
            elif request_phase == "waiting" and now - request_phase_time >= 0.5:
                request_phase = "msg"
                request_phase_time = now
                request_btn_visible = True
            elif request_phase == "msg" and now - request_phase_time >= 2.0:
                request_phase = "msg_retreating"
                request_btn_visible = False
            elif request_phase == "msg_retreating" and request_btn_slide <= 0.0:
                request_phase = "idle"

            if remaining <= 0:
                state = "input"
                timer_input = ""
                current_fact = ""
                cooldown_active = False
                cooldown_start_time = 0.0
                request_btn_visible = False
                request_btn_slide = 0.0
                request_btn_rect = None
                request_phase = "idle"
                request_used = False
                note_used = False
                threading.Thread(target=sound_cooldown_end, daemon=True).start()
            else:
                hh = remaining // 3600
                mm = (remaining % 3600) // 60
                ss = remaining % 60

                label = font_big.render(t("cooldown"), True, RED)
                screen.blit(label, label.get_rect(center=(w // 2, h // 2 - 60)))

                txt = font_big.render(f"{hh:02d}:{mm:02d}:{ss:02d}", True, TEXT_COLOR)
                screen.blit(txt, txt.get_rect(center=(w // 2, h // 2 + 10)))

                hint = font_small.render(t("no_play"), True, RED)
                screen.blit(hint, hint.get_rect(center=(w // 2, h // 2 + 70)))

                draw_fact(screen, w, h, current_fact)
                draw_note(screen, w, h, current_note)

                if request_btn_slide > 0.0 and request_phase in ("button", "retreating", "msg", "msg_retreating"):
                    btn_w, btn_h = 260, 50
                    target_x = 20
                    btn_x = target_x - int((1.0 - request_btn_slide) * (btn_w + 40))
                    btn_y = h - 100

                    if request_phase in ("button", "retreating"):
                        pygame.draw.rect(screen, ACCENT, (btn_x, btn_y, btn_w, btn_h), border_radius=8)
                        pygame.draw.rect(screen, BLACK, (btn_x, btn_y, btn_w, btn_h), 2, border_radius=8)
                        draw_text_with_outline(
                            screen, "Request Discard", font_small,
                            (btn_x + btn_w // 2, btn_y + btn_h // 2), WHITE, BLACK,
                        )
                        request_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

                    elif request_phase in ("msg", "msg_retreating"):
                        pygame.draw.rect(screen, ACCENT, (btn_x, btn_y, btn_w, btn_h), border_radius=8)
                        draw_text_with_outline(
                            screen, "Request sent. Please wait...", font_small,
                            (btn_x + btn_w // 2, btn_y + btn_h // 2), WHITE, BLACK,
                        )
                        request_btn_rect = None
                else:
                    request_btn_rect = None

        elif state == "closing":
            label = font_big.render(t("closing1"), True, TEXT_COLOR)
            screen.blit(label, label.get_rect(center=(w // 2, h // 2 - 80)))

            label2a = font_mid.render(t("closing2a"), True, TEXT_COLOR)
            screen.blit(label2a, label2a.get_rect(center=(w // 2, h // 2 - 20)))

            label2b = font_mid.render(t("closing2b"), True, TEXT_COLOR)
            screen.blit(label2b, label2b.get_rect(center=(w // 2, h // 2 + 20)))

            label3 = font_mid.render(t("closing3"), True, TEXT_COLOR)
            screen.blit(label3, label3.get_rect(center=(w // 2, h // 2 + 80)))

            if time.time() - close_start >= 6:
                running = False

        if state == "input":
            mouse_pos = pygame.mouse.get_pos()
            dist = (mouse_pos[0] - button_center[0]) ** 2 + (mouse_pos[1] - button_center[1]) ** 2

            btn_pressed = False
            if event.type == pygame.MOUSEBUTTONDOWN and dist <= 80 ** 2:
                btn_pressed = True
            if event.type == pygame.MOUSEBUTTONUP:
                btn_pressed = False

            if btn_pressed:
                current_radius = 75
                inner_color = WHITE_DARK
            elif dist <= 80 ** 2:
                current_radius = 80
                inner_color = WHITE_DARK
            else:
                current_radius = 80
                inner_color = WHITE

            pygame.draw.circle(screen, ACCENT, button_center, current_radius)
            pygame.draw.circle(screen, inner_color, button_center, current_radius - 5)

            btn_text = font_big.render(t("start"), True, TEXT_COLOR)
            screen.blit(btn_text, btn_text.get_rect(center=button_center))

    pygame.display.flip()

pygame.quit()
sys.exit()