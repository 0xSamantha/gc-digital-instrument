"""Continuous phase synthesis with sample-wise pitch, timbre and envelope ramps."""
import time
import numpy as np

# Approximate time to decay by 60 dB, plus wet level.
REVERBS = {'Dry': (0.3, 0.), 'Room': (1.2, .22),
           'Hall': (3.2, .34), 'Verse': (6.0, .44)}


class Reverb:
    """Parallel damped combs followed by serial all-pass diffusion.

    Delay storage is allocated once. Chunking at delay boundaries also supports
    callback sizes larger than a delay without changing the feedback result.
    """
    def __init__(self, samplerate):
        self.samplerate = samplerate
        self.combs = [np.zeros(round(n * samplerate / 48000))
                      for n in (1423, 1559, 1747, 1867, 1999, 2131, 2281, 2411)]
        self.positions = [0] * len(self.combs)
        self.previous = [0.] * len(self.combs)
        self.diffusers = [np.zeros(round(n * samplerate / 48000)) for n in (347, 113)]
        self.diff_positions = [0, 0]
        self.wet = 0.

    def process(self, dry, decay, wet):
        output = np.zeros(len(dry))
        for i, buffer in enumerate(self.combs):
            feedback = 10 ** (-3 * len(buffer) / (decay * self.samplerate))
            offset = 0
            while offset < len(dry):
                pos = self.positions[i]
                count = min(len(dry)-offset, len(buffer)-pos)
                delayed = buffer[pos:pos+count].copy()
                # Low-pass the feedback to let high frequencies decay faster.
                damped = .5 * (delayed + np.concatenate(([self.previous[i]], delayed[:-1])))
                self.previous[i] = delayed[-1]
                buffer[pos:pos+count] = dry[offset:offset+count] + feedback * damped
                output[offset:offset+count] += delayed / len(self.combs)
                self.positions[i] = (pos+count) % len(buffer)
                offset += count
        for i, buffer in enumerate(self.diffusers):
            offset = 0
            while offset < len(dry):
                pos = self.diff_positions[i]
                count = min(len(dry)-offset, len(buffer)-pos)
                source = output[offset:offset+count].copy()
                delayed = buffer[pos:pos+count].copy()
                diffused = delayed - .65 * source
                buffer[pos:pos+count] = source + .65 * diffused
                output[offset:offset+count] = diffused
                self.diff_positions[i] = (pos+count) % len(buffer)
                offset += count
        ramp = wet + (self.wet-wet) * np.exp(-np.arange(1,len(dry)+1)/(self.samplerate*.08))
        self.wet = ramp[-1]
        return dry + output * ramp


class Synth:
    def __init__(self, samplerate=48000):
        self.samplerate = samplerate
        self.target = (261.6256, .3, False, time.monotonic())
        self.phase = 0.
        self.frequency = 261.6256
        self.brightness = .3
        self.envelope = 0.
        self.volume = .22
        self.muted = False
        self.peak = 0.
        self.last_wave = np.zeros(256)
        self.underruns = 0
        self.reverb_preset = "Verse"
        self.reverb = Reverb(samplerate)
        self.output_gain = 1.

    def set_voice(self, voice):
        self.target = (440 * 2 ** ((voice.midi - 69) / 12), voice.brightness, voice.gate, time.monotonic())

    def callback(self, outdata, frames, timing, status):
        if status:
            self.underruns += 1
        freq, bright, gate, updated = self.target
        if not gate:
            freq, bright = self.frequency, self.brightness
        gate = gate and not self.muted and time.monotonic() - updated < .3
        samples = np.arange(1, frames + 1)
        frequency = freq + (self.frequency - freq) * np.exp(-samples / (self.samplerate * .025))
        brightness = bright + (self.brightness - bright) * np.exp(-samples / (self.samplerate * .035))
        target = self.volume if gate else 0.
        envelope = target + (self.envelope - target) * np.exp(-samples / (self.samplerate * (.012 if gate else .055)))
        phase = self.phase + 2 * np.pi * np.cumsum(frequency) / self.samplerate
        wave = np.sin(phase)
        # Harmonic additive synthesis avoids the aliasing of naive saw oscillators.
        for harmonic in range(2, 13):
            if harmonic * max(freq, self.frequency) < self.samplerate * .45:
                wave += brightness ** .7 * np.sin(harmonic * phase) / harmonic ** 1.35
        wave = np.tanh(wave * envelope)
        decay, wet = REVERBS[self.reverb_preset]
        wave = self.reverb.process(wave, decay, wet)
        # Mute fades the complete output, including the reverb tail.
        gain_target = 0. if self.muted else 1.
        gain = gain_target + (self.output_gain-gain_target) * np.exp(-samples/(self.samplerate*.012))
        self.output_gain = gain[-1]
        wave = np.clip(wave * gain, -.98, .98)
        outdata[:] = wave[:, None]
        self.phase = phase[-1] % (2 * np.pi)
        self.frequency, self.brightness, self.envelope = frequency[-1], brightness[-1], envelope[-1]
        self.peak = float(np.max(np.abs(wave)))
        self.last_wave = wave[::max(1, frames // 256)].copy()
