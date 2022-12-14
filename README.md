# r2g video annotator

## Installation
Upgrade pip (can prevent some issues with the installation of pyqt5), download the repository and install the requirements as follows :

```bash
$ pip install --upgrade pip
$ git clone https://gitlab.com/TailoredDataSolutions/r2g.git
$ cd r2g
$ pip install -r requirements.txt
```

From the r2g folder you can the launch the gui by running:

```bash
$ python -m gui.ui
```

An example video dataset for testing the ui is available [here](https://drive.google.com/file/d/1QXyP-PK-j5aPQeegqqKgihsdWYlcfDOL/view?usp=sharing).


## GUI use

1. To launch, execute the `ui.py` file from the `r2g` directory.
2. Open a [_VideoBase_ json file](#video_base) using the `Choose` button at the top of the window. See next section for details
3. Set a username if the automatically generated one is not valid
4. Labels are stored in the `r2g/labels.json` file. They can be [edited](#label_edit) using the `Edit labels` button
5. Videos are autoplayed. Playback speed can be adjusted using the slider at bottom
6. Videos can be viewed frame by frame using the `Backward` and `Forward` buttons
7. One can scroll through clips using the `Previous` and `Next` buttons
8. Checking / Unchecking the labels checkboxes will update the labels of the currently viewed video. Saving is automatic

##  <a name="label_edit"></a> Editing labels

Labels are organized by categories. There are multiple categories, and multiple label per category.
All label editing happens in the dialog box opened by clicking on the `Edit labels` button.
* To rename a category, edit its name in the dialog box.
* To rename a label choose the current name in the `Old label` combobox.
Set a new name below in the `Label` line. New name is set to all previous video labeled in the _VideoBase_.
* To generate a new label, leave the `Old label` selector empty. Set a new name.

##  <a name="video_base"></a> Structure of the Video Base JSON file

A _VideoBase_ file defines a set of video clips, plus its annotations and some metadata.
It is a JSON file with the following structure:
* Segments: list of video clips, and their metadata. Each segment is a dictionary with the following structure:
  * "subject": str, animal name
  * "date": str, date of recording
  * "session": str, session id,
  * "uid": str, some sort of unique identifier for this clip,
  * "folder": str, path the folder containing the videos. Could be used for easy relative paths. Not used now.
  * "files": list of str, paths to the video clips of each camera.
  * "frames": dict
    * "begin": int, first frame index
    * "end": int, last frame index
  * "annotations": list of dicts
    * "user": str, username of the person annotating,
    * "date": str, date of annotations,
    * "labels": list of str, one element per label.

Currently, the software works with different video clips, pre-cut, so the `begin` and `end` fields might not be useful.
Nevertheless, it should work with one long video file, and those frame indices. But it wil be much slower, and it is not guaranteed that one
will be able to go back and forth in the large video, it largely depends on the video format.
