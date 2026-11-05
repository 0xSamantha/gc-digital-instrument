"""Hand landmark mapping, independent of camera and audio libraries."""
import math
from dataclasses import dataclass

SCALES = {'Major pentatonic': (0, 2, 4, 7, 9), 'Major': (0, 2, 4, 5, 7, 9, 11),
          'Minor': (0, 2, 3, 5, 7, 8, 10), 'Chromatic': tuple(range(12)), 'Continuous': None}

@dataclass
class Voice:
    midi: float = 60
    brightness: float = 0.3
    gate: bool = False
    status: str = 'Show your hand · open pinch to prepare'

class Instrument:
    def __init__(self):
        self.layout = 'Vertical'
        self.angle = None
        self.circle_index = None
        self.scale = 'Major pentatonic'
        self.root = 0
        self.ready = False
        self.pinched = False
        self.smoothed = None
        self.note = None
        self.voice = Voice()

    def reset(self, status='Tracking lost · open pinch to prepare'):
        self.ready = self.pinched = False
        self.smoothed = self.note = None
        self.angle = self.circle_index = None
        self.voice = Voice(status=status)
        return self.voice

    def toggle_layout(self):
        self.layout = 'Circle' if self.layout == 'Vertical' else 'Vertical'
        self.reset('Layout changed · open pinch to prepare')

    def circle_notes(self):
        intervals = SCALES[self.scale]
        return [n for n in range(48, 73) if intervals is None or (n-self.root) % 12 in intervals]

    def circle_pitch(self, point, aspect):
        dx, dy = (point[0]-.5)*aspect, point[1]-.5
        # Near the center angle becomes unstable; retain the previous pitch.
        if math.hypot(dx, dy) < .11:
            return self.voice.midi
        phase = (math.atan2(dx, -dy)/(2*math.pi)) % 1
        if self.angle is None:
            self.angle = phase
        else:
            delta = (phase-self.angle+.5) % 1 - .5
            self.angle = (self.angle+.35*delta) % 1
        if SCALES[self.scale] is None:
            return 48+24*self.angle
        notes = self.circle_notes()
        position = self.angle*len(notes)
        candidate = int(position) % len(notes)
        # Circular hysteresis includes the high/low seam without gliding
        # through every intervening note when crossing it.
        if self.circle_index is None or self.circle_index >= len(notes):
            self.circle_index = candidate
        else:
            distance = (position-(self.circle_index+.5)+len(notes)/2) % len(notes)-len(notes)/2
            if abs(distance) > .62:
                self.circle_index = candidate
        return notes[self.circle_index]

    def update(self, points, aspect=4/3):
        if points is None or len(points) != 21 or any(not math.isfinite(v) for p in points for v in p):
            return self.reset()
        # Correct normalized camera coordinates for the image aspect ratio.
        p = [(x * aspect, y) for x, y in points]
        palm = math.dist(p[0], p[9])
        if palm < 0.045:
            return self.reset('Move closer · hand too small')
        pinch = math.dist(p[4], p[8]) / palm
        if pinch > 0.48:
            self.ready = True
            self.pinched = False
        elif pinch < 0.26 and self.ready:
            self.pinched = True
        if self.layout == 'Circle':
            midi = self.circle_pitch(points[9], aspect)
        else:
            pitch = 48 + 24 * max(0, min(1, (0.85 - points[9][1]) / 0.70))
            self.smoothed = pitch if self.smoothed is None else self.smoothed + .22 * (pitch - self.smoothed)
            intervals = SCALES[self.scale]
            if intervals is None:
                midi = self.smoothed
            else:
                allowed = [n for n in range(36, 85) if (n - self.root) % 12 in intervals]
                nearest = min(allowed, key=lambda n: abs(n - self.smoothed))
                # Schmitt-like note boundary: retain a note until clearly across it.
                if self.note not in allowed or abs(nearest-self.smoothed) + .22 < abs(self.note-self.smoothed):
                    self.note = nearest
                midi = self.note
        # Middle-to-little finger spread remains available during a thumb/index pinch.
        spread = math.dist(p[12], p[20]) / palm
        brightness = max(0, min(1, (spread - .18) / .95))
        brightness = self.voice.brightness + .18 * (brightness - self.voice.brightness)
        status = 'PLAYING · release pinch to stop' if self.pinched else ('READY · pinch to play' if self.ready else 'Open thumb + index to prepare')
        self.voice = Voice(midi, brightness, self.pinched, status)
        return self.voice

def note_name(midi):
    n = round(midi)
    return ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')[n % 12] + str(n // 12 - 1)
