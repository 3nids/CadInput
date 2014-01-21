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
import math
import ast
import operator as op
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *


class GhostWidget(QWidget):
    """
    This class is a transparent Widget in from of the QMapCanvas.
    It captures all mouse input, displays the cad-like input drawing aid and sends translated mouse events to QMapCanvas
    """

    def __init__(self, iface, cadwidget):
        QWidget.__init__(self)
        self.iface = iface
        self.cadwidget = cadwidget

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

        self.suspendForPan = False

        self.constructionsInc = 0
        self.segment = None

        self.p1 = QgsPoint() # previous click
        self.p2 = QgsPoint() # last click
        self.p3 = QgsPoint() # current position

        self.x = 0
        self.y = 0
        self.d = 0
        self.a = 0

    def _active(self):
        return self.cadwidget.c or (self.iface.mapCanvas().mapTool() is not None and self.iface.mapCanvas().mapTool().isEditTool())

    ###########################
    ##### INPUT EVENTS ########
    ###########################

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.suspendForPan and self._active():
            #CADINPUT is active


            if self.cadwidget.par or self.cadwidget.per:
                self.segment = self.toSegment( event.pos() )
                QgsMessageLog.logMessage("found segment "+str(self.segment),"CadInput")
                self.alignToSegment()

            else:
                self.p3 = self.manageP3(self.toMap( event.pos() ) )

                if self.cadwidget.c:
                    self.constructionsInc = min(self.constructionsInc+1, 2)

                else:
                    event = QMouseEvent( event.type(), self.toPixels(self.p2), event.button(), event.buttons(), event.modifiers() )
                    self.iface.mapCanvas().mousePressEvent(event)
                    self.constructionsInc = max(self.constructionsInc-1, 0)

                self.p1 = self.p2
                self.p2 = self.p3

        else:
            #CADINPUT is inactive, simply forward event to mapCanvas
            if event.button() == Qt.MidButton:
                self.suspendForPan = True
            self.iface.mapCanvas().mousePressEvent(event)
    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton and not self.suspendForPan and self._active():
            #CADINPUT is active

            if self.cadwidget.par or self.cadwidget.per:
                if self.segment is not None:
                    self.cadwidget.par = False
                    self.cadwidget.per = False
            else:
                if event.button() != Qt.MidButton:
                    self.cadwidget.unlockAll()

                if self.cadwidget.c and self.segment is not None:
                    pass
                else:
                    event = QMouseEvent( event.type(), self.toPixels(self.p2), event.button(), event.buttons(), event.modifiers() )
                    self.iface.mapCanvas().mouseReleaseEvent(event)

        else:
            #CADINPUT is inactive, simply forward event to mapCanvas
            if event.button() == Qt.MidButton:
                self.suspendForPan = False
            self.iface.mapCanvas().mouseReleaseEvent(event)
    def mouseMoveEvent(self, event):

        if not self.suspendForPan and self._active():
            #CADINPUT is active

            if self.cadwidget.par or self.cadwidget.per:

                self.segment = self.toSegment( event.pos() )
            else:
                self.p3 = self.manageP3(self.toMap( event.pos() ))

                if self.cadwidget.c:
                    pass
                else:
                    event = QMouseEvent( event.type(), self.toPixels(self.p3), event.button(), event.buttons(), event.modifiers() )
                    self.iface.mapCanvas().mouseMoveEvent(event)

            self.update() #runs paintEvent

        else:
            #CADINPUT is inactive, simply forward event to mapCanvas
            self.iface.mapCanvas().mouseMoveEvent(event)
    def wheelEvent(self, event):
        self.iface.mapCanvas().wheelEvent(event)
    def keyPressEvent(self, event):
        """
        Shortcuts to the cadwidget
        """
        self.cadwidget.keyPressEvent(event)
        if not event.isAccepted():
            self.iface.mapCanvas().keyPressEvent(event)




    ###############################
    ##### COORDINATE TOOLS ########
    ###############################

    def manageP3(self, p3):
        """
        This method returns a point constrained by the w's settings and, by the way, updates the w's displayed values.
        """


        #X
        if self.cadwidget.lx:
            if self.cadwidget.rx:
                p3.setX( self.p2.x() + self.cadwidget.x )
            else:
                p3.setX( self.cadwidget.x )
        else:
            if self.cadwidget.rx:
                self.cadwidget.x = p3.x()-self.p2.x()
            else:
                self.cadwidget.x = p3.x()

        #Y
        if self.cadwidget.ly:
            if self.cadwidget.ry:
                p3.setY( self.p2.y() + self.cadwidget.y )
            else:
                p3.setY( self.cadwidget.y )
        else:
            if self.cadwidget.ry:
                self.cadwidget.y = p3.y()-self.p2.y()
            else:
                self.cadwidget.y = p3.y()


        #A
        dx =  p3.x()-self.p2.x()
        dy =  p3.y()-self.p2.y()

        if self.cadwidget.la:
            a = self.cadwidget.a/180.0*math.pi
            if self.cadwidget.ra:
                # We compute the angle relative to the last segment (0° is aligned with last segment)
                lastA = math.atan2(self.p2.y() - self.p1.y(), self.p2.x() - self.p1.x())
                a = lastA+a
                cosA = math.cos( a )
                sinA = math.sin( a )
                v1 = [ cosA, sinA ]
                v2 = [ dx, dy ]
                vP = v1[0]*v2[0]+v1[1]*v2[1]
                p3.set( self.p2.x()+cosA*vP, self.p2.y()+sinA*vP)
            else:
                # We compute the absolute angle (0° is horizontal to the right)
                cosA = math.cos( a )
                sinA = math.sin( a )
                v1 = [ cosA, sinA ]
                v2 = [ dx, dy ]
                vP = v1[0]*v2[0]+v1[1]*v2[1]
                p3.set( self.p2.x()+cosA*vP, self.p2.y()+sinA*vP)
        else:
            if self.cadwidget.ra:
                lastA = math.atan2(self.p2.y() - self.p1.y(), self.p2.x() - self.p1.x())
                self.cadwidget.a = (math.atan2( dy, dx )-lastA)/math.pi*180
            else:
                self.cadwidget.a = math.atan2( dy, dx )/math.pi*180


        #D
        dx =  p3.x()-self.p2.x()
        dy =  p3.y()-self.p2.y()

        if self.cadwidget.ld:
            vP = self.cadwidget.d / math.sqrt( dx*dx + dy*dy )
            p3.set( self.p2.x()+dx*vP,  self.p2.y()+dy*vP )
        else:
            self.cadwidget.d = math.sqrt( dx*dx + dy*dy )

        return p3
    def toMap(self, qpoint):
        snapper = QgsMapCanvasSnapper(self.iface.mapCanvas())

        (reval, snapped) = snapper.snapToCurrentLayer(qpoint,QgsSnapper.SnapToVertex)
        if snapped == []:
            (reval, snapped) = snapper.snapToBackgroundLayers(qpoint)

        if snapped != []:
            # It seems to be necessary to create a new QgsPoint from the snapping result
            return QgsPoint(snapped[0].snappedVertex.x(), snapped[0].snappedVertex.y())

        return self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates( qpoint )
    def toPixels(self, qgspoint):
        try:
            p = self.iface.mapCanvas().getCoordinateTransform().transform( qgspoint )
            return QPoint( int(p.x()), int(p.y()) )
        except ValueError:
            #this happens sometimes at loading, it seems the mapCanvas is not ready and returns a point at NaN;NaN
            return QPoint()
    def toSegment(self, qpoint):
        snapper = QgsMapCanvasSnapper(self.iface.mapCanvas())

        (reval, snapped) = snapper.snapToCurrentLayer(qpoint,QgsSnapper.SnapToSegment)
        if snapped == []:
            (reval, snapped) = snapper.snapToBackgroundLayers(qpoint)

        if snapped != []:
            return snapped[0]

    def alignToSegment(self):

        if self.segment is not None:

            angle = math.atan2( self.segment.beforeVertex.y()-self.segment.afterVertex.y(), self.segment.beforeVertex.x()-self.segment.afterVertex.x() )
            if self.cadwidget.ra:
                lastangle = math.atan2(self.p2.y()-self.p1.y(),self.p2.x()-self.p1.x())
                angle -= lastangle

            if self.cadwidget.par:
                pass
            elif self.cadwidget.per:
                angle += math.pi / 2.0

            self.cadwidget.la = True
            self.cadwidget.a = math.degrees(angle)      
    

    #######################
    ##### PAINTING ########
    #######################

    def _t(self, qgspoint):
        return self.iface.mapCanvas().getCoordinateTransform().transform(qgspoint)
    def _tX(self, x):
        return self._t(QgsPoint(x,0)).x()
    def _tY(self, y):
        return self._t(QgsPoint(0,y)).y()
    def _f(self, v):
        return v/self.iface.mapCanvas().getCoordinateTransform().mapUnitsPerPixel()

    def paintEvent(self, paintEvent):

        if math.isnan( self._tX(0) ) or not self._active():
            #on loading QGIS, it seems QgsMapToPixel is not ready and return NaNs...
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        pNeutral = QPen(QColor(0,0,100,100), 1)  
        pLocked = QPen(QColor(100,100,255, 150), 2, Qt.DashLine) 
        pConstruction = QPen(QColor(100,255,100, 225), 2, Qt.DashLine)

        if (self.cadwidget.per or self.cadwidget.par) and self.segment is not None:
            painter.setPen( pConstruction )           

            painter.drawLine(   self._tX( self.segment.beforeVertex.x()),
                                self._tY( self.segment.beforeVertex.y()),
                                self._tX( self.segment.afterVertex.x()),
                                self._tY( self.segment.afterVertex.y())  )

        #Draw angle
        if self.cadwidget.la:

            if self.cadwidget.ra:                
                a0 = math.atan2( -(self.p2.y()-self.p1.y()), self.p2.x()-self.p1.x() )
                a = a0-math.radians(self.cadwidget.a)
            else:
                a0 = 0
                a = -math.radians(self.cadwidget.a)

            painter.setPen( pNeutral )
            painter.drawArc(    self._tX( self.p2.x())-20,
                                self._tY( self.p2.y())-20,
                                40, 40,
                                16*math.degrees(-a0),
                                16*self.cadwidget.a  )
            painter.drawLine(   self._tX( self.p2.x()),
                                self._tY( self.p2.y()),
                                self._tX( self.p2.x())+60*math.cos(a0),
                                self._tY( self.p2.y())+60*math.sin(a0)  )

            painter.setPen( pLocked )
            painter.drawLine(   self._tX( self.p2.x())-self.width()*math.cos(a),
                                self._tY( self.p2.y())-self.width()*math.sin(a),
                                self._tX( self.p2.x())+self.width()*math.cos(a),
                                self._tY( self.p2.y())+self.width()*math.sin(a)  )



        #Draw distance
        if self.cadwidget.ld:
            painter.setPen( pLocked )
            painter.drawEllipse(    self._tX( self.p2.x() - self.cadwidget.d ),
                                    self._tY( self.p2.y() + self.cadwidget.d ),
                                    self._f( 2.0*self.cadwidget.d ),
                                    self._f( 2.0*self.cadwidget.d )  )


        #Draw x
        if self.cadwidget.lx:
            painter.setPen( pLocked )
            if self.cadwidget.rx:
                x = self._tX( self.p2.x()+self.cadwidget.x )
            else:   
                x = self._tX( self.cadwidget.x )
            painter.drawLine(   x,
                                0,
                                x,
                                self.height() )

        #Draw y
        if self.cadwidget.ly:
            painter.setPen( pLocked )
            if self.cadwidget.ry:
                y = self._tY( self.p2.y()+self.cadwidget.y )
            else:   
                y = self._tY( self.cadwidget.y )
            painter.drawLine(   0,
                                y,
                                self.width(),
                                y )

        #Draw constr
        painter.setPen( pConstruction )
        if self.cadwidget.c or self.constructionsInc > 0:
            painter.drawLine(   self._tX( self.p2.x()),
                                self._tY( self.p2.y()),
                                self._tX( self.p3.x()),
                                self._tY( self.p3.y())  )

            if self.cadwidget.c or self.constructionsInc > 1:
                painter.drawLine(   self._tX( self.p1.x()),
                                    self._tY( self.p1.y()),
                                    self._tX( self.p2.x()),
                                    self._tY( self.p2.y())  )


        painter.drawLine(   self._tX( self.p3.x())-5,
                            self._tY( self.p3.y())-5,
                            self._tX( self.p3.x())+5,
                            self._tY( self.p3.y())+5  )
        painter.drawLine(   self._tX( self.p3.x())-5,
                            self._tY( self.p3.y())+5,
                            self._tX( self.p3.x())+5,
                            self._tY( self.p3.y())-5  )




