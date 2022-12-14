import typing
from queue import Empty, Queue
from pathlib import Path
from typing import List
from functools import partial
from core.models import Category
from typing import Optional
import PySide2
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtGui import QImage, QPainter
from PySide2.QtCore import QRectF, Slot, Signal
from core.crud import find_category


class VideoTab(QtWidgets.QWidget):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        main_lyt = QtWidgets.QVBoxLayout(self)
        self.display = Display(self)
        # self.display = QtWidgets.QLabel(self)
        main_lyt.addWidget(self.display)
        self.setMinimumWidth(1024)

    def on_new_image(self, image: QImage):
        self.display.on_image_received(image)
        # self.display.setPixmap(QPixmap(image))


class Display(QtWidgets.QGraphicsView):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.__scene = CustomGraphicsScene(self)
        self.setScene(self.__scene)

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

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget], queue: Queue,
                 min_vid: int = 5) -> None:
        super().__init__(parent)
        self.queue = queue
        lyt = QtWidgets.QHBoxLayout(self)
        self._min_vid = min_vid
        self.l_video_tabs = [VideoTab(self) for _ in range(min_vid)]
        # self.l_video_tabs = [QtWidgets.QLabel(self) for _ in range(min_vid)]
        self.tabs = QtWidgets.QTabWidget(self)
        for ix, tab in enumerate(self.l_video_tabs):
            # lyt.addWidget(tab)
            self.tabs.addTab(tab, f'Camera &{ix+1}')
        lyt.addWidget(self.tabs)
        self.setMinimumSize(1024, 780)

    @staticmethod
    def np_to_qimage(np_img):
        height, width, channels = np_img.shape
        return QtGui.QImage(np_img.copy(), width, height, channels*width,
                            QtGui.QImage.Format_RGB888)

    @Slot()
    def set_frames(self):
        try:
            frames = self.queue.get_nowait()
        except Empty:
            return
        ix = self.tabs.currentIndex()
        self.l_video_tabs[ix].on_new_image(self.np_to_qimage(frames[ix]))
        # for np_img, tab in zip(frames, self.l_video_tabs):
        #     frame = self.np_to_qimage(np_img)
        #     tab.on_new_image(frame)


class Player(QtWidgets.QWidget):
    play = Signal()
    stop = Signal()
    prev = Signal()
    next = Signal()
    speed_adjusted = Signal(int)

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.play_btn = QtWidgets.QPushButton('&Play')
        self.stop_btn = QtWidgets.QPushButton('&Stop')
        self.speed_sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_sl.setRange(-500, -5)  # Large value = large interval = slow speed
        self.speed_sl.setSingleStep(1)
        self.speed_sl.setValue(-30)
        self.prev_frame_btn = QtWidgets.QPushButton('&Backward')
        self.next_frame_btn = QtWidgets.QPushButton('&Forward')
        lyt = QtWidgets.QHBoxLayout(self)
        lyt.addWidget(self.play_btn)
        lyt.addWidget(self.stop_btn)
        lyt.addWidget(QtWidgets.QLabel('Playback speed'))
        lyt.addWidget(self.speed_sl)
        lyt.addWidget(self.prev_frame_btn)
        lyt.addWidget(self.next_frame_btn)

        self.play_btn.clicked.connect(self.play_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        self.next_frame_btn.clicked.connect(self.next_frame)
        self.speed_sl.valueChanged.connect(self.speed_adjustment)

    @Slot()
    def play_clicked(self):
        self.play.emit()

    @Slot()
    def stop_clicked(self):
        self.stop.emit()

    @Slot()
    def prev_frame(self):
        self.stop.emit()
        self.prev.emit()

    @Slot()
    def next_frame(self):
        self.stop.emit()
        self.next.emit()

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

    def reset_state(self):
        for cb in self.all_cb:
            cb.setChecked(False)

    def check_label(self, label):
        if label not in self.labels:
            return
        ix = self.labels.index(label)
        self.all_cb[ix].setChecked(True)


class LabelPanel(QtWidgets.QWidget):
    new_state = Signal(str, dict)

    def __init__(self, categories: List[Category],
                 parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        lyt = QtWidgets.QGridLayout(self)
        self.groups = {cat.name: LabelGroup(cat, self) for cat in categories}
        for ix, gp in enumerate(self.groups.values()):
            row = ix // 2
            col = ix % 2
            lyt.addWidget(gp, row, col)
            gp.labels_updated.connect(partial(self.label_clicked, category=gp.name))

        self.states = {}

    @Slot(dict)
    def label_clicked(self, state: dict, category: str):
        self.states[category] = state
        self.new_state.emit(category, state)

    def reset_all(self):
        for gp in self.groups.values():
            gp.reset_state()

    def check_label(self, category: str, label: str):
        gp = self.groups[category]
        gp.check_label(label)


class PathPicker(QtWidgets.QWidget):
    new_path = QtCore.Signal(str)

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._path = ""
        self.cwd = Path('~').expanduser().as_posix()
        lyt = QtWidgets.QHBoxLayout(self)
        self.path_le = QtWidgets.QLineEdit(parent=parent)
        self.path_le.setText("")
        self.path_le.setPlaceholderText('Choose a video base file')
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


class Navigator(QtWidgets.QWidget):
    previous = QtCore.Signal()
    next = QtCore.Signal()

    def __init__(self, parent: Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        lyt = QtWidgets.QHBoxLayout(self)
        prev_btn = QtWidgets.QPushButton('Previous')
        next_btn = QtWidgets.QPushButton('Next')
        lyt.addWidget(prev_btn)
        lyt.addWidget(next_btn)
        prev_btn.clicked.connect(self._previous_clicked)
        next_btn.clicked.connect(self._next_clicked)

    @Slot()
    def _previous_clicked(self):
        self.previous.emit()

    @Slot()
    def _next_clicked(self):
        self.next.emit()


class LabelCreator(QtWidgets.QDialog):
    def __init__(self, parent: typing.Optional[PySide2.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit or add a label')
        self._categories: List[Category] = []
        main_lyt = QtWidgets.QVBoxLayout(self)
        form_lyt = QtWidgets.QFormLayout()
        self.cat_cb = QtWidgets.QComboBox(self)
        self.labels_cb = QtWidgets.QComboBox(self)
        self.label_le = QtWidgets.QLineEdit(self)
        self.cat_cb.currentTextChanged.connect(self.category_changed)
        self.cat_cb.setEditable(True)
        form_lyt.addRow('Category', self.cat_cb)
        form_lyt.addRow('Old label', self.labels_cb)
        form_lyt.addRow('Label', self.label_le)
        btn_lyt = QtWidgets.QHBoxLayout()
        self.cancel_btn = QtWidgets.QPushButton('&Cancel')
        self.ok_btn = QtWidgets.QPushButton('&Apply')
        self.ok_btn.setDefault(True)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
        btn_lyt.addWidget(self.cancel_btn)
        btn_lyt.addWidget(self.ok_btn)
        main_lyt.addLayout(form_lyt)
        main_lyt.addLayout(btn_lyt)

    def category_changed(self, cat_name):
        self.labels_cb.clear()
        self.labels_cb.addItem('')
        r = find_category(self._categories, cat_name)
        if r is None:
            return
        _, cat = r
        self.labels_cb.addItems(cat.labels)

    def edit_label(self, categories: List[Category]):
        self._categories = categories
        for cat in categories:
            self.cat_cb.addItem(cat.name, cat)
            # self.labels_cb.addItems(cat.labels)
        if self.exec_():
            return self.cat_cb.currentText(), self.labels_cb.currentText(), self.label_le.text()
