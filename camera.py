"""Select the built-in FaceTime camera by name, or an explicit index."""
from macos_cameras import list_cameras


def open_camera(cv, device=None):
    label = f'camera {device}'
    if device is None:
        cameras = list_cameras()
        matches = [item for item in cameras if 'facetime' in item['name'].casefold()]
        if len(matches) != 1:
            available = ', '.join(f"{item['index']}: {item['name']}" for item in cameras) or 'none'
            raise RuntimeError('Could not uniquely identify the FaceTime camera. '
                               f'Available cameras: {available}. '
                               'Check Camera permission, or select one with --device INDEX.')
        device = matches[0]['index']
        label = matches[0]['name']
    # Explicit AVFoundation backend keeps indices consistent with named discovery.
    cap = cv.VideoCapture(device, cv.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f'{label} (index {device}) unavailable. Check Camera permission '
                           'and whether another application is using it. '
                           'Run ./run.sh --list-cameras to see current devices.')
    print(f'Using {label} (camera {device}).', flush=True)
    return cap, device
