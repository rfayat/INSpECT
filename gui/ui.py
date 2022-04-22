import sys
from core import crud
from core.video_reader import VideoReader
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Slot
import gui.controls as ctrl


class UI(QtWidgets.QMainWindow):
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        main_wdg = QtWidgets.QWidget(self)
        self.setCentralWidget(main_wdg)
        lyt = QtWidgets.QHBoxLayout(main_wdg)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        # Left
        left_wdg = QtWidgets.QWidget()
        left_lyt = QtWidgets.QVBoxLayout(left_wdg)
        self.path_picker = ctrl.PathPicker(self)
        self.video_tabs = ctrl.MultiVid(self)
        self.player = ctrl.Player(self)
        left_lyt.addWidget(self.path_picker)
        left_lyt.addWidget(self.video_tabs)
        left_lyt.addWidget(self.player)
        splitter.addWidget(left_wdg)
        # Right
        categories = crud.load_labels('labels.json')
        self.panel = ctrl.LabelPanel(categories)
        splitter.addWidget(self.panel)
        lyt.addWidget(splitter)
        # Videos
        self.video_reader = VideoReader(['Video.mp4'])
        self.video_reader.frames_ready.connect(self.new_frames)
        self.video_reader.c_frame = 1
        self.player.play.connect(self.video_reader.start)
        self.player.stop.connect(self.video_reader.stop)
        self.setMinimumSize(1500, 1000)
        self.show()

    @Slot(list)
    def new_frames(self, images):
        print(images)
        self.video_tabs.set_frames(images)


if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    w = UI()
    sys.exit(qApp.exec_())

