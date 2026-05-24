import cv2
import numpy as np
from collections import deque


class RilevamentoMovimento:
    # Sfondo nero con silhouette bianche delle zone in movimento (absdiff + soglia + dilate).
    def __init__(self):
        self.prev = None

    def apply(self, frame, faces=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.prev is None:
            self.prev = gray
            return np.zeros_like(frame)
        diff = cv2.absdiff(gray, self.prev)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        self.prev = gray
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


class Ghost:
    # Scia sfumata: media pesata degli ultimi N frame (peso crescente verso il presente).
    def __init__(self, n=10):
        self.buf = deque(maxlen=n)

    def apply(self, frame, faces=None):
        self.buf.append(frame.astype(np.float32))
        total_w = len(self.buf) * (len(self.buf) + 1) / 2
        acc = np.zeros_like(self.buf[0])
        for i, f in enumerate(self.buf):
            acc += f * (i + 1)
        return (acc / total_w).clip(0, 255).astype(np.uint8)


class GhostRGB:
    # Scia a tre canali con ritardi diversi: R=18 frame fa, G=9 frame fa, B=corrente.
    def __init__(self):
        self.buf_r = deque(maxlen=18)
        self.buf_g = deque(maxlen=9)

    def apply(self, frame, faces=None):
        self.buf_r.append(frame)
        self.buf_g.append(frame)
        out = np.empty_like(frame)
        out[:, :, 0] = frame[:, :, 0]
        out[:, :, 1] = self.buf_g[0][:, :, 1]
        out[:, :, 2] = self.buf_r[0][:, :, 2]
        return out


class MotionBlur:
    # Sfocatura direzionale orizzontale con kernel 21×21 (riga centrale = 1/21).
    def __init__(self):
        k = np.zeros((21, 21), dtype=np.float32)
        k[10, :] = 1.0 / 21
        self.kernel = k

    def apply(self, frame, faces=None):
        return cv2.filter2D(frame, -1, self.kernel)


class Neve:
    # Fiocchi di neve con fisica: cadono, si depositano sui bordi rilevati con Canny, svaniscono.
    def __init__(self):
        self.falling = []
        self.settled = []
        self.edge_map = None
        self.frame_n = 0
        self.dt = 1.0 / 30.0

    def update_edges(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 120)
        self.edge_map = cv2.dilate(edges, None, iterations=1)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        out = frame.copy()

        self.frame_n += 1
        if self.frame_n % 6 == 0 or self.edge_map is None:
            self.update_edges(frame)

        for _ in range(5):
            if len(self.falling) < 500:
                self.falling.append({
                    'x': float(np.random.randint(0, w)),
                    'y': 0.0,
                    'vx': float(np.random.uniform(-0.4, 0.4)),
                    'vy': float(np.random.uniform(60, 160) * self.dt),
                    'r': int(np.random.randint(2, 6)),
                })

        still_falling = []
        for f in self.falling:
            f['x'] += f['vx']
            f['y'] += f['vy']
            xi, yi = int(f['x']), int(f['y'])
            deposited = False

            if yi >= h:
                deposited = True
                yi = h - 1
            elif (0 <= xi < w and 0 <= yi < h and
                  self.edge_map is not None and self.edge_map[yi, xi] > 0):
                deposited = True

            if deposited:
                if len(self.settled) < 1200:
                    self.settled.append({'x': xi, 'y': yi, 'r': f['r'], 'alpha': 240.0})
            else:
                still_falling.append(f)
        self.falling = still_falling

        still_settled = []
        for s in self.settled:
            a = s['alpha'] / 255.0
            v = int(255 * a)
            cv2.circle(out, (s['x'], s['y']), s['r'], (v, v, v), -1)
            s['alpha'] -= 0.5
            if s['alpha'] > 0:
                still_settled.append(s)
        self.settled = still_settled

        for f in self.falling:
            cv2.circle(out, (int(f['x']), int(f['y'])), f['r'], (255, 255, 255), -1)

        return out


class Subacqueo:
    # Distorsione ondulata che cambia nel tempo + dominante blu-verde + bolle fisiche.
    def __init__(self):
        self.t = 0.0
        self.bubbles = []
        self.base_xy = None
        self.frame_size = None

    def build_base(self, h, w):
        cols = np.arange(w, dtype=np.float32)
        rows = np.arange(h, dtype=np.float32)
        self.base_xy = np.meshgrid(cols, rows)
        self.frame_size = (h, w)

    def apply(self, frame, faces=None):
        h, w = frame.shape[:2]
        if self.frame_size != (h, w):
            self.build_base(h, w)

        xg, yg = self.base_xy
        self.t += 0.05

        map_x = (xg + 7 * np.sin(2 * np.pi * yg / 55 + self.t)).astype(np.float32)
        map_y = (yg + 4 * np.cos(2 * np.pi * xg / 75 + self.t * 0.8)).astype(np.float32)

        out = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE).astype(np.int16)
        out[:, :, 0] = np.clip(out[:, :, 0] + 25, 0, 255)
        out[:, :, 2] = np.clip(out[:, :, 2] - 20, 0, 255)
        out = out.astype(np.uint8)

        if np.random.random() < 0.25 and len(self.bubbles) < 70:
            self.bubbles.append({
                'x': float(np.random.randint(0, w)),
                'y': float(h),
                'r': int(np.random.randint(4, 19)),
                'dx': float(np.random.uniform(-1.0, 1.0)),
            })

        still = []
        for b in self.bubbles:
            b['y'] -= float(np.random.uniform(2, 6))
            b['x'] += b['dx'] + float(np.random.uniform(-0.3, 0.3))
            if b['y'] < 0:
                continue
            bx, by = int(b['x']), int(b['y'])
            cv2.circle(out, (bx, by), b['r'], (200, 200, 200), 1)
            rx, ry = bx - b['r'] // 3, by - b['r'] // 3
            if 0 <= rx < w and 0 <= ry < h:
                cv2.circle(out, (rx, ry), max(1, b['r'] // 4), (255, 255, 255), -1)
            still.append(b)
        self.bubbles = still

        return out
