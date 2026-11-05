import unittest
from instrument import Instrument, SCALES


def hand(pinch=.7, y=.5):
    p = [(.5,.7)] * 21
    p[9] = (.5,y)
    p[4] = (.4,.4)
    p[8] = (.4+pinch*.2/(4/3),.4)
    p[12],p[20] = (.45,.2),(.65,.25)
    return p

class MappingTests(unittest.TestCase):
    def test_requires_open_before_play_and_after_loss(self):
        c = Instrument()
        self.assertFalse(c.update(hand(.1)).gate)
        self.assertFalse(c.update(hand()).gate)
        self.assertTrue(c.update(hand(.1)).gate)
        self.assertFalse(c.update(None).gate)
        self.assertFalse(c.update(hand(.1)).gate)

    def test_release_and_hysteresis(self):
        c = Instrument()
        c.update(hand())
        self.assertTrue(c.update(hand(.1)).gate)
        self.assertTrue(c.update(hand(.35)).gate)
        self.assertFalse(c.update(hand(.7)).gate)

    def test_scales_and_pitch_direction(self):
        for scale, intervals in SCALES.items():
            c = Instrument()
            c.scale = scale
            low = c.update(hand(y=.8)).midi
            for _ in range(40):
                v = c.update(hand(y=.2))
            self.assertGreater(v.midi,low)
            if intervals:
                self.assertIn(v.midi % 12,intervals)

    def test_bad_tracking_silences(self):
        c = Instrument()
        for p in ([], [(float('nan'),0)]*21, [(0,0)]*21):
            self.assertFalse(c.update(p).gate)

class CircleTests(unittest.TestCase):
    def test_seam_crosses_directly_between_range_ends(self):
        c = Instrument()
        high = c.circle_pitch((.49,.18),4/3)
        self.assertEqual(high,72)
        transition = [c.circle_pitch((.55,.18),4/3) for _ in range(12)]
        self.assertEqual(transition[-1],48)
        self.assertTrue(set(transition) <= {48,72})

    def test_cardinals_ascend_clockwise_in_every_scale(self):
        for scale, intervals in SCALES.items():
            pitches = []
            for point in ((.51,.18),(.74,.5),(.5,.82),(.26,.5)):
                c = Instrument()
                c.scale = scale
                pitch = c.circle_pitch(point,4/3)
                pitches.append(pitch)
                if intervals is not None:
                    self.assertIn(pitch % 12, intervals)
            self.assertEqual(pitches,sorted(pitches))

    def test_center_holds_last_pitch(self):
        c = Instrument()
        c.toggle_layout()
        p = hand()
        p[9] = (.75,.5)
        previous = c.update(p).midi
        p[9] = (.5,.5)
        self.assertEqual(c.update(p).midi,previous)

    def test_layout_switch_releases_and_requires_open_pinch(self):
        c = Instrument()
        c.update(hand())
        self.assertTrue(c.update(hand(.1)).gate)
        c.toggle_layout()
        self.assertEqual(c.layout,'Circle')
        self.assertFalse(c.voice.gate)
        self.assertFalse(c.update(hand(.1)).gate)
        c.update(hand())
        self.assertTrue(c.update(hand(.1)).gate)
        c.toggle_layout()
        self.assertEqual(c.layout,'Vertical')

if __name__ == '__main__':
    unittest.main()
