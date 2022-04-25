from queue import Empty, Queue
import numpy as np
from typing import Optional
import sys
from core import crud
from core.video_reader import VideoReader
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Slot
import gui.controls as ctrl


class UI(QtWidgets.QMainWindow):
    frames_ready = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.queue = Queue()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        main_wdg = QtWidgets.QWidget(self)
        self.setCentralWidget(main_wdg)
        lyt = QtWidgets.QHBoxLayout(main_wdg)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        # Left
        left_wdg = QtWidgets.QWidget()
        left_lyt = QtWidgets.QVBoxLayout(left_wdg)
        self.path_picker = ctrl.PathPicker(self)
        self.path_picker.new_path.connect(self.open_file)
        self.video_tabs = ctrl.MultiVid(self, self.queue)
        self.frames_ready.connect(self.video_tabs.set_frames)
        self.player = ctrl.Player(self)
        left_lyt.addWidget(self.path_picker)
        left_lyt.addWidget(self.video_tabs)
        left_lyt.addWidget(self.player)
        splitter.addWidget(left_wdg)
        # Right
        right_wdg = QtWidgets.QWidget(self)
        right_lyt = QtWidgets.QVBoxLayout(right_wdg)
        categories = crud.load_labels('labels.json')
        self.panel = ctrl.LabelPanel(categories)
        nav = ctrl.Navigator(self)
        nav.previous.connect(self.prev_seg)
        nav.next.connect(self.next_seg)
        right_lyt.addWidget(self.panel)
        right_lyt.addWidget(nav)
        splitter.addWidget(right_wdg)
        lyt.addWidget(splitter)
        # Videos
        self.video_reader = VideoReader()
        self.video_reader.frames_ready.connect(self.new_frames)
        self.video_reader.c_frame = 1
        self.player.play.connect(self.video_reader.start)
        self.player.stop.connect(self.video_reader.stop)
        self.player.speed_adjusted.connect(self.video_reader.change_speed)
        self.setMinimumSize(1500, 1000)
        # Internal data
        self._vb: Optional[crud.VideoBase] = None
        self._order: Optional[np.ndarray] = None
        self._c_seg_ix = 0
        self._c_seg: Optional[crud.Segment] = None
        # Open main window
        self.show()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.video_reader.close_all_videos()
        print('Closing everything')
        event.accept()
        super().closeEvent(event)

    @property
    def c_seg(self):
        return self._c_seg

    @c_seg.setter
    def c_seg(self, value: crud.Segment):
        self._c_seg = value
        # print(self._c_seg.files)

    @property
    def seg_ix(self):
        return self._c_seg_ix

    @seg_ix.setter
    def seg_ix(self, value):
        if value < 0:
            return
        if value >= len(self._vb.segments):
            return
        self._c_seg_ix = value
        self.c_seg = self._vb.segments[self._order[value]]
        self.display_segment()

    @Slot()
    def new_frames(self):
        try:
            frames = self.video_reader.queue.get_nowait()
        except Empty:
            return
        # images = [self.np_to_qimage(np_img) for np_img in frames]
        # self.video_tabs.set_frames(images)
        self.queue.put(frames)
        self.frames_ready.emit()

    @Slot(str)
    def open_file(self, new_path):
        self._vb = crud.load_videobase(new_path)
        self._order = np.random.permutation(np.arange(len(self._vb.segments)))
        self.seg_ix = 0

    @Slot()
    def prev_seg(self):
        self.seg_ix -= 1

    @Slot()
    def next_seg(self):
        self.seg_ix += 1

    def display_segment(self):
        self.video_reader.stop()
        begin = self.c_seg.frames.begin
        end = self.c_seg.frames.end
        self.video_reader.begin = begin
        self.video_reader.end = end
        self.video_reader.c_frame = begin
        self.video_reader.video_files = self.c_seg.files
        self.video_reader.end = self.video_reader.n_frames
        self.video_reader.start()


if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    w = UI()
    sys.exit(qApp.exec_())

