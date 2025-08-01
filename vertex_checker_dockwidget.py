from qgis.PyQt.QtWidgets import QDockWidget, QVBoxLayout, QPushButton, QLineEdit, QComboBox, QListWidget, QWidget, QCheckBox, QProgressBar
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.core import (
    QgsProject,
    QgsSpatialIndex,
    QgsPointXY,
    QgsGeometry,
    QgsFeature,
    QgsVectorLayer,
)
from qgis.gui import QgsVertexMarker
from qgis.utils import iface

class VertexCheckerDockWidget(QDockWidget):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.setWindowTitle("Unsnapped Vertices Checker")
        self.flagged_pairs = []

        # UI widgets
        self.layerCombo = QComboBox()
        self.distanceInput = QLineEdit()
        self.distanceInput.setPlaceholderText("Distance in meters")
        self.check_selected = QCheckBox("Check only selected features")
        self.runButton = QPushButton("Run Check")
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setVisible(False)
        self.resultList = QListWidget()

        self.download_button = QPushButton("Download Shapefile")
        self.download_button.clicked.connect(self.export_to_shapefile)
        self.download_button.setVisible(False)

        # Layout setup
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.layerCombo)
        self.layout.addWidget(self.distanceInput)
        self.layout.addWidget(self.check_selected)
        self.layout.addWidget(self.runButton)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.resultList)
        self.layout.addWidget(self.download_button)

        container = QWidget()
        container.setLayout(self.layout)
        self.setWidget(container)

        self.populate_layers()

        self.runButton.clicked.connect(self.check_vertices)
        self.resultList.itemClicked.connect(self.zoom_to_vertex)

    def populate_layers(self):
        self.layerCombo.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == 1:
                self.layerCombo.addItem(lyr.name(), lyr.id())

    def start_progress(self, total_features):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def end_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_bar.reset()

    def check_vertices(self):
        lyr_id = self.layerCombo.currentData()
        layer = QgsProject.instance().mapLayer(lyr_id)
        try:
            threshold = float(self.distanceInput.text())
        except ValueError:
            self.resultList.clear()
            self.resultList.addItem("Please enter a valid numeric distance.")
            return

        if not layer:
            self.resultList.clear()
            self.resultList.addItem("No layer found.")
            return

        if self.check_selected.isChecked() and layer.selectedFeatureCount() == 0:
            self.resultList.clear()
            self.resultList.addItem("Please select features to check.")
            return

        if self.check_selected.isChecked() and layer.selectedFeatureCount() > 0:
            features = layer.selectedFeatures()
            total_features = layer.selectedFeatureCount()
        else:
            features = layer.getFeatures()
            total_features = layer.featureCount()

        self.start_progress(total_features)

        point_list = []
        point_feature_map = {}
        feature_map = {}
        vertex_lines_map = {}

        for i, feat in enumerate(features):
            geom = feat.geometry()
            if geom.isNull():
                continue
            lines = geom.asMultiPolyline() if geom.isMultipart() else [geom.asPolyline()]
            for line in lines:
                if not line:
                    continue
                for vidx, pt in enumerate(line):
                    ptxy = QgsPointXY(pt)
                    idx = len(point_list)
                    point_list.append(ptxy)
                    point_feature_map[idx] = ptxy
                    feature_map[idx] = (feat.id(), vidx, line)
                    key = (round(ptxy.x(), 6), round(ptxy.y(), 6))
                    if key not in vertex_lines_map:
                        vertex_lines_map[key] = set()
                    vertex_lines_map[key].add(feat.id())
            self.update_progress((i + 1) * 100 // total_features)

        feature_list = []
        for i, pt in enumerate(point_list):
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPointXY(pt))
            f.setId(i)
            feature_list.append(f)

        index = QgsSpatialIndex()
        for f in feature_list:
            index.addFeature(f)

        self.resultList.clear()
        checked_pairs = set()
        flagged_points = set()
        self.flagged_pairs = []

        for i, pt in enumerate(point_list):
            fid_i, vidx_i, line_i = feature_map[i]
            key_i = (round(pt.x(), 6), round(pt.y(), 6))

            if len(vertex_lines_map[key_i]) >= 3:
                continue

            neighbors = index.nearestNeighbor(pt, 20)
            for j in neighbors:
                if j == i:
                    continue
                fid_j, vidx_j, line_j = feature_map[j]
                pair = tuple(sorted((i, j)))
                if pair in checked_pairs:
                    continue

                key_j = (round(point_list[j].x(), 6), round(point_list[j].y(), 6))
                if len(vertex_lines_map[key_j]) >= 3:
                    continue
                if fid_i == fid_j:
                    continue

                dist = pt.distance(point_list[j])
                if dist > 0 and dist < threshold:
                    if key_i == key_j:
                        continue
                    if key_i not in flagged_points and key_j not in flagged_points:
                        flagged_points.add(key_i)
                        flagged_points.add(key_j)
                        text = f"{pt.x():.3f}, {pt.y():.3f} <--> {point_list[j].x():.3f}, {point_list[j].y():.3f} | Dist: {dist:.3f}m"
                        self.resultList.addItem(text)
                        self.flagged_pairs.append({
                            'point1': pt,
                            'point2': point_list[j],
                            'distance': dist
                        })
                    checked_pairs.add(pair)

        self.end_progress()

        count = len(checked_pairs)
        self.resultList.addItem(f"Total flagged pairs: {count}")
        if count > 0:
            self.download_button.setVisible(True)
        else:
            iface.messageBar().pushMessage("Unsnapped Vertices Checker", "Total flagged pairs: 0", level=0)

    def export_to_shapefile(self):
        if not self.flagged_pairs:
            return

        vl = QgsVectorLayer("Point?crs=epsg:2100", "unsnapped_vertices_midpoints", "memory")
        pr = vl.dataProvider()
        vl.startEditing()

        for pair in self.flagged_pairs:
            p1 = pair['point1']
            p2 = pair['point2']
            center = QgsPointXY((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(center))
            fet.setAttributes([pair['distance']])
            pr.addFeature(fet)

        vl.commitChanges()
        vl.updateExtents()

        from qgis.PyQt.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(None, "Save Shapefile", "", "Shapefile (*.shp)")
        if save_path:
            from qgis.core import QgsVectorFileWriter
            error = QgsVectorFileWriter.writeAsVectorFormat(vl, save_path, "UTF-8", vl.crs(), "ESRI Shapefile")
            if error[0] == QgsVectorFileWriter.NoError:
                iface.messageBar().pushSuccess("Export", "Shapefile saved successfully.")
            else:
                iface.messageBar().pushCritical("Error", "Failed to save shapefile.")

    def zoom_to_vertex(self, item):
        coords = item.text().split('<-->')[0].strip()
        x, y = map(float, coords.split(','))
        point = QgsPointXY(x, y)

        self.canvas.setCenter(point)
        self.canvas.zoomScale(50)
        self.canvas.refresh()

        marker = QgsVertexMarker(self.canvas)
        marker.setCenter(point)
        marker.setColor(Qt.red)
        marker.setIconSize(10)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setPenWidth(3)

        QTimer.singleShot(1500, marker.hide)
