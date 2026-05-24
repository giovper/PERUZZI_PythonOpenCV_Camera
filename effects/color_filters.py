import cv2
import numpy as np


class Grigi:
    # Converte in luminanza e restituisce un frame BGR in scala di grigi.
    def apply(self, frame, faces=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


class Negativo:
    # Inverte ogni canale: out = 255 - in.
    def apply(self, frame, faces=None):
        return cv2.bitwise_not(frame)


class Sepia:
    # Tonalità calda marrone-arancio secondo la matrice di seppia standard (BGR).
    M = np.array([
        [0.131, 0.534, 0.272],
        [0.168, 0.686, 0.349],
        [0.189, 0.769, 0.393],
    ], dtype=np.float32)

    def apply(self, frame, faces=None):
        out = np.dot(frame.astype(np.float32), self.M.T)
        return np.clip(out, 0, 255).astype(np.uint8)


class Termico:
    # Colormap termica COLORMAP_JET: zone scure blu, chiare rosse.
    def apply(self, frame, faces=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_JET)


class Fumetto:
    # Colori piatti (bilateral filter ×4 a metà res) con contorni neri (adaptive threshold).
    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        small = cv2.resize(frame, (w // 2, h // 2))
        for _ in range(4):
            small = cv2.bilateralFilter(small, 9, 75, 75)
        flat = cv2.resize(small, (w, h))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(blur, 255,
                                      cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 9, 2)
        return cv2.bitwise_and(flat, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))


class Halftone:
    # Pattern a punti Ben-Day: celle 10×10, raggio proporzionale alla luminosità media.
    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        cell = 10
        out = np.full_like(frame, 30)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        lum_small = cv2.resize(gray, (w // cell, h // cell), interpolation=cv2.INTER_AREA)
        lum_up = cv2.resize(lum_small, (w, h), interpolation=cv2.INTER_NEAREST)

        cols = np.arange(w, dtype=np.float32)
        rows = np.arange(h, dtype=np.float32)
        xg, yg = np.meshgrid(cols, rows)

        cell_cx = (xg.astype(np.int32) // cell) * cell + cell // 2
        cell_cy = (yg.astype(np.int32) // cell) * cell + cell // 2

        radius_map = (cell / 2.0 + 2.0) * lum_up
        dist = np.sqrt((xg - cell_cx) ** 2 + (yg - cell_cy) ** 2)

        out[dist <= radius_map] = frame[dist <= radius_map]
        return out


class PopArt:
    # Griglia 2×2: saturazione esaltata, hue+60, hue+120, sepia.
    SEPIA = np.array([
        [0.131, 0.534, 0.272],
        [0.168, 0.686, 0.349],
        [0.189, 0.769, 0.393],
    ], dtype=np.float32)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        hh, hw = h // 2, w // 2
        small = cv2.resize(frame, (hw, hh))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV).astype(np.int32)

        q1 = hsv.copy()
        q1[:, :, 1] = np.clip(q1[:, :, 1] * 2.2, 0, 255)
        q1 = cv2.cvtColor(q1.astype(np.uint8), cv2.COLOR_HSV2BGR)

        q2 = hsv.copy()
        q2[:, :, 0] = (q2[:, :, 0] + 60) % 180
        q2 = cv2.cvtColor(q2.astype(np.uint8), cv2.COLOR_HSV2BGR)

        q3 = hsv.copy()
        q3[:, :, 0] = (q3[:, :, 0] + 120) % 180
        q3 = cv2.cvtColor(q3.astype(np.uint8), cv2.COLOR_HSV2BGR)

        q4 = np.clip(np.dot(small.astype(np.float32), self.SEPIA.T), 0, 255).astype(np.uint8)

        out = np.empty((h, w, 3), dtype=np.uint8)
        out[:hh, :hw] = q1
        out[:hh, hw:] = q2
        out[hh:, :hw] = q3
        out[hh:, hw:] = q4
        return out
