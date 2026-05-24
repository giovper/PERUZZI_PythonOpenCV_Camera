import cv2
import numpy as np
from camera import GenericCamera, CameraManager

#schermata iniziale:
TILE_W = 320    #larghezza anteprima singola camera
TILE_H = 240    #altezza anteprima singola camera
PAD = 24        #margine tra elementi
HEADER_H = 72   #altezza fascia titolo in cima
TEXT_H = 84     #altezza fascia testo sotto ogni tile
BG = (25, 25, 25) #colore background
FONT = cv2.FONT_HERSHEY_SIMPLEX


def put_centered(img, text: str, cx: int, y: int,
                 font_scale: float, color: tuple, thickness: int = 1) -> None:
    (tw, th), _ = cv2.getTextSize(text, FONT, font_scale, thickness)
    cv2.putText(img, text, (cx - tw // 2, y + th),
                FONT, font_scale, color, thickness, cv2.LINE_AA)


def show_startup_screen() -> 'GenericCamera | None': # messa tra virtgolette perché GenericCamera è definita in un altro file (camera.py) e Python a volte le richede per evitare errori di riferimento circolare
    functional = CameraManager.get_all_cameras()

    usb_cams = [c for c in functional if c.source != "picamera"]
    pi_in_list = next((c for c in functional if c.source == "picamera"), None)

    #Pi Camera: funzionante o placeholder rosso
    if pi_in_list is not None:
        pi_display = pi_in_list
        pi_placeholder = None
    else:
        pi_placeholder = GenericCamera("picamera")
        pi_display = pi_placeholder

    display_cams = usb_cams + [pi_display]
    n = len(display_cams)

    win_w = PAD + n * (TILE_W + PAD)
    win_h = HEADER_H + PAD + TILE_H + TEXT_H + PAD

    win_name = "Seleziona Camera"
    cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)

    #Tasti numerici: solo le camera funzionanti
    key_map: dict[int, int] = {}
    camera_keys: list = []
    key_index = 0
    for i, cam in enumerate(display_cams):
        if cam.is_available():
            camera_keys.append(key_index)
            key_map[ord(str(key_index))] = i
            key_index += 1
        else:
            camera_keys.append(None)

    selected_cam = None

    while True:
        canvas = np.full((win_h, win_w, 3), BG, dtype=np.uint8)

        # Header
        put_centered(canvas, "FILTRI WEBCAM - Seleziona una camera",
                      win_w // 2, (HEADER_H - 36) // 2, 0.7, (200, 200, 200), 1)
        put_centered(canvas, "Premi il numero della camera desiderata  |  Q = esci",
                      win_w // 2, HEADER_H - 32, 0.42, (110, 110, 110), 1)

        for i, cam in enumerate(display_cams):
            tx = PAD + i * (TILE_W + PAD)
            ty = HEADER_H + PAD
            available = cam.is_available()

            if available:
                ok, frame = cam.read()
                if ok and frame is not None:
                    canvas[ty:ty + TILE_H, tx:tx + TILE_W] = cv2.resize(frame, (TILE_W, TILE_H))
                else:
                    canvas[ty:ty + TILE_H, tx:tx + TILE_W] = (40, 40, 40)
            else:
                canvas[ty:ty + TILE_H, tx:tx + TILE_W] = (0, 0, 255)  # rosso pieno BGR

            border_color = (0, 200, 0) if available else (0, 0, 180)
            cv2.rectangle(canvas, (tx, ty), (tx + TILE_W, ty + TILE_H), border_color, 2)

            cx   = tx + TILE_W // 2
            ty_t = ty + TILE_H + 8

            put_centered(canvas, cam.name, cx, ty_t, 0.55, (210, 210, 210), 1)

            if available:
                put_centered(canvas, "(disponibile)", cx, ty_t + 24, 0.44, (60, 200, 60), 1)
            else:
                put_centered(canvas, "(non disponibile)", cx, ty_t + 24, 0.44, (80, 80, 200), 1)

            cam_key = camera_keys[i]
            if cam_key is not None:
                put_centered(canvas, f"[ {cam_key} ]", cx, ty_t + 50, 0.65, (0, 220, 220), 2)

        cv2.imshow(win_name, canvas)

        key = cv2.waitKey(30) & 0xFF

        if key in (ord('q'), ord('Q'), 27):
            break

        if key in key_map:
            selected_cam = display_cams[key_map[key]]
            break

    cv2.destroyWindow(win_name)

    if pi_placeholder is not None:
        pi_placeholder.release()

    for cam in functional:
        if cam is not selected_cam:
            cam.release()

    return selected_cam


#Main Window

SLOT_NAMES = ["MODIFICATORI", "COLORE", "VOLTO"]

HUD_X = 10 #posizione dell'angolo in alto a sx dell'hub (coi valori e stats)
HUD_Y = 10
HUD_ALPHA = 0.55

NAV_H = 130 #altezza barra bassa
NAV_ALPHA = 0.65


def semi_rect(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int,
               color: tuple, alpha: float) -> None: #aggiungi un rettangolo semitrasparente sul frame
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_hud(frame: np.ndarray, fps: float, face_count: int,
             slot_names: list, active_slot: int, vcam_status: str = "",
             auto_mode: bool = False) -> None:

    vcam_color = (0, 220, 100) if vcam_status == "attiva" else (80, 80, 200) if "vcam" in vcam_status else (100, 100, 100)
    auto_color = (0, 220, 100) if auto_mode else (100, 100, 100)
    lines = [
        (f"FPS: {fps:.1f}", 0.5, (0, 230, 230), 1),
        (f"Volti: {face_count}", 0.5, (200, 200, 200), 1),
        (f"VCam: {vcam_status}", 0.45, vcam_color, 1),
        (f"X auto: {'ON' if auto_mode else 'OFF'}", 0.45, auto_color, 1),
        ("", 0.4, (0, 0, 0), 0),
        (f"[1] {slot_names[0]}", 0.45, (180, 180, 255), 1),
        (f"[2] {slot_names[1]}", 0.45, (180, 255, 180), 1),
        (f"[3] {slot_names[2]}", 0.45, (255, 200, 180), 1),
        ("", 0.4, (0, 0, 0), 0),
        ("WASD naviga  O/P intens.", 0.38, (120, 120, 120), 1),
        ("E foto  R rec  Q esci", 0.38, (120, 120, 120), 1),
    ]

    line_h = 20
    box_w  = 230
    box_h  = len(lines) * line_h + 12

    semi_rect(frame, HUD_X, HUD_Y, HUD_X + box_w, HUD_Y + box_h, (0, 0, 0), HUD_ALPHA)

    y = HUD_Y + line_h
    for text, scale, color, thick in lines:
        if text:
            cv2.putText(frame, text, (HUD_X + 8, y), FONT,
                        scale, color, thick, cv2.LINE_AA)
        y += line_h


def draw_nav_bar(frame: np.ndarray, slot_lists: list,
                 slot_indices: list, active_slot: int,
                 slot_effects: list) -> None: #modifica frame in place, agigunge barra 3 colonnein basso
    H, W = frame.shape[:2]
    bar_y = H - NAV_H
    semi_rect(frame, 0, bar_y, W, H, (0, 0, 0), NAV_ALPHA)

    col_w = W // 3

    for slot_i, (effect_list, idx, effect_obj) in enumerate( #disegna 3 slot
            zip(slot_lists, slot_indices, slot_effects)):

        x_off = slot_i * col_w
        cx = x_off + col_w // 2
        is_active = (slot_i == active_slot)

        #  Header slot
        header_col = (0, 220, 220) if is_active else (120, 120, 120)
        put_centered(frame, SLOT_NAMES[slot_i], cx, bar_y + 6, 0.48, header_col, 1)

        #  Effetto precedente
        prev_idx = (idx - 1) % len(effect_list)
        prev_name = effect_list[prev_idx][0]
        put_centered(frame, f"^ {prev_name}", cx, bar_y + 30, 0.40, (100, 100, 100), 1)

        #  Effetto corrente 
        curr_name = effect_list[idx][0]
        curr_col = (0, 220, 220) if is_active else (200, 200, 200)
        put_centered(frame, curr_name, cx, bar_y + 56, 0.52, curr_col, 2 if is_active else 1)

        #  Effetto successivo o barra intensità
        if slot_i == 0 and hasattr(effect_obj, 'intensity'):
            lvl = effect_obj.intensity
            bar = "#" * lvl + "-" * (2 - lvl)
            put_centered(frame, f"[{bar}]", cx, bar_y + 84, 0.50, (0, 180, 255), 1)
        else:
            next_idx= (idx + 1) % len(effect_list)
            next_name = effect_list[next_idx][0]
            put_centered(frame, f"v {next_name}", cx, bar_y + 84, 0.40, (100, 100, 100), 1)


        if slot_i < 2:
            cv2.line(frame, (x_off + col_w, bar_y + 4), (x_off + col_w, H - 4),
                     (70, 70, 70), 1)


def draw_rec_indicator(frame: np.ndarray) -> None: #disegna bordo rosso spesso
    H, W = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (W - 1, H - 1), (0, 0, 220), 6)
    cv2.circle(frame, (W - 40, 22), 10, (0, 0, 255), -1)
    cv2.putText(frame, "REC", (W - 26, 28), FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)


def draw_screenshot_flash(frame: np.ndarray) -> None: #disegna bordo bianco
    H, W = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (W - 1, H - 1), (255, 255, 255), 8)
