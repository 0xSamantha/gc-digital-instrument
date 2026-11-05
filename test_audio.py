import time
import unittest
from unittest.mock import patch
import numpy as np
from audio import Synth, Reverb, REVERBS
from instrument import Voice

class AudioTests(unittest.TestCase):
    def render(self, s, n=256):
        out = np.empty((n,1),np.float32)
        s.callback(out,n,None,False)
        return out

    def test_signal_and_release(self):
        s = Synth()
        s.reverb_preset = "Dry"
        s.set_voice(Voice(72,1,True))
        out = np.concatenate([self.render(s) for _ in range(20)])
        self.assertTrue(np.isfinite(out).all())
        self.assertGreater(np.max(np.abs(out)),.05)
        self.assertLess(np.max(np.abs(out)),1)
        s.set_voice(Voice(gate=False))
        for _ in range(100):
            out = self.render(s)
        self.assertLess(np.max(np.abs(out)),.0001)

    def test_stale_tracking_and_mute_release(self):
        for mute in (False,True):
            s = Synth()
            s.envelope = .2
            s.target = (440,.5,True,time.monotonic() - (0 if mute else 1))
            s.muted = mute
            for _ in range(100):
                self.render(s)
            self.assertLess(s.envelope,.0001)

    def test_phase_is_continuous_across_blocks(self):
        a,b = Synth(),Synth()
        with patch('audio.time.monotonic',return_value=100):
            a.set_voice(Voice(60,.7,True))
            b.set_voice(Voice(60,.7,True))
            whole = self.render(a,512)
            split = np.concatenate([self.render(b),self.render(b)])
        np.testing.assert_allclose(whole,split,atol=1e-6)

class ReverbTests(unittest.TestCase):
    def test_tail_is_bounded_and_decays_for_every_preset(self):
        for name, (decay, wet) in REVERBS.items():
            with self.subTest(preset=name):
                reverb = Reverb(48000)
                impulse = np.zeros(256)
                impulse[0] = .2
                blocks = [reverb.process(impulse, decay, wet)]
                for _ in range(1875):  # Ten seconds of impulse response.
                    blocks.append(reverb.process(np.zeros(256), decay, wet))
                response = np.concatenate(blocks)
                self.assertTrue(np.isfinite(response).all())
                self.assertLess(np.max(np.abs(response)), 1)
                self.assertLess(np.max(np.abs(response[-48000:])), .0001)
                if wet:
                    self.assertGreater(np.max(np.abs(response[4800:24000])), .00001)
                else:
                    self.assertEqual(np.max(np.abs(response[1:])), 0)

    def test_delay_processing_does_not_depend_on_block_size(self):
        a, b = Reverb(48000), Reverb(48000)
        impulse = np.zeros(8192)
        impulse[0] = .2
        whole = a.process(impulse, 6., .44)
        split = np.concatenate([b.process(chunk, 6., .44) for chunk in np.split(impulse,32)])
        np.testing.assert_allclose(whole, split, atol=1e-12)

    def test_mute_silences_reverb(self):
        synth = Synth()
        synth.reverb.process(np.ones(4800)*.1, 6., .44)
        synth.muted = True
        output = np.empty((256,1), np.float32)
        for _ in range(100):
            synth.callback(output,256,None,False)
        self.assertLess(np.max(np.abs(output)), .000001)

if __name__ == '__main__':
    unittest.main()
