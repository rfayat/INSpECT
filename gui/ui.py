from pathlib import Path
from queue import Empty, Queue
import numpy as np
from typing import Optional
import sys
from core import crud
from core.video_reader import VideoReader
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Slot
import gui.controls as ctrl
from datetime import datetime
from getpass import getuser


class UI(QtWidgets.QMainWindow):
    frames_ready = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle('r2g - Video Annotator Multi-Angles')
        self.setWindowIconText('r2g')
        self.setWindowIcon(QtGui.QIcon('gui/icon.svg'))
        self._now = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
        self.queue = Queue()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        main_wdg = QtWidgets.QWidget(self)
        self.setCentralWidget(main_wdg)
        self.lyt = QtWidgets.QHBoxLayout(main_wdg)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        # Left
        left_wdg = QtWidgets.QWidget()
        left_lyt = QtWidgets.QVBoxLayout(left_wdg)
        top_bar_lyt = QtWidgets.QHBoxLayout()
        self.path_picker = ctrl.PathPicker(self)
        self.path_picker.new_path.connect(self.open_file)
        self.c_path: Optional[str] = None
        self.user_le = QtWidgets.QLineEdit(self)
        self.user_le.setPlaceholderText('User name')
        self.user_le.setText(getuser())
        self.label_add = ctrl.LabelCreator(self)
        self.label_add_btn = QtWidgets.QPushButton('Edit labels')
        self.label_add_btn.clicked.connect(self.edit_labels)
        top_bar_lyt.addWidget(self.path_picker)
        top_bar_lyt.addWidget(self.user_le)
        top_bar_lyt.addWidget(self.label_add_btn)
        top_bar_lyt.setStretch(0, 3)
        top_bar_lyt.setStretch(1, 1)
        self.video_tabs = ctrl.MultiVid(self, self.queue)
        self.frames_ready.connect(self.video_tabs.set_frames)
        self.player = ctrl.Player(self)
        left_lyt.addLayout(top_bar_lyt)
        left_lyt.addWidget(self.video_tabs)
        left_lyt.addWidget(self.player)
        splitter.addWidget(left_wdg)
        # Right
        right_wdg = QtWidgets.QWidget(self)
        self._right_lyt = QtWidgets.QVBoxLayout(right_wdg)
        self.categories = crud.load_labels('labels.json')
        self.panel = ctrl.LabelPanel(self.categories)
        self.panel.new_state.connect(self.new_annotation)
        nav = ctrl.Navigator(self)
        nav.previous.connect(self.prev_seg)
        nav.next.connect(self.next_seg)
        self._right_lyt.addWidget(self.panel)
        self._right_lyt.addWidget(nav)
        splitter.addWidget(right_wdg)
        self.lyt.addWidget(splitter)
        # Videos
        self.video_reader = VideoReader()
        self.video_reader.frames_ready.connect(self.new_frames)
        self.video_reader.c_frame = 1
        self.player.play.connect(self.video_reader.start)
        self.player.stop.connect(self.video_reader.stop)
        self.player.prev.connect(self.video_reader.prev_frame)
        self.player.next.connect(self.video_reader.next_frame)
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
        self.auto_save_annotations()
        self.auto_save_labels()
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
        self._vb.segments[self._order[self._c_seg_ix]] = value

    @property
    def seg_ix(self):
        return self._c_seg_ix

    @seg_ix.setter
    def seg_ix(self, value):
        if value < 0:
            return
        if self._vb is None:
            return
        if value >= len(self._vb.segments):
            return
        self._c_seg_ix = value
        self.c_seg = self._vb.segments[self._order[value]]
        self.auto_save_annotations()
        # self._vb
        self.show_annotations()
        self.display_segment()

    def show_annotations(self):
        if self.c_seg is None:
            return
        self.panel.blockSignals(True)
        self.panel.reset_all()
        for an in self.c_seg.annotations:
            if an.user != self.user_le.text():
                continue
            for lbl in an.labels:
                r = crud.find_label_category(self.categories, lbl)
                if r is None:
                    continue
                self.panel.check_label(r[1].name, lbl)
        self.panel.blockSignals(False)

    @Slot()
    def edit_labels(self):
        r = self.label_add.edit_label(self.categories)
        if r is None:
            return
        cat, old_label, new_label = r
        if old_label == '':
            # Creating a new label
            self.categories = crud.create_label(self.categories, cat, new_label)
        else:
            # Renaming a label
            self.categories, self._vb = crud.rename_label(self.categories, self._vb,
                                                          old_label, new_label)
        self.auto_save_labels()
        new_panel = ctrl.LabelPanel(self.categories)
        new_panel.new_state.connect(self.new_annotation)
        found_item = self._right_lyt.replaceWidget(self.panel, new_panel)
        found_item.widget().deleteLater()
        self.panel = new_panel

    @Slot(str, dict)
    def new_annotation(self, category: str, state: dict):
        if self.c_seg is None:
            return
        for label, checked in state.items():
            if not checked:
                self.c_seg = crud.remove_annotation(self.c_seg, self.user_le.text(), label)
            else:
                self.c_seg = crud.create_annotation(self.c_seg, self.user_le.text(),
                                                    self._now, label)

    @Slot()
    def new_frames(self):
        try:
            frames = self.video_reader.queue.get_nowait()
        except Empty:
            return
        self.queue.put(frames)
        self.frames_ready.emit()

    @Slot(str)
    def open_file(self, new_path):
        self._vb = crud.load_videobase(new_path)
        self.c_path = new_path
        self._order = np.random.permutation(np.arange(len(self._vb.segments)))
        self.seg_ix = 0

    def auto_save_annotations(self):
        if self.c_path is None:
            return
        orig_path = Path(self.c_path)
        json_path = orig_path.parent / f'{orig_path.stem}_{self._now}.json'
        with open(json_path, 'w') as jf:
            jf.write(self._vb.json(indent=2))

    def auto_save_labels(self):
        json_path = Path("labels.json")
        with json_path.open('w') as jf:
            jf.write(crud.AllGroups(groups=self.categories).json(indent=2))

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

