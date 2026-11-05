import unittest
from unittest.mock import patch
from camera import open_camera

class Capture:
    def __init__(self, opened):
        self.opened = opened
        self.released = False
    def isOpened(self):
        return self.opened
    def release(self):
        self.released = True

class Cameras:
    CAP_AVFOUNDATION = 1200
    def __init__(self, count):
        self.count = count
        self.captures = []
        self.indices = []
    def VideoCapture(self, index, backend):
        assert backend == self.CAP_AVFOUNDATION
        cap = Capture(0 <= index < self.count)
        self.captures.append(cap)
        self.indices.append(index)
        return cap

class CameraTests(unittest.TestCase):
    def test_named_selection_tracks_changing_index(self):
        for index in (0,1,2):
            cv = Cameras(3)
            devices = [{'index':i,'name':'FaceTime HD Camera' if i == index else 'Other Camera'} for i in range(3)]
            with patch('camera.list_cameras',return_value=devices):
                cap, selected = open_camera(cv)
            self.assertEqual(selected,index)
            self.assertEqual(cv.indices,[index])
            self.assertFalse(cap.released)
    def test_explicit_override_is_respected(self):
        cv = Cameras(3)
        with patch('camera.list_cameras',side_effect=AssertionError('Should not enumerate')):
            cap, index = open_camera(cv,0)
        self.assertEqual(index,0)
        self.assertEqual(cv.indices,[0])
    def test_missing_or_ambiguous_name_does_not_open_other_cameras(self):
        for devices in ([], [{'index':0,'name':'OBS Virtual Camera'}],
                        [{'index':i,'name':'FaceTime HD Camera'} for i in range(2)]):
            cv = Cameras(3)
            with patch('camera.list_cameras',return_value=devices):
                with self.assertRaises(RuntimeError):
                    open_camera(cv)
            self.assertFalse(cv.captures)
    def test_failed_open_releases_capture(self):
        cv = Cameras(0)
        with self.assertRaises(RuntimeError):
            open_camera(cv,0)
        self.assertTrue(cv.captures[0].released)
