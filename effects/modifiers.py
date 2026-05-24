import cv2
import numpy as np


class Nessuno:
    def apply(self, frame, faces=None):
        return frame


class FlipH:
    def apply(self, frame, faces=None):
        return cv2.flip(frame, 1)


class FlipV:
    def apply(self, frame, faces=None):
        return cv2.flip(frame, 0)


class SpecchioSx:
    # Riflette la metà destra sulla metà sinistra.
    def apply(self, frame, faces=None):
        out = frame.copy()
        w = frame.shape[1]
        out[:, :w // 2] = cv2.flip(frame[:, w // 2:], 1)
        return out


class SpecchioDx:
    # Riflette la metà sinistra sulla metà destra.
    def apply(self, frame, faces=None):
        out = frame.copy()
        w = frame.shape[1]
        out[:, w // 2:] = cv2.flip(frame[:, :w // 2], 1)
        return out


class SpecchioSu:
    # Riflette la metà inferiore sulla metà superiore.
    def apply(self, frame, faces=None):
        out = frame.copy()
        h = frame.shape[0]
        out[:h // 2, :] = cv2.flip(frame[h // 2:, :], 0)
        return out


class SpecchioGiu:
    # Riflette la metà superiore sulla metà inferiore.
    def apply(self, frame, faces=None):
        out = frame.copy()
        h = frame.shape[0]
        out[h // 2:, :] = cv2.flip(frame[:h // 2, :], 0)
        return out


class SpecchioTagliato:
    # La metà superiore viene specchiata orizzontalmente su sé stessa; metà inferiore invariata.
    def apply(self, frame, faces=None):
        out = frame.copy()
        h = frame.shape[0]
        out[:h // 2, :] = cv2.flip(frame[:h // 2, :], 1)
        return out


class Caleidoscopio:
    #remap: ogni pixel di output viene preso dalla posizione (map_x[y,x], map_y[y,x]) nel frame   sorgente
    # 12 spicchi di 30° che ripetono uno spicchio sorgente (alternando dritto/specchiato).
    def __init__(self):
        self.maps = None
        self.frame_size = None

    def build_maps(self, h, w):
        cx, cy = w / 2.0, h / 2.0
        r_max = min(cx, cy)

        xs = np.arange(w, dtype=np.float32)
        ys = np.arange(h, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)
        dx = xg - cx
        dy = yg - cy
        r = np.sqrt(dx ** 2 + dy ** 2)

        theta = np.arctan2(dx, -dy) % (2 * np.pi)
        slice_angle = np.pi / 6.0
        sector = (theta / slice_angle).astype(np.int32)
        alpha = theta - sector * slice_angle
        alpha = np.where(sector % 2 == 1, slice_angle - alpha, alpha)

        x_src = (cx + r * np.sin(alpha)).astype(np.float32)
        y_src = (cy - r * np.cos(alpha)).astype(np.float32)
        mask = r <= r_max
        x_src = np.where(mask, x_src, cx).astype(np.float32)
        y_src = np.where(mask, y_src, cy).astype(np.float32)

        self.maps = (x_src, y_src, mask)
        self.frame_size = (h, w)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        if self.frame_size != (h, w):
            self.build_maps(h, w)
        x_src, y_src, mask = self.maps
        out = cv2.remap(frame, x_src, y_src, cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE)
        out[~mask] = 0
        return out


class Fisheye:
    # Distorsione barrel (k=0.55): i bordi vengono compressi verso l'esterno.
    def __init__(self):
        self.maps = None
        self.frame_size = None

    def build_maps(self, h, w):
        cx, cy = w / 2.0, h / 2.0
        k = 0.55
        xs = np.arange(w, dtype=np.float32)
        ys = np.arange(h, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)
        dx = (xg - cx) / cx
        dy = (yg - cy) / cy
        factor = 1.0 + k * (dx ** 2 + dy ** 2)
        self.maps = (
            (cx + dx * factor * cx).astype(np.float32),
            (cy + dy * factor * cy).astype(np.float32),
        )
        self.frame_size = (h, w)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        if self.frame_size != (h, w):
            self.build_maps(h, w)
        x_src, y_src = self.maps
        return cv2.remap(frame, x_src, y_src, cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)


class Pixellato:
    def __init__(self):
        self.intensity = 1

    def apply(self, frame, faces=None):
        factor = 8 * self.intensity
        h, w = frame.shape[:2]
        small = cv2.resize(frame, (max(1, w // factor), max(1, h // factor)),
                           interpolation=cv2.INTER_NEAREST)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


class Vignettatura:
    def __init__(self):
        self.intensity = 1
        self.mask = None
        self.cache_key = None

    def build_mask(self, h, w, strength):
        cx, cy = w / 2.0, h / 2.0
        xs = np.arange(w, dtype=np.float32)
        ys = np.arange(h, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)
        dist = np.sqrt(((xg - cx) / cx) ** 2 + ((yg - cy) / cy) ** 2)
        m = np.clip(1.0 - dist * strength, 0.0, 1.0).astype(np.float32)
        self.mask = m[:, :, np.newaxis]
        self.cache_key = (h, w, strength)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        strength = 0.55 if self.intensity == 1 else 0.90
        if self.cache_key != (h, w, strength):
            self.build_mask(h, w, strength)
        return (frame.astype(np.float32) * self.mask).clip(0, 255).astype(np.uint8)
