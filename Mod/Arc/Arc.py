# Copyright Jan Tanja 2017
# www.arc-engines.com
# Included in this class are the functions that we will be using 
# in reference to this google spreadsheet: 
# https://docs.google.com/spreadsheets/d/1JpvR5A3rmrudutUJjEJ2Y21SHiPGYqy6VomfuhC2ZM8/edit
# Modeled after Draft.py 

# NOTE: MOST OF WORK IS ON JAN'S LOCAL WORKSTATION ( MACBOOK PRO ) 

import FreeCAD, math, sys, os, DraftVecUtils, Draft_rc, Draft, Part, DraftGeomUtils
import numpy as np


from FreeCAD import Vector


if FreeCAD.GuiUp:
    import FreeCADGui, WorkingPlane
    from PySide import QtCore
    from PySide.QtCore import QT_TRANSLATE_NOOP
    gui = True
else:
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    #print("FreeCAD Gui not present. Draft module will have some features disabled.")
    gui = False

arrowtypes = ["Dot","Circle","Arrow","Tick"]

# --------------------------------------------------------------------------------------------------------
# MAKE POINT 
# --------------------------------------------------------------------------------------------------------
def addPoint(X=0, Y=0, Z=0,color=None,name = "Point", point_size= 5):
    ''' makePoint(x,y,z ,[color(r,g,b),point_size]) or
        makePoint(Vector,color(r,g,b),point_size]) -
        creates a Point in the current document.
        example usage:
        p1 = makePoint()
        p1.ViewObject.Visibility= False # make it invisible
        p1.ViewObject.Visibility= True  # make it visible
        p1 = makePoint(-1,0,0) #make a point at -1,0,0
        p1 = makePoint(1,0,0,(1,0,0)) # color = red
        p1.X = 1 #move it in x
        p1.ViewObject.PointColor =(0.0,0.0,1.0) #change the color-make sure values are floats
    '''
    obj=FreeCAD.ActiveDocument.addObject("Part::FeaturePython",name)
    if isinstance(X,FreeCAD.Vector):
        Z = X.z
        Y = X.y
        X = X.x
    _Point(obj,X,Y,Z)
    obj.X = X
    obj.Y = Y
    obj.Z = Z
    if gui:
        _ViewProviderPoint(obj.ViewObject)
        if not color:
            color = FreeCADGui.draftToolBar.getDefaultColor('ui')
        obj.ViewObject.PointColor = (float(color[0]), float(color[1]), float(color[2]))
        obj.ViewObject.PointSize = point_size
        obj.ViewObject.Visibility = True
    select(obj)
    FreeCAD.ActiveDocument.recompute()
    return obj

# --------------------------------------------------------------------------------------------------------
# MAKE CURVE
# --------------------------------------------------------------------------------------------------------
    def addCurve(objectslist):
        """joins edges in the given objects list into wires"""
        edges = []
        for o in objectslist:
            for e in o.Shape.Edges:
                edges.append(e)
        try:
            nedges = Part.__sortEdges__(edges[:])
            # for e in nedges: print("debug: ",e.Curve,e.Vertexes[0].Point,e.Vertexes[-1].Point)
            w = Part.Wire(nedges)
        except Part.OCCError:
            return None
        else:
            if len(w.Edges) == len(edges):
                newobj = FreeCAD.ActiveDocument.addObject("Part::Feature","Wire")
                newobj.Shape = w
                addList.append(newobj)
                deleteList.extend(objectslist)
                return True
        return None

# --------------------------------------------------------------------------------------------------------
# MAKE CIRCLE
# --------------------------------------------------------------------------------------------------------
# refer to makeCircle in Draft.py
def addCircle(radius, placement=None, face=None, startangle=None, endangle=None, support=None):
    import Part, DraftGeomUtils
    if placement: typecheck([(placement,FreeCAD.Placement)], "makeCircle")
    if startangle != endangle:
        n = "Arc"
    else:
        n = "Circle"
    obj = FreeCAD.ActiveDocument.addObject("Part::Part2DObjectPython",n)
    _Circle(obj)
    if face != None:
        obj.MakeFace = face
    if isinstance(radius,Part.Edge):
        edge = radius
        if DraftGeomUtils.geomType(edge) == "Circle":
            obj.Radius = edge.Curve.Radius
            placement = FreeCAD.Placement(edge.Placement)
            delta = edge.Curve.Center.sub(placement.Base)
            placement.move(delta)
            if len(edge.Vertexes) > 1:
                ref = placement.multVec(FreeCAD.Vector(1,0,0))
                v1 = (edge.Vertexes[0].Point).sub(edge.Curve.Center)
                v2 = (edge.Vertexes[-1].Point).sub(edge.Curve.Center)
                a1 = -math.degrees(DraftVecUtils.angle(v1,ref))
                a2 = -math.degrees(DraftVecUtils.angle(v2,ref))
                obj.FirstAngle = a1
                obj.LastAngle = a2
    else:
        obj.Radius = radius
        if (startangle != None) and (endangle != None):
            if startangle == -0: startangle = 0
            obj.FirstAngle = startangle
            obj.LastAngle = endangle
    obj.Support = support
    if placement: obj.Placement = placement
    if gui:
        _ViewProviderDraft(obj.ViewObject)
        formatObject(obj)
        select(obj)
    FreeCAD.ActiveDocument.recompute()
    return obj

# --------------------------------------------------------------------------------------------------------
# MAKE PLANE 
# --------------------------------------------------------------------------------------------------------

def addPlane(length, height, placement=None, face=None, support=None):
    # refer to makeRectangle in Draft 
    if placement: typecheck([(placement,FreeCAD.Placement)], "makeRectangle")
    obj = FreeCAD.ActiveDocument.addObject("Part::Part2DObjectPython","Rectangle")
    _Rectangle(obj)

    obj.Length = length
    obj.Height = height
    obj.Support = support
    if face != None:
        obj.MakeFace = face
    if placement: obj.Placement = placement
    if gui:
        _ViewProviderRectangle(obj.ViewObject)
        formatObject(obj)
        select(obj)
    FreeCAD.ActiveDocument.recompute()
    return obj

# --------------------------------------------------------------------------------------------------------
# POLAR()
# --------------------------------------------------------------------------------------------------------
# this function actually converts cartesian in R3 to spherical in R3, not cartesian in R2 to polar in R2

def Polar(X, Y, Z):
    
    foobar = X**2 + Y**2
    _r = math.sqrt(foobar + Z**2)               # r
    _theta = math.atan2(Z,math.sqrt(foobar))     # theta
    _phi = math.atan2(Y,X)                           # phi
    return _r, _theta, _phi

# --------------------------------------------------------------------------------------------------------
# CenterOfMass 
# --------------------------------------------------------------------------------------------------------
# calls in function calculatePlacement from draftgeomutils

def CenterOfMass(shape):

    return DraftGeomUtils.calculatePlacement(shape)

# --------------------------------------------------------------------------------------------------------
# MomentOfInertia() for a curve/surface
# --------------------------------------------------------------------------------------------------------
# this also substitutes as a function for 2nd moment of inertia, and eventually 3rd moment of inertia 

def MomentOfInertia():

    return