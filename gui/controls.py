from pathlib import Path
import sys
from typing import List
from functools import partial
from core.models import Category
from core import crud
from typing import Optional
import PySide2
from PySide2 import QtWidgets, QtCore
from PySide2.QtGui import QImage, QPainter
from PySide2.QtCore import QRectF, Slot, Signal


class VideoTab(QtWidgets.QWidget):

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.display = Display(self)

    @Slot(QImage)
    def on_new_image(self, image: QImage):
        self.display.on_image_received(image)


class Display(QtWidgets.QGraphicsView):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.__scene = CustomGraphicsScene(self)
        self.setScene(self.__scene)

    @Slot(QImage)
    def on_image_received(self, image: QImage):
        self.__scene.set_image(image)
        self.update()


class CustomGraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent: Display = None):
        super().__init__(parent)
        self.__parent = parent
        self.__image = QImage()

    def set_image(self, image: QImage):
        self.__image = image
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Display size
        display_width = self.__parent.width()
        display_height = self.__parent.height()

        # Image size
        image_width = self.__image.width()
        image_height = self.__image.height()

        # Return if we don't have an image yet
        if image_width == 0 or image_height == 0:
            return

        # Calculate aspect ratio of display
        ratio1 = display_width / display_height
        # Calculate aspect ratio of image
        ratio2 = image_width / image_height

        if ratio1 > ratio2:
            # The height with must fit to the display height.So h remains and w must be scaled down
            image_width = display_height * ratio2
            image_height = display_height
        else:
            # The image with must fit to the display width. So w remains and h must be scaled down
            image_width = display_width
            image_height = display_height / ratio2

        image_pos_x = -1.0 * (image_width / 2.0)
        image_pox_y = -1.0 * (image_height / 2.0)

        # Remove digits after point
        image_pos_x = int(image_pos_x)
        image_pox_y = int(image_pox_y)

        rect = QRectF(image_pos_x, image_pox_y, image_width, image_height)

        painter.drawImage(rect, self.__image)


class MultiVid(QtWidgets.QWidget):

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None,
                 min_vid: int = 5) -> None:
        super().__init__(parent)
        self._min_vid = min_vid
        self.l_video_tabs = [VideoTab(self) for _ in range(min_vid)]
        self.tabs = QtWidgets.QTabWidget(self)
        for ix, tab in enumerate(self.l_video_tabs):
            self.tabs.addTab(tab, f'Camera &{ix+1}')


class Player(QtWidgets.QWidget):
    play = Signal()
    stop = Signal()
    speed_adjusted = Signal(int)

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.play_btn = QtWidgets.QPushButton('&Play')
        self.stop_btn = QtWidgets.QPushButton('&Stop')
        self.speed_sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_sl.setRange(-500, -20)  # Large value = large interval = slow speed
        self.speed_sl.setSingleStep(1)
        self.speed_sl.setValue(30)
        lyt = QtWidgets.QHBoxLayout(self)
        lyt.addWidget(self.play_btn)
        lyt.addWidget(self.stop_btn)
        lyt.addWidget(self.speed_sl)
        self.play_btn.clicked.connect(self.play_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.speed_sl.valueChanged.connect(self.speed_adjustment)

    @Slot()
    def play_clicked(self):
        self.play.emit()

    @Slot()
    def stop_clicked(self):
        self.stop.emit()

    @Slot(int)
    def speed_adjustment(self, value):
        self.speed_adjusted.emit(abs(value))


class LabelGroup(QtWidgets.QWidget):
    labels_updated = Signal(dict)

    def __init__(self, category: Category,
                 parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.category = category
        self.name = category.name
        self.labels = category.labels
        self.states = {lbl: False for lbl in self.labels}
        lyt = QtWidgets.QHBoxLayout(self)
        cb_grp = QtWidgets.QGroupBox(self.name, self)
        grp_lyt = QtWidgets.QVBoxLayout(cb_grp)

        self.all_cb = [QtWidgets.QCheckBox(lbl, self) for lbl in self.labels]
        for lbl, cb in zip(self.labels, self.all_cb):
            cb.stateChanged.connect(partial(self.state_changed, label=lbl))
            grp_lyt.addWidget(cb)
        grp_lyt.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed,
                              QtWidgets.QSizePolicy.Expanding))
        lyt.addWidget(cb_grp)

    @Slot(int)
    def state_changed(self, state: int, label: str):
        self.states[label] = state > 0
        self.labels_updated.emit(self.states)


class LabelPanel(QtWidgets.QWidget):
    def __init__(self, categories: List[Category],
                 parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        lyt = QtWidgets.QGridLayout(self)
        groups = [LabelGroup(cat, self) for cat in categories]
        for ix, gp in enumerate(groups):
            row = ix // 2
            col = ix % 2
            lyt.addWidget(gp, row, col)
            gp.labels_updated.connect(partial(self.label_clicked, category=gp.name))

        self.states = {}

    @Slot(dict)
    def label_clicked(self, state: dict, category: str):
        self.states[category] = state


class MainWindow(QtWidgets.QMainWindow):
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
        self.path_picker = PathPicker(self)
        self.video_tabs = MultiVid(self)
        self.player = Player(self)
        left_lyt.addWidget(self.path_picker)
        left_lyt.addWidget(self.video_tabs)
        left_lyt.addWidget(self.player)
        splitter.addWidget(left_wdg)
        # Right
        categories = crud.load_labels('labels.json')
        self.panel = LabelPanel(categories)
        splitter.addWidget(self.panel)
        # lyt.addWidget(self.panel)
        lyt.addWidget(splitter)
        self.show()


class PathPicker(QtWidgets.QWidget):
    new_path = QtCore.Signal(str)

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._path = ""
        self.cwd = Path('~').expanduser().as_posix()
        lyt = QtWidgets.QHBoxLayout(self)
        self.path_le = QtWidgets.QLineEdit(parent=parent)
        self.path_le.setText("")
        self.path_le.setPlaceholderText('Choose a file to save to')
        self.btn = QtWidgets.QPushButton('Choose...')
        lyt.addWidget(self.path_le)
        lyt.addWidget(self.btn)
        self.btn.clicked.connect(self.get_path)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.cwd = Path(value).parent.as_posix()
        self.new_path.emit(value)

    def get_path(self):
        open_dialog = QtWidgets.QFileDialog(self)
        dpath, _ = open_dialog.getOpenFileName(self, "Choose a Video Base file",
                                               self.cwd,
                                               "JSON files (*.json)")
        if dpath != '':
            self.path = dpath


if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    sys.exit(qApp.exec_())

