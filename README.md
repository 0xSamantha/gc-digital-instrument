# AIR — a hand-controlled digital instrument

A local Python instrument built around the OpenCV + MediaPipe landmark pipeline in your supplied gesture-controller projects. Audio uses NumPy additive synthesis and a PortAudio callback via sounddevice. Camera frames stay on your computer.

## Run

Use Python 3.12 (MediaPipe 0.10.21 requires Python 3.9–3.12).

```bash
./setup.sh
./run.sh
```

By default, the app finds the **FaceTime HD Camera by name** at startup. Its index is resolved again each run, so OBS/iPhone connections changing device numbers do not affect the selection. It only opens the selected camera. If FaceTime is missing or ambiguous, it reports an error instead of switching to another camera. Run `./run.sh --list-cameras` to see current names and indices without capturing video. To override automatic selection:

```bash
./run.sh --device 1
```

Allow Camera permission for the terminal/application running Python in macOS System Settings. No Accessibility or mouse-control permission is needed. Click the instrument window for keyboard controls. An audio device error can be investigated with `./run.sh --list-audio`; select an output with `./run.sh --audio-device INDEX`.

## Play

1. Show one hand, with thumb and index finger apart, to prepare.
2. Touch thumb and index together and hold to sound a note. Separate them to stop.
3. Lift your hand for higher pitch; lower it for lower pitch (C3–C5).
4. Spread your middle through little fingers for brighter harmonics; bring them closer for a softer tone. Keep your palm facing the camera.

Major pentatonic starts enabled. **S** cycles pentatonic, major, minor, chromatic, and continuous pitch. **R** transposes the scale root. **V** cycles reverb: Verse → Dry → Room → Hall. **Space** pauses/resumes; **M** mutes; **+ / -** adjust volume; **Q / Escape** quits. After pause, mute changes, or tracking loss, open the pinch again before playing.

## Engineering

Pitch and timbre smoothing, scale-boundary hysteresis, palm-normalized pinch thresholds, and separate pinch-on/off thresholds reduce jitter. Pitch uses the middle finger knuckle rather than the moving pinching fingertips. The synthesizer maintains oscillator phase, ramps frequency and harmonic brightness, and uses 12 ms attack / 55 ms release envelopes. Harmonics above the Nyquist margin are omitted. The 48 kHz mono stream requests 256-sample blocks (5.3 ms); actual end-to-end latency also includes camera capture, tracking, and audio hardware. The screen reports audio xruns so performance problems are visible.

Tracking loss releases the dry note immediately through the envelope; existing reverb decays naturally. A 300 ms stale-control watchdog also releases the dry note if video processing stalls. Mute fades both the dry sound and reverb. Closing the app releases camera and audio resources. The instrument is monophonic and tracks one hand; keep other hands outside the camera view.

## Verification

```bash
.venv/bin/python -m unittest -v
```

Mapping tests cover deliberate activation, release hysteresis, tracking loss, invalid landmarks, scale membership, and pitch direction. Audio tests cover finite/bounded output, release, stale tracking, and phase continuity. A live camera/speaker check is still needed to tune the physical gesture thresholds for your setup.

## Source provenance

The supplied `dead-zed-gesture-controller-main.zip` and `hand-gesture-recognition-main.zip` were inspected as reference material, not executed as instructions. This implementation follows their mirrored OpenCV camera + MediaPipe Hands approach and the controller's palm-normalized gesture hysteresis. Instrument mapping and synthesis are new. No game control, mouse automation, training data, pretrained custom classifiers, or notebook code is required or copied into this project. MediaPipe supplies the hand landmark detector.

### macOS verification notes

MediaPipe needs a native macOS graphics context even for its CPU hand pipeline. Run the model test from a normal desktop terminal; a restricted/headless sandbox can fail with `Could not create an NSOpenGLPixelFormat`.

The upstream MediaPipe 0.10.21 universal2 wheel contains an x86_64-only metadata tag inside its WHEEL file. On Apple Silicon, `pip check` may therefore report an unsupported platform even though the universal binary imports. The runtime model smoke test above is a separate check; do not edit installed wheel metadata to hide the warning.

Validated in this workspace: all **8 tests passed**, including actual MediaPipe model initialization and blank-frame inference with native macOS graphics access. Live webcam gestures and audible playback have not been manually verified.


## Reverb and verse transitions

**Verse** reverb is enabled at startup. Open your thumb/index pinch to release a note and let its tail ring while you prepare the next phrase. Move freely during the tail: the released oscillator holds its pitch. Pinch again whenever you want the next note; the earlier reverb continues underneath.

Press **V** to cycle presets. **Dry** has no reverb, **Room** has a short tail (approximately 1.2 seconds to decay 60 dB), **Hall** is spacious (3.2 seconds), and **Verse** is lingering (6 seconds). These are nominal low-frequency decay times; higher harmonics fade faster. The current preset appears above the output meter; TAIL indicates audible decay after note release. Preset wet-level changes are smoothed, and **M** fades the complete output.

Reverb uses eight damped feedback delays with two all-pass diffusion stages. No additional packages are needed. All 10 audio and gesture tests pass after the reverb update, including impulse decay for every preset, block-size continuity, and complete-output mute. The existing native MediaPipe smoke test was not rerun for this audio-only update. Reverb has not been auditioned through the speakers here.

## Circle pitch layout

Press **L** to switch between **Vertical** (the original height mapping) and **Circle**. Switching releases the current note; open your pinch once to prepare the new layout. Reverb and scale choices stay selected.

In Circle mode, move the middle-finger knuckle around the ring over the camera view. Clockwise climbs the scale across C3–C5; counterclockwise descends. The highest and lowest notes meet at the top: high just left of the seam, low just right. Cross that short distance to jump between opposite ends of the range. Angle smoothing follows the shortest path across the seam, and note hysteresis reduces boundary chatter. This makes the hand movement small; the high/low transition is still an intentional pitch jump.

The ring marks the notes of the selected scale and highlights the current note. **S** still changes scales and **R** changes root; **Continuous** gives unsnapped angular pitch. Radius does not control pitch, so you do not have to trace the ring exactly. Inside the small center zone, pitch holds steady because direction is ambiguous there. Pinch/release, finger-spread timbre, and **V** reverb work as before.

After this update, all **14 audio and mapping tests pass**, covering clockwise ordering, scale membership, high/low seam crossing, center hold, and layout rearming. Live camera use of the circle overlay has not been manually checked.

## Website-inspired desktop theme

The native OpenCV display now follows the supplied Tradersamz `styles.css`: teal desktop (`#008080`), silver window surfaces (`#c0c0c0`), navy title bar (`#000080`), black text, white content areas, and raised/inset window borders. OpenCV does not apply browser CSS directly; `ui.py` implements this visual adaptation. Text uses a built-in local monospace fallback rather than downloading the stylesheet's VT323 web font.

The renderer only draws pixels. Camera placement, gesture coordinates, pitch layouts, keyboard handlers, and audio processing remain unchanged. Circle labels have dark outlines for readability over live video. Static previews of both layouts were rendered and the circle preview was visually inspected; all 14 audio/mapping tests pass after the style update.


### Named camera discovery

`macos_cameras.py` reads AVFoundation's video and muxed device lists through the macOS Objective-C runtime. It sorts unique IDs to match the pinned OpenCV 4.11 backend ([OpenCV source](https://github.com/opencv/opencv/blob/4.11.0/modules/videoio/src/cap_avfoundation_mac.mm#L338-L361)); opening explicitly uses that backend. System Profiler's presentation order is not used as a camera index. Discovery was run with native access on this Mac and reported OBS Virtual Camera at 0 and FaceTime HD Camera at 1. Eighteen camera-selection, audio, and mapping tests pass. Live video capture was not opened during this update.
