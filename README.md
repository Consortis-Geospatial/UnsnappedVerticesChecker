# UnsnappedVerticesChecker
**UnsnappedVerticesChecker** is a QGIS plugin designed to detect vertices that are spatially close to each other but belong to different line features and are not snapped together. These unsnapped connections may indicate topological errors, such as road segments that appear connected but aren't. Users can define a proximity threshold in meters, analyze vertices in a line layer, and view results in an interactive dock with zoom-to functionality. Flagged vertex pairs can be exported as a point shapefile marking their midpoints, supporting both full-layer and selected-feature analysis.

---

## Features

- Identify vertices from different line features that are closer than a user-defined distance threshold but not snapped.
- Specify a proximity threshold in meters to detect unsnapped vertices.
- Option to analyze full line layers or restrict to selected features.
- Visual feedback with temporary red vertex markers highlighting flagged points on the map canvas.
- Interactive dock widget to list flagged vertex pairs with zoom-to functionality.
- Export midpoints of flagged vertex pairs as a point Shapefile (EPSG:2100) for further analysis.
- Progress bar to monitor analysis progress.

---

## How It Works

1. Activate the plugin to open the "Unsnapped Vertices Checker" dock widget.
2. Select a line layer from the dropdown menu in the dock panel.
3. Enter a distance threshold (in meters) to define the proximity for checking unsnapped vertices.
4. Optionally, enable the "Check only selected features" checkbox to limit analysis to selected features.
5. Click "Run Check" to start the analysis.
6. View flagged vertex pairs in the results list; click an item to zoom to the first vertex with a temporary red marker.
7. Export midpoints of flagged pairs to a Shapefile using the "Download Shapefile" button.

---

## Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/Consortis-Geospatial/UnsnappedVerticesChecker.git
   ```
2. Copy the folder to your QGIS plugin directory:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Open QGIS and enable the plugin via Plugins > Manage and Install Plugins.

---

## Screenshot
Coming Soon...

---

## Developer Notes

- Developed in Python using PyQt and PyQGIS APIs.
- Uses a custom `QDockWidget` for layer selection, parameter input, and result display.
- Employs `QgsSpatialIndex` for efficient spatial queries to identify nearby vertices.
- Temporary red `QgsVertexMarker` visualization with a 1500ms display for flagged vertices.
- Exports midpoints of flagged vertex pairs as a point Shapefile in EPSG:2100, optimized for Greek road network datasets.
- Handles invalid inputs and empty selections with user-friendly error messages.
- Compatible with QGIS 3.0 and later.

---

## Dependencies

- **QGIS 3.x**: Compatible with QGIS version 3.0 and later (tested with 3.38.3), providing the core GIS functionality and PyQGIS API.
- **Python 3**: QGIS 3.x includes an embedded Python 3 interpreter (typically version 3.7 or higher).
- **PyQt5**: Required for GUI components like `QDockWidget`, `QComboBox`, `QLineEdit`, `QPushButton`, `QListWidget`, `QCheckBox`, and `QProgressBar`. Bundled with QGIS 3.x installations (version 5.15.10 or similar).
- **PyQGIS**: Provides core QGIS functionality, including `QgsProject`, `QgsSpatialIndex`, `QgsGeometry`, `QgsVectorLayer`, `QgsVertexMarker`, and `QgsVectorFileWriter`. Included with QGIS.
- **PyQt5-sip**: A dependency for PyQt5, typically included with QGIS (version 12.13.0 or higher).

---

## Support and Contributions

- **Homepage**: [https://github.com/Consortis-Geospatial](https://github.com/Consortis-Geospatial)
- **Issue Tracker**: [https://github.com/Consortis-Geospatial/UnsnappedVerticesChecker/issues](https://github.com/Consortis-Geospatial/UnsnappedVerticesChecker/issues)
- **Author**: Gkaravelis Andreas - Consortis Geospatial
- **Email**: gkaravelis@consortis.gr
- **Repository**: [https://github.com/Consortis-Geospatial/UnsnappedVerticesChecker](https://github.com/Consortis-Geospatial/UnsnappedVerticesChecker)

---

## License
This plugin is released under the GPL-3.0 license.
