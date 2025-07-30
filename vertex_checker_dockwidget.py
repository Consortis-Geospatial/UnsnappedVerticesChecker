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
        self.setWindowTitle("Έλεγχος μη αγκυρωμένου οδικού δικτύου")
        self.flagged_pairs = []  # To store flagged point pairs for export

        # UI widgets
        self.layerCombo = QComboBox()
        self.distanceInput = QLineEdit()
        self.distanceInput.setPlaceholderText("Απόσταση σε μέτρα")
        self.check_selected = QCheckBox("Έλεγχος μόνο στα επιλεγμένα")
        self.runButton = QPushButton("Έλεγχος")
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setVisible(False)  # Initially hidden
        self.resultList = QListWidget()

        # Download Shapefile Button (created once, hidden initially)
        self.download_button = QPushButton("Download Shapefile")
        self.download_button.clicked.connect(self.export_to_shapefile)
        self.download_button.setVisible(False)  # Initially hidden

        # Layout
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

        # Populate layers
        self.populate_layers()

        # Signals
        self.runButton.clicked.connect(self.check_vertices)
        self.resultList.itemClicked.connect(self.zoom_to_vertex)

    def populate_layers(self):
        self.layerCombo.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == 1:  # 1 = Line layer
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
            self.resultList.addItem("Παρακαλώ πληκτρολογίστε έγκυρη απόσταση.")
            return

        if not layer:
            self.resultList.clear()
            self.resultList.addItem("Δεν βρέθηκε layer.")
            return

        # Check if "Έλεγχος μόνο στα επιλεγμένα" is checked but no selections exist
        if self.check_selected.isChecked() and layer.selectedFeatureCount() == 0:
            self.resultList.clear()
            self.resultList.addItem("Παρακαλώ επιλέξτε οντότητες προς έλεγχο")
            return

        # Check features based on checkbox
        if self.check_selected.isChecked() and layer.selectedFeatureCount() > 0:
            features = layer.selectedFeatures()
            total_features = layer.selectedFeatureCount()
        else:
            features = layer.getFeatures()
            total_features = layer.featureCount()

        self.start_progress(total_features)

        point_list = []
        point_feature_map = {}  # maps index to QgsPointXY
        feature_map = {}  # maps index to (feature id, vertex index, line geometry)
        vertex_lines_map = {}  # map QgsPointXY to set of feature ids (for junction checking)

        # Collect all vertices
        for i, feat in enumerate(features):
            geom = feat.geometry()
            if geom.isNull():
                continue
            if geom.isMultipart():
                lines = geom.asMultiPolyline()
            else:
                lines = [geom.asPolyline()]
            for line in lines:
                if not line:
                    continue
                for vidx, pt in enumerate(line):
                    ptxy = QgsPointXY(pt)
                    idx = len(point_list)
                    point_list.append(ptxy)
                    point_feature_map[idx] = ptxy
                    feature_map[idx] = (feat.id(), vidx, line)
                    # Track which features share this vertex (for junction detection)
                    key = (round(ptxy.x(), 6), round(ptxy.y(), 6))  # rounded coords as key
                    if key not in vertex_lines_map:
                        vertex_lines_map[key] = set()
                    vertex_lines_map[key].add(feat.id())
            self.update_progress((i + 1) * 100 // total_features)

        # Build spatial index on features
        feature_list = []
        for i, pt in enumerate(point_list):
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPointXY(pt))
            f.setId(i)
            feature_list.append(f)

        # Create spatial index and add features
        index = QgsSpatialIndex()
        for f in feature_list:
            index.addFeature(f)

        self.resultList.clear()
        checked_pairs = set()  # to avoid duplicates
        flagged_points = set()
        self.flagged_pairs = []  # Reset flagged pairs for export

        # Iterate all points and find neighbors
        for i, pt in enumerate(point_list):
            fid_i, vidx_i, line_i = feature_map[i]
            key_i = (round(pt.x(), 6), round(pt.y(), 6))

            # Skip junctions where 3 or more lines share the vertex (considered snapped junction)
            if len(vertex_lines_map[key_i]) >= 3:
                continue

            neighbors = index.nearestNeighbor(pt, 20)  # check up to 20 nearest neighbors

            for j in neighbors:
                if j == i:
                    continue
                fid_j, vidx_j, line_j = feature_map[j]

                # Skip if same point already checked in other order
                pair = tuple(sorted((i, j)))
                if pair in checked_pairs:
                    continue

                key_j = (round(point_list[j].x(), 6), round(point_list[j].y(), 6))
                # Skip junctions with 3+ connected lines
                if len(vertex_lines_map[key_j]) >= 3:
                    continue

                # Ignore vertices on the same feature (line)
                if fid_i == fid_j:
                    continue

                # Check distance threshold
                dist = pt.distance(point_list[j])
                if dist > 0 and dist < threshold:
                    # Check if these two points are exactly snapped (coordinates equal)
                    if key_i == key_j:
                        # snapped - skip
                        continue
                    # Not snapped and within threshold -> flag
                    if key_i not in flagged_points and key_j not in flagged_points:
                        flagged_points.add(key_i)
                        flagged_points.add(key_j)
                        text = f"{pt.x():.3f}, {pt.y():.3f} <--> {point_list[j].x():.3f}, {point_list[j].y():.3f} | Dist: {dist:.3f}m"
                        self.resultList.addItem(text)
                        # Store the pair for export (point1, point2, distance)
                        self.flagged_pairs.append({
                            'point1': pt,
                            'point2': point_list[j],
                            'distance': dist
                        })
                    checked_pairs.add(pair)

        self.end_progress()

        count = len(checked_pairs)
        self.resultList.addItem(f"Σύνολο: {count}")
        if count > 0:
            # Show the download button
            self.download_button.setVisible(True)
        else:
            # Show message but keep the panel open
            iface.messageBar().pushMessage("Έλεγχος μη αγκυρωμένου οδικού δικτύου", "Σύνολο: 0", level=0)

    def export_to_shapefile(self):
        if not self.flagged_pairs:
            return

        # Create a new point layer for midpoints with EPSG:2100
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

        # Save to shapefile
        from qgis.PyQt.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(None, "Save Shapefile", "", "Shapefile (*.shp)")
        if save_path:
            from qgis.core import QgsVectorFileWriter
            error = QgsVectorFileWriter.writeAsVectorFormat(vl, save_path, "UTF-8", vl.crs(), "ESRI Shapefile")
            if error[0] == QgsVectorFileWriter.NoError:
                iface.messageBar().pushSuccess("Εξαγωγή", "Το shapefile αποθηκεύτηκε επιτυχώς.")
            else:
                iface.messageBar().pushCritical("Σφάλμα", "Αποτυχία αποθήκευσης του shapefile.")

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