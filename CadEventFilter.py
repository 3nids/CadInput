# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CadInput
                                 A QGIS plugin
 Provides CAD-like input globally : digitize features with precise numerical input for the angle, the distance, and easily make constructions lines
                              -------------------
        begin                : 2014-01-15
        copyright            : (C) 2014 by Olivier Dalang
        email                : olivier.dalang@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

import math
import random

class CadEventFilter(QObject):
    """
    This class manages the events for the MapCanvas.

    It is responsible of constraining events according to the 
    inputwidget's values and to update the inputwidget's values 
    according to the constrained mouse position.
    """


    def __init__(self, iface, inputwidget):
        QObject.__init__(self)
        self.iface = iface
        self.inputwidget = inputwidget

        #input coordinates
        self.p1 = QgsPoint() # previous click, used for delta angles
        self.p2 = QgsPoint() # last click, used for delta positions
        self.p3 = QgsPoint() # current position
        self.snapSegment = None # segment snapped at current position (if any)
        self.snapPoint = None # point snapped at current position (if any)

        #snapping hack
        self.storeOtherSnapping = None #holds the layer's snapping options when snapping is suspended or None if snappig is not suspended
        self.otherSnappingStored = False


    ############################
    ##### EVENT MANAGEMENT #####
    ############################

    def eventFilter(self, obj, event):
        # We only run this if the event is spontaneous, which means that it was generated by the OS.
        # This way, the event we create below won't be processed (which would be an inifinite loop)
        if ( self.inputwidget.active and self.inputwidget.enabled and event.spontaneous() and
                    (  (event.type() == QEvent.MouseMove and event.button() != Qt.MidButton) or
                       (event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton) or
                       (event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton) ) ):
            
            # Get the snaps
            (self.snapPoint, self.snapSegment) = self._toMapSnap( event.pos() )

            # Set the current mouse position (either from snapPoint, from snapSegment, or regular coordinate transform)
            if self.snapPoint is not None:
                p3 = QgsPoint(self.snapPoint)
            elif self.snapSegment is not None:
                p3 = self.snapSegment[0]
            else:
                p3 = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( event.pos() )

            self.p3 = self._constrain(p3)


            # Depending on the mode...
            if self.inputwidget.par or self.inputwidget.per:
                #A. Set segment mode (we set the angle)
                if event.type() == QEvent.MouseButtonPress:
                    self._alignToSegment()
                elif event.type() == QEvent.MouseButtonRelease and self.snapSegment:
                    self.inputwidget.par = False
                    self.inputwidget.per = False

            else:
                #B. Input mode


                if self.inputwidget.c:
                    #B1. Construction mode
                    pass

                else:
                    #B2. Normal input mode

                    if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseButtonRelease:
                        #B2a. Mouse press input mode
                        self.createSnappingPoint()
                        modifiedEvent = QMouseEvent( event.type(), self._toPixels(self.p3), event.button(), event.buttons(), event.modifiers() )
                        QCoreApplication.sendEvent(obj,modifiedEvent)
                        self.removeSnappingPoint()

                    else:
                        #B2B. Mouse move input mode
                        modifiedEvent = QMouseEvent( event.type(), self._toPixels(self.p3), event.button(), event.buttons(), event.modifiers() )
                        QCoreApplication.sendEvent(obj,modifiedEvent)

                # We unlock all the inputs, since we don't want locking to stay for the next point (actually, sometimes we do, this could be an option)
                if event.type() == QEvent.MouseButtonRelease:
                    self.inputwidget.unlockAll()

                if event.type() == QEvent.MouseButtonRelease:
                    # In input mode (B), we register the last points for following relative calculation in case of mousePress
                    self.p1 = self.p2
                    self.p2 = self.p3


            # By returning True, we inform the eventSystem that the event must not be sent further (since a new event has been sent through QCoreApplication)
            return True
        elif self.inputwidget.active and event.type() == QEvent.KeyPress:
            # We redirect all key inputs to the inputwidget.
            # TODO : This will probably prevent all shortcuts to fail... Probably this would work : return self.inputwidget.keyPressEvent(event)
            QCoreApplication.sendEvent(self.inputwidget,event)            
            return True
        else:
            #In case we don't manage this type of event, or if it was already treated (spontaneous==False), we return the normal implementation
            return QObject.eventFilter(self, obj, event)


    ########################
    ##### CONSTRAINING #####
    ########################

    def _constrain(self, p3):
        """
        This method returns a point constrained by the w's settings and, by the way, updates the w's displayed values.
        """


        #X
        if self.inputwidget.lx:
            if self.inputwidget.rx:
                p3.setX( self.p2.x() + self.inputwidget.x )
            else:
                p3.setX( self.inputwidget.x )
   
            if self.snapSegment is not None and not self.inputwidget.ly:
                # we will magnietize to the intersection of that segment and the lockedX !
                x = p3.x()

                x1 = self.snapSegment[1].x()
                y1 = self.snapSegment[1].y()
                x2 = self.snapSegment[2].x()
                y2 = self.snapSegment[2].y()

                dx = x2 - x1
                dy = y2 - y1

                if dy==0:
                    y = y1
                else:
                    y = y1+(dy * (x-x1) ) / dx

                p3.setY( y )

        else:
            if self.inputwidget.rx:
                self.inputwidget.x = p3.x()-self.p2.x()
            else:
                self.inputwidget.x = p3.x()

        #Y
        if self.inputwidget.ly:
            if self.inputwidget.ry:
                p3.setY( self.p2.y() + self.inputwidget.y )
            else:
                p3.setY( self.inputwidget.y )

            if self.snapSegment is not None and not self.inputwidget.lx:  
                # we will magnietize to the intersection of that segment and the lockedY !              

                y = p3.y()

                x1 = self.snapSegment[1].x()
                y1 = self.snapSegment[1].y()
                x2 = self.snapSegment[2].x()
                y2 = self.snapSegment[2].y()

                dx = x2 - x1
                dy = y2 - y1

                if dy==0:
                    x = x1
                else:
                    x = x1+(dx * (y-y1) ) / dy

                p3.setX( x )
        else:
            if self.inputwidget.ry:
                self.inputwidget.y = p3.y()-self.p2.y()
            else:
                self.inputwidget.y = p3.y()

        #A
        dx =  p3.x()-self.p2.x()
        dy =  p3.y()-self.p2.y()

        if self.inputwidget.la:
            a = self.inputwidget.a/180.0*math.pi
            if self.inputwidget.ra:
                # We compute the angle relative to the last segment (0° is aligned with last segment)
                lastA = math.atan2(self.p2.y() - self.p1.y(), self.p2.x() - self.p1.x())
                a = lastA+a

            cosA = math.cos( a )
            sinA = math.sin( a )
            v1 = [ cosA, sinA ]
            v2 = [ dx, dy ]
            vP = v1[0]*v2[0]+v1[1]*v2[1]
            p3.set( self.p2.x()+cosA*vP, self.p2.y()+sinA*vP)

            if self.snapSegment is not None and not self.inputwidget.ld:  
                # we will magnietize to the intersection of that segment and the lockedAngle !

                l1 = QLineF(self.p2.x(), self.p2.y(), self.p2.x()+math.cos(a), self.p2.y()+math.sin(a))
                l2 = QLineF(self.snapSegment[1].x(), self.snapSegment[1].y(), self.snapSegment[2].x() ,self.snapSegment[2].y())

                intP = QPointF()
                ang = l1.angleTo(l2)
                t = 0.0001
                # TODO : this may cause some accuracy problem ?
                if l1.intersect(l2, intP) == QLineF.UnboundedIntersection and not (ang < t or ang > 360-t or (ang > 180-t and ang < 180+t) ):
                    p3.setX( intP.x() )
                    p3.setY( intP.y() )

        else:
            if self.inputwidget.ra:
                lastA = math.atan2(self.p2.y() - self.p1.y(), self.p2.x() - self.p1.x())
                self.inputwidget.a = (math.atan2( dy, dx )-lastA)/math.pi*180
            else:
                self.inputwidget.a = math.atan2( dy, dx )/math.pi*180



        #D
        dx =  p3.x()-self.p2.x()
        dy =  p3.y()-self.p2.y()

        if self.inputwidget.ld:
            vP = self.inputwidget.d / math.sqrt( dx*dx + dy*dy )
            p3.set( self.p2.x()+dx*vP,  self.p2.y()+dy*vP )

            if self.snapSegment is not None and not self.inputwidget.la:  
                # we will magnietize to the intersection of that segment and the lockedDistance !
                # formula taken from http://mathworld.wolfram.com/Circle-LineIntersection.html

                xo = self.p2.x()
                yo = self.p2.y()

                x1 = self.snapSegment[1].x()-xo
                y1 = self.snapSegment[1].y()-yo
                x2 = self.snapSegment[2].x()-xo
                y2 = self.snapSegment[2].y()-yo

                r = self.inputwidget.d

                dx = x2-x1
                dy = y2-y1
                dr = math.sqrt(dx**2+dy**2)
                d = x1*y2-x2*y1

                def sgn(x): return -1 if x<0 else 1

                DISC = r**2 * dr**2 - d**2

                if DISC<=0:
                    #no intersection or tangeant
                    pass
                else:
                    #first possible point
                    ax = xo  +  (d*dy+sgn(dy)*dx*math.sqrt(r**2*dr**2-d**2))/(dr**2)
                    ay = yo  +  (-d*dx+abs(dy)*math.sqrt(r**2*dr**2-d**2))/(dr**2)

                    #second possible point
                    bx = xo  +  (d*dy-sgn(dy)*dx*math.sqrt(r**2*dr**2-d**2))/(dr**2)
                    by = yo  +  (-d*dx-abs(dy)*math.sqrt(r**2*dr**2-d**2))/(dr**2)

                    #we snap to the nearest intersection
                    if (ax-p3.x())**2+(ay-p3.y())**2 >= (bx-p3.x())**2+(by-p3.y())**2:
                        p3.setX( bx )
                        p3.setY( by )
                    else:
                        p3.setX( ax )
                        p3.setY( ay )
                
                
        else:
            self.inputwidget.d = math.sqrt( dx*dx + dy*dy )

        return p3
    def _alignToSegment(self):
        """
        Set's the CadWidget's angle value to be parrelel to self.snapSegment's angle
        """

        if self.snapSegment is not None:

            angle = math.atan2( self.snapSegment[1].y()-self.snapSegment[2].y(), self.snapSegment[1].x()-self.snapSegment[2].x() )
            if self.inputwidget.ra:
                lastangle = math.atan2(self.p2.y()-self.p1.y(),self.p2.x()-self.p1.x())
                angle -= lastangle

            if self.inputwidget.par:
                pass
            elif self.inputwidget.per:
                angle += math.pi / 2.0

            self.inputwidget.la = True
            self.inputwidget.a = math.degrees(angle)      
    

    #####################################
    ##### COORDINATE TRANSFORMATIONS ####
    #####################################

    def _toMapSnap(self, qpoint):
        """
        returns the current snapped point (if any) and the current snapped segment (if any) in map coordinates
        The current snapped segment is returned as (snapped point on segment, startPoint, endPoint)

        We will :
        1) check if this snaps on a point of the current layer, if not :
        2) check if this snaps on a point of a background layer, if not :
        3) check if this snaps on a segment of the current layer, if not :
        4) check if this snaps on a segment of the background layer

        if 1 or 2) we, snap to that point, and set the segment to None
        if 3 or 4) we, we snap to that segment, and set the segment for advanced snap (if another constraint is set)

        if none, we simply map the point to the scene
        """

        #1) Snap on current layer vertex
        snapper = QgsMapCanvasSnapper(self.iface.mapCanvas())
        (reval, snapped) = snapper.snapToCurrentLayer(qpoint,QgsSnapper.SnapToVertex)
        if snapped != []:
            point = QgsPoint(snapped[0].snappedVertex.x(), snapped[0].snappedVertex.y())
            return (point, None)

        #2) Snap on background vertex
        self.disableBackgroundSnapping('vertex')        
        (reval, snapped) = snapper.snapToBackgroundLayers(qpoint)
        self.restoreBackgroundSnapping()
        if snapped != []:
            point = QgsPoint(snapped[0].snappedVertex.x(), snapped[0].snappedVertex.y())
            return (point, None)

        #3) Snap on current layer segments
        snapper = QgsMapCanvasSnapper(self.iface.mapCanvas())
        (reval, snapped) = snapper.snapToCurrentLayer(qpoint,QgsSnapper.SnapToSegment)
        if snapped != []:
            point = QgsPoint(snapped[0].snappedVertex.x(), snapped[0].snappedVertex.y())
            prevPoint = QgsPoint(snapped[0].beforeVertex.x(), snapped[0].beforeVertex.y())
            afterPoint = QgsPoint(snapped[0].afterVertex.x(), snapped[0].afterVertex.y())
            return (None, (point,prevPoint,afterPoint))

        #4) Snap on background segments
        self.disableBackgroundSnapping('segment')        
        (reval, snapped) = snapper.snapToBackgroundLayers(qpoint)
        self.restoreBackgroundSnapping()
        if snapped != []:
            point = QgsPoint(snapped[0].snappedVertex.x(), snapped[0].snappedVertex.y())
            prevPoint = QgsPoint(snapped[0].beforeVertex.x(), snapped[0].beforeVertex.y())
            afterPoint = QgsPoint(snapped[0].afterVertex.x(), snapped[0].afterVertex.y())
            return (None, (point,prevPoint,afterPoint))

        return (None, None)

    def _toPixels(self, qgspoint):
        """
        Given a point in project's coordinates, returns a point in screen (pixel) coordinates
        """
        try:
            p = self.iface.mapCanvas().getCoordinateTransform().transform( qgspoint )
            return QPoint( int(p.x()), int(p.y()) )
        except ValueError:
            #this happens sometimes at loading, it seems the mapCanvas is not ready and returns a point at NaN;NaN
            return QPoint()


    #########################
    ##### SNAPPING HACK #####
    #########################
    
    def createSnappingPoint(self):
        """
        This method creates a point that will be snapped by the next click so that the point will be at model precision and not at screen precision.
        It also disables all the other layer's snapping so they won't interfere. Those are reset in rmeoveSnapping point.
        """
        activeLayer = self.iface.activeLayer()

        #store and remove all the snapping options
        self.disableBackgroundSnapping()

        try:
            provider = self.memoryLayer.dataProvider()
        except (RuntimeError, AttributeError):
            #RuntimeError : if the user removed the layer, the underlying c++ object will be deleted
            #AttributeError : if self.memory is None
            self.cleanLayers("(cadinput_techical_snap_layer)")
            self.memoryLayer = QgsVectorLayer("point", "(cadinput_techical_snap_layer)", "memory")
            QgsMapLayerRegistry.instance().addMapLayer(self.memoryLayer, False)
            provider = self.memoryLayer.dataProvider()

        QgsProject.instance().blockSignals(True) #we don't want to refresh the snapping UI
        QgsProject.instance().setSnapSettingsForLayer(self.memoryLayer.id(),  True, QgsSnapper.SnapToVertex , QgsTolerance.Pixels, 20.0, False )
        QgsProject.instance().blockSignals(False) #we don't want to refresh the snapping UI

        feature = QgsFeature()
        feature.setGeometry( QgsGeometry.fromPoint( self.p3 ) )
        provider.addFeatures([feature])

        self.memoryLayer.updateExtents()

        self.iface.setActiveLayer(activeLayer)
    def removeSnappingPoint(self):
        """
        This methods empties the snapping layer.
        It must be called after createSnappingPoint (once the snapping has been done), since it also reenables the other layer's snapping
        """

        #empty the layer
        provider = self.memoryLayer.dataProvider()
        features = provider.getFeatures( QgsFeatureRequest() )

        for feature in features:
            provider.deleteFeatures([feature.id()])

        #In 2.2, this will be  (untested):
        #provider = self.memoryLayer.dataProvider()
        #provider.deleteFeatures( self.memoryLayer.allFeatureIds() )


        #restore the snapping options
        self.restoreBackgroundSnapping()

    def disableBackgroundSnapping(self, keepSnapping=None):
        """
        Stores (for latter restoring) and then remove all the snapping options.
        """


        if self.otherSnappingStored:
            QgsMessageLog.logMessage("WARNING : restoreBackgroundSnapping was not called before disableBackgroundSnapping ! We don't store it again...")
        else:
            self.otherSnappingStored = True
            QgsProject.instance().blockSignals(True) #we don't want to refresh the snapping UI
            self.storeOtherSnapping = dict()
            for name in QgsMapLayerRegistry.instance().mapLayers():
                layer = QgsMapLayerRegistry.instance().mapLayers()[name]
                self.storeOtherSnapping[layer.id()] = QgsProject.instance().snapSettingsForLayer(layer.id())

                if keepSnapping=='vertex':
                    QgsProject.instance().setSnapSettingsForLayer(layer.id(),True,QgsSnapper.SnapToVertex, QgsTolerance.Pixels, 20,False)
                elif keepSnapping=='segment':
                    QgsProject.instance().setSnapSettingsForLayer(layer.id(),True,QgsSnapper.SnapToSegment, QgsTolerance.Pixels, 20,False)
                else:
                    QgsProject.instance().setSnapSettingsForLayer(layer.id(),False,0,0,0,False)

            QgsProject.instance().blockSignals(False) #we don't want to refresh the snapping UI
    def restoreBackgroundSnapping(self):
        """
        Restores previously stored snapping options
        """

        self.otherSnappingStored = False

        QgsProject.instance().blockSignals(True) #we don't want to refresh the snapping UI

        for layerId in self.storeOtherSnapping:
            options = self.storeOtherSnapping[layerId]
            QgsProject.instance().setSnapSettingsForLayer(layerId,options[1],options[2],options[3],options[4],options[5])

        QgsProject.instance().blockSignals(False) #we don't want to refresh the snapping UI

    def cleanLayers(self, layernameToClean):
        """
        Cleans the old memory layers (all layer having layernameToClean for name) to avoid proliferation of unused memory layers.
        """

        # Clean the old memory layers
        for name in QgsMapLayerRegistry.instance().mapLayers():
            layer = QgsMapLayerRegistry.instance().mapLayers()[name]
            if layer.name() == layernameToClean:
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())
