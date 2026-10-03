import pygame
import sys
import socket
import time
import math
import numpy as np
import json
import os


pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

W, H = 500, 700
screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("PBcontrol")

WHITE = (255, 255, 255)
WHITE_DARK = (230, 230, 230)
GRAY_SOFT = (240, 240, 240)
GRAY_TEXT = (100, 100, 100)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
GREEN = (100, 220, 100)
BORDER = 10

font_big = pygame.font.Font(None, 48)
font_mid = pygame.font.Font(None, 36)
font_small = pygame.font.Font(None, 30)
font_tiny = pygame.font.Font(None, 24)

THEMES = {
    "Классика": (255, 215, 0),
    "Фиолетовая": (180, 100, 255),
    "Зелёная": (100, 220, 120),
    "Синяя": (100, 160, 255),
}
current_theme = "Классика"
ACCENT = THEMES[current_theme]

TEXT_COLORS = {
    "Чёрный": (0, 0, 0),
    "Серый": (100, 100, 100),
    "Тёмно-синий": (20, 40, 90),
    "Тёмно-фиолетовый": (70, 30, 110),
}
current_text_color = "Чёрный"
TEXT_COLOR = TEXT_COLORS[current_text_color]

PATTERNS = ["Шахматка", "Полосы", "Точки", "Ромбы", "Пусто"]
current_pattern = "Шахматка"
invert_pattern = False

LANGUAGES = ["Русский", "English", "Deutsch", "Français", "Español"]
current_language = "Русский"

TRANSLATIONS = {
    "Русский": {"settings": "Настройки", "sound": "Звук", "themes": "Темы", "text": "Текст",
                "patterns": "Узоры", "langs": "Языки", "volume": "Громкость", "history": "История",
                "choose_theme": "Выберите тему", "choose_text": "Цвет текста",
                "choose_pattern": "Узор фона", "inversion": "Инверсия", "language": "Язык"},
    "English": {"settings": "Settings", "sound": "Sound", "themes": "Themes", "text": "Text",
                "patterns": "Patterns", "langs": "Languages", "volume": "Volume", "history": "History",
                "choose_theme": "Choose theme", "choose_text": "Text color",
                "choose_pattern": "Background pattern", "inversion": "Inversion", "language": "Language"},
    "Deutsch": {"settings": "Einstellungen", "sound": "Ton", "themes": "Themen", "text": "Text",
                "patterns": "Muster", "langs": "Sprachen", "volume": "Lautstärke", "history": "Verlauf",
                "choose_theme": "Thema wählen", "choose_text": "Textfarbe",
                "choose_pattern": "Hintergrundmuster", "inversion": "Inversion", "language": "Sprache"},
    "Français": {"settings": "Paramètres", "sound": "Son", "themes": "Thèmes", "text": "Texte",
                 "patterns": "Motifs", "langs": "Langues", "volume": "Volume", "history": "Historique",
                 "choose_theme": "Choisir un thème", "choose_text": "Couleur du texte",
                 "choose_pattern": "Motif de fond", "inversion": "Inversion", "language": "Langue"},
    "Español": {"settings": "Ajustes", "sound": "Sonido", "themes": "Temas", "text": "Texto",
                "patterns": "Patrones", "langs": "Idiomas", "volume": "Volumen", "history": "Historial",
                "choose_theme": "Elige tema", "choose_text": "Color del texto",
                "choose_pattern": "Patrón de fondo", "inversion": "Inversión", "language": "Idioma"},
}

def t(key):
    return TRANSLATIONS[current_language].get(key, key)

volume = 75
slider_drag = False
menu_state = "closed"
history_cache = None
history_scroll = 0

pending_request = None
request_popup_slide = 0.0
accept_button_rect = None
deny_button_rect = None

OPTIONS = ["Lock", "Set Password", "Close", "Block", "Unblock", "Discard", "Free Day"]
current_option = 0

text_anim_offset = 0.0
text_anim_alpha = 255
button_pressed = False

menu_fade = 0.0
menu_target = 0.0

socket_status = "disconnected"
last_socket_check = 0.0

input_mode = False
input_text = ""
input_action = ""
input_error = ""
input_error_until = 0
status_message = ""
status_message_until = 0

HOST = "127.0.0.1"
PORT = 9900  # заглушка, реальный порт читается из pb_session.json
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pb_session.json")

def load_session():
    """Читает порт и токен из pb_session.json."""
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def play_key_sound():
    sr = 44100
    duration = 0.04
    n = int(sr * duration)
    t_arr = np.arange(n) / sr
    wave = np.sin(2 * np.pi * 800 * t_arr) * np.exp(-t_arr * 60)
    buf = (wave * 0.2 * (volume / 100) * 32767).astype(np.int16)
    stereo = np.column_stack((buf, buf))
    sound = pygame.sndarray.make_sound(stereo)
    sound.play()


def send_command(command):
    session = load_session()
    if not session:
        print("[CONTROL] Main not running (no session file)")
        return False
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1.0)
        client.connect((HOST, session["port"]))
        client.sendall(f"AUTH:{session['token']}\n".encode())
        client.sendall(command.encode())
        client.close()
        return True
    except Exception as e:
        print(f"[CONTROL] Send failed: {e}")
        return False


def ping_child():
    session = load_session()
    print(f"[PING] session={session}")
    if not session:
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        s.connect((HOST, session["port"]))
        s.close()
        print(f"[PING] OK, port={session['port']}")
        return True
    except Exception as e:
        print(f"[PING] FAIL: {e}")
        return False


def check_pending_request():
    """Опрашивает main на предмет запросов от ребёнка."""
    global pending_request
    
    session = load_session()
    if not session:
        pending_request = None
        return
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.sendall(f"AUTH:{session['token']}\n".encode())
        client.settimeout(1.0)
        client.connect((HOST, session["port"]))
        client.sendall(f"AUTH:{session['token']}".encode())
        client.sendall(b"GET_PENDING")
        response = client.recv(1024).decode().strip()
        client.close()
        print(f"[PARENT] GET_PENDING → {response}")
        if response.startswith("PENDING:"):
            req = response.split(":", 1)[1]
            if req == "NONE":
                pending_request = None
            else:
                pending_request = req
    except Exception as e:
        print(f"[PARENT] check_pending error: {e}")
        pending_request = None


def get_history():
    session = load_session()
    if not session:
        print("[PARENT] Main not running (no session file)")
        return None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(3.0)
        client.connect((HOST, session["port"]))
        client.sendall(f"AUTH:{session['token']}".encode())
        client.sendall(b"GET_HISTORY\n")
        client.sendall(f"AUTH:{session['token']}\n".encode())

        buffer = b""
        while b"HISTORY_END" not in buffer:
            chunk = client.recv(1024)
            if not chunk:
                break
            buffer += chunk

        client.close()

        text = buffer.decode()
        lines = text.split("\n")

        try:
            start = lines.index("HISTORY_START")
            end = lines.index("HISTORY_END")
        except ValueError:
            print("[PARENT] Некорректный ответ от основы")
            return None

        history = []
        for line in lines[start + 1:end]:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) == 2:
                history.append({"duration": parts[0], "time": parts[1]})
        return history

    except Exception as e:
        print(f"[PARENT] Ошибка получения истории: {e}")
        return None


def validate_lock(value):
    if len(value) < 2:
        return False, "Format: 10m / 30s / 1h"
    try:
        num = int(value[:-1])
    except ValueError:
        return False, "Format: 10m / 30s / 1h"
    unit = value[-1].lower()
    if unit not in ("s", "m", "h"):
        return False, "Use s, m or h!"
    secs = num if unit == "s" else num * 60 if unit == "m" else num * 3600
    if secs <= 0:
        return False, "Must be > 0"
    if secs > 7200:
        return False, "Max 2 hours!"
    return True, ""


def draw_pattern(surface, w, h):
    if current_pattern == "Пусто":
        return
    size = 40
    pattern_color = WHITE if invert_pattern else GRAY_SOFT
    for x in range(0, w, size):
        for y in range(0, h, size):
            if current_pattern == "Шахматка" and (x // size + y // size) % 2 == 0:
                pygame.draw.rect(surface, pattern_color, (x, y, size, size))
            elif current_pattern == "Полосы" and (x // size) % 2 == 0:
                pygame.draw.rect(surface, pattern_color, (x, 0, size, h))
            elif current_pattern == "Точки":
                pygame.draw.circle(surface, pattern_color, (x + size // 2, y + size // 2), 3)
            elif current_pattern == "Ромбы" and (x // size + y // size) % 2 == 0:
                pygame.draw.polygon(surface, pattern_color, [
                    (x + size // 2, y), (x + size, y + size // 2),
                    (x + size // 2, y + size), (x, y + size // 2)
                ])


def draw_gear(surface, x, y, r, color):
    pygame.draw.circle(surface, color, (x, y), r)
    pygame.draw.circle(surface, WHITE, (x, y), r - 5)
    pygame.draw.circle(surface, color, (x, y), r - 10)
    for i in range(8):
        angle = i * math.pi / 4
        gx = x + int(math.cos(angle) * r)
        gy = y + int(math.sin(angle) * r)
        pygame.draw.circle(surface, color, (gx, gy), 4)


def draw_close_button(surface, w):
    cx, cy = w - 55, 105
    pygame.draw.line(surface, BLACK, (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
    pygame.draw.line(surface, BLACK, (cx + 12, cy - 12), (cx - 12, cy + 12), 3)
    return (cx, cy, 20)


def draw_icon(surface, x, y, option):
    color = ACCENT
    if option == "Lock":
        pygame.draw.rect(surface, color, (x - 10, y - 2, 20, 16), 2, border_radius=3)
        pygame.draw.arc(surface, color, (x - 7, y - 12, 14, 14), 0, 3.15, 2)
    elif option == "Set Password":
        pygame.draw.circle(surface, color, (x - 4, y - 4), 5, 2)
        pygame.draw.line(surface, color, (x - 1, y - 1), (x + 8, y + 8), 2)
        pygame.draw.line(surface, color, (x + 4, y + 4), (x + 6, y + 2), 2)
        pygame.draw.line(surface, color, (x + 6, y + 6), (x + 8, y + 4), 2)
    elif option == "Close":
        pygame.draw.line(surface, color, (x - 8, y - 8), (x + 8, y + 8), 3)
        pygame.draw.line(surface, color, (x + 8, y - 8), (x - 8, y + 8), 3)
    elif option == "Block":
        pygame.draw.circle(surface, color, (x, y), 9, 2)
        pygame.draw.line(surface, color, (x - 6, y - 6), (x + 6, y + 6), 2)
    elif option == "Unblock":
        pygame.draw.line(surface, color, (x - 8, y), (x - 3, y + 6), 3)
        pygame.draw.line(surface, color, (x - 3, y + 6), (x + 8, y - 6), 3)
    elif option == "Discard":
        pygame.draw.polygon(surface, color, [(x + 6, y - 8), (x + 6, y + 8), (x - 4, y)])
        pygame.draw.line(surface, color, (x - 10, y), (x + 2, y), 3)
    elif option == "Free Day":
        pygame.draw.circle(surface, color, (x, y), 7, 2)
        for i in range(8):
            angle = i * math.pi / 4
            sx = x + int(math.cos(angle) * 11)
            sy = y + int(math.sin(angle) * 11)
            ex = x + int(math.cos(angle) * 13)
            ey = y + int(math.sin(angle) * 13)
            pygame.draw.line(surface, color, (sx, sy), (ex, ey), 2)


def draw_folder_icon(surface, x, y, key):
    color = ACCENT
    if key == "sound":
        pygame.draw.polygon(surface, color, [(x - 8, y - 4), (x - 3, y - 4), (x + 2, y - 9), (x + 2, y + 9), (x - 3, y + 4), (x - 8, y + 4)])
        pygame.draw.arc(surface, color, (x + 2, y - 8, 10, 16), -1.0, 1.0, 2)
    elif key == "themes":
        pygame.draw.circle(surface, color, (x, y), 9, 2)
        pygame.draw.circle(surface, color, (x - 3, y - 3), 2)
        pygame.draw.circle(surface, color, (x + 3, y - 3), 2)
        pygame.draw.circle(surface, color, (x, y + 3), 2)
    elif key == "text":
        pygame.draw.line(surface, color, (x - 8, y - 7), (x + 8, y - 7), 3)
        pygame.draw.line(surface, color, (x, y - 7), (x, y + 8), 3)
    elif key == "patterns":
        pygame.draw.rect(surface, color, (x - 8, y - 8, 7, 7), 2)
        pygame.draw.rect(surface, color, (x + 1, y - 8, 7, 7), 2)
        pygame.draw.rect(surface, color, (x - 8, y + 1, 7, 7), 2)
        pygame.draw.rect(surface, color, (x + 1, y + 1, 7, 7), 2)
    elif key == "langs":
        pygame.draw.circle(surface, color, (x, y), 9, 2)
        pygame.draw.line(surface, color, (x - 9, y), (x + 9, y), 2)
        pygame.draw.ellipse(surface, color, (x - 5, y - 9, 10, 18), 2)
    elif key == "history":
        pygame.draw.circle(surface, color, (x, y), 9, 2)
        pygame.draw.line(surface, color, (x, y), (x, y - 5), 2)
        pygame.draw.line(surface, color, (x, y), (x + 4, y + 2), 2)


running = True
while running:
    now = time.time()

    if now - last_socket_check >= 1.0:
        last_socket_check = now
        socket_status = "connected" if ping_child() else "disconnected"
        if socket_status == "connected":
            check_pending_request()
        else:
            pending_request = None

    w, h = screen.get_size()
    button_center = (w // 2, h // 2 - 100)
    button_radius = 80
    text_y = h // 2 + 80
    left_arrow_rect = pygame.Rect(w // 2 - 180, text_y - 25, 50, 50)
    right_arrow_rect = pygame.Rect(w // 2 + 130, text_y - 25, 50, 50)
    gear_pos = (w - 35, 35)
    gear_radius = 20

    menu_target = 0.0 if menu_state == "closed" else 1.0
    if menu_fade < menu_target:
        menu_fade = min(menu_target, menu_fade + 0.15)
    elif menu_fade > menu_target:
        menu_fade = max(menu_target, menu_fade - 0.15)

    request_target = 1.0 if pending_request else 0.0
    if request_popup_slide < request_target:
        request_popup_slide = min(request_target, request_popup_slide + 0.12)
    elif request_popup_slide > request_target:
        request_popup_slide = max(request_target, request_popup_slide - 0.12)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and input_mode:
            if event.key == pygame.K_RETURN:
                cmd = input_action
                value = input_text.strip()
                ok = False

                if cmd == "Lock":
                    valid, err = validate_lock(value)
                    if not valid:
                        input_error = err
                        input_error_until = time.time() + 2
                    else:
                        ok = send_command(f"LOCK:{value}")
                        if not ok:
                            input_error = "Base not running!"
                            input_error_until = time.time() + 2
                elif cmd == "Set Password":
                    if not value:
                        input_error = "Password can't be empty!"
                        input_error_until = time.time() + 2
                    else:
                        ok = send_command(f"SETPASSWORD:{value}")
                        if not ok:
                            input_error = "Base not running!"
                            input_error_until = time.time() + 2
                elif cmd == "Close":
                    if not value:
                        input_error = "Enter password (default CL0SE)"
                        input_error_until = time.time() + 2
                    else:
                        ok = send_command(f"CLOSE:{value}")
                        if not ok:
                            input_error = "Base not running!"
                            input_error_until = time.time() + 2
                        else:
                            status_message = "Close sent."
                            status_message_until = time.time() + 3
                elif cmd == "Block":
                    if not value:
                        input_error = "Enter app name!"
                        input_error_until = time.time() + 2
                    else:
                        ok = send_command(f"BLOCK:{value}")
                        if not ok:
                            input_error = "Base not running!"
                            input_error_until = time.time() + 2
                elif cmd == "Unblock":
                    if not value:
                        input_error = "Enter app name!"
                        input_error_until = time.time() + 2
                    else:
                        ok = send_command(f"UNBLOCK:{value}")
                        if not ok:
                            input_error = "Base not running!"
                            input_error_until = time.time() + 2
                elif cmd == "Discard":
                    ok = send_command("DISCARD")
                    if not ok:
                        input_error = "Base not running!"
                        input_error_until = time.time() + 2

                if ok:
                    input_mode = False
                    input_text = ""
                    input_error = ""

            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_ESCAPE:
                input_mode = False
                input_text = ""
                input_error = ""
            else:
                if event.unicode and event.unicode.isprintable() and len(input_text) < 20:
                    input_text += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if pending_request and accept_button_rect and deny_button_rect:
                if accept_button_rect.collidepoint(event.pos):
                    if pending_request == "discard":
                        send_command("DISCARD_ACCEPT")
                    else:
                        send_command("FREE_DAY_ACCEPT")
                    pending_request = None
                    continue
                elif deny_button_rect.collidepoint(event.pos):
                    if pending_request == "discard":
                        send_command("DISCARD_DENY")
                    else:
                        send_command("FREE_DAY_DENY")
                    pending_request = None
                    continue

            if input_mode:
                box_rect = pygame.Rect(w // 2 - 150, h // 2 + 40, 300, 60)
                if not box_rect.collidepoint(event.pos):
                    input_mode = False
                    input_text = ""
                    input_error = ""

            elif (event.pos[0] - gear_pos[0]) ** 2 + (event.pos[1] - gear_pos[1]) ** 2 <= gear_radius ** 2:
                menu_state = "closed" if menu_state != "closed" else "list"
                history_cache = None

            elif menu_state != "closed":
                close_rect = draw_close_button(screen, w)
                if (event.pos[0] - close_rect[0]) ** 2 + (event.pos[1] - close_rect[1]) ** 2 <= close_rect[2] ** 2:
                    menu_state = "list" if menu_state != "list" else "closed"
                    history_cache = None

                elif menu_state == "list":
                    folders = [("sound", 200), ("themes", 270), ("text", 340), ("patterns", 410), ("langs", 480), ("history", 550)]
                    for key, y_pos in folders:
                        if 60 < event.pos[0] < w - 60 and y_pos < event.pos[1] < y_pos + 55:
                            menu_state = key
                            if key == "history":
                                history_cache = None
                                history_scroll = 0

                elif menu_state == "sound":
                    sx, sy, sw = 100, 350, 300
                    if sx - 10 < event.pos[0] < sx + sw + 10 and sy - 20 < event.pos[1] < sy + 20:
                        slider_drag = True
                        volume = max(0, min(100, int((event.pos[0] - sx) / sw * 100)))

                elif menu_state == "themes":
                    ty = 200
                    for name in THEMES:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 50:
                            current_theme = name
                            ACCENT = THEMES[name]
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
                        ty += 55
                    if 100 < event.pos[0] < 400 and ty + 10 < event.pos[1] < ty + 55:
                        invert_pattern = not invert_pattern

                elif menu_state == "langs":
                    ty = 200
                    for name in LANGUAGES:
                        if 100 < event.pos[0] < 400 and ty < event.pos[1] < ty + 45:
                            current_language = name
                        ty += 55

            else:
                if left_arrow_rect.collidepoint(event.pos):
                    current_option = (current_option - 1) % len(OPTIONS)
                    text_anim_offset = -30
                    text_anim_alpha = 0
                    play_key_sound()
                elif right_arrow_rect.collidepoint(event.pos):
                    current_option = (current_option + 1) % len(OPTIONS)
                    text_anim_offset = 30
                    text_anim_alpha = 0
                    play_key_sound()
                elif (event.pos[0] - button_center[0]) ** 2 + (event.pos[1] - button_center[1]) ** 2 <= button_radius ** 2:
                    button_pressed = True
                    cmd = OPTIONS[current_option]

                    if cmd in ["Lock", "Set Password", "Close", "Block", "Unblock"]:
                        input_mode = True
                        input_action = cmd
                        input_text = ""
                        input_error = ""
                    elif cmd == "Discard":
                        ok = send_command("DISCARD")
                        if ok:
                            status_message = "Cooldown discarded."
                            status_message_until = time.time() + 3
                        else:
                            status_message = "Base not running!"
                            status_message_until = time.time() + 3
                    elif cmd == "Free Day":
                        ok = send_command("FREE_DAY")
                        if ok:
                            status_message = "Free Day granted."
                            status_message_until = time.time() + 3
                        else:
                            status_message = "Base not running!"
                            status_message_until = time.time() + 3

        if event.type == pygame.MOUSEBUTTONUP:
            slider_drag = False
            button_pressed = False

        if event.type == pygame.MOUSEMOTION and slider_drag and menu_state == "sound":
            sx, sw = 100, 300
            volume = max(0, min(100, int((event.pos[0] - sx) / sw * 100)))

        if event.type == pygame.MOUSEWHEEL:
            if menu_state == "history" and history_cache:
                max_scroll = max(0, len(history_cache) * 30 - (h - 250) + 20)
                history_scroll -= event.y * 30
                history_scroll = max(0, min(history_scroll, max_scroll))

    if text_anim_alpha < 255:
        text_anim_alpha = min(255, text_anim_alpha + 6)
    if text_anim_offset != 0:
        if text_anim_offset > 0:
            text_anim_offset = max(0, text_anim_offset - 0.5)
        else:
            text_anim_offset = min(0, text_anim_offset + 0.5)

    screen.fill(GRAY_SOFT if invert_pattern else WHITE)
    draw_pattern(screen, w, h)
    pygame.draw.rect(screen, ACCENT, (0, 0, w, BORDER))
    pygame.draw.rect(screen, ACCENT, (0, h - BORDER, w, BORDER))
    pygame.draw.rect(screen, ACCENT, (0, 0, BORDER, h))
    pygame.draw.rect(screen, ACCENT, (w - BORDER, 0, BORDER, h))

    draw_gear(screen, gear_pos[0], gear_pos[1], gear_radius, ACCENT)

    status_color = GREEN if socket_status == "connected" else RED
    status_text = font_tiny.render(
        "SOCKET: CONNECTED" if socket_status == "connected" else "SOCKET: DISCONNECTED",
        True, status_color
    )
    screen.blit(status_text, (15, 15))

    if status_message and time.time() < status_message_until:
        sm = font_tiny.render(status_message, True, GRAY_TEXT)
        screen.blit(sm, sm.get_rect(center=(w // 2, h - 25)))

    if menu_fade > 0.0:
        menu_alpha = int(255 * menu_fade)
        menu_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        menu_surf.fill((0, 0, 0, 0))

        panel_rect = pygame.Rect(30, 80, w - 60, h - 160)
        pygame.draw.rect(menu_surf, (*WHITE, menu_alpha), panel_rect, border_radius=12)
        pygame.draw.rect(menu_surf, (*ACCENT, menu_alpha), panel_rect, 3, border_radius=12)

        cx, cy = w - 55, 105
        pygame.draw.line(menu_surf, (*BLACK, menu_alpha), (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
        pygame.draw.line(menu_surf, (*BLACK, menu_alpha), (cx + 12, cy - 12), (cx - 12, cy + 12), 3)

        screen.blit(menu_surf, (0, 0))

        if menu_state == "list":
            title = font_big.render(t("settings"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 140)))
            folders = [("sound", 200), ("themes", 270), ("text", 340), ("patterns", 410), ("langs", 480), ("history", 550)]
            for key, y_pos in folders:
                rect = pygame.Rect(60, y_pos, w - 120, 55)
                pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
                pygame.draw.rect(screen, ACCENT, rect, 2, border_radius=8)
                draw_folder_icon(screen, 90, y_pos + 28, key)
                text = font_mid.render(t(key), True, BLACK)
                screen.blit(text, text.get_rect(center=(w // 2 + 20, y_pos + 28)))

        elif menu_state == "sound":
            title = font_mid.render(t("sound"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("volume"), True, BLACK)
            screen.blit(lbl, (60, 300))
            sx, sy, sw = 100, 350, 300
            pygame.draw.rect(screen, WHITE_DARK, (sx, sy - 5, sw, 10), border_radius=5)
            pygame.draw.rect(screen, ACCENT, (sx, sy - 5, int(sw * volume / 100), 10), border_radius=5)
            pygame.draw.circle(screen, ACCENT, (sx + int(sw * volume / 100), sy), 12)
            pygame.draw.circle(screen, BLACK, (sx + int(sw * volume / 100), sy), 12, 2)
            vt = font_tiny.render(f"{volume}", True, BLACK)
            screen.blit(vt, (sx + sw + 20, sy - 10))

        elif menu_state == "themes":
            title = font_mid.render(t("themes"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("choose_theme"), True, BLACK)
            screen.blit(lbl, (60, 175))
            ty = 200
            for name, color in THEMES.items():
                rect = pygame.Rect(100, ty, 300, 50)
                pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
                if name == current_theme:
                    pygame.draw.rect(screen, ACCENT, rect, 3, border_radius=8)
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
                rect = pygame.Rect(100, ty, 300, 50)
                pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
                if name == current_text_color:
                    pygame.draw.rect(screen, ACCENT, rect, 3, border_radius=8)
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
                rect = pygame.Rect(100, ty, 300, 45)
                pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
                if name == current_pattern:
                    pygame.draw.rect(screen, ACCENT, rect, 3, border_radius=8)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 10))
                ty += 55
            rect = pygame.Rect(100, ty + 10, 300, 45)
            pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
            if invert_pattern:
                pygame.draw.rect(screen, ACCENT, rect, 3, border_radius=8)
            it = font_small.render(t("inversion"), True, BLACK)
            screen.blit(it, (160, ty + 20))

        elif menu_state == "langs":
            title = font_mid.render(t("langs"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))
            lbl = font_small.render(t("language"), True, BLACK)
            screen.blit(lbl, (60, 175))
            ty = 200
            for name in LANGUAGES:
                rect = pygame.Rect(100, ty, 300, 45)
                pygame.draw.rect(screen, WHITE_DARK, rect, border_radius=8)
                if name == current_language:
                    pygame.draw.rect(screen, ACCENT, rect, 3, border_radius=8)
                tn = font_small.render(name, True, BLACK)
                screen.blit(tn, (160, ty + 10))
                ty += 55

        elif menu_state == "history":
            title = font_mid.render(t("history"), True, BLACK)
            screen.blit(title, title.get_rect(center=(w // 2, 150)))

            if history_cache is None:
                history_cache = get_history()

            if history_cache is None:
                err = font_small.render("No connection to Base", True, RED)
                screen.blit(err, err.get_rect(center=(w // 2, h // 2)))
            elif len(history_cache) == 0:
                empty = font_small.render("No timers yet", True, GRAY_TEXT)
                screen.blit(empty, empty.get_rect(center=(w // 2, h // 2)))
            else:
                list_rect = pygame.Rect(50, 185, w - 100, h - 290)
                pygame.draw.rect(screen, WHITE_DARK, list_rect, border_radius=10)
                pygame.draw.rect(screen, ACCENT, list_rect, 2, border_radius=10)

                clip_before = screen.get_clip()
                screen.set_clip(list_rect)

                y = list_rect.y + 10 - history_scroll
                for entry in reversed(history_cache):
                    line = f"{entry.get('duration', '?')}  —  {entry.get('time', '?')}"
                    text = font_tiny.render(line, True, TEXT_COLOR)
                    screen.blit(text, (list_rect.x + 15, y))
                    y += 30

                screen.set_clip(clip_before)

                total_h = len(history_cache) * 30
                visible_h = list_rect.h
                if total_h > visible_h:
                    bar_h = max(30, int(visible_h * visible_h / total_h))
                    scroll_ratio = history_scroll / max(1, (total_h - visible_h))
                    bar_y = list_rect.y + int((visible_h - bar_h) * scroll_ratio)
                    pygame.draw.rect(screen, ACCENT, (list_rect.right - 8, bar_y, 4, bar_h), border_radius=2)

                hint = font_tiny.render("Scroll with mouse wheel", True, GRAY_TEXT)
                screen.blit(hint, hint.get_rect(center=(w // 2, h - 110)))

    elif input_mode:
        title = font_mid.render(input_action, True, TEXT_COLOR)
        screen.blit(title, title.get_rect(center=(w // 2, h // 2 - 60)))

        if input_action == "Lock":
            hint_text = "Format: 10m, 30s, 1h (max 2h)"
        elif input_action == "Set Password":
            hint_text = "New password for Base"
        elif input_action == "Close":
            hint_text = "Enter Base's password (default CL0SE)"
        elif input_action == "Block":
            hint_text = "App name, e.g. Roblox"
        elif input_action == "Unblock":
            hint_text = "App name to unblock"
        else:
            hint_text = ""
        if hint_text:
            ht = font_tiny.render(hint_text, True, GRAY_TEXT)
            screen.blit(ht, ht.get_rect(center=(w // 2, h // 2 - 25)))

        box_rect = pygame.Rect(w // 2 - 150, h // 2 + 40, 300, 60)
        pygame.draw.rect(screen, ACCENT, (box_rect.x - 3, box_rect.y - 3, box_rect.w + 6, box_rect.h + 6), border_radius=8)
        pygame.draw.rect(screen, WHITE, box_rect, border_radius=8)

        txt = font_mid.render(input_text, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(midleft=(box_rect.x + 15, box_rect.centery)))

        if (time.time() * 2) % 2 < 1:
            cursor_x = box_rect.x + 15 + txt.get_width() + 2
            pygame.draw.line(screen, TEXT_COLOR, (cursor_x, box_rect.y + 10), (cursor_x, box_rect.bottom - 10), 2)

        hint = font_tiny.render("Enter — send, Esc — cancel", True, GRAY_TEXT)
        screen.blit(hint, hint.get_rect(center=(w // 2, h // 2 + 130)))

        if time.time() < input_error_until:
            err = font_small.render(input_error, True, RED)
            screen.blit(err, err.get_rect(center=(w // 2, h // 2 + 170)))

    else:
        mouse_pos = pygame.mouse.get_pos()
        dist = (mouse_pos[0] - button_center[0]) ** 2 + (mouse_pos[1] - button_center[1]) ** 2

        if dist <= button_radius ** 2:
            inner_color = WHITE_DARK
        else:
            inner_color = WHITE

        current_radius = button_radius - 5 if button_pressed else button_radius
        pygame.draw.circle(screen, ACCENT, button_center, current_radius)
        pygame.draw.circle(screen, inner_color, button_center, current_radius - 5)

        btn_text = font_big.render("GO", True, TEXT_COLOR)
        screen.blit(btn_text, btn_text.get_rect(center=button_center))

        draw_icon(screen, w // 2 - 100 + int(text_anim_offset), text_y, OPTIONS[current_option])
        option_surface = font_mid.render(OPTIONS[current_option], True, TEXT_COLOR)
        option_surface.set_alpha(int(text_anim_alpha))
        option_rect = option_surface.get_rect(center=(w // 2 + 10 + int(text_anim_offset), text_y))
        screen.blit(option_surface, option_rect)

        pygame.draw.polygon(screen, ACCENT, [
            (left_arrow_rect.right, left_arrow_rect.top),
            (left_arrow_rect.right, left_arrow_rect.bottom),
            (left_arrow_rect.left, left_arrow_rect.centery)
        ])
        pygame.draw.polygon(screen, BLACK, [
            (left_arrow_rect.right, left_arrow_rect.top),
            (left_arrow_rect.right, left_arrow_rect.bottom),
            (left_arrow_rect.left, left_arrow_rect.centery)
        ], 3)

        pygame.draw.polygon(screen, ACCENT, [
            (right_arrow_rect.left, right_arrow_rect.top),
            (right_arrow_rect.left, right_arrow_rect.bottom),
            (right_arrow_rect.right, right_arrow_rect.centery)
        ])
        pygame.draw.polygon(screen, BLACK, [
            (right_arrow_rect.left, right_arrow_rect.top),
            (right_arrow_rect.left, right_arrow_rect.bottom),
            (right_arrow_rect.right, right_arrow_rect.centery)
        ], 3)

    # --- Попап запроса от ребёнка ---
    if request_popup_slide > 0.0 and pending_request:
        popup_w = w - 60
        popup_h = 130
        target_y = 90
        popup_y = target_y - int((1.0 - request_popup_slide) * (popup_h + 100))
        popup_x = 30

        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        pygame.draw.rect(screen, WHITE, popup_rect, border_radius=14)
        pygame.draw.rect(screen, ACCENT, popup_rect, 3, border_radius=14)

        if pending_request == "discard":
            text = "Your child wants to discard cooldown."
        else:
            text = "Your child wants a Free Day."

        msg = font_small.render(text, True, BLACK)
        screen.blit(msg, msg.get_rect(center=(w // 2, popup_y + 35)))

        btn_w = 100
        btn_h = 40
        btn_y = popup_y + 75
        accept_rect = pygame.Rect(w // 2 - btn_w - 10, btn_y, btn_w, btn_h)
        deny_rect = pygame.Rect(w // 2 + 10, btn_y, btn_w, btn_h)

        pygame.draw.rect(screen, GREEN, accept_rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, accept_rect, 2, border_radius=8)
        acc_text = font_small.render("Accept", True, BLACK)
        screen.blit(acc_text, acc_text.get_rect(center=accept_rect.center))

        pygame.draw.rect(screen, RED, deny_rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, deny_rect, 2, border_radius=8)
        den_text = font_small.render("Deny", True, WHITE)
        screen.blit(den_text, den_text.get_rect(center=deny_rect.center))

        accept_button_rect = accept_rect
        deny_button_rect = deny_rect

    pygame.display.flip()

pygame.quit()
sys.exit()