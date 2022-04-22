import numpy as np
from typing import List
from pims import Video
from PySide2 import QtCore, QtGui


class VideoReader(QtCore.QObject):
    frames_ready = QtCore.Signal(list)

    def __init__(self, video_files: List[str], interval: int = 30) -> None:
        super().__init__()
        self.video_files = video_files
        self.videos = [Video(vf) for vf in video_files]
        self.n_frames = len(self.videos[0])
        self._c_frame = 0
        self._interval = interval
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(False)
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self.get_next_frames)
        self.c_frame = 0

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        self._interval = value
        self._timer.stop()
        self._timer.setInterval(value)
        self._timer.start()

    @property
    def c_frame(self):
        return self._c_frame

    @c_frame.setter
    def c_frame(self, value):
        self._c_frame = value
        self.get_current_frames()

    def get_next_frames(self):
        self.c_frame += 1

    @staticmethod
    def np_to_qimage(np_img):
        # np_img = np.atleast_3d(np_img)
        height, width, channels = np_img.shape
        # bgra = np.zeros([height, width, 4], dtype=np.uint8)
        # bgra[:, :, 0:3] = np_img
        return QtGui.QImage(np_img, width, height, channels*width, QtGui.QImage.Format_RGB888)

    def get_current_frames(self):
        frames = [vid[self.c_frame] for vid in self.videos]
        images = [self.np_to_qimage(np_im) for np_im in frames]
        self.frames_ready.emit(images)

    def change_speed(self, interval: int):
        self.interval = interval

