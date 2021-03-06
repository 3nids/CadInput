# CadInput


CadInput is a __PROTOTYPE__ QGIS Python plugin that allows to numerically constrain the cursor to achieve efficient and precise digitizing, as possible in CAD packages, with any QGIS tool.

It currently relies on too many hacks and may therefore be unstable. **DO NOT USE THIS IN PRODUCTION !!!**

## TOC
<!-- MarkdownTOC -->
- How to use
    - Editfields
    - Shortcuts
- Known issues
- Feedback / Bugs / Contribute
- Roadmap
    - Features done
    - Features planned
    - Features ideas
- Technical notes
    - MapCanvas mouseEvents hack (improved since plugin's v0.2)
    - Tools numeric input hack
    - Background snapping on vertexes / segments only
    - Free drawing on QgsMapCanvas
    - What API improvements would avoid the need of those hacks ?
    - What other QGIS improvement woud make the plugin work better
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
- Combine those with "alt" or "ctrl" to toggle locked mode.
- *C* : construction mode
- *P* : parralel / perpendicular to a segment
- *ESC* : unlock all locked parameters

## Known issues

- Several (cadinput_technical_snap_layer) entries will flood the snap setting windows (one at each project load).
- A CRS Prompt will appear at first use of the tool if "use default CRS for new layers" is not set in the options.
- The snapping radius of the tool is hard coded to 20. The best is to set your radius to 20 too so it's more usable. 
- ...

## Feedback / Bugs / Contribute

...

## Roadmap

### Features done

- [x] available with all the QGIS map tools (probably)
- [x] digitize using relative/absolute XY coordinates
- [x] digitize using relative/absolute angular coordinates
- [x] parralel/perpendicular from existing features
- [x] extend/trim a line using segment's snapping
- [x] mathematical input

### Features planned

- [ ] incremental values lock (for instance 30°, or 10m grid)
- [ ] set origin (for absolute mode with custom origin)
- [ ] intersection of segments / having segments as a true constraint (not only for parralel/perpendicular)


### Features ideas

- [ ] one-click extend/trim a line (not directly linked to CadInput -> CadTools ?)
- [ ] midpoints (can be achieved using D/2)



## Technical notes

The plugin relies on several hacks to work, since (afaik) the current QGIS API :
- does not allow to hook into MapCanvas mouse events
- does not allow numerical input for tools in scene coordinates
- does not allow to restrict background snapping on Vertexes or Segments only
- does not allow free drawing on the mapcanvas

### MapCanvas mouseEvents hack (improved since plugin's v0.2)

To be able to capture the mouseEvents of the MapCanvas, the plugin installs an eventFilter on it.

### Tools numeric input hack

Capture the mouseEvents is fine for graphical feedback, but does not allow for precise input (since mouseEvents are in pixels, and not in map units).
To workaround this limitation, the plugin creates a memory layer, in which a point is created each time a precise coordinate input is needed, to which the native tools will snap.

### Background snapping on vertexes / segments only

To achieve that result, the plugin iterates through all layers, disables their snapping, performs the snappings, and restores the snapping afterwards.
Signals are blocked during that, so that the UI is not refreshed.

### Free drawing on QgsMapCanvas
To be able to freely draw on the MapCanvas, the plugin adds a QWidget as child of the mapCanvas.
A drawback is that there is a "double cursor", the native QGIS cursor, and a CadInput-specific cursor, inducing a little bit of confusion.


### What API improvements would avoid the need of those hacks ? 

- **Have QgsMapCanvas emit signals on mouseEvents **

In current version, QgsMapCanvas emits xyCoordinates(const QgsPoint &p) on mouseMoveEvent. The same could be done for mousePressEvent and mouseReleaseEvent (maybe with better names?).

- **Allow to input scene coordinats to QgsMapTool**

For instance by adding `void QgsMapTool::scenePressEvent( QMouseEvent *e, QgsPoint *p )` (and the same for move and release events).

Or by adding an optional `scenePos *pos=0` parameter to the existing `void QgsMapTool::canvasPressEvent( QMouseEvent *e )`
This could anyways be very useful for different uses (automation ?).

The problem is, it seems the snapping/coordinate translation is implemented by each Tool subclass... So it will be some work !

- **Allow to restrict snapping for background layers, just as there is for the active layer**

Modify QgsMapCanvasSnapper's snapToBackgroundLayers method to work like snapToCurrentLayer.
`int snapToBackgroundLayers( const QPoint& p, QList<QgsSnappingResult>& results, const QList<QgsPoint>& excludePoints = QList<QgsPoint>() );` would become 
`int snapToBackgroundLayers( const QPoint& p, QList<QgsSnappingResult>& results, QgsSnapper::SnappingType snap_to, double snappingTol = -1, const QList<QgsPoint>& excludePoints = QList<QgsPoint>() );`

Alternatively, QgsSnappingResult could have a field informing wheter it was a vertex or a segment snap.

### What other QGIS improvement woud make the plugin work better

- **Click-drag tools should allow click-move-click input method**

Some tools work in click-click mode (add feature...), but some other in click-drag mode (move vertex, ...). That second method is less common in CAD softwares, since it is less practical. Those click-drag tools work currently with the plugin, but the user must keep the mouse pressed, which is a bit annoying. Allowing click-move-click mode for those tool as well would be an improvement.
    

