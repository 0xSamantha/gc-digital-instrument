"""Local webcam instrument using the supplied projects' OpenCV/MediaPipe stack."""
import argparse
import time
from instrument import Instrument, SCALES, note_name
from camera import open_camera
from macos_cameras import list_cameras

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', type=int, default=None, help='camera index override; default: find the built-in FaceTime camera by name')
    parser.add_argument('--audio-device', type=int, default=None)
    parser.add_argument('--list-audio', action='store_true')
    parser.add_argument('--list-cameras', action='store_true', help='show camera names and current indices without opening them')
    args = parser.parse_args()
    if args.list_cameras:
        cameras = list_cameras()
        for device in cameras:
            print(f"{device['index']}: {device['name']}")
        if not cameras:
            print('No cameras visible. Check camera connections and permissions.')
        return
    import cv2 as cv
    import mediapipe as mp
    import sounddevice as sd
    from audio import Synth, REVERBS
    from ui import render_ui
    if args.list_audio:
        print(sd.query_devices())
        return
    if not hasattr(mp, 'solutions'):
        raise RuntimeError('Install requirements.txt: this app uses MediaPipe 0.10.21.')
    control, synth = Instrument(), Synth()
    cap, selected_device = open_camera(cv, args.device)
    title = 'AIR / hand-controlled instrument'
    paused = False
    started = time.monotonic()
    fps = 0.
    try:
        with sd.OutputStream(samplerate=synth.samplerate, blocksize=256, channels=1, dtype='float32',
                             device=args.audio_device, latency='low', callback=synth.callback), \
             mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=.75, min_tracking_confidence=.75) as hands:
            cv.namedWindow(title, cv.WINDOW_NORMAL)
            cv.resizeWindow(title, 1180, 760)
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError('Camera disconnected; audio stopped.')
                frame = cv.flip(frame, 1)
                result = hands.process(cv.cvtColor(frame, cv.COLOR_BGR2RGB))
                points = None
                if result.multi_hand_landmarks:
                    hand = result.multi_hand_landmarks[0]
                    points = [(p.x, p.y) for p in hand.landmark]
                    mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
                voice = control.reset('PAUSED · Space to resume') if paused else control.update(points, frame.shape[1]/frame.shape[0])
                synth.set_voice(voice)
                now = time.monotonic()
                fps = .9 * fps + .1 / max(.001, now-started)
                started = now
                ui = render_ui(frame, points, control, voice, synth, fps)
                cv.imshow(title, ui)
                key = cv.waitKey(1) & 0xff
                if key in (ord('q'),27) or cv.getWindowProperty(title, cv.WND_PROP_VISIBLE)<1:
                    break
                if key == ord(' '):
                    paused = not paused
                    control.reset()
                elif key == ord('l'):
                    control.toggle_layout()
                elif key == ord('s'):
                    scales = list(SCALES)
                    control.scale = scales[(scales.index(control.scale)+1)%len(scales)]
                    control.note = None
                    control.circle_index = None
                elif key == ord('r'):
                    control.root = (control.root+1)%12
                    control.note = None
                    control.circle_index = None
                elif key == ord('v'):
                    presets = list(REVERBS)
                    synth.reverb_preset = presets[(presets.index(synth.reverb_preset)+1)%len(presets)]
                elif key == ord('m'):
                    synth.muted = not synth.muted
                    control.reset()
                elif key in (ord('+'),ord('=')):
                    synth.volume = min(.4,synth.volume+.02)
                elif key == ord('-'):
                    synth.volume = max(0,synth.volume-.02)
    finally:
        synth.muted = True
        cap.release()
        cv.destroyAllWindows()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        raise SystemExit(f'Instrument stopped: {exc}')
