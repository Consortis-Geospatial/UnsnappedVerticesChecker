from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from .vertex_checker_dockwidget import VertexCheckerDockWidget
import os

class VertexProximityPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(QIcon(icon_path), 'Unsnapped Vertices Checker', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu('&Unsnapped Vertices Checker', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu('&Unsnapped Vertices Checker', self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock = None

    def run(self):
        # Create or show the dock widget
        if self.dock:
            self.iface.removeDockWidget(self.dock)
        self.dock = VertexCheckerDockWidget(self.iface)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
