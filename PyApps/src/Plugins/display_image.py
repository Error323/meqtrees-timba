#!/usr/bin/env python

import sys
from qt import *
from qwt import *
from numarray import *
#import numarray.nd_image
from UVPAxis import *
from printfilter import *
from ComplexColorMap import *
from ComplexScaleDraw import *
from QwtPlotImage import *
#from app_browsers import *
from Timba.GUI.pixmaps import pixmaps
import random

from Timba.utils import verbosity
_dbg = verbosity(0,name='displayimage');
_dprint = _dbg.dprint;
_dprintf = _dbg.dprintf;

# compute standard deviation of a complex or real array
# the std_dev given here was computed according to the
# formula given by Oleg (It should work for real or complex array)
def standard_deviation(incoming_array,complex_type):
#  return incoming_array.stddev()
  if complex_type:
    incoming_mean = incoming_array.mean()
    temp_array = incoming_array - incoming_mean
    abs_array = abs(temp_array)
# get the conjugate of temp_array ...
    temp_array_conj = (abs_array * abs_array) / temp_array
    temp_array = temp_array * temp_array_conj
    mean = temp_array.mean()
    std_dev = sqrt(mean)
    std_dev = abs(std_dev)
    return std_dev
  else:
    return incoming_array.stddev()

def linearX(nx, ny):
    return repeat(arange(nx, typecode = Float32)[:, NewAxis], ny, -1)

def linearY(nx, ny):
    return repeat(arange(ny, typecode = Float32)[NewAxis, :], nx, 0)

def rectangle(nx, ny, scale):
    # swap axes in the fromfunction call
    s = scale/(nx+ny)
    x0 = nx/2
    y0 = ny/2
    
    def test(y, x):
        return cos(s*(x-x0))*sin(s*(y-y0))

    result = fromfunction(test, (ny, nx))
    return result

#  distance from (5,5) squared
def dist(x,y):
  return (x-15)**2+(y-5)**2  
def imag_dist(x,y):
  return (x-10)**2+(y-10)**2  
def RealDist(x,y):
  return (x)**2  
def ImagDist(x,y):
  return (x-29)**2  
#m = fromfunction(dist, (10,10))


    
display_image_instructions = \
'''This plot basically shows the contents of one or two-dimensional arrays. Most decision making takes place behind the scenes, so to speak, as the system uses the dimensionality of the data and the source of the data to decide how the data will be displayed. However, once a display appears, you can interact with it in certain standardized ways.<br><br>
Button 1 (Left): If you click the <b>left</b> mouse button on a location inside a two-dimensional array plot, the x and y coordinates of this location, and its value, will appear at the lower left hand corner of the display. This information is shown until you release the mouse button. If you click the left mouse button down and then drag it, a rectangular square will be seen. Then when you release the left mouse button, the plot will 'zoom in' on the area defined inside the rectangle.<br><br>
Button 2 (Middle): If you click the <b>middle</b> mouse button on a location inside a <b>two-dimensional</b> array plot, then X and Y cross-sections centred on this location are overlaid on the display. A continuous black line marks the location of the X cross-section and the black dotted line shows the cross section values, which are tied to the right hand scale. The white lines show corresponding information for the Y cross section, whose values are tied to the top scale of the plot. You can remove the X,Y cross sections from the display by hitting the 'refresh' icon (the two arrows circling each other) in the upper left corner of the plot window.(NOTE: There is presently a bug here - if the plot panel is floated free of the browser, the refresh option does not work.) If the <b>Legends</b> display has been toggled to ON (see Button 3 below), then a sequence of push buttons will appear along the right hand edge of the display. Each of the push buttons is associated with one of the cross-section plots. Clicking on a push button will cause the corresponding plot to appear or disappear, depending on the current state.<br><br>
Button 3 (Right):Click the <b>right</b> mouse button in a spectrum display window to get get a context menu with options for printing, resetting the zoom, selecting another image, or toggling a <b>Legends</b> display. If you click on the 'Disable zoomer ' icon  in a window where you had zoomed in on a selected region, then the original entire array is re-displayed. Vellsets or <b>visu</b> data sets may contain multiple arrays. Only one of these arrays can be displayed at any one time. If additional images are available for viewing, they will be listed in the context menu. If you move the right mouse button to the desired image name in the menu and then release the button, the requested image will now appear in the display. If you select the Print option from the menu, the standard Qt printer widget will appear. That widget will enable you print out a copy of your plot, or save the plot in Postscript format to a file. Note that at present one cannot print out the Colorbar display associated with a two-dimensional array plot. This will be worked on. If you make cross-section plots (see Button 2 above), by default a <b>Legends</b> display associating push buttons with these plots is not shown. You can toggle the display of these push buttons ON or OFF by selecting the Toggle Cross-Section Legend option from the context menu.'''

class QwtImageDisplay(QwtPlot):

    display_table = {
        'hippo': 'hippo',
        'grayscale': 'grayscale',
        'brentjens': 'brentjens',
        }

    def __init__(self, plot_key=None, parent=None):
        QwtPlot.__init__(self, plot_key, parent)

        self._mainwin = parent and parent.topLevelWidget();

# set default display type to 'hippo'
        self._display_type = "hippo"

        self.emit(PYSIGNAL("display_type"),(self._display_type,))

        self._vells_plot = False
	self._flags_array = None
	self.flag_toggle = False
	self.flag_blink = False
        self._solver_flag = False

# save raw data
        self.plot_key = plot_key
        self.x_array = None
        self.y_array = None
        self.x_index = None
	self._x_axis = None
	self._y_axis = None
	self._title = None
	self._menu = None
        self._plot_type = None
	self._plot_dict_size = None
	self.created_combined_image = False
	self._combined_image_id = None
	self.is_combined_image = False
        self.active_image_index = None
        self.y_marker_step = None
        self.imag_flag_vector = None
        self.real_flag_vector = None
        self.array_parms = None
        self.metrics_rank = None
        self.iteration_number = None
        self._active_plane = None
        self._active_perturb = None
        self.is_time_vector = None
        self.is_freq_vector = None
        self._mhz = False
        self._khz = False
        # make a QwtPlot widget
        self.plotLayout().setMargin(0)
        self.plotLayout().setCanvasMargin(0)
        self.plotLayout().setAlignCanvasToScales(1)
        self.setTitle('QwtImageDisplay: demo')

        self.setlegend = 0
        self.setAutoLegend(self.setlegend)
        self.enableLegend(False)
        self.setLegendPos(Qwt.Right)
        self.setAxisTitle(QwtPlot.xBottom, 'Channel Number')
        self.setAxisTitle(QwtPlot.yLeft, 'value')
        
        self.enableAxis(QwtPlot.yRight, False)
        self.enableAxis(QwtPlot.xTop, False)
        self.dummy_xCrossSection = None
        self.xCrossSection = None
        self.yCrossSection = None
        self.myXScale = None
        self.myYScale = None
        self.active_image = False

        self.plotImage = QwtPlotImage(self)

        self.zoomStack = []
        self.connect(self,
                     SIGNAL('plotMouseMoved(const QMouseEvent&)'),
                     self.onMouseMoved)
        self.connect(self,
                     SIGNAL('plotMousePressed(const QMouseEvent&)'),
                     self.onMousePressed)
        self.connect(self,
                     SIGNAL('plotMouseReleased(const QMouseEvent&)'),
                     self.onMouseReleased)
        self.connect(self, SIGNAL("legendClicked(long)"), self.toggleCurve)
        self.index = 1
        self.is_vector = False
        self.xpos = 0
        self.ypos = 0
        QWhatsThis.add(self, display_image_instructions)


#        self.__initContextMenu()

    def initSpectrumContextMenu(self):
        """Initialize the spectra context menu
        """
        # skip if no main window
        if not self._mainwin:
          return;

        if self._menu is None:
          self._menu = QPopupMenu(self._mainwin);
          self.add_basic_menu_items()
          QObject.connect(self._menu,SIGNAL("activated(int)"),self.update_spectrum_display);
          self._signal_id = -1
          self._plot_dict = {}
          self._plot_label = {}
          self._combined_label_dict = {}

        num_plot_arrays = len(self._data_values)
        _dprint(2,' number of arrays to plot ', num_plot_arrays)
        for i in range(num_plot_arrays):
          data_label = ''
	  plot_label = ''
          combined_display_label = ''
          if isinstance(self._data_labels, tuple):
            data_label = 'go to ' + self._string_tag  +  " " +self._data_labels[i] + ' ?'
            combined_display_label = self._string_tag  +  " " + self._data_labels[i]
            plot_label = 'spectra:' + combined_display_label
          else:
            data_label = 'go to ' + self._string_tag  +  " " +self._data_labels +' ?'
            combined_display_label = self._string_tag  +  " " + self._data_labels
            plot_label = 'spectra:' + combined_display_label
	  plot_label_not_found = True


# use hack below instead
#          plot_array = self._data_values[i].copy()

# hack to get array display correct until forest.state
# record is available
          axes = arange(self._data_values[i].rank)[::-1]
          plot_array = transpose(self._data_values[i], axes)


	  for j in range(len(self._plot_label)):
	    if self._plot_label[j] == plot_label:
	      plot_label_not_found =False
# if we are finding repeat plot labels, then we have cycled
# through the plot tree at least once, and we have
# the maximum size of the plot_dict
              self._plot_dict_size = len(self._plot_dict)
              _dprint(2,' plot_dict_size: ', self._plot_dict_size)
	      self._plot_dict[j] = plot_array
	      break

# if no plot label found, then add array into plot_dict and
# update selection menu
          if plot_label_not_found:
            self._signal_id = self._signal_id + 1
            self._menu.insertItem(data_label,self._signal_id)
	    self._plot_dict[self._signal_id] = plot_array
            self._plot_dict_size = len(self._plot_dict)
	    self._plot_label[self._signal_id] = plot_label
            self._combined_label_dict[self._signal_id] = combined_display_label
# otherwise create or update the combined image
	  else:
	    if self._plot_dict_size > 1 and not self.created_combined_image:
	      self.create_combined_array()
	    else: 
	      if self.created_combined_image:
	        self.update_combined_array()

    def create_combined_array(self):
# create combined array from contents of plot_dict
      shape = self._plot_dict[0].shape
      self.y_marker_step = shape[1]
      self.num_y_markers = self._plot_dict_size 
      temp_array = zeros((shape[0],self._plot_dict_size* shape[1]), self._plot_dict[0].type())
      self.marker_labels = []
      for l in range(self._plot_dict_size ):
#        dummy_array =  self._plot_dict[l].copy()
        dummy_array =  self._plot_dict[l]
        for k in range(shape[0]):
          for j in range(shape[1]):
            j_index = l * shape[1] + j
            temp_array[k,j_index] = dummy_array[k,j]
        self.marker_labels.append(self._combined_label_dict[l])
      self.created_combined_image = True
      self._signal_id = self._signal_id + 1
      self._combined_image_id = self._signal_id
      self._menu.insertItem('go to combined image',self._signal_id)
      self._plot_dict[self._signal_id] = temp_array
      self._plot_label[self._signal_id] = 'spectra: combined image'

    def update_combined_array(self):
# remember that the size of the plot_dict includes the combined array    
      data_dict_size = self._plot_dict_size - 1
# create combined array from contents of plot_dict
      shape = self._plot_dict[0].shape
      self.y_marker_step = shape[1]
      temp_array = zeros((shape[0], data_dict_size* shape[1]), self._plot_dict[0].type())
      self.marker_labels = []
      for l in range(data_dict_size ):
        dummy_array =  self._plot_dict[l]
        shape_array = dummy_array.shape
        for k in range(shape_array[0]):
          for j in range(shape_array[1]):
            j_index = l * shape[1] + j
            if j_index <data_dict_size* shape[1]:
              temp_array[k,j_index] = dummy_array[k,j]
        self.marker_labels.append(self._combined_label_dict[l])
      self._plot_dict[self._combined_image_id] = temp_array

    def update_spectrum_display(self, menuid):
      if menuid < 0:
        self.unzoom()
        return
      if menuid == 300:
        self.toggleLegend()
        return
      self.active_image_index = menuid
      if self.is_combined_image:
        self.removeMarkers()
      self.is_combined_image = False
      if not self._combined_image_id is None:
        if self._combined_image_id == menuid:
	  self.is_combined_image = True
      self.array_plot(self._plot_label[menuid], self._plot_dict[menuid], False)

    def initVellsContextMenu (self):
        # skip if no main window
        if not self._mainwin:
          return;
        self._menu = QPopupMenu(self._mainwin);
        QObject.connect(self._menu,SIGNAL("activated(int)"),self.update_vells_display);
        id = -1
        perturb_index = -1
# are we dealing with Vellsets?
        number_of_planes = len(self._vells_rec["vellsets"])
        _dprint(3, 'number of planes ', number_of_planes)
        self._next_plot = {}
        self._perturb_menu = {}
        for i in range(number_of_planes):
          id = id + 1
          if self._vells_rec.vellsets[i].has_key("value"):
            self._label = "go to plane " + str(i) + " value" 
            self._next_plot[id] = self._label
            self._menu.insertItem(self._label,id)
          if self._vells_rec.vellsets[i].has_key("perturbed_value"):
            try:
              number_of_perturbed_arrays = len(self._vells_rec.vellsets[i].perturbed_value)
              perturb_index  = perturb_index  + 1
              self._perturb_menu[perturb_index] = QPopupMenu(self._mainwin);
              for j in range(number_of_perturbed_arrays):
                id = id + 1
                key = " perturbed_value "
                self._label =  "   -> go to plane " + str(i) + key + str(j) 
                self._next_plot[id] = self._label 
                self._menu.insertItem(self._label,id)
            except:
              _dprint(3, 'The perturbed values cannot be displayed.')
# don't display message for the time being
#              Message =  'It would appear that there is a problem with perturbed values.\nThey cannot be displayed.'
#              mb_msg = QMessageBox("display_image.py",
#                               Message,
#                               QMessageBox.Warning,
#                               QMessageBox.Ok | QMessageBox.Default,
#                               QMessageBox.NoButton,
#                               QMessageBox.NoButton)
#              mb_msg.exec_loop()
          if self._vells_rec.vellsets[i].has_key("flags"):
            self._label = "toggle flagged data for plane " + str(i) 
	    toggle_id = 200
            self._menu.insertItem(self._label,toggle_id)
            self._label = "toggle blink of flagged data for plane " + str(i) 
            toggle_id = 201
            self._menu.insertItem(self._label,toggle_id)

# add stuff for printer, etc
        self.add_basic_menu_items()
    # end initVellsContextMenu()

    def unzoom(self):
        self.zooming = 0
        if len(self.zoomStack):
          xmin, xmax, ymin, ymax = self.zoomStack.pop()
          self.setAxisScale(QwtPlot.xBottom, xmin, xmax)
          self.setAxisScale(QwtPlot.yLeft, ymin, ymax)
          self.refresh_marker_display()
          self.replot()
          _dprint(3, 'called replot in unzoom')
        else:
          return

    def toggleLegend(self):
      if self.setlegend == 1:
        self.setlegend = 0
        self.enableLegend(False)
      else:
        self.setlegend = 1
        self.enableLegend(True)
      self.setAutoLegend(self.setlegend)
      self.replot()

    # toggleLegend()


    def timerEvent_blink(self):
# stop blinking     
      if not self.flag_blink:
        self.timer.stop()
        self.flag_toggle = False
        if self.real_flag_vector is None:
          self.plotImage.setDisplayFlag(self.flag_toggle)
        else:
          self.curve(self.real_flag_vector).setEnabled(self.flag_toggle)
          if not self.imag_flag_vector is None:
            self.curve(self.imag_flag_vector).setEnabled(self.flag_toggle)
        self.replot()
        _dprint(3, 'called replot in timerEvent_blink')
      else:
        if self.flag_toggle == False:
          self.flag_toggle = True
        else:
          self.flag_toggle = False
        if self.real_flag_vector is None:
          self.plotImage.setDisplayFlag(self.flag_toggle)
        else:
          self.curve(self.real_flag_vector).setEnabled(self.flag_toggle)
          if not self.imag_flag_vector is None:
            self.curve(self.imag_flag_vector).setEnabled(self.flag_toggle)
        self.replot()
        _dprint(3, 'called replot in timerEvent_blink')

    def update_vells_display(self, menuid):
      if menuid < 0:
        self.unzoom()
        return
      if menuid == 300:
        self.toggleLegend()
        return

	
# toggle flags display	
      if menuid == 200:
        if self.flag_toggle == False:
          self.flag_toggle = True
        else:
          self.flag_toggle = False
        if self.real_flag_vector is None:
          self.plotImage.setDisplayFlag(self.flag_toggle)
        else:
          self.curve(self.real_flag_vector).setEnabled(self.flag_toggle)
          if not self.imag_flag_vector is None:
            self.curve(self.imag_flag_vector).setEnabled(self.flag_toggle)
        self.replot()
        _dprint(3, 'called replot in update_vells_display')
	return

      if menuid == 201:
        if self.flag_blink == False:
          self.flag_blink = True
	  self.timer = QTimer(self)
          self.timer.connect(self.timer, SIGNAL('timeout()'), self.timerEvent_blink)
          self.timer.start(2000)
        else:
          self.flag_blink = False
	return

      id_string = self._next_plot[menuid]
      perturb = -1
      plane = 0
      perturb_loc = id_string.find("perturbed_value")
      str_len = len(id_string)
      if perturb_loc >= 0:
        perturb = int(id_string[perturb_loc+15:str_len])
      plane_loc = id_string.find("go to plane")
      if plane_loc >= 0:
        plane = int( id_string[plane_loc+12:plane_loc+14])
        self._active_plane = plane
        self._active_perturb = None
# get the shape tuple - useful if the Vells have been compressed down to
# a constant
      self._shape = self._vells_rec.vellsets[plane]["shape"]
# handle "value" first
      if perturb < 0 and self._vells_rec.vellsets[plane].has_key("value"):
        complex_type = False;
# test if we have a numarray
        try:
          if self._vells_rec.vellsets[plane].value.type() == Complex32:
            complex_type = True;
          if self._vells_rec.vellsets[plane].value.type() == Complex64:
            complex_type = True;
          self._value_array = self._vells_rec.vellsets[plane].value
          _dprint(3, 'self._value_array ', self._value_array)
          array_shape = self._value_array.shape
          if len(array_shape) == 1 and array_shape[0] == 1:
            temp_value = self._value_array[0]
            temp_array = numarray.asarray(temp_value)
            self._value_array = numarray.resize(temp_array,self._shape)
        except:
          temp_array = numarray.asarray(self._vells_rec.vellsets[i].value)
          self._value_array = numarray.resize(temp_array,self._shape)
          if self._value_array.type() == Complex32:
            complex_type = True;
          if self._value_array.type() == Complex64:
            complex_type = True;

        key = " value "
        if complex_type:
          _dprint(3,'handling complex array')
#extract real component
          self._value_real_array = self._value_array.getreal()
          self._z_real_min = self._value_real_array.min()
          self._z_real_max = self._value_real_array.max()
#extract imaginary component
          self._value_imag_array = self._value_array.getimag()
          self._z_imag_min = self._value_imag_array.min()
          self._z_imag_max = self._value_imag_array.max()
          self._label = "plane " + str(plane) + key 
          if self._solver_flag:
            self.array_plot(self._label, self._value_array, False)
          else:
            self.array_plot(self._label, self._value_array)
        else:
#we have a real array
          _dprint(3,'handling real array')
          self._label = "plane " + str(plane) + key 
          self._z_real_min = self._value_array.min()
          self._z_real_max = self._value_array.max()
          if self._solver_flag:
            self.array_plot(self._label, self._value_array, False)
          else:
            self.array_plot(self._label, self._value_array)

      else:
# handle "perturbed_value"
        if self._vells_rec.vellsets[plane].has_key("perturbed_value"):
# test if we have a numarray
          complex_type = False;
          perturbed_array_diff = None
          self._active_perturb = perturb
          try:
            if self._vells_rec.vellsets[plane].perturbed_value[perturb].type() == Complex32:
              complex_type = True;
            if self._vells_rec.vellsets[plane].perturbed_value[perturb].type() == Complex64:
              complex_type = True;
            perturbed_array_diff = self._vells_rec.vellsets[plane].perturbed_value[perturb]
          except:
            temp_array = numarray.asarray(self._vells_rec.vellsets[plane].perturbed_value[perturb])
            perturbed_array_diff = numarray.resize(temp_array,self._shape)
            if perturbed_array_diff.type() == Complex32:
              complex_type = True;
            if perturbed_array_diff.type() == Complex64:
              complex_type = True;

          key = " perturbed_value "
          self._label =  "plane " + str(plane) + key + str(perturb)
          if self._solver_flag:
            self.array_plot(self._label, perturbed_array_diff, False)
          else:
            self.array_plot(self._label, perturbed_array_diff)
        
    def printplot(self):
        try:
            printer = QPrinter(QPrinter.HighResolution)
        except AttributeError:
            printer = QPrinter()
        printer.setOrientation(QPrinter.Landscape)
        printer.setColorMode(QPrinter.Color)
        printer.setOutputToFile(True)
        printer.setOutputFileName('image_plot.ps')
        if printer.setup():
            filter = PrintFilter()
            if (QPrinter.GrayScale == printer.colorMode()):
                filter.setOptions(QwtPlotPrintFilter.PrintAll
                                  & ~QwtPlotPrintFilter.PrintCanvasBackground)
            self.printPlot(printer, filter)
    # printplot()


    def drawCanvasItems(self, painter, rectangle, maps, filter):
        if not self.is_vector:
          self.plotImage.drawImage(
            painter, maps[QwtPlot.xBottom], maps[QwtPlot.yLeft])
        QwtPlot.drawCanvasItems(self, painter, rectangle, maps, filter)


    def formatCoordinates(self, x, y, value = None):
        """Format mouse coordinates as real world plot coordinates.
        """
        result = ''
        xpos = self.invTransform(QwtPlot.xBottom, x)
        ypos = self.invTransform(QwtPlot.yLeft, y)
	marker_index = None
        if self._vells_plot:
	  xpos1 = xpos
	  if not self.split_axis is None:
	    if xpos1 >  self.split_axis:
	        xpos1 = xpos1 - self.delta_vells
          temp_str = result + "x =%+.2g" % xpos1
          result = temp_str
          temp_str = result + " y =%+.2g" % ypos
          result = temp_str
          xpos = self.plotImage.xMap.limTransform(xpos)
          ypos = self.plotImage.yMap.limTransform(ypos)
        else:
          xpos = int(xpos)
	  xpos1 = xpos
	  if not self.split_axis is None:
	    if xpos1 >  self.split_axis:
	      xpos1 = xpos1 % self.split_axis
          temp_str = result + "x =%+.2g" % xpos1
          result = temp_str
          ypos = int(ypos)
	  ypos1 = ypos
	  if not self.y_marker_step is None:
	    if ypos1 >  self.y_marker_step:
	      marker_index = ypos1 / self.y_marker_step
	      ypos1 = ypos1 % self.y_marker_step
	    else:
	      marker_index = 0
          temp_str = result + " y =%+.2g" % ypos1
          result = temp_str
        if value is None:
          value = self.raw_image[xpos,ypos]
	message = None
        temp_str = " value: %-.3g" % value
	if not marker_index is None:
          message = result + temp_str + '\nsource: ' + self.marker_labels[marker_index]
	else:
          message = result + temp_str
    
# alias
        fn = self.fontInfo().family()

# text marker giving source of point that was clicked
        self.marker = self.insertMarker()
        ylb = self.axisScale(QwtPlot.yLeft).lBound()
        xlb = self.axisScale(QwtPlot.xBottom).lBound()
        self.setMarkerPos(self.marker, xlb, ylb)
        self.setMarkerLabelAlign(self.marker, Qt.AlignRight | Qt.AlignTop)
        self.setMarkerLabel( self.marker, message,
          QFont(fn, 9, QFont.Bold, False),
          Qt.blue, QPen(Qt.red, 2), QBrush(Qt.yellow))

# insert array info if available
        self.insert_array_info()
        self.replot()
        _dprint(3, 'called replot in formatCoordinates ')
            
    # formatCoordinates()

    def reportCoordinates(self, x, y):
        """Format mouse coordinates as real world plot coordinates.
        """
        result = ''
        xpos = x
        ypos = y
        temp_str = "nearest x=%-.3g" % x
        temp_str1 = " y=%-.3g" % y
	message = temp_str + temp_str1 
# alias
        fn = self.fontInfo().family()

# text marker giving source of point that was clicked
        self.marker = self.insertMarker()
        ylb = self.axisScale(QwtPlot.yLeft).lBound()
        xlb = self.axisScale(QwtPlot.xBottom).lBound()
        self.setMarkerPos(self.marker, xlb, ylb)
        self.setMarkerLabelAlign(self.marker, Qt.AlignRight | Qt.AlignTop)
        self.setMarkerLabel( self.marker, message,
          QFont(fn, 9, QFont.Bold, False),
          Qt.blue, QPen(Qt.red, 2), QBrush(Qt.yellow))

# insert array info if available
        self.insert_array_info()
        self.replot()
        _dprint(3, 'called replot in reportCoordinates ')
    # reportCoordinates()

    def refresh_marker_display(self):
      self.removeMarkers()
      if self.is_combined_image:
        self.insert_marker_lines()
      self.insert_array_info()
      self.replot()
      _dprint(3, 'called replot in refresh_marker_display ')
    # refresh_marker_display()

    def insert_marker_lines(self):
      _dprint(2, 'refresh_marker_display inserting markers')
# alias
      fn = self.fontInfo().family()
      y = 0
      for i in range(self.num_y_markers):
        label = self.marker_labels[i]
        mY = self.insertLineMarker('', QwtPlot.yLeft)
        self.setMarkerLinePen(mY, QPen(Qt.white, 2, Qt.DashDotLine))
        y = y + self.y_marker_step
        self.setMarkerYPos(mY, y)
    
    def onMouseMoved(self, e):
       if self.is_vector:
          return

    # onMouseMoved()

    def onMousePressed(self, e):
        if Qt.LeftButton == e.button():
            if self.is_vector:
            # Python semantics: self.pos = e.pos() does not work; force a copy
              xPos = e.pos().x()
              yPos = e.pos().y()
              _dprint(2,'xPos yPos ', xPos, ' ', yPos);
# We get information about the qwt plot curve that is
# closest to the location of this mouse pressed event.
# We are interested in the nearest curve_number and the index, or
# sequence number of the nearest point in that curve.
              curve_number, distance, xVal, yVal, index = self.closestCurve(xPos, yPos)
              _dprint(2,' curve_number, distance, xVal, yVal, index ', curve_number, ' ', distance,' ', xVal, ' ', yVal, ' ', index);
              self.reportCoordinates(xVal, yVal)

            else:
              self.formatCoordinates(e.pos().x(), e.pos().y())
            self.xpos = e.pos().x()
            self.ypos = e.pos().y()
            self.enableOutline(1)
            self.setOutlinePen(QPen(Qt.black))
            self.setOutlineStyle(Qwt.Rect)
            self.zooming = 1
            if self.zoomStack == []:
                self.zoomState = (
                    self.axisScale(QwtPlot.xBottom).lBound(),
                    self.axisScale(QwtPlot.xBottom).hBound(),
                    self.axisScale(QwtPlot.yLeft).lBound(),
                    self.axisScale(QwtPlot.yLeft).hBound(),
                    )
        elif Qt.RightButton == e.button():
            e.accept()
            self._menu.popup(e.globalPos());

        elif Qt.MidButton == e.button():
            if self.active_image:
              xpos = e.pos().x()
              ypos = e.pos().y()
              shape = self.raw_image.shape
              xpos = self.invTransform(QwtPlot.xBottom, xpos)
              ypos = self.invTransform(QwtPlot.yLeft, ypos)
              temp_array = asarray(ypos)
              self.x_arrayloc = resize(temp_array,shape[0])
              temp_array = asarray(xpos)
              self.y_arrayloc = resize(temp_array,shape[1])
              if self._vells_plot:
                xpos = self.plotImage.xMap.limTransform(xpos)
                ypos = self.plotImage.yMap.limTransform(ypos)
              else:
                xpos = int(xpos)
                ypos = int(ypos)
              self.x_array = zeros(shape[0], Float32)
              self.x_index = arange(shape[0])
              self.x_index = self.x_index + 0.5
              for i in range(shape[0]):
                self.x_array[i] = self.raw_image[i,ypos]
              self.setAxisAutoScale(QwtPlot.yRight)
              self.y_array = zeros(shape[1], Float32)
              self.y_index = arange(shape[1])
              self.y_index = self.y_index + 0.5
              for i in range(shape[1]):
                self.y_array[i] = self.raw_image[xpos,i]
              self.setAxisAutoScale(QwtPlot.xTop)
              if self.xCrossSection is None:
                self.xCrossSection = self.insertCurve('xCrossSection')
                self.setCurvePen(self.xCrossSection, QPen(Qt.black, 2))
                plot_curve=self.curve(self.xCrossSection)
                plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, 
                   QBrush(Qt.black), QPen(Qt.black), QSize(10,10)))
              self.enableAxis(QwtPlot.yRight)
              self.setAxisTitle(QwtPlot.yRight, 'x cross-section value')
              self.setCurveYAxis(self.xCrossSection, QwtPlot.yRight)
# nope!
#              self.setCurveStyle(self.xCrossSection, QwtCurve.Steps)
              if self.yCrossSection is None:
                self.yCrossSection = self.insertCurve('yCrossSection')
                self.setCurvePen(self.yCrossSection, QPen(Qt.white, 2))
                plot_curve=self.curve(self.yCrossSection)
                plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, 
                   QBrush(Qt.white), QPen(Qt.white), QSize(10,10)))
              self.enableAxis(QwtPlot.xTop)
              self.setAxisTitle(QwtPlot.xTop, 'y cross-section value')
              self.setCurveYAxis(self.yCrossSection, QwtPlot.yLeft)
              self.setCurveXAxis(self.yCrossSection, QwtPlot.xTop)
#              self.setAxisOptions(QwtPlot.xTop,QwtAutoScale.Inverted)
              if self._vells_plot:
                delta_vells = self.vells_end_freq - self.vells_start_freq
                x_step = delta_vells / shape[0] 
                start_freq = self.vells_start_freq + 0.5 * x_step
                for i in range(shape[0]):
                  self.x_index[i] = start_freq + i * x_step
                delta_vells = self.vells_end_time - self.vells_start_time
                y_step = delta_vells / shape[1] 
                start_time = self.vells_start_time + 0.5 * y_step
                for i in range(shape[1]):
                  self.y_index[i] = start_time + i * y_step
              self.setCurveData(self.xCrossSection, self.x_index, self.x_array)
              self.setCurveData(self.yCrossSection, self.y_array, self.y_index)

# put in a line where cross sections are selected
              if self.xCrossSectionLoc is None:
                self.xCrossSectionLoc = self.insertCurve('xCrossSectionLocation')
                self.setCurvePen(self.xCrossSectionLoc, QPen(Qt.black, 2))
                self.setCurveYAxis(self.xCrossSectionLoc, QwtPlot.yLeft)
              self.setCurveData(self.xCrossSectionLoc, self.x_index, self.x_arrayloc)
              if self.yCrossSectionLoc is None:
                self.yCrossSectionLoc = self.insertCurve('yCrossSectionLocation')
                self.setCurvePen(self.yCrossSectionLoc, QPen(Qt.white, 2))
                self.setCurveYAxis(self.yCrossSectionLoc, QwtPlot.yLeft)
                self.setCurveXAxis(self.yCrossSectionLoc, QwtPlot.xBottom)
              self.setCurveData(self.yCrossSectionLoc, self.y_arrayloc, self.y_index)
              if self.is_combined_image:
                self.removeMarkers()
	        self.insert_marker_lines()
              self.replot()
              _dprint(2, 'called replot in onMousePressed');
           
# fake a mouse move to show the cursor position
        self.onMouseMoved(e)

    # onMousePressed()

    def onMouseReleased(self, e):
        if Qt.LeftButton == e.button():
            self.refresh_marker_display()
            xmin = min(self.xpos, e.pos().x())
            xmax = max(self.xpos, e.pos().x())
            ymin = min(self.ypos, e.pos().y())
            ymax = max(self.ypos, e.pos().y())
            self.setOutlineStyle(Qwt.Cross)
            xmin = self.invTransform(QwtPlot.xBottom, xmin)
            xmax = self.invTransform(QwtPlot.xBottom, xmax)
            ymin = self.invTransform(QwtPlot.yLeft, ymin)
            ymax = self.invTransform(QwtPlot.yLeft, ymax)
            if xmin == xmax or ymin == ymax:
                return
            self.zoomStack.append(self.zoomState)
            self.zoomState = (xmin, xmax, ymin, ymax)
            self.enableOutline(0)
        elif Qt.RightButton == e.button():
            if len(self.zoomStack):
                xmin, xmax, ymin, ymax = self.zoomStack.pop()
            else:
                return
        elif Qt.MidButton == e.button():
          return

        self.setAxisScale(QwtPlot.xBottom, xmin, xmax)
        self.setAxisScale(QwtPlot.yLeft, ymin, ymax)
        self.replot()
        _dprint(2, 'called replot in onMouseReleased');

    # onMouseReleased()

    def toggleCurve(self, key):
        curve = self.curve(key)
        if curve:
            curve.setEnabled(not curve.enabled())
            self.replot()
            _dprint(2, 'called replot in toggleCurve');
    # toggleCurve()

    def setDisplayType(self, display_type):
      self._display_type = display_type
      self.plotImage.setDisplayType(display_type)
      self.emit(PYSIGNAL("display_type"),(self._display_type,))
    # setDisplayType

    def display_image(self, image):
      image_for_display = None
      if image.type() == Complex32 or image.type() == Complex64:
# if incoming array is complex, create array of reals followed by imaginaries
        real_array =  image.getreal()
        imag_array =  image.getimag()
        shape = real_array.shape
        image_for_display = zeros((2*shape[0],shape[1]), Float32)
        for k in range(shape[0]):
          for j in range(shape[1]):
            image_for_display[k,j] = real_array[k,j]
            image_for_display[k+shape[0],j] = imag_array[k,j]
      else:
        image_for_display = image
      
      # emit range for the color bar
      self.emit(PYSIGNAL("image_range"),(image_for_display.min(), image_for_display.max()))
      if self._vells_plot:
        self.plotImage.setData(image_for_display, self.vells_freq, self.vells_time)
      else:
        self.plotImage.setData(image_for_display)

      self.raw_image = image_for_display

      if self.is_combined_image:
         _dprint(2, 'display_image inserting markers')
         self.removeMarkers()
	 self.insert_marker_lines()
      self.insert_array_info()

# add solver metrics info?
      if not self.metrics_rank is None:
        self.metrics_plot = self.insertCurve('metrics')
        self.setCurvePen(self.metrics_plot, QPen(Qt.black, 2))
        self.setCurveStyle(self.metrics_plot,Qt.SolidLine)
        self.setCurveYAxis(self.metrics_plot, QwtPlot.yLeft)
        self.setCurveXAxis(self.metrics_plot, QwtPlot.xBottom)
        plot_curve=self.curve(self.metrics_plot)
        plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.black),
                   QPen(Qt.black), QSize(10,10)))
        self.setCurveData(self.metrics_plot, self.metrics_rank, self.iteration_number)
      self.replot()
      _dprint(2, 'called replot in display_image');
    # display_image()

    def insert_array_info(self):
# insert mean and standard deviation
      if not self.array_parms is None:
# alias
        fn = self.fontInfo().family()

# text marker giving mean and std deviation of array
        self.info_marker = self.insertMarker()
        ylb = self.axisScale(QwtPlot.yLeft).hBound()
        xlb = self.axisScale(QwtPlot.xBottom).hBound()
        self.setMarkerPos(self.info_marker, xlb, ylb)
        self.setMarkerLabelAlign(self.info_marker, Qt.AlignLeft | Qt.AlignBottom)
        self.setMarkerLabel( self.info_marker, self.array_parms,
          QFont(fn, 9, QFont.Bold, False),
          Qt.blue, QPen(Qt.red, 2), QBrush(Qt.white))
    # insert_array_info()

    def plot_data(self, visu_record, attribute_list=None):
      """ process incoming data and attributes into the
          appropriate type of plot """
      _dprint(2, 'in plot data');
#      _dprint(2, 'visu_record ', visu_record)

# first find out what kind of plot we are making
      self._plot_type = None
      self._title = None
      self._x_axis = None
      self._y_axis = None
      self._display_type = None
      self._string_tag = None
      self._data_labels = None
      self._tag_plot_attrib={}
      if attribute_list is None: 
        if visu_record.has_key('attrib'):
          self._attrib_parms = visu_record['attrib']
          _dprint(2,'self._attrib_parms ', self._attrib_parms);
          plot_parms = self._attrib_parms.get('plot')
          if plot_parms.has_key('tag_attrib'):
            temp_parms = plot_parms.get('tag_attrib')
            tag = temp_parms.get('tag')
            self._tag_plot_attrib[tag] = temp_parms
          if plot_parms.has_key('attrib'):
            temp_parms = plot_parms.get('attrib')
            plot_parms = temp_parms
          if self._plot_type is None and plot_parms.has_key('plot_type'):
            self._plot_type = plot_parms.get('plot_type')
          if self._display_type is None and plot_parms.has_key('spectrum_color'):
            self._display_type = plot_parms.get('spectrum_color')
            self.emit(PYSIGNAL("display_type"),(self._display_type,))
          if self._attrib_parms.has_key('tag'):
            tag = self._attrib_parms.get('tag')
        else:
          self._plot_type = self.plot_key
      else:
# first get plot_type at first possible point in list - nearest root
        list_length = len(attribute_list)
        for i in range(list_length):
          self._attrib_parms = attribute_list[i]
          if self._attrib_parms.has_key('plot'):
            plot_parms = self._attrib_parms.get('plot')
            if plot_parms.has_key('tag_attrib'):
              temp_parms = plot_parms.get('tag_attrib')
              tag = temp_parms.get('tag')
              self._tag_plot_attrib[tag] = temp_parms
            if plot_parms.has_key('attrib'):
              temp_parms = plot_parms.get('attrib')
              plot_parms = temp_parms
            if self._plot_type is None and plot_parms.has_key('plot_type'):
              self._plot_type = plot_parms.get('plot_type')
            if self._title is None and plot_parms.has_key('title'):
              self._title = plot_parms.get('title')
              self.setTitle(self._title)
            if self._x_axis is None and plot_parms.has_key('x_axis'):
              self._x_axis = plot_parms.get('x_axis')
            if self._y_axis is None and plot_parms.has_key('y_axis'):
              self._y_axis = plot_parms.get('y_axis')
            if self._display_type is None and plot_parms.has_key('spectrum_color'):
              self._display_type = plot_parms.get('spectrum_color')
              self.emit(PYSIGNAL("display_type"),(self._display_type,))
          if self._attrib_parms.has_key('tag'):
            tag = self._attrib_parms.get('tag')
            if self._string_tag is None:
              self._string_tag = ''
            if isinstance(tag, tuple):
              _dprint(2,'tuple tag ', tag);
              for i in range(0, len(tag)):
                if self._string_tag.find(tag[i]) < 0:
                  temp_tag = self._string_tag + ' ' + tag[i]
                  self._string_tag = temp_tag
              _dprint(2,'self._string_tag ', self._string_tag);
            else:
              _dprint(2,'non tuple tag ', tag);
              if self._string_tag is None:
                self._string_tag = ''
              if self._string_tag.find(tag) < 0:
                temp_tag = self._string_tag + ' ' + tag
                self._string_tag = temp_tag

      if visu_record.has_key('label'):
        self._data_labels = visu_record['label']
        _dprint(2,'display_image: self._data_labels ', self._data_labels);
      else:
        self._data_labels = ''

# set defaults for anything that is not specified
      if self._string_tag is None:
        self._string_tag = ''
      if self._display_type is None:
        self._display_type = 'hippo'
        self.emit(PYSIGNAL("display_type"),(self._display_type,))
      if self._plot_type is None:
        self._plot_type = 'spectra'

# set the display color type in the low level QwtPlotImage class
      self.setDisplayType(self._display_type)

      if visu_record.has_key('value'):
        self._data_values = visu_record['value']

      if len(self._tag_plot_attrib) > 0:
        _dprint(3, 'self._tag_plot_attrib has keys ', self._tag_plot_attrib.keys())

# extract and define labels for this data item
     # now generate  particular plot type
      if  self._plot_type == 'spectra':
# ensure that menu for display is updated if required
        self.initSpectrumContextMenu()
# plot first instance of array
        if not self.active_image_index is None:
          self.array_plot(self._plot_label[self.active_image_index], self._plot_dict[self.active_image_index],False)
          if self.active_image_index == self._combined_image_id:
	    self.is_combined_image = True
            self.removeMarkers()
	    self.insert_marker_lines()
        elif not self._combined_image_id is None:
          self.array_plot(self._plot_label[ self._combined_image_id], self._plot_dict[ self._combined_image_id],False)
	  self.is_combined_image = True
          self.removeMarkers()
          self.insert_marker_lines()
	else:
          if not self._plot_dict_size is None:
            data_label = ''
            if isinstance(self._data_labels, tuple):
              data_label = 'spectra:' + self._string_tag +  " " +self._data_labels[0]
            else:
              data_label = 'spectra:' + self._string_tag +  " " +self._data_labels
            _dprint(3, 'plotting array with label ', data_label)
            self.array_plot(data_label, self._data_values[0])
      _dprint(2, 'exiting plot_data');

    # end plot_data()

    def calc_vells_ranges(self):
      """ get vells frequency and time ranges for use 
          with other functions """
                                                                                
      self.vells_start_freq = self._vells_rec.cells.domain.freq[0] 
      self.vells_end_freq  =  self._vells_rec.cells.domain.freq[1]
#     self.vells_start_time = self._vells_rec.cells.domain.time[0] 
#     self.vells_end_time  =  self._vells_rec.cells.domain.time[1]
      self.vells_start_time = 0
      self.vells_end_time  =  self._vells_rec.cells.domain.time[1] - self._vells_rec.cells.domain.time[0]
      if self.vells_start_freq > 1.0e6:
        self.vells_start_freq = self.vells_start_freq / 1.0e6
        self.vells_end_freq = self.vells_end_freq / 1.0e6
        self._mhz = True
      elif self.vells_start_freq > 1.0e3:
        self.vells_start_freq = self.vells_start_freq / 1.0e3
        self.vells_end_freq = self.vells_end_freq / 1.0e3
        self._khz = True

      self.vells_freq = (self.vells_start_freq,self.vells_end_freq)
      self.vells_time = (self.vells_start_time,self.vells_end_time)

# get grid parameters - will help decide if we are dealing with
# time or frequency data for 1-D vells arrays
      try:
        test_freq_shape = self._vells_rec.cells.grid.freq.shape
      except:
        self.is_time_vector = True
      try:
        test_time_shape = self._vells_rec.cells.grid.time.shape
      except:
        self.is_freq_vector = True

                                                                                
    def plot_vells_data (self, vells_record):
      """ process incoming vells data and attributes into the
          appropriate type of plot """

      _dprint(2, 'in plot_vells_data');
      self.metrics_rank = None
      self.iteration_number = None
      self._vells_rec = vells_record;
# if we are single stepping through requests, Oleg may reset the
# cache, so check for a non-data record situation
      if isinstance(self._vells_rec, bool):
        return

# are we dealing with 'solver' results?
      if self._vells_rec.has_key("solver_result"):
        if self._vells_rec.solver_result.has_key("incremental_solutions"):
          self._solver_flag = True
          complex_type = False;
          if self._vells_rec.solver_result.incremental_solutions.type() == Complex32:
            complex_type = True;
          if self._vells_rec.solver_result.incremental_solutions.type() == Complex64:
            complex_type = True;
          self._value_array = self._vells_rec.solver_result.incremental_solutions
          if self._vells_rec.solver_result.has_key("metrics"):
            metrics = self._vells_rec.solver_result.metrics
            self.metrics_rank = zeros(len(metrics), Int32)
            self.iteration_number = zeros(len(metrics), Int32)
            for i in range(len(metrics)):
               self.metrics_rank[i] = metrics[i].rank
               self.iteration_number[i] = i+1
          shape = self._value_array.shape
          if shape[1] > 1:
            self._x_axis = 'Solvable Coeffs'
            self._y_axis = 'Iteration Nr'
            self.array_plot("Solver Incremental Solutions", self._value_array, True)
          else:
            self._y_axis = 'Value'
            self._x_axis = 'Iteration Nr'
            self.array_plot("Solver Incremental Solution", self._value_array, True)

# are we dealing with Vellsets?
      if self._vells_rec.has_key("vellsets") and not self._solver_flag:
        self._vells_plot = True
        self.calc_vells_ranges()
        self. initVellsContextMenu()
        _dprint(3, 'handling vellsets')


# how many VellSet planes (e.g. I, Q, U, V would each be a plane) are there?
        if self._active_plane is None:
          self._active_plane = 0
        number_of_planes = len(self._vells_rec["vellsets"])
        _dprint(3, 'number of planes ', number_of_planes)
        if self._vells_rec.vellsets[self._active_plane].has_key("shape"):
          self._shape = self._vells_rec.vellsets[self._active_plane]["shape"]

# do we have flags for data	  
        if self._vells_rec.vellsets[self._active_plane].has_key("flags"):
# test if we have a numarray
          try:
            self._flags_array = self._vells_rec.vellsets[self._active_plane].flags
            _dprint(3, 'self._flags_array ', self._flags_array)
            array_shape = self._flags_array.shape
            if len(array_shape) == 1 and array_shape[0] == 1:
              temp_value = self._flags_array[0]
              temp_array = asarray(temp_value)
              self._flags_array = resize(temp_array,self._shape)
          except:
            temp_array = asarray(self._vells_rec.vellsets[self._active_plane].flags)
            self._flags_array = resize(temp_array,self._shape)

          self.setFlagsData(self._flags_array)

	
# plot the appropriate plane / perturbed value
        complex_type = False;
        if not self._active_perturb is None:
          self._value_array = self._vells_rec.vellsets[self._active_plane].perturbed_value[self._active_perturb]
        else:
          if self._vells_rec.vellsets[self._active_plane].has_key("value"):
            self._value_array = self._vells_rec.vellsets[self._active_plane].value
# test if we have a numarray
        try:
            if self._value_array.type() == Complex32:
              complex_type = True;
            if self._value_array.type() == Complex64:
              complex_type = True;
            _dprint(3, 'self._value_array ', self._value_array)
            array_shape = self._value_array.shape
            if len(array_shape) == 1 and array_shape[0] == 1:
              temp_value = self._value_array[0]
              temp_array = asarray(temp_value)
              self._value_array = resize(temp_array,self._shape)

        except:
            temp_array = None
            if self._active_perturb is None:
              temp_array = asarray(self._vells_rec.vellsets[self._active_plane].value)
            else:
              temp_array = asarray(self._vells_rec.vellsets[self._active_plane].perturbed_value[self._active_perturb])
            self._shape = self._vells_rec.vellsets[self._active_plane]["shape"]
            self._value_array = resize(temp_array,self._shape)
            if self._value_array.type() == Complex32:
              complex_type = True;
            if self._value_array.type() == Complex64:
              complex_type = True;

        key = ""
        if self._active_perturb is None:
          key = " value "
          self._label =  "plane " + str(self._active_plane) + key 
        else:
          key = " perturbed_value "
          self._label =  "plane " + str(self._active_plane) + key + str(self._active_perturb)
        if self._solver_flag:
          self.array_plot(self._label, self._value_array, False)
        else:
          self.array_plot(self._label, self._value_array)

    # end plot_vells_data()

    def handle_finished (self):
      print 'in handle_finished'

    def array_plot (self, data_label, incoming_plot_array, flip_axes=True):
      """ figure out shape, rank etc of a spectrum array and
          plot it  """

# delete any previous curves
      self.removeCurves()
      self.xCrossSection = None
      self.yCrossSection = None
      self.enableAxis(QwtPlot.yRight, False)
      self.enableAxis(QwtPlot.xTop, False)
      self.xCrossSectionLoc = None
      self.yCrossSectionLoc = None
      self.dummy_xCrossSection = None
      self.myXScale = None
      self.myYScale = None
      self.split_axis = None
      self.array_parms = None

# pop up menu for printing
      if self._menu is None:
        self._menu = QPopupMenu(self._mainwin);
        self.add_basic_menu_items()
        QObject.connect(self._menu,SIGNAL("activated(int)"),self.update_spectrum_display);


# set title
      if self._title is None:
        self.setTitle(data_label)

# hack to get array display correct until forest.state
# record is available
      plot_array = incoming_plot_array
      if flip_axes:
        axes = arange(incoming_plot_array.rank)[::-1]
        plot_array = transpose(incoming_plot_array, axes)

# figure out type and rank of incoming array
# for vectors, this is a pain as e.g. (8,) and (8,1) have
# different 'formal' ranks but really are the same 1-D vectors
# I'm not sure that the following covers all bases, but we are getting close
      self.is_vector = False;
      array_rank = 0
      is_frequency = False
      num_elements = 1
      for i in range(len(plot_array.shape)):
        num_elements = num_elements * plot_array.shape[i]
        if plot_array.shape[i] > 1:
          array_rank = array_rank + 1
      if array_rank == 1:
        self.is_vector = True;
# check if grid frequency/time layout gives extra info
        if self._vells_plot:
          if not self.is_freq_vector is None:
            is_frequency = True
          if not self.is_time_vector is None:
            is_frequency = False
          if self.is_time_vector is None and self.is_freq_vector is None:
            if len(plot_array.shape) > 1:
              if plot_array.shape[1] == 1:
                is_frequency = True
        else:
          if len(plot_array.shape) > 1:
            if plot_array.shape[1] == 1:
              is_frequency = True

# test for real or complex
      complex_type = False;
      if plot_array.type() == Complex32:
        complex_type = True;
      if plot_array.type() == Complex64:
        complex_type = True;

# test if we have a 2-D array
      if self.is_vector == False:
        self.active_image = True

# get mean and standard deviation of array
        temp_str = ""
        if complex_type:
          if plot_array.mean().imag < 0:
            temp_str = "m: %-.3g %-.3gj" % (plot_array.mean().real,plot_array.mean().imag)
          else:
            temp_str = "m: %-.3g+ %-.3gj" % (plot_array.mean().real,plot_array.mean().imag)
        else:
          temp_str = "m: %-.3g" % plot_array.mean()
        temp_str1 = "sd: %-.3g" % standard_deviation(plot_array,complex_type )
        self.array_parms = temp_str + " " + temp_str1

        self.setAxisTitle(QwtPlot.yLeft, 'sequence')
        if complex_type and self._display_type != "brentjens":
          if self._vells_plot:
	    if self._x_axis is None:
              if self._mhz:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(MHz): (real followed by imaginary)')
              elif self._khz:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(KHz): (real followed by imaginary)')
              else:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(Hz): (real followed by imaginary)')
	    else:  
              self.setAxisTitle(QwtPlot.xBottom, self._x_axis)
	    if self._y_axis is None:
              self.setAxisTitle(QwtPlot.yLeft, 'Time(sec): (relative to start)')
	    else:
              self.setAxisTitle(QwtPlot.yLeft, self._y_axis)
            self.myXScale = ComplexScaleSeparate(self.vells_start_freq,self.vells_end_freq)
            self.delta_vells = self.vells_end_freq - self.vells_start_freq
	    self.vells_end_freq = self.vells_start_freq + 2 * self.delta_vells
	    self.vells_freq = (self.vells_start_freq,self.vells_end_freq)
            self.split_axis = self.vells_start_freq  + self.delta_vells
            self.setAxisScaleDraw(QwtPlot.xBottom, self.myXScale)
          else:
	    if self._x_axis is None:
              self.setAxisTitle(QwtPlot.xBottom, 'Channel Number (real followed by imaginary)')
	    else:  
              self.setAxisTitle(QwtPlot.xBottom, self._x_axis)
	    if self._y_axis is None:
              self.setAxisTitle(QwtPlot.yLeft, 'sequence')
	    else:
              self.setAxisTitle(QwtPlot.yLeft, self._y_axis)
            self.myXScale = ComplexScaleDraw(plot_array.shape[0])
            self.setAxisScaleDraw(QwtPlot.xBottom, self.myXScale)
	    self.split_axis = plot_array.shape[0]
	    if not self.y_marker_step is None:
              self.myYScale = ComplexScaleDraw(self.y_marker_step)
              self.setAxisScaleDraw(QwtPlot.yLeft, self.myYScale)

          self.display_image(plot_array)

        else:
          if self._vells_plot:
	    if self._x_axis is None:
              if self._mhz:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(MHz)')
              elif self._khz:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(KHz)')
              else:
                self.setAxisTitle(QwtPlot.xBottom, 'Frequency(Hz)')
	    else:  
              self.setAxisTitle(QwtPlot.xBottom, self._x_axis)
	    if self._y_axis is None:
              self.setAxisTitle(QwtPlot.yLeft, 'Time(sec): (relative to start)')
	    else:
              self.setAxisTitle(QwtPlot.yLeft, self._y_axis)
          else:
	    if self._x_axis is None:
              self.setAxisTitle(QwtPlot.xBottom, 'Channel Number')
	    else:  
              self.setAxisTitle(QwtPlot.xBottom, self._x_axis)
	    if self._y_axis is None:
              self.setAxisTitle(QwtPlot.yLeft, 'sequence')
	    else:
              self.setAxisTitle(QwtPlot.yLeft, self._y_axis)
          self.display_image(plot_array)

      if self.is_vector == True:
# make sure we are autoscaling in case an image was previous
        self.setAxisAutoScale(QwtPlot.xBottom)
        self.setAxisAutoScale(QwtPlot.yLeft)
        self.setAxisAutoScale(QwtPlot.yRight)

        if not self._flags_array is None:
          self.flags_x_index = []
          self.flags_r_values = []
          self.flags_i_values = []
        self.active_image = False
        if self._vells_plot:
          if is_frequency:
            if self._mhz:
              self.setAxisTitle(QwtPlot.xBottom, 'Frequency(MHz)')
            elif self._khz:
              self.setAxisTitle(QwtPlot.xBottom, 'Frequency(KHz)')
            else:
              self.setAxisTitle(QwtPlot.xBottom, 'Frequency(Hz)')
            delta_vells = self.vells_end_freq - self.vells_start_freq
            x_step = delta_vells / num_elements 
            start_freq = self.vells_start_freq + 0.5 * x_step
            self.x_index = zeros(num_elements, Float32)
            for j in range(num_elements):
              self.x_index[j] = start_freq + j * x_step
          else:
            self.setAxisTitle(QwtPlot.xBottom, 'Time(sec): (relative to start)')
            delta_vells = self.vells_end_time - self.vells_start_time
            x_step = delta_vells / num_elements 
            start_time = self.vells_start_time + 0.5 * x_step
            self.x_index = zeros(num_elements, Float32)
            for j in range(num_elements):
              self.x_index[j] = start_time + j * x_step
        else:
	  if self._x_axis is None:
            self.setAxisTitle(QwtPlot.xBottom, 'Channel Number')
	  else:  
            self.setAxisTitle(QwtPlot.xBottom, self._x_axis)
          self.x_index = arange(num_elements)
          self.x_index = self.x_index + 0.5
# if we are plotting a single iteration solver solution
# plot on 'locations' of solver parameters. Use 'self.metrics_rank'
# as test, but don't plot metrics in this case
          if not self.metrics_rank is None:
            self.x_index = self.x_index + 0.5
        flattened_array = reshape(plot_array,(num_elements,))
        if not self._flags_array is None:
          if complex_type:
            x_array =  flattened_array.getreal()
            y_array =  flattened_array.getimag()
            for j in range(num_elements):
              if self._flags_array[j] > 0:
                self.flags_x_index.append(self.x_index[j])
                self.flags_r_values.append(x_array[j])
                self.flags_i_values.append(y_array[j])
          else:
            for j in range(num_elements):
              if self._flags_array[j] > 0:
                self.flags_x_index.append(self.x_index[j])
                self.flags_r_values.append(flattened_array[j])
# we have a complex vector
        if complex_type:
          self.enableAxis(QwtPlot.yRight)
          self.setAxisTitle(QwtPlot.yLeft, 'Value: real (black line / red dots)')
          self.setAxisTitle(QwtPlot.yRight, 'Value: imaginary (blue line / green dots)')
          self.xCrossSection = self.insertCurve('xCrossSection')
          self.yCrossSection = self.insertCurve('yCrossSection')
          self.setCurvePen(self.xCrossSection, QPen(Qt.black, 2))
          self.setCurvePen(self.yCrossSection, QPen(Qt.blue, 2))
          self.setCurveYAxis(self.xCrossSection, QwtPlot.yLeft)
          self.setCurveYAxis(self.yCrossSection, QwtPlot.yRight)
          plot_curve=self.curve(self.xCrossSection)
          plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.red),
                     QPen(Qt.red), QSize(10,10)))
          plot_curve=self.curve(self.yCrossSection)
          plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.green),
                     QPen(Qt.green), QSize(10,10)))
          self.x_array =  flattened_array.getreal()
          self.y_array =  flattened_array.getimag()
          self.setCurveData(self.xCrossSection, self.x_index, self.x_array)
          self.setCurveData(self.yCrossSection, self.x_index, self.y_array)
          if not self.dummy_xCrossSection is None:
            self.removeCurve(self.dummy_xCrossSection)
            self.dummy_xCrossSection = None

# stuff for flags
          if not self._flags_array is None:
            self.real_flag_vector = self.insertCurve('real_flags')
            self.setCurvePen(self.real_flag_vector, QPen(Qt.black))
            self.setCurveStyle(self.real_flag_vector, QwtCurve.Dots)
            self.setCurveYAxis(self.real_flag_vector, QwtPlot.yLeft)
            plot_flag_curve = self.curve(self.real_flag_vector)
            plot_flag_curve.setSymbol(QwtSymbol(QwtSymbol.XCross, QBrush(Qt.black),
                     QPen(Qt.black), QSize(20, 20)))
            self.setCurveData(self.real_flag_vector, self.flags_x_index, self.flags_r_values)
# Note: We don't show the flag data in the initial display
# but toggle it on or off (ditto for imaginary data flags).
            self.curve(self.real_flag_vector).setEnabled(False)
            self.imag_flag_vector = self.insertCurve('imag_flags')
            self.setCurvePen(self.imag_flag_vector, QPen(Qt.black))
            self.setCurveStyle(self.imag_flag_vector, QwtCurve.Dots)
            self.setCurveYAxis(self.imag_flag_vector, QwtPlot.yRight)
            plot_flag_curve = self.curve(self.imag_flag_vector)
            plot_flag_curve.setSymbol(QwtSymbol(QwtSymbol.XCross, QBrush(Qt.black),
                     QPen(Qt.black), QSize(20, 20)))
            self.setCurveData(self.imag_flag_vector, self.flags_x_index, self.flags_i_values)
            self.curve(self.imag_flag_vector).setEnabled(False)

        else:
          self.setAxisTitle(QwtPlot.yLeft, 'Value')
          self.enableAxis(QwtPlot.yRight, False)
          self.x_array = zeros(num_elements, Float32)
          self.y_array = zeros(num_elements, Float32)
          self.x_array =  flattened_array
          self.xCrossSection = self.insertCurve('xCrossSection')
          self.setCurvePen(self.xCrossSection, QPen(Qt.black, 2))
          self.setCurveStyle(self.xCrossSection,Qt.SolidLine)
          self.setCurveYAxis(self.xCrossSection, QwtPlot.yLeft)
          plot_curve=self.curve(self.xCrossSection)
          plot_curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse, QBrush(Qt.red),
                     QPen(Qt.red), QSize(10,10)))
          self.setCurveData(self.xCrossSection, self.x_index, self.x_array)
          if not self.dummy_xCrossSection is None:
            self.removeCurve(self.dummy_xCrossSection)
            self.dummy_xCrossSection = None
# stuff for flags
          if not self._flags_array is None:
            self.real_flag_vector = self.insertCurve('real_flags')
            self.setCurvePen(self.real_flag_vector, QPen(Qt.black))
            self.setCurveStyle(self.real_flag_vector, QwtCurve.Dots)
            self.setCurveYAxis(self.real_flag_vector, QwtPlot.yLeft)
            plot_flag_curve = self.curve(self.real_flag_vector)
            plot_flag_curve.setSymbol(QwtSymbol(QwtSymbol.XCross, QBrush(Qt.black),
                     QPen(Qt.black), QSize(20, 20)))
            self.setCurveData(self.real_flag_vector, self.flags_x_index, self.flags_r_values)
            self.curve(self.real_flag_vector).setEnabled(False)

# do the replot
        self.replot()
        _dprint(2, 'called replot in array_plot');
    # array_plot()

    def setFlagsData (self, incoming_flag_array, flip_axes=True):
      """ figure out shape, rank etc of a flag array and
          plot it  """

# hack to get array display correct until forest.state
# record is available
      flag_array = incoming_flag_array
      if flip_axes:
        axes = arange(incoming_flag_array.rank)[::-1]
        flag_array = transpose(incoming_flag_array, axes)

# figure out type and rank of incoming array
      flag_is_vector = False;
      array_rank = 0
      for i in range(len(flag_array.shape)):
        if flag_array.shape[i] > 1:
          array_rank = array_rank + 1
      if array_rank == 1:
        flag_is_vector = True;

      n_rows = 1
      n_cols = 1
      if array_rank == 1:
        n_rows = flag_array.shape[0]
        if len(flag_array.shape) > 1:
          n_cols = flag_array.shape[1]

      if flag_is_vector == False:
        self.plotImage.setFlagsArray(flag_array)
      else:
        num_elements = n_rows*n_cols
        self._flags_array = reshape(flag_array,(num_elements,))

    # setFlagData()

    def add_basic_menu_items(self):
        toggle_id = 300
        self._menu.insertItem("Toggle Cross-Section Legend", toggle_id)
        zoom = QAction(self);
        zoom.setIconSet(pixmaps.viewmag.iconset());
        zoom.setText("Disable zoomer");
        zoom.addTo(self._menu);
        printer = QAction(self);
        printer.setIconSet(pixmaps.fileprint.iconset());
        printer.setText("Print plot");
        QObject.connect(printer,SIGNAL("activated()"),self.printplot);
        printer.addTo(self._menu);

    def start_test_timer(self, time, test_complex, display_type):
      self.test_complex = test_complex
      self.setDisplayType(display_type)
      self.startTimer(time)
     # start_test_timer()
                                                                                
    def timerEvent(self, e):
      if self.test_complex:
        m = fromfunction(RealDist, (30,20))
        n = fromfunction(ImagDist, (30,20))
        vector_array = zeros((30,1), Complex64)
        shape = m.shape
        for i in range(shape[0]):
          for j in range(shape[1]):
            m[i,j] = m[i,j] + self.index * random.random()
            n[i,j] = n[i,j] + 3 * self.index * random.random()
        a = zeros((shape[0],shape[1]), Complex64)
        a.setreal(m)
        a.setimag(n)         
        for i in range(shape[0]):
          vector_array[i,0] = a[i,0]
        if self.index % 2 == 0:
          _dprint(2, 'plotting array');
          self.array_plot('test_image_complex',a)
          self.test_complex = False
        else:
          _dprint(2, 'plotting vector');
          self.array_plot('test_vector_complex', vector_array)
      else:
        vector_array = zeros((30,1), Float32)
        m = fromfunction(dist, (30,20))
        shape = m.shape
        for i in range(shape[0]):
          for j in range(shape[1]):
            m[i,j] = m[i,j] + self.index * random.random()
        for i in range(shape[0]):
          vector_array[i,0] = m[i,0]
        if self.index % 2 == 0:
          _dprint(2, 'plotting vector');
          self.array_plot('test_vector', vector_array)
          self.test_complex = True
        else:
          _dprint(2, 'plotting array');
          self.array_plot('test_image',m)

      self.index = self.index + 1
    # timerEvent()


def make():
    demo = QwtImageDisplay('plot_key')
    demo.resize(500, 300)
    demo.show()
# uncomment the following
    demo.start_test_timer(5000, False, "brentjens")

# or
# uncomment the following three lines
#   import pyfits
#   image = pyfits.open('./3C236.FITS')
#   demo.array_plot('3C236', image[0].data)

    return demo

def main(args):
    app = QApplication(args)
    demo = make()
    app.setMainWidget(demo)
    app.exec_loop()


# Admire
if __name__ == '__main__':
    main(sys.argv)

