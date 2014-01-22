# CadInput


CadInput is an _EXPERIMENTAL_ [QGIS](http://www.qgis.org) [Python](http://www.python.org) plugin that allows to numerically constrain the cursor to achieve efficient and precise digitizing, as possible in CAD packages, with any QGIS tool.

It currently relies on several hacks and may therefore be unstable.

**DO NOT USE THIS IN PRODUCTION !!!**

<!-- MarkdownTOC -->
- How to use
    - Editfields
    - Shortcuts
- Feedback / Bugs / Contribute
- Changelog
- Technical notes
    - MapCanvas mouseEvents hack
    - Tools numeric input hack
    - What API improvements would avoid the need of those hacks ?
<!-- /MarkdownTOC -->


## How to use

### Editfields

Validating an editfield with Return will lock the value.
Setting a value to an empty string will unlock the value.

You can enter basic math operations in the editfields.


### Shortcuts

Shortcuts are accessible if the MapCanvas or the CadInputWidget have focus :

- *A* : angle
- *D* : distance
- *X* : x coordinate
- *Y* : y coordinate
- Combine those with "shift" to toggle absolute/relative mode
- Combine those with "alt" to toggle locked mode.
- *C* : construction mode
- *P* : parralel / perpendicular to a segment

## Feedback / Bugs / Contribute

Feedback...

## Changelog

Changelog...

## Technical notes

The plugin relies on several hacks to work, since (afaik) the current QGIS API :
- does not allow to hook into MapCanvas mouse events 
- does not allow numerical input for tools

### MapCanvas mouseEvents hack

To be able to capture the mouseEvents of the MapCanvas, the plugin adds a QWidget as child of the mapCanvas.
That QWidget will recieve all mouseEvents, process them (constraining cursor position), and finally send them to the mapCanvas.
A drawback is that there is a "double cursor", the native QGIS cursor, and a CadInput-specific cursor, inducing a little bit of confusion.

### Tools numeric input hack

Capture the mouseEvents is fine for graphical feedback, but does not allow for precise input (since mouseEvents are in pixels, and not in map units).
To workaround this limitation, the plugin creates a memory layer, in which a point is created each time a precise coordinate input is needed, to which the native tools will snap.

### What API improvements would avoid the need of those hacks ? 

- **Have QgsMapCanvas emit signals on mouseEvents **

In current version, QgsMapCanvas emits xyCoordinates(const QgsPoint &p) on mouseMoveEvent. The same could be done for mousePressEvent and mouseReleaseEvent (maybe with better names?).

- **Allow to input scene coordinats to QgsMapTool**

For instance by adding `void QgsMapTool::scenePressEvent( QMouseEvent *e, QgsPoint *p )` (and the same for move and release events).

Or by adding an optional `scenePos *pos=0` parameter to the existing `void QgsMapTool::canvasPressEvent( QMouseEvent *e )`
This could anyways be very useful for different uses (automation ?).

The problem is, it seems the snapping/coordinate translation is implemented by each Tool subclass... So it will be some work !