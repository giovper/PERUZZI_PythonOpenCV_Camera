import cv2
import unicodedata


def to_ascii(text: str) -> str:
    #la uso in init_webcam per sanificare i nomi camera dall'OS perchè possono contenere caratteri non ascii che sarebbero rappresentati scorrettamente
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').strip()

try:
    from cv2_enumerate_cameras import enumerate_cameras
    cams = list(enumerate_cameras())
    offset = min(c.index for c in cams) if cams else 0
    if offset < 10: #succede talvolta che la libreria cv2_enumerate_cameras ritorni camere con indici ce partono da numeri alti (tipo 1200 su macbook) quindi bisogna "associarle" abbasando i numeri
        offset = 0 
    CAM_NAMES = {c.index - offset: c.name for c in cams}
except Exception:
    CAM_NAMES = {}

MAX_USB_PROBE = 5


class GenericCamera: #astrazione su qualsiasi sorgente video - is_avaiable per capire se funziona

    def __init__(self, source): #int per webcam, stringa "picamera" per Pi Camera
        self.source = source
        self.cap = None
        self.picam = None
        self.available = False
        self.is_virtual = False

        if source == "picamera":
            self.name = "Raspberry Pi Camera"
            self.init_picamera()
        else:
            self.name = f"Camera {source}"
            self.init_webcam(source)

    def init_webcam(self, index: int) -> None:
        real_name = CAM_NAMES.get(index, "")
        if real_name:
            self.name = to_ascii(real_name)
        self.is_virtual = any(k in real_name.lower() for k in ("obs", "virtual")) # la lib cv2_enumerate_cameras è usata per capire se è una camera virtuale (usata in input), dunque non doeve proiettare l'output del programa su essa altirmenti andrebbe in loop
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    self.cap = cap
                    self.available = True
                    return
            cap.release()
        except Exception:
            pass

    def init_picamera(self) -> None:
        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cfg = cam.create_preview_configuration(
                main={"format": "RGB888", "size": (1280, 720)}
            )
            cam.configure(cfg)
            cam.start()
            self.picam = cam
            self.available = True
        except Exception:
            pass

    def is_available(self) -> bool:
        return self.available

    def read(self) -> tuple: #legge il frame corrente restituendo (bool Successo, frame_BGR)
        if not self.available:
            return False, None

        if self.picam is not None:
            try:
                rgb = self.picam.capture_array()
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                return True, bgr
            except Exception:
                return False, None

        if self.cap is not None:
            return self.cap.read()

        return False, None

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.picam is not None:
            try:
                self.picam.stop()
                self.picam.close()
            except Exception:
                pass
            self.picam = None
        self.available = False


class CameraManager: # Manager statico che individua tutte le sorgenti video funzionanti con la fn get_all_cameras testando gli indici da 0 a N delle camere normali e poi la Pi Camera
    @staticmethod
    def get_all_cameras() -> list:
        cameras: list[GenericCamera] = []

        for i in range(MAX_USB_PROBE):
            cam = GenericCamera(i)
            if cam.is_available():
                cameras.append(cam)
            else:
                cam.release()
                break

        pi_cam = GenericCamera("picamera")
        if pi_cam.is_available():
            cameras.append(pi_cam)
        else:
            pi_cam.release()

        return cameras
