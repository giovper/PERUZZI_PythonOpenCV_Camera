import cv2
import numpy as np
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')


def load_asset(filename: str) -> np.ndarray:
    path = os.path.join(ASSETS_DIR, filename)
    return cv2.imread(path, cv2.IMREAD_UNCHANGED)


def overlay_png(frame: np.ndarray, img: np.ndarray,
                cx: int, cy: int, ow: int, oh: int) -> np.ndarray:
    if ow <= 0 or oh <= 0:
        return frame

    if img.shape[2] == 3:
        img = np.concatenate(
            [img, np.full((*img.shape[:2], 1), 255, dtype=np.uint8)], axis=2
        )

    img = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_AREA)
    x1, y1 = cx - ow // 2, cy - oh // 2
    x2, y2 = x1 + ow, y1 + oh
    H, W = frame.shape[:2]

    fx1, fy1 = max(0, x1), max(0, y1)
    fx2, fy2 = min(W, x2), min(H, y2)
    if fx1 >= fx2 or fy1 >= fy2:
        return frame

    ix1, iy1 = fx1 - x1, fy1 - y1
    ix2, iy2 = ix1 + (fx2 - fx1), iy1 + (fy2 - fy1)

    crop = img[iy1:iy2, ix1:ix2]
    alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
    roi = frame[fy1:fy2, fx1:fx2].astype(np.float32)
    blended = roi * (1 - alpha) + crop[:, :, :3].astype(np.float32) * alpha
    frame[fy1:fy2, fx1:fx2] = blended.clip(0, 255).astype(np.uint8)
    return frame


class SfondoBlur:
    # Applica GaussianBlur sull'intero frame; le regioni dei volti vengono mantenute nitide.
    def apply(self, frame, faces=None):
        out = cv2.GaussianBlur(frame, (51, 51), 0)
        if faces:
            pad = 24
            H, W = frame.shape[:2]
            for (x, y, w, h) in faces:
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = min(W, x + w + pad)
                y2 = min(H, y + h + pad)
                out[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
        return out


class Cappello:
    def __init__(self):
        self.img = load_asset('hat.jpg')

    def apply(self, frame, faces=None):
        out = frame.copy()
        if faces:
            for (x, y, w, _) in faces:
                ow = w
                oh = int(w * 0.8)
                cx = x + w // 2
                cy = y - oh // 2
                out = overlay_png(out, self.img, cx, cy, ow, oh)
        return out


class Occhiali:
    def __init__(self):
        self.img = load_asset('glasses.jpg')

    def apply(self, frame, faces=None):
        out = frame.copy()
        if faces:
            for (x, y, w, h) in faces:
                ow = w
                oh = int(w * 0.35)
                cx = x + w // 2
                cy = int(y + h * 0.38)
                out = overlay_png(out, self.img, cx, cy, ow, oh)
        return out


class Maschera:
    def __init__(self):
        self.img = load_asset('mask.png')

    def apply(self, frame, faces=None):
        out = frame.copy()
        if faces:
            for (x, y, w, h) in faces:
                ow = int(w * 2.6)
                oh = int(w * 1.2)
                cx = x + w // 2
                cy = int(y + h * 0.5)
                out = overlay_png(out, self.img, cx, cy, ow, oh)
        return out


class Etichetta:
    def apply(self, frame, faces=None):
        out = frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        if faces:
            for i, (x, y, w, _) in enumerate(faces):
                label = f"Persona{i}"
                (tw, th), _ = cv2.getTextSize(label, font, 0.6, 1)
                tx = x + (w - tw) // 2
                ty = y - 6
                cv2.rectangle(out, (tx - 2, ty - th - 2), (tx + tw + 2, ty + 2), (0, 0, 0), -1)
                cv2.putText(out, label, (tx, ty), font, 0.6, (0, 255, 100), 1, cv2.LINE_AA)
        return out
