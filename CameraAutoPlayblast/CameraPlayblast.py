from typing import Union

from PySide2.QtWidgets import QLabel, QLineEdit, QPushButton, QListWidget
from shiboken2 import wrapInstance
import os
import sys
import maya.cmds as cm
import maya.OpenMaya as oM
import maya.OpenMayaUI as oMUI
from PySide2 import QtWidgets, QtCore, QtGui


class CameraPlayBlast(QtWidgets.QWidget):
    """
    A custom widget for handling camera playblasts in Maya.
    """
    playblast_btn: Union[QPushButton, QPushButton]
    connection_lwg: Union[QListWidget, QListWidget]
    show_btn: Union[QPushButton, QPushButton]
    select_file_path_btn: Union[QPushButton, QPushButton]
    file_path_le: Union[QLineEdit, QLineEdit]
    file_path_lb: Union[QLabel, QLabel]

    def __init__(self):
        super(CameraPlayBlast, self).__init__()

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self) -> None:
        """
        Create and initialize all widgets used in the UI.
        """
        # Label to display the "File path" text
        self.file_path_lb = QtWidgets.QLabel("File path:")

        # Input field for the file path
        self.file_path_le = QtWidgets.QLineEdit()

        # Button to open the file selection dialog
        self.select_file_path_btn = QtWidgets.QPushButton()
        self.select_file_path_btn.setIcon(QtGui.QIcon(":fileOpen.png"))  # Set file icon
        self.select_file_path_btn.setToolTip("Select File")  # Add helpful tooltip

        # Button to show available connections
        self.show_btn = QtWidgets.QPushButton("Show")

        # List widget for displaying available scene connections
        self.connection_lwg = QtWidgets.QListWidget()
        self.connection_lwg.setSelectionMode(QtWidgets.QListWidget.MultiSelection)  # Allow multi-selection

        # Button to execute playblast
        self.playblast_btn = QtWidgets.QPushButton("Playblast")

    def create_layouts(self):
        file_option_layout = QtWidgets.QGridLayout()
        file_option_layout.addWidget(self.file_path_lb, 0, 0)
        file_option_layout.addWidget(self.file_path_le, 0, 1)
        file_option_layout.addWidget(self.select_file_path_btn, 0, 2)

        button_down_layout = QtWidgets.QHBoxLayout()
        button_down_layout.addWidget(self.show_btn)
        button_down_layout.addWidget(self.playblast_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(file_option_layout)
        main_layout.addWidget(self.connection_lwg)
        main_layout.addLayout(button_down_layout)

    def create_connections(self):
        self.select_file_path_btn.clicked.connect(self.show_file_select_dialog)
        self.connection_lwg.itemSelectionChanged.connect(self.current_selected)
        self.show_btn.clicked.connect(self.show_connections)
        self.playblast_btn.clicked.connect(self.playblast)

    def show_file_select_dialog(self):
        """
        Show a dialog to allow the user to select a directory.
        """
        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        self.file_path_le.setText(file_path)

    def validate_and_get_filepath(self) -> str:
        """
        Validate the entered file path and convert it to a normalized absolute path.
        Returns:
            A valid normalized file path, or an empty string if validation fails.
        """
        filepath = os.path.normpath(self.file_path_le.text())
        if not os.path.isdir(filepath):
            self.display_error("File path doesn't exist. Please provide a valid path.")
            return ""
        return filepath

    @staticmethod
    def ensure_directory(path: str) -> str:
        """
        Ensure the provided directory exists, and create it if necessary.
        Args:
            path: The directory path.
        Returns:
            The absolute directory path.
        """
        os.makedirs(path, exist_ok=True)
        return os.path.abspath(path)

    @staticmethod
    def display_error(message: str) -> None:
        """
        Display an error message in Maya's script editor.
        Args:
            message: The error message to display.
        """
        oM.MGlobal.displayError(message)

    def get_scene_shot_name(self) -> str:
        """
        Get the name of the current Maya scene file (sans extension).
        Returns:
            The scene name, or an empty string if it fails.
        """
        shot_name = cm.file(query=True, sceneName=True, shortName=True).split(".")[0]
        if not shot_name:
            self.display_error("Scene name is missing. Please save the file and retry.")
            return ""
        return shot_name

    def show_connections(self):
        """
        Populate the list widget with all cameras in the scene, excluding system cameras.
        """
        self.connection_lwg.clear()
        cameras = cm.ls(type="camera")
        exclude_list = ["topShape", "frontShape", "sideShape", "perspShape"]

        for cam in cameras:
            cam_name = cam.split(":")[-1]  # Handle namespace-separated cameras
            if cam_name not in exclude_list:
                transform_node = cam.replace("Shape", "")
                self.connection_lwg.addItem(QtWidgets.QListWidgetItem(transform_node))
        cm.select(clear=True)

    def playblast(self) -> None:
        """
        Main method to handle the playblast functionality, including validation and execution.
        """
        filepath = self.validate_and_get_filepath()
        if not filepath:
            return

        shot_name = self.get_scene_shot_name()
        if not shot_name:
            return

        playblast_dir = self.ensure_directory(os.path.join(filepath, shot_name))

        selected_cameras = self.get_selected_cameras()
        if not selected_cameras:
            return

        for camera in selected_cameras:
            self.perform_playblast(camera, playblast_dir)

    def get_selected_cameras(self) -> list:
        """
        Get the cameras currently selected in the scene.
        Returns:
            A list of camera names, or an empty list if no cameras are selected.
        """
        selected_cameras = cm.ls(selection=True, type="camera")
        if not selected_cameras:
            self.display_error("No camera selected for the playblast. Please select a camera.")
            return []
        return selected_cameras

    def perform_playblast(self, camera: str, playblast_dir: str) -> None:
        """
        Perform the playblast for a specific camera.
        Args:
            camera: The camera name.
            playblast_dir: The directory path where the playblast will be saved.
        """
        cm.lookThru(camera)
        playblast_path = os.path.join(playblast_dir, f"{camera.split(':')[-1]}.mov")
        try:
            self.execute_playblast(playblast_path)
        except Exception as e:
            self.display_error(f"Failed to create playblast for {camera}: {e}")

    @staticmethod
    def execute_playblast(playblast_path: str) -> None:
        """
        Execute the Maya playblast command with pre-configured settings.
        Args:
            playblast_path: Full path of the output playblast file.
        """
        cm.playblast(
            format="qt",
            filename=playblast_path.replace("\\", "/"),
            forceOverwrite=True,
            sequenceTime=False,
            clearCache=True,
            viewer=False,
            showOrnaments=True,
            fp=4,
            percent=100,
            compression="H.264",
            quality=100,
            widthHeight=[1920, 1080]  # Changed to use Full HD for better visuals
        )

    def current_selected(self):
        """
        Update the Maya selection to match the selected items in the list widget.
        """
        items = self.connection_lwg.selectedItems()
        selected_items = [item.text() for item in items]
        cm.select(clear=True)
        cm.select(selected_items)


# noinspection PyMethodMayBeStatic,PyAttributeOutsideInit,PyMethodOverriding
class MainWindow(QtWidgets.QDialog):
    WINDOW_TITLE = "Camera Playblast"

    SCRIPTS_DIR = cm.internalVar(userScriptDir=True)
    ICON_DIR = os.path.join(SCRIPTS_DIR, 'Thi/Icon')

    dlg_instance = None

    @classmethod
    def display(cls):
        if not cls.dlg_instance:
            cls.dlg_instance = MainWindow()

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()

        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()

    @classmethod
    def maya_main_window(cls):
        """

        Returns: The Maya main window widget as a Python object

        """
        main_window_ptr = oMUI.MQtUtil.mainWindow()
        if sys.version_info.major >= 3:
            return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
        else:
            return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)

    def __init__(self):
        super(MainWindow, self).__init__(self.maya_main_window())

        self.setWindowTitle(self.WINDOW_TITLE)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.geometry = None

        self.setMinimumSize(400, 300)
        self.setMaximumSize(400, 300)
        self.create_widget()
        self.create_layouts()
        self.create_connections()

    def create_widget(self):
        self.content_layout = QtWidgets.QHBoxLayout()
        self.content_layout.addWidget(CameraPlayBlast())

        self.close_btn = QtWidgets.QPushButton("Close")

    def create_layouts(self):
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.close_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(self.content_layout)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self.close_btn.clicked.connect(self.close)

    def showEvent(self, e):
        super(MainWindow, self).showEvent(e)

        if self.geometry:
            self.restoreGeometry(self.geometry)

    def closeEvent(self, e):
        super(MainWindow, self).closeEvent(e)

        self.geometry = self.saveGeometry()
