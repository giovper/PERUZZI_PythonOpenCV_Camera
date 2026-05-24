import cv2
import numpy as np
import os
import time
from datetime import datetime

try:
    import pyvirtualcam
except ImportError:
    pyvirtualcam = None

from camera import GenericCamera
from ui import (show_startup_screen,
                draw_hud, draw_nav_bar, draw_rec_indicator, draw_screenshot_flash)
from effects import (
    Nessuno,
    FlipH, FlipV, SpecchioSx, SpecchioDx, SpecchioSu, SpecchioGiu,
    SpecchioTagliato, Caleidoscopio, Fisheye, Pixellato, Vignettatura,
    Grigi, Negativo, Sepia, Termico, Fumetto, Halftone, PopArt,
    RilevamentoMovimento, Ghost, GhostRGB, MotionBlur, Neve, Subacqueo,
    SfondoBlur, Cappello, Occhiali, Maschera, Etichetta,
)

# ── Definizione degli slot ────────────────────────────────────────────────────
# Ogni voce è (nome_visualizzato, classe_effetto)

SLOT1 = [
    ("Nessuno", Nessuno),
    ("Flip H", FlipH),
    ("Flip V", FlipV),
    ("Specchio Sx", SpecchioSx),
    ("Specchio Dx", SpecchioDx),
    ("Specchio Su", SpecchioSu),
    ("Specchio Giu", SpecchioGiu),
    ("Spec. Tagliato", SpecchioTagliato),
    ("Caleidoscopio", Caleidoscopio),
    ("Fisheye", Fisheye),
    ("Pixellato", Pixellato),
    ("Vignettatura", Vignettatura),
]

SLOT2 = [
    ("Nessuno", Nessuno),
    ("Grigi", Grigi),
    ("Negativo", Negativo),
    ("Sepia", Sepia),
    ("Termico", Termico),
    ("Fumetto", Fumetto),
    ("Halftone", Halftone),
    ("Pop Art", PopArt),
    ("Movimento", RilevamentoMovimento),
    ("Ghost", Ghost),
    ("Ghost RGB", GhostRGB),
    ("MotionBlur", MotionBlur),
    ("Neve", Neve),
    ("Subacqueo", Subacqueo),
]

SLOT3 = [
    ("Nessuno", Nessuno),
    ("Sfondo Blur", SfondoBlur),
    ("Cappello", Cappello),
    ("Occhiali", Occhiali),
    ("Maschera", Maschera),
    ("Etichetta", Etichetta),
]

ALL_SLOTS = [SLOT1, SLOT2, SLOT3]


# ── Letterbox ─────────────────────────────────────────────────────────────────

def letterbox(frame, win_w: int, win_h: int): #ridimenisona il frame agiungendo bande nere per raggiungere win_w e win_h della finestra, mantenendo il rapporto del frame
    h, w = frame.shape[:2]
    scale = min(win_w / w, win_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(frame, (new_w, new_h))
    canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
    x_off = (win_w - new_w) // 2
    y_off = (win_h - new_h) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


def run_main(camera: GenericCamera) -> None:
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml' # venv/lib/python3.14/site-packages/cv2/data/ nome_cascade
    face_cascade = cv2.CascadeClassifier(cascade_path)

    slot_indices = [0, 0, 0]
    slot_effects = [SLOT1[0][1](), SLOT2[0][1](), SLOT3[0][1]()] # ("Nessuno", Nessuno)[0] è l'oggetto da instanziare

    active_slot = 0
    is_recording = False
    video_writer = None
    screenshot_flash = 0

    vcam = None
    if camera.is_virtual:
        vcam_status = "no (input vcam)"
    elif pyvirtualcam is None:
        vcam_status = "no driver"
    else:
        try:
            vcam = pyvirtualcam.Camera(width=1280, height=720, fps=30)
            vcam_status = "attiva"
        except Exception:
            vcam_status = "no driver"

    fps_prev_time = time.perf_counter()
    fps = 0.0

    WIN = "Filtri Webcam"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 1280, 720)

    while True:
        ok, frame = camera.read()
        if not ok or frame is None:
            break

        frame = cv2.resize(frame, (1280, 720))

        #Face detection su frame ridotto per velocità
        gray_small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (640, 360))
        raw_faces  = face_cascade.detectMultiScale(
            gray_small, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        faces = [(x * 2, y * 2, w * 2, h * 2)
                 for (x, y, w, h) in raw_faces] if len(raw_faces) > 0 else []

        #effetti: Slot3, poi 1, poi 2
        result = slot_effects[2].apply(frame, faces)
        result = slot_effects[0].apply(result)
        result = slot_effects[1].apply(result)

        now = time.perf_counter()
        fps = 1.0 / (now - fps_prev_time)
        fps_prev_time = now

        effect_names = [SLOT1[slot_indices[0]][0],
                        SLOT2[slot_indices[1]][0],
                        SLOT3[slot_indices[2]][0]]

        # vcam e recording usano il frame pulito (senza UI)
        if vcam is not None:
            vcam.send(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        if is_recording:
            video_writer.write(result)

        # disegna UI su una copia separata
        display = result.copy()
        draw_hud(display, fps, len(faces), effect_names, active_slot, vcam_status)
        draw_nav_bar(display, ALL_SLOTS, slot_indices, active_slot, slot_effects)
        if is_recording:
            draw_rec_indicator(display)
        if screenshot_flash > 0:
            draw_screenshot_flash(display)
            screenshot_flash -= 1

        # letterbox per finestra ridimensionabile
        try:
            _, _, win_w, win_h = cv2.getWindowImageRect(WIN)
            if win_w > 10 and win_h > 10:
                display = letterbox(display, win_w, win_h)
        except Exception:
            pass

        cv2.imshow(WIN, display)

        #Se chiude la finestra
        if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            break

        # Input
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('q'), ord('Q')):
            break

        elif key in (ord('a'), ord('A')):
            active_slot = max(0, active_slot - 1)

        elif key in (ord('d'), ord('D')):
            active_slot = min(2, active_slot + 1)

        elif key in (ord('w'), ord('W')):
            effect_list = ALL_SLOTS[active_slot]
            slot_indices[active_slot] = (slot_indices[active_slot] - 1) % len(effect_list)
            slot_effects[active_slot] = effect_list[slot_indices[active_slot]][1]()

        elif key in (ord('s'), ord('S')):
            effect_list = ALL_SLOTS[active_slot]
            slot_indices[active_slot] = (slot_indices[active_slot] + 1) % len(effect_list)
            slot_effects[active_slot] = effect_list[slot_indices[active_slot]][1]()

        elif key in (ord('o'), ord('O')):
            if active_slot == 0 and hasattr(slot_effects[0], 'intensity'):
                slot_effects[0].intensity = min(2, slot_effects[0].intensity + 1)

        elif key in (ord('p'), ord('P')):
            if active_slot == 0 and hasattr(slot_effects[0], 'intensity'):
                slot_effects[0].intensity = max(1, slot_effects[0].intensity - 1)

        elif key in (ord('e'), ord('E')):
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = os.path.join('screenshots', f'screen_{ts}.jpg')
            cv2.imwrite(path, result)
            screenshot_flash = 6 # per 6 frame

        elif key in (ord('r'), ord('R')):
            if not is_recording:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join('recordings', f'rec_{ts}.mp4')
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(path, fourcc, 30.0, (1280, 720))
                is_recording = True
            else:
                video_writer.release()
                video_writer = None
                is_recording = False

    #chiusura
    if is_recording and video_writer is not None:
        video_writer.release() #perchè quando il programma termina con Q, se stava registrando bisogna chiudere correttamente il file video, altirmenti viene corrotto
    if vcam is not None:
        vcam.close()
    cv2.destroyWindow(WIN)




def main():
    selected = show_startup_screen()
    if selected is None:
        return
    
    os.makedirs('screenshots', exist_ok=True)
    os.makedirs('recordings',  exist_ok=True)
    run_main(selected)
    selected.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
