# Filtri Webcam

Applicazione Python per visualizzare in tempo reale il feed di una webcam con effetti e filtri sovrapposti in tre slot indipendenti. Supporta screenshot, registrazione video e output su webcam virtuale (OBS Virtual Camera).

---

## Installazione

### PC — Windows / macOS / Linux (solo webcam USB normali)

```
pip install -r requirements.txt
```

`requirements.txt` include: `numpy`, `opencv-python`, `cv2-enumerate-cameras`

---

### PC — Windows / macOS con webcam virtuale OBS

```
pip install -r requirements.txt
pip install pyvirtualcam
```

Requisiti aggiuntivi:
- OBS Studio installato da https://obsproject.com
- Aprire OBS almeno una volta e cliccare **Start Virtual Camera** nel pannello Controls (eventualmente modificare imposazioni di sistema relative per permettere a OBS di creare una vcam)

---

### Raspberry Pi (Sistema operativo Raspberry Bullseye o Bookworm o successive) — webcam USB

```
sudo apt install python3-opencv python3-numpy
```
Requisiti aggiuntivi:
- Sessione grafica X11, non Wayland (Bookworm e Trixie usano Wayland di default — scegliere X11 con sudo raspi-config poi Advanced poi A6 Wayland/X11 e scegliere il X11)

> Non usare `pip install opencv-python` su Raspberry Pi: non esistono wheel precompilate per ARM e la compilazione da sorgente richiede ore.

---

### Raspberry Pi (Sistema operativo Raspberry Bullseye o Bookworm o successive) — modulo Pi Camera (CSI)

```
sudo apt install python3-opencv python3-numpy python3-picamera2
```

> Su **Bookworm** picamera2 e' preinstallata nell'immagine Desktop; il comando sopra serve solo sull'immagine Lite.
> Su **Bullseye** se `python3-picamera2` non e' disponibile nei repo, installare con pip: prima `sudo apt install libcamera-dev python3-libcamera`, poi `pip install picamera2`. Usare pip solo in questo caso — su Bookworm non serve.

Requisiti aggiuntivi:
- Cavo flat collegato alla porta CSI (con Pi spento)
- Camera abilitata in `raspi-config` (Bullseye) o presente in `config.txt` (Bookworm)
- Sessione grafica X11, non Wayland (Bookworm e Trixie usano Wayland di default — scegliere X11 con sudo raspi-config poi Advanced poi A6 Wayland/X11 e scegliere il X11)

---

## Come funziona

All'avvio viene mostrata una schermata di selezione con l'anteprima live di tutte le webcam rilevate. La Raspberry Pi Camera e' sempre mostrata per ultima: se non disponibile appare come rettangolo rosso senza tasto associato.

Selezionata la camera, si apre la finestra principale ridimensionabile con bande nere. Il frame passa attraverso tre slot di effetti applicati in sequenza:

1. **Slot 1 — Modificatori**: trasformazioni geometriche e distorsioni
2. **Slot 2 — Colore**: filtri cromatici e effetti temporali
3. **Slot 3 — Volto**: effetti basati sul rilevamento facciale (Haar cascade)

La pipeline e': Slot 3 → Slot 1 → Slot 2

Il rilevamento dei volti e' sempre attivo (su frame ridotto a meta risoluzione per velocita') e serve agli effetti dello Slot 3.

### Controlli

| Tasto | Azione |
|-------|--------|
| A / D | Slot precedente / successivo |
| W / S | Effetto precedente / successivo nello slot attivo |
| O / P | Aumenta / diminuisce intensita' (solo alcuni effetti Slot 1) |
| E     | Screenshot (salvato in `screenshots/`) |
| R     | Avvia / ferma registrazione (salvata in `recordings/`) |
| Q     | Esci |

### HUD e interfaccia

- In alto a sinistra: FPS, numero di volti rilevati, effetti attivi per slot, stato webcam virtuale
- In basso: barra di navigazione con i tre slot, effetto corrente e adiacenti
- Bordo rosso lampeggiante durante la registrazione
- Flash bianco al momento dello screenshot

### Webcam virtuale

Se pyvirtualcam e' installato e OBS Virtual Camera e' attiva, il frame processato viene inviato automaticamente alla webcam virtuale ed e' visibile in qualsiasi applicazione di videoconferenza come "OBS Virtual Camera". Se la camera selezionata come input e' gia' una webcam virtuale, l'output viene disabilitato per evitare loop.

---

## Effetti disponibili

### Slot 1 — Modificatori
- Nessuno
- Flip H
- Flip V
- Specchio Sx
- Specchio Dx
- Specchio Su
- Specchio Giu
- Spec. Tagliato
- Caleidoscopio
- Fisheye
- Pixellato
- Vignettatura

### Slot 2 — Colore
- Nessuno
- Grigi
- Negativo
- Sepia
- Termico
- Fumetto
- Halftone
- Pop Art
- Movimento
- Ghost
- Ghost RGB
- MotionBlur
- Neve
- Subacqueo

### Slot 3 — Volto
- Nessuno
- Sfondo Blur
- Cappello
- Occhiali
- Maschera
- Etichetta
