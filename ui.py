"""Windows desktop styling adapted from the user's stylesheet.

Drawing only: no gesture, camera, audio or keyboard state is changed here.
"""
import math
import cv2 as cv
import numpy as np
from instrument import SCALES, note_name


def render_ui(frame, points, control, voice, synth, fps):
    # BGR values taken from the supplied Windows-style CSS palette.
    ui = np.full((760, 1180, 3), (128,128,0), np.uint8)
    navy, silver, black, white = (128,0,0), (192,192,192), (0,0,0), (255,255,255)
    def bevel(left, top, right, bottom, inset=False, fill=silver):
        cv.rectangle(ui, (left,top), (right,bottom), fill,-1)
        light, dark = (white,(128,128,128)) if not inset else ((128,128,128),white)
        for d in range(2):
            cv.line(ui,(left+d,top+d),(right-d,top+d),light,1)
            cv.line(ui,(left+d,top+d),(left+d,bottom-d),light,1)
            cv.line(ui,(left+d,bottom-d),(right-d,bottom-d),dark,1)
            cv.line(ui,(right-d,top+d),(right-d,bottom-d),dark,1)
    bevel(20,16,1160,683)
    cv.rectangle(ui,(26,22),(1154,77),navy,-1)
    bevel(32,96,680,584,inset=True,fill=black)
    bevel(700,96,1144,633,inset=True,fill=white)
    for y in (98,280,395):
        cv.rectangle(ui,(703,y),(1141,y+31),silver,-1)
    bevel(32,594,680,635,inset=True)
    bevel(0,695,1179,759)
    bevel(871,701,1164,750,inset=True)
    def text(s, x, y, size=.6, color=(0,0,0)):
        # A local monospace fallback keeps rendering offline and lightweight.
        cv.putText(ui, s.replace("·", "|"), (x,y), cv.FONT_HERSHEY_PLAIN, size*1.65, color, 1, cv.LINE_AA)
    mint = navy
    text('AIR.exe', 36, 58, 1.15, white)
    text('A HAND-CONTROLLED INSTRUMENT', 215, 53, .55, white)
    text('LOCAL CAMERA / LIVE SYNTHESIS', 810, 53, .48, white)
    ui[100:580, 36:676] = cv.resize(frame, (640,480))
    if control.layout == 'Circle':
        def overlay(s, x, y, size=.36, color=white):
            cv.putText(ui,s,(x,y),cv.FONT_HERSHEY_PLAIN,size*1.65,black,3,cv.LINE_AA)
            cv.putText(ui,s,(x,y),cv.FONT_HERSHEY_PLAIN,size*1.65,color,1,cv.LINE_AA)
        ring_color = (0,255,255)
        # Ring is centered on the camera. Correct for the camera's
        # native aspect ratio, matching the angle mapping exactly.
        aspect = frame.shape[1]/frame.shape[0]
        cx, cy = 356, 340
        rx, ry = .32/aspect*640, .32*480
        cv.ellipse(ui, (cx,cy), (round(rx),round(ry)), 0, 0, 360, ring_color, 1, cv.LINE_AA)
        notes = control.circle_notes()
        for i, note in enumerate(notes):
            angle = 2*math.pi*(i+.5)/len(notes)
            x, y = round(cx+rx*math.sin(angle)), round(cy-ry*math.cos(angle))
            active = SCALES[control.scale] is not None and note == voice.midi
            cv.circle(ui, (x,y), 6 if active else 3, ring_color, -1, cv.LINE_AA)
            if SCALES[control.scale] is not None:
                overlay(note_name(note), x-12, y-10, .34, ring_color if active else (220,220,220))
        cv.ellipse(ui, (cx,cy), (round(.11/aspect*640),53), 0,0,360, (130,130,130),1)
        overlay('HOLD PITCH', cx-37, cy+4, .32)
        overlay('HIGH | LOW', cx-40, round(cy-ry)-26, .36, ring_color)
        cv.line(ui, (cx,round(cy-ry)-14), (cx,round(cy-ry)+14), ring_color,1)
        if points is not None:
            x,y = round(36+points[9][0]*640), round(100+points[9][1]*480)
            cv.line(ui, (cx,cy), (x,y), ring_color,1,cv.LINE_AA)
            cv.circle(ui, (x,y), 8, ring_color,2,cv.LINE_AA)
    text('01 / VOICE', 720, 120, .5)
    text(note_name(voice.midi), 715, 215, 2.4, mint)
    text(f'{440*2**((voice.midi-69)/12):.1f} Hz', 720, 252)
    text('PLAYING' if voice.gate else ('TAIL' if synth.peak > .001 else 'SILENT'), 950, 206, .6, mint)
    text('02 / COLOR', 720, 302, .5)
    text('SOFT', 720, 343, .45)
    text('BRIGHT', 1050, 343, .45)
    cv.rectangle(ui, (720,360), (1125,370), silver, -1)
    cv.rectangle(ui, (720,360), (720+int(405*voice.brightness),370), mint, -1)
    text('03 / SCALE', 720, 420, .5)
    text(control.scale.upper(), 720, 460, .7, mint)
    text('Root: ' + note_name(60+control.root)[:-1] + '   |   S scale  /  R root', 720, 495, .48)
    text('V reverb: ' + synth.reverb_preset.upper(), 720, 529, .48, mint)
    text('OUTPUT   ' + ('MUTED' if synth.muted else f'{int(synth.volume/.4*100)}%'), 720, 555, .5)
    wave = synth.last_wave
    if len(wave)>1:
        coords = np.column_stack((np.linspace(720,1125,len(wave)), 600-wave*100)).astype(np.int32)
        cv.polylines(ui, [coords], False, mint, 1, cv.LINE_AA)
    text(voice.status, 36, 615, .62, mint)
    text(('CIRCLE / clockwise = higher   L layout' if control.layout == 'Circle' else 'VERTICAL / lift = higher   L layout') + '   |   SPREAD / timbre   PINCH / play', 36, 657, .49)
    text('Space pause    S scale    R root    V reverb    M mute    +/- volume    Q quit', 28, 730, .46)
    text(f'{fps:.0f} FPS | audio xruns {synth.underruns}', 886, 730, .42)
    return ui
