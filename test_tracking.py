"""Smoke test the installed landmark model without a webcam."""
import unittest
import numpy as np
import mediapipe as mp

class TrackingTests(unittest.TestCase):
    def test_blank_frame_has_no_hand(self):
        with mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=1) as hands:
            result = hands.process(np.zeros((480,640,3), dtype=np.uint8))
            self.assertFalse(result.multi_hand_landmarks)

if __name__ == '__main__':
    unittest.main()
