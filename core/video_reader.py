from queue import Queue
from typing import List, Optional
from pims import Video
from PySide2 import QtCore


class VideoReader(QtCore.QObject):
    frames_ready = QtCore.Signal()

    def __init__(self, video_files: Optional[List[str]] = None, interval: int = 30) -> None:
        super().__init__()
        self._video_files = video_files
        if video_files is not None:
            self._videos = [Video(vf) for vf in video_files]
        else:
            self._videos = None
        self._n_frames = 0
        self._c_frame = 0
        self._playing = False
        self.begin = 0
        self.end = 0
        self.queue = Queue()
        self._interval = interval
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(False)
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self.get_next_frames)
        self.c_frame = 0

    @property
    def n_frames(self):
        if self._videos is None:
            return -1
        return len(self._videos[0])

    @property
    def video_files(self):
        return self._video_files

    @video_files.setter
    def video_files(self, value):
        was_playing = self._playing
        if was_playing:
            self.stop()
        self.close_all_videos()
        self._video_files = value
        self.open_all_videos()
        if was_playing:
            self.start()

    def start(self):
        self._timer.start()
        self._playing = True

    def stop(self):
        self._timer.stop()
        self._playing = False

    def prev_frame(self):
        self.c_frame -= 1

    def next_frame(self):
        self.c_frame += 1

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
        if value < self.begin:
            value = self.end - 1
        if value >= self.end:
            value = self.begin
        self._c_frame = value
        self.get_current_frames()

    def get_next_frames(self):
        self.c_frame += 1

    def get_frames(self, frame_ix):
        if self._videos is None:
            return None
        try:
            frames = [vid[frame_ix].copy() for vid in self._videos]
        except AttributeError:
            # We reached the end of the video and can't seek
            self.close_all_videos()
            self.open_all_videos()
            frames = self.get_frames(frame_ix)
        return frames

    def get_current_frames(self):
        frames = self.get_frames(self.c_frame)
        if frames is None:
            return
        self.queue.put(frames)
        # images = [self.np_to_qimage(np_im) for np_im in frames]
        self.frames_ready.emit()

    def change_speed(self, interval: int):
        self.interval = interval

    def close_all_videos(self):
        if self._videos is not None:
            for vf in self._videos:
                vf.close()
        while not self.queue.empty():
            print('emptying')
            self.queue.get_nowait()

    def open_all_videos(self):
        self._videos = [Video(vf) for vf in self.video_files]

