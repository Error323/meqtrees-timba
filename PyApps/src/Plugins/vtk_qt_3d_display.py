#!/usr/bin/env python

#% $Id$ 

#
# Copyright (C) 2006
# ASTRON (Netherlands Foundation for Research in Astronomy)
# and The MeqTree Foundation
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands, seg@astron.nl
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# modules that are imported

import sys
import random
import qt
import traceback
from math import *

#test if vtk has been installed
global has_vtk
has_vtk = False
try:
  import vtk
  from vtk.qt.QVTKRenderWindowInteractor import *
  #from vtk.util.vtkImageImportFromArray import *
  from vtkImageImportFromNumarray import *
  has_vtk = True
except:
  print 'Exception while importing vtk module:'
  traceback.print_exc();

from Timba.dmi import *
from Timba import utils
from Timba.GUI.pixmaps import pixmaps
from Timba.GUI import widgets
from Timba.GUI.browsers import *
from Timba.Plugins.ResultsRange import *
from Timba import Grid
import numarray 

rendering_control_instructions = \
'''
You can interact directly with the 3-dimensional VTK display by using your the left, middle and right mouse buttons. <br><br>
Button 1 (Left): Rotates the camera around its focal point. The rotation is in the direction defined from the center of the renderer's viewport towards the mouse position.<br><br>
Button 2 (Middle): Pans the camera. The direction of motion is the direction the mouse moves. (Note: with 2-button mice, pan is defined as 'Shift'-Button 1.)<br><br>
Button 3 (Right): Zooms the camera. Moving the mouse from the top to the bottom of the display causes the camera to appear to move away from the display (zoom out). Moving the mouse from the bottom to the top of the display causes the camera to appear to move toward the display (zoom in).<br><br>
You can control and select the active plane to be moved by means of the spinbox and slider widgets shown beneath the 3-dimensional display. The text to the left of the spinbox tells which axis/plane is active. Moving the slider or clicking the spinbox will cause the active plane to move so that you can see how the data changes as you move through the cube.<br><br>
Since VTK uses the right mouse button to control the camera zoom in the 3-D display, you cannot obtain a context menu directly within the 3-D display. However, by right clicking in the area near the spinbox and slider, you will obtain a context menu. This menu will allow you to change to a new active plane, switch back to the 2-dimensional display or print a copy of the display to a Postscript file.<br><br>
Hardcopy printing is a bit primitive at present; essentially you get a screenshot of the display. So if you want a reasonably sized hardcopy you need to float the display widget from the MeqBrowser and resize it with your mouse to be larger.<br><br>
'''
if has_vtk:
  class MEQ_QVTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    """ We override the default QVTKRenderWindowInteractor
        class in order to add an extra method
    """
    def __init__(self, parent=None, name=None, *args, **kw):
      if not has_vtk:
        return None
      QVTKRenderWindowInteractor.__init__(self,parent,name,*args,**kw)

    def contextMenuEvent(self,ev):
      """ This function is necessary when a QVTKRenderWindowInteractor
          is embedded inside the MeqTrees browser. Any higher-level 
          context menu is now ignored when the right mouse
          button is clicked inside the QVTKRenderWindowInteractor.
      """
      ev.accept()

class vtk_qt_3d_display(qt.QWidget):

  def __init__( self, *args ):
    if not has_vtk:
      return None
    qt.QWidget.__init__(self, *args)
#    self.resize(640,640)
#=============================
# VTK code to create test array
#=============================
    self.complex_plot = False
    self.toggle_ND_Controller = 1
    self.button_hide = None
    self.image_array = None
    self.iteration = 0
    self.renwininter = None
    self.warped_surface = False
    self.scale_factor = 50
    self.data_min = 1000000.0
    self.data_max = -1000000.0

    self.setCaption("VTK 3D Demo")

#-----------------------------
    self.winlayout = qt.QVBoxLayout(self,20,20,"WinLayout")
#-----------------------------
    self.winsplitter = qt.QSplitter(self,"WinSplitter")
    self.winsplitter.setOrientation(qt.QSplitter.Vertical)
    self.winsplitter.setHandleWidth(10)
    self.winlayout.addWidget(self.winsplitter)
#-----------------------------

# create VBox for controls
    self.v_box_controls = qt.QVBox(self.winsplitter)

# spinbox / slider control GUI
    self.index_selector = ResultsRange(self.v_box_controls)
    self.index_selector.setStringInfo(' selector index ')
    self.index_selector.init3DContextmenu()
    offset_index = 0
    self.index_selector.set_offset_index(offset_index)
# create connections from spinbox / slider control GUI
# context menu to callbacks
    qt.QObject.connect(self.index_selector,PYSIGNAL("postscript_requested"),self.CaptureImage)
    qt.QObject.connect(self.index_selector,PYSIGNAL("update_requested"),self.testEvent)
    qt.QObject.connect(self.index_selector,PYSIGNAL("X_axis_selected"),self.AlignXaxis)
    qt.QObject.connect(self.index_selector,PYSIGNAL("Y_axis_selected"),self.AlignYaxis)
    qt.QObject.connect(self.index_selector,PYSIGNAL("Z_axis_selected"),self.AlignZaxis)
    qt.QObject.connect(self.index_selector,PYSIGNAL("show_ND_Controller"),self.hide_Event)
    qt.QObject.connect(self.index_selector,PYSIGNAL('result_index'), self.SetSlice)
    qt.QObject.connect(self.index_selector,PYSIGNAL('twoD_display_requested'), self.two_D_Event)
    qt.QObject.connect(self.index_selector,PYSIGNAL('align_camera'), self.AlignCamera)

  def delete_vtk_renderer(self):
    if not self.renwininter is None:
      self.renwininter.reparent(QWidget(), 0, QPoint()) 
    self.renwininter = None
    self.image_array = None

  def hide_vtk_controls(self):
    self.v_box_controls.hide()

  def show_vtk_controls(self):
    self.v_box_controls.show()

  def set_initial_display(self):
    if self.renwininter is None:
      self.renwininter = MEQ_QVTKRenderWindowInteractor(self.winsplitter)
      qt.QWhatsThis.add(self.renwininter, rendering_control_instructions)
      self.renwin = self.renwininter.GetRenderWindow()
      self.inter = self.renwin.GetInteractor()
      self.winsplitter.moveToFirst(self.renwininter)
      self.winsplitter.moveToLast(self.v_box_controls)
      self.winsplitter.setSizes([500,100])
      self.renwininter.show()

    self.extents =  self.image_array.GetDataExtent()
    self.spacing = self.image_array.GetDataSpacing()
    self.origin = self.image_array.GetDataOrigin()

# An outline is shown for context.
    if self.warped_surface:
      self.index_selector.initWarpContextmenu()
      xMin, xMax, yMin, yMax, zMin, zMax = self.image_array.GetDataExtent()
      self.scale_factor = 0.5 * ((xMax-xMin) + (yMax-yMin)) / (self.data_max - self.data_min)
      zMin = self.data_min * self.scale_factor
      zMax = self.data_max * self.scale_factor
      self.outline = vtk.vtkOutlineSource();
      self.outline.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
    else:
      self.index_selector.init3DContextmenu()
      self.outline = vtk.vtkOutlineFilter()
      self.outline.SetInput(self.image_array.GetOutput())
    outlineMapper = vtk.vtkPolyDataMapper();
    outlineMapper.SetInput(self.outline.GetOutput() );
    outlineActor = vtk.vtkActor();
    outlineActor.SetMapper(outlineMapper);

# create blue to red color table
    self.lut = vtk.vtkLookupTable()
    self.lut.SetHueRange(0.6667, 0.0)
    self.lut.SetNumberOfColors(256)
    self.lut.Build()

# here is where the 2-D image gets warped
    if self.warped_surface:
      geometry = vtk.vtkImageDataGeometryFilter()
      geometry.SetInput(self.image_array.GetOutput())
      self.warp = vtk.vtkWarpScalar()
      self.warp.SetInput(geometry.GetOutput())
      self.warp.SetScaleFactor(self.scale_factor)
      self.mapper = vtk.vtkPolyDataMapper();
      self.mapper.SetInput(self.warp.GetPolyDataOutput())
      self.mapper.SetScalarRange(self.data_min,self.data_max)
      self.mapper.SetLookupTable(self.lut)
      self.mapper.ImmediateModeRenderingOff()
      warp_actor = vtk.vtkActor()
      warp_actor.SetMapper(self.mapper)

      min_range = 0.5 * self.scale_factor
      max_range = 2.0 * self.scale_factor
      self.index_selector.set_emit(False)
      self.index_selector.setMaxValue(max_range,False)
      self.index_selector.setMinValue(min_range)
      self.index_selector.setTickInterval( (max_range - min_range) / 10 )
      self.index_selector.setRange(max_range, False)
      self.index_selector.setValue(self.scale_factor)
      self.index_selector.setLabel('scale factor')
      self.index_selector.hideNDControllerOption()
      self.index_selector.set_emit(True)
    else:
# set up ImagePlaneWidgets ...

# The shared picker enables us to use 3 planes at one time
# and gets the picking order right
      picker = vtk.vtkCellPicker()
      picker.SetTolerance(0.005)

# get locations for initial slices
      xMin, xMax, yMin, yMax, zMin, zMax =  self.extents
      x_index = (xMax-xMin) / 2
      y_index = (yMax-yMin) / 2
      z_index = (zMax-zMin) / 2

# The 3 image plane widgets are used to probe the dataset.
      self.planeWidgetX = vtk.vtkImagePlaneWidget()
      self.planeWidgetX.DisplayTextOn()
      self.planeWidgetX.SetInput(self.image_array.GetOutput())
      self.planeWidgetX.SetPlaneOrientationToXAxes()
      self.planeWidgetX.SetSliceIndex(x_index)
      self.planeWidgetX.SetPicker(picker)
      self.planeWidgetX.SetKeyPressActivationValue("x")
      self.planeWidgetX.SetLookupTable(self.lut)
      self.planeWidgetX.TextureInterpolateOff()
      self.planeWidgetX.SetResliceInterpolate(0)

      self.planeWidgetY = vtk.vtkImagePlaneWidget()
      self.planeWidgetY.DisplayTextOn()
      self.planeWidgetY.SetInput(self.image_array.GetOutput())
      self.planeWidgetY.SetPlaneOrientationToYAxes()
      self.planeWidgetY.SetSliceIndex(y_index)
      self.planeWidgetY.SetPicker(picker)
      self.planeWidgetY.SetKeyPressActivationValue("y")
      self.planeWidgetY.SetLookupTable(self.planeWidgetX.GetLookupTable())
      self.planeWidgetY.TextureInterpolateOff()
      self.planeWidgetY.SetResliceInterpolate(0)

# for the z-slice, turn off texture interpolation:
# interpolation is now nearest neighbour, to demonstrate
# cross-hair cursor snapping to pixel centers
      self.planeWidgetZ = vtk.vtkImagePlaneWidget()
      self.planeWidgetZ.DisplayTextOn()
      self.planeWidgetZ.SetInput(self.image_array.GetOutput())
      self.planeWidgetZ.SetPlaneOrientationToZAxes()
      self.planeWidgetZ.SetSliceIndex(z_index)
      self.planeWidgetZ.SetPicker(picker)
      self.planeWidgetZ.SetKeyPressActivationValue("z")
      self.planeWidgetZ.SetLookupTable(self.planeWidgetX.GetLookupTable())
      self.planeWidgetZ.TextureInterpolateOff()
      self.planeWidgetZ.SetResliceInterpolate(0)
    
      self.current_widget = self.planeWidgetZ
      self.mode_widget = self.planeWidgetZ
      self.index_selector.set_emit(False)
      self.index_selector.setMinValue(zMin)
      self.index_selector.setMaxValue(zMax,False)
      self.index_selector.setTickInterval( (zMax-zMin) / 10 )
      self.index_selector.setRange(zMax, False)
      self.index_selector.setValue(z_index)
      self.index_selector.setLabel('Z axis')
      self.index_selector.set_emit(True)

# create scalar bar for display of intensity range
    self.scalar_bar = vtk.vtkScalarBarActor()
    self.scalar_bar.SetLookupTable(self.lut)
    self.scalar_bar.SetOrientationToVertical()
    self.scalar_bar.SetWidth(0.1)
    self.scalar_bar.SetHeight(0.8)
    self.scalar_bar.SetTitle("Intensity")
    self.scalar_bar.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
#   self.scalar_bar.GetPositionCoordinate().SetCoordinateSystemToViewport()
    self.scalar_bar.GetPositionCoordinate().SetValue(0.01, 0.1)


# Create the RenderWindow and Renderer
    self.ren = vtk.vtkRenderer()
    self.renwin.AddRenderer(self.ren)
    
# Add the outline actor to the renderer, set the background color and size
    if self.warped_surface:
      self.ren.AddActor(warp_actor)
    self.ren.AddActor(outlineActor)
    self.ren.SetBackground(0.1, 0.1, 0.2)
    self.ren.AddActor2D(self.scalar_bar)

# Create a text property for cube axes
    tprop = vtk.vtkTextProperty()
    tprop.SetColor(1, 1, 1)
    tprop.ShadowOn()

# Create a vtkCubeAxesActor2D.  Use the outer edges of the bounding box to
# draw the axes.  Add the actor to the renderer.
    self.axes = vtk.vtkCubeAxesActor2D()
    if self.warped_surface:
      self.axes.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
    else:
      self.axes.SetInput(self.image_array.GetOutput())
    self.axes.SetCamera(self.ren.GetActiveCamera())
    self.axes.SetLabelFormat("%6.4g")
    self.axes.SetFlyModeToOuterEdges()
    self.axes.SetFontFactor(0.8)
    self.axes.SetAxisTitleTextProperty(tprop)
    self.axes.SetAxisLabelTextProperty(tprop)
    self.axes.SetXLabel("X")
    self.axes.SetYLabel("Y")
    self.axes.SetZLabel("Z")
    self.ren.AddProp(self.axes)

# Set the interactor for the widgets
    if not self.warped_surface:
      self.planeWidgetX.SetInteractor(self.inter)
      self.planeWidgetX.On()
      self.planeWidgetY.SetInteractor(self.inter)
      self.planeWidgetY.On()
      self.planeWidgetZ.SetInteractor(self.inter)
      self.planeWidgetZ.On()

# Create an initial interesting view
    cam1 = self.ren.GetActiveCamera()
    cam1.Azimuth(45)
    if self.warped_surface:
      cam1.Elevation(30)
      xMin, xMax, yMin, yMax, zMin, zMax = self.image_array.GetDataExtent()
      cx = 0.5*(xMax-xMin)
      cy = 0.5*(yMax-yMin)
      cz = 0
      cam1.SetFocalPoint(cx, cy, cz)
# following statement does something really nasty here!
#     cam1.SetPosition(cx,cy, cz)
#     cam1.Zoom(-2)
    else:
      cam1.Elevation(110)
      cam1.SetViewUp(0, 0, 1)
    cam1.ParallelProjectionOn()
    self.ren.ResetCamera()
    self.ren.ResetCameraClippingRange()

# Paul Kemper suggested the following:
    camstyle = vtk.vtkInteractorStyleTrackballCamera()
    self.renwininter.SetInteractorStyle(camstyle)

# Align the camera so that it faces the desired widget
  def AlignCamera(self):
    xMin, xMax, yMin, yMax, zMin, zMax = self.extents
    ox, oy, oz = self.origin
    sx, sy, sz = self.spacing
    cx = ox+(0.5*(xMax-xMin))*sx
    cy = oy+(0.5*(yMax-yMin))*sy
    cz = oz+(0.5*(zMax-zMin))*sz
    vx, vy, vz = 0, 0, 0
    nx, ny, nz = 0, 0, 0
    iaxis = self.current_widget.GetPlaneOrientation()
    slice_number = self.current_widget.GetSliceIndex()
    if iaxis == 0:
        vz = -1
        nx = ox + xMax*sx
        cx = ox + slice_number*sx
    elif iaxis == 1:
        vz = -1
        ny = oy+yMax*sy
        cy = oy+slice_number*sy
    else:
        vy = 1
        nz = oz+zMax*sz
        cz = oz+slice_number*sz
 
    px = cx+nx*2
    py = cy+ny*2
    pz = cz+nz*3

    camera = self.ren.GetActiveCamera()
    camera.SetFocalPoint(cx, cy, cz)
    camera.SetPosition(px, py, pz)
    camera.ComputeViewPlaneNormal()
    camera.SetViewUp(vx, vy, vz)
    camera.OrthogonalizeViewUp()
#    self.ren.ResetCameraClippingRange()
    self.ren.ResetCamera()
    self.renwin.Render()
 
# Capture the display to a Postscript file
  def CaptureImage(self):
    if not self.image_array is None:
      w2i = vtk.vtkWindowToImageFilter()
      writer = vtk.vtkPostScriptWriter()
      w2i.SetInput(self.renwin)
      w2i.Update()
      writer.SetInput(w2i.GetOutput())
      writer.SetFileName("image.ps")
      self.renwin.Render()
      writer.Write()

# Align the widget back into orthonormal position,
# set the slider to reflect the widget's position,
# call AlignCamera to set the camera facing the widget
  def AlignXaxis(self):
    xMin, xMax, yMin, yMax, zMin, zMax =  self.extents
    slice_number = None
    po = self.planeWidgetX.GetPlaneOrientation()
    if po == 3:
        self.planeWidgetX.SetPlaneOrientationToXAxes()
        slice_number = (xMax-xMin)/2
        self.planeWidgetX.SetSliceIndex(slice_number)
    else:
        slice_number = self.planeWidgetX.GetSliceIndex()
 
    self.current_widget = self.planeWidgetX
    self.index_selector.set_emit(False)
    self.index_selector.setMinValue(xMin)
    self.index_selector.setMaxValue(xMax,False)
    self.index_selector.setRange(xMax, False)
    self.index_selector.setValue(slice_number)
    self.index_selector.setTickInterval( (xMax-xMin) / 10 )
    self.index_selector.setLabel('X axis')
    self.index_selector.set_emit(True)
#   self.AlignCamera()

  def AlignYaxis(self):
    xMin, xMax, yMin, yMax, zMin, zMax =  self.extents
    slice_number = None
    po = self.planeWidgetY.GetPlaneOrientation()
    if po == 3:
        self.planeWidgetY.SetPlaneOrientationToYAxes()
        slice_number = (yMax-yMin)/2
        self.planeWidgetY.SetSliceIndex(slice_number)
    else:
        slice_number = self.planeWidgetY.GetSliceIndex()
 
    self.current_widget = self.planeWidgetY
    self.index_selector.set_emit(False)
    self.index_selector.setMinValue(yMin)
    self.index_selector.setMaxValue(yMax,False)
    self.index_selector.setRange(yMax, False)
    self.index_selector.setValue(slice_number)
    self.index_selector.setTickInterval( (yMax-yMin) / 10 )
    self.index_selector.setLabel('Y axis')
    self.index_selector.set_emit(True)
#   self.AlignCamera()
 
  def AlignZaxis(self):
    xMin, xMax, yMin, yMax, zMin, zMax =  self.extents
    slice_number = None
    po = self.planeWidgetZ.GetPlaneOrientation()
    if po == 3:
        self.planeWidgetZ.SetPlaneOrientationToZAxes()
        slice_number = (zMax-zMin)/2
        self.planeWidgetZ.SetSliceIndex(slice_number)
    else:
        slice_number = self.planeWidgetZ.GetSliceIndex()
 
    self.current_widget = self.planeWidgetZ
    self.index_selector.set_emit(False)
    self.index_selector.setMinValue(zMin)
    self.index_selector.setMaxValue(zMax,False)
    self.index_selector.setRange(zMax, False)
    self.index_selector.setValue(slice_number)
    self.index_selector.setTickInterval((zMax-zMin) / 10 )
    self.index_selector.setLabel('Z axis')
    self.index_selector.set_emit(True)
#   self.AlignCamera()

  def SetSlice(self, sl):
    if self.warped_surface:
      self.scale_factor = sl
      xMin, xMax, yMin, yMax, zMin, zMax = self.image_array.GetDataExtent()
#     self.scale_factor = 0.5 * ((xMax-xMin) + (yMax-yMin)) / (self.data_max - self.data_min)
      zMin = self.data_min * self.scale_factor
      zMax = self.data_max * self.scale_factor
      self.outline.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
      self.axes.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
      self.warp.SetScaleFactor(self.scale_factor)
    else:
      self.current_widget.SetSliceIndex(sl)
      self.ren.ResetCameraClippingRange()
    self.renwin.Render()

  def UpdateBounds(self):
    if self.warped_surface:
      xMin, xMax, yMin, yMax, zMin, zMax = self.image_array.GetDataExtent()
      self.scale_factor = 0.5 * ((xMax-xMin) + (yMax-yMin)) / (self.data_max - self.data_min)
      zMin = self.data_min * self.scale_factor
      zMax = self.data_max * self.scale_factor
      self.outline.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
      self.axes.SetBounds(xMin, xMax, yMin, yMax, zMin, zMax)
      self.warp.SetScaleFactor(self.scale_factor)
      self.mapper.SetScalarRange(self.data_min,self.data_max)

      min_range = 0.5 * self.scale_factor
      max_range = 2.0 * self.scale_factor
      self.index_selector.set_emit(False)
      self.index_selector.setMaxValue(max_range,False)
      self.index_selector.setMinValue(min_range)
      self.index_selector.setTickInterval( (max_range - min_range) / 10 )
      self.index_selector.setRange(max_range, False)
      self.index_selector.setValue(self.scale_factor)
      self.index_selector.setLabel('scale factor')
      self.index_selector.set_emit(True)


#=============================
# VTK code for test arrays
#=============================
  def define_sinx_image(self, iteration=1):
# image is just a scaled sin(x) / x. (One could probably compute
# this more quickly.)
    num_ys = 100
    num_xs = 100
    image_numarray = numarray.ones((1,num_ys,num_xs),type=numarray.Float32)
    for k in range(num_ys):
      k_dist = abs (k - num_ys/2)
      for i in range(num_xs):         
        i_dist = abs (i - num_xs/2)
        dist = sqrt(k_dist*k_dist + i_dist*i_dist)         
        if dist == 0:
          image_numarray[0,k,i] = 1.0 * iteration         
        else:
          image_numarray[0,k,i] =  iteration * sin(dist) / dist

    self.array_plot(' ', image_numarray)

  def define_image(self, iteration=1):
#    num_arrays = 2
#    num_arrays = 92
#    num_arrays = 10
#    array_dim = 700
    num_arrays = 600
    array_dim = 64
    axis_slice = slice(0,array_dim)
    gain = 1.0 / num_arrays
    image_numarray = numarray.ones((num_arrays,array_dim,array_dim),type=numarray.Float32)
    array_selector = []
    array_selector.append(0)
    array_selector.append(axis_slice)
    array_selector.append(axis_slice)
#   max_distance = num_arrays / iteration
    max_distance = num_arrays 
    for k in range(max_distance):
      array_tuple = tuple(array_selector)
      image_numarray[array_tuple] = iteration * k * gain
      if k < max_distance:
        array_selector[0] = k + 1
    self.array_plot(' ', image_numarray)

  def define_complex_image(self, iteration=1):
#    num_arrays = 2
#    num_arrays = 92
#    num_arrays = 10
#    array_dim = 700
    num_arrays = 600
    array_dim = 64
    axis_slice = slice(0,array_dim)
    gain = 1.0 / num_arrays
    image_cx_numarray = numarray.ones((num_arrays,array_dim,array_dim),type=numarray.Complex32)
    image_r_numarray = numarray.ones((num_arrays,array_dim,array_dim),type=numarray.Float32)
    image_i_numarray = numarray.ones((num_arrays,array_dim,array_dim),type=numarray.Float32)
    array_selector = []
    array_selector.append(0)
    array_selector.append(axis_slice)
    array_selector.append(axis_slice)
    max_distance = num_arrays / iteration
    for k in range(max_distance):
      array_tuple = tuple(array_selector)
      image_r_numarray[array_tuple] = iteration * k * gain
      image_i_numarray[array_tuple] = iteration * gain / (k+1)
      if k < max_distance:
        array_selector[0] = k + 1
    image_cx_numarray.setreal(image_r_numarray)
    image_cx_numarray.setimag(image_i_numarray)
    self.array_plot(' ', image_cx_numarray)

  def define_complex_image1(self, iteration=1):
    num_arrays = 20
    array_dim = 3
    axis_slice = slice(1,array_dim)
    axis_slice1 = slice(1,array_dim-1)
    gain = 1.0 / num_arrays
    image_cx_numarray = numarray.zeros((num_arrays,array_dim,array_dim),type=numarray.Complex32)
    image_r_numarray = numarray.zeros((num_arrays,array_dim,array_dim),type=numarray.Float32)
    image_i_numarray = numarray.zeros((num_arrays,array_dim,array_dim),type=numarray.Float32)
    array_selector = []
    array_selector.append(0)
    array_selector.append(axis_slice)
    array_selector.append(axis_slice1)
    max_distance = num_arrays / iteration
    for k in range(max_distance):
      array_tuple = tuple(array_selector)
      image_r_numarray[array_tuple] = iteration * k * gain
      image_i_numarray[array_tuple] = iteration * gain / (k+1)
      if k < max_distance:
        array_selector[0] = k + 1
    image_cx_numarray.setreal(image_r_numarray)
    image_cx_numarray.setimag(image_i_numarray)
    self.array_plot(' ', image_cx_numarray)

#=============================
# VTK code for test array
#=============================
  def define_random_image(self):
    num_arrays = 93
    array_dim = 64
    image_numarray = numarray.ones((num_arrays,array_dim,array_dim),type=numarray.Float32)
    for k in range(num_arrays):
      for i in range(array_dim):
        for j in range(array_dim):
          image_numarray[k,i,j] = random.random()
    self.array_plot(' ', image_numarray)

  def array_plot(self, caption, incoming_array, dummy_parm=False):
    """ convert an incoming numarray into a format that can
        be plotted with VTK
    """
    if incoming_array.rank == 2:
        temp_array = numarray.ones((1,incoming_array.shape[0],incoming_array.shape[1]),type=incoming_array.type()) 
        temp_array[0,:incoming_array.shape[0],:incoming_array.shape[1]] = incoming_array
        incoming_array = temp_array
    plot_array = None
# convert a complex array to reals followed by imaginaries
    if incoming_array.type() == numarray.Complex32 or incoming_array.type() == numarray.Complex64:
        real_array =  incoming_array.getreal()
        imag_array =  incoming_array.getimag()
        (nx,ny,nz) = real_array.shape

        image_for_display = numarray.zeros(shape=(nx,ny,nz*2),type=real_array.type());
        image_for_display[:nx,:ny,:nz] = real_array[:nx,:ny,:nz]
        image_for_display[:nx,:ny,nz:] = imag_array[:nx,:ny,:nz]
        plot_array = image_for_display
        self.complex_plot = True
    else:
        plot_array = incoming_array
        self.complex_plot = False
    if plot_array.rank == 3 and plot_array.shape[0] == 1:
      self.warped_surface = True
      if  plot_array.min() != self.data_min or plot_array.max() != self.data_max:
        self.data_min = plot_array.min()
        self.data_max = plot_array.max()
# make sure that we're not trying to plot a flat surface
        if self.data_min == self.data_max:
          print ' '
          print ' **************************************** '
          print ' sorry - cannot visualize a flat surface! '
          print ' **************************************** '
          print ' '
          return
    else:
      self.warped_surface = False
    if self.image_array is None:
      self.image_array = vtkImageImportFromNumarray()
      if plot_array.rank > 3:
        self.image_array.SetArray(plot_array[0])
      else:
        self.image_array.SetArray(plot_array)

# use default VTK parameters for spacing at the moment
      spacing = (1.0, 1.0, 1.0)
      self.image_array.SetDataSpacing(spacing)

# create new VTK pipeline
      self.set_initial_display()

      self.lut.SetTableRange(plot_array.min(), plot_array.max())
      self.lut.ForceBuild()
    else:
      if plot_array.rank > 3:
        self.image_array.SetArray(plot_array[0])
      else:
        self.image_array.SetArray(plot_array)
      self.lut.SetTableRange(plot_array.min(), plot_array.max())
      self.lut.ForceBuild()
      self.UpdateBounds()
# refresh display if data contents updated after
# first display
      self.renwin.Render()
 
  def reset_image_array(self):
    self.image_array = None

  def AddUpdate(self):
    self.index_selector.displayUpdateItem()

  def HideNDButton(self):
    self.index_selector.HideNDOption()

  def start_timer(self, time):
    timer = qt.QTimer()
    timer.connect(timer, qt.SIGNAL('timeout()'), self.testEvent)
    timer.start(time)

  def testEvent(self):
    self.iteration = self.iteration + 1
#   self.define_random_image()
#   self.define_image(self.iteration)
#   self.define_complex_image(self.iteration)
#   self.define_complex_image1(self.iteration)
    self.define_sinx_image(self.iteration)

  def two_D_Event(self):
    self.emit(PYSIGNAL("show_2D_Display"),(0,))

  def hide_Event(self, toggle_ND_Controller):
    self.emit(PYSIGNAL("show_ND_Controller"),(toggle_ND_Controller,))

  def AddVTKExitEvent(self):
# next line causes confusion if run inside the MeqBrowser
    self.renwininter.AddObserver("ExitEvent", lambda o, e, a=app: a.quit())

  def setAxisParms(self, axis_parms):
    """ set display information from axis parameters """

    if self.warped_surface:
      text = ' '
      if axis_parms[1] is None:
        text = 'X'
      else:
        text = 'X ' + axis_parms[1]
      if not self.axes is None:
          self.axes.SetXLabel(text)

      if axis_parms[0] is None:
        text = 'Y'
      else: 
        text = 'Y ' + axis_parms[0]
      if not self.axes is None:
        self.axes.SetYLabel(text)
    else:
      text = ' '
      text_menu = ' '
      if axis_parms[2] is None:
        text_menu = 'X axis '
        if self.complex_plot:
          text = 'X (real then imag) '
        else:
          text = 'X '
      else: 
        text_menu = 'X axis: ' + axis_parms[2]
        if self.complex_plot:
          text = 'X ' + axis_parms[2] + ' (real then imag)'
        else:
          text = 'X ' + axis_parms[2]
      self.index_selector.setXMenuLabel(text_menu)
      if not self.axes is None:
        self.axes.SetXLabel(text)

      if axis_parms[1] is None:
        text_menu = 'Y axis '
        text = 'Y'
      else:
        text_menu = 'Y axis: ' + axis_parms[1]
        text = 'Y ' + axis_parms[1]
      self.index_selector.setYMenuLabel(text_menu)
      if not self.axes is None:
          self.axes.SetYLabel(text)

      if axis_parms[0] is None:
        text = 'Z'
        text_menu = 'Z axis '
      else: 
        text_menu = 'Z axis: ' + axis_parms[0]
        text = 'Z ' + axis_parms[0]
      self.index_selector.setZMenuLabel(text_menu)
      if not self.axes is None:
        self.axes.SetZLabel(text)

#=============================
if __name__ == "__main__":
  if has_vtk:
    app = qt.QApplication(sys.argv)
    qt.QObject.connect(app,qt.SIGNAL("lastWindowClosed()"),
		app,qt.SLOT("quit()"))
    display = vtk_qt_3d_display()
    display.show()
    display.AddUpdate()
    display.testEvent()
    app.exec_loop()
  else:
    print ' '
    print '**** Sorry! It looks like VTK is not available! ****'

