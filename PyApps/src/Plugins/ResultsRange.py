#!/usr/bin/env python

# a class to generate control buttons etc for use in controlling N-dimensional
# displays

# modules that are imported

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

import sys
from qt import *
from Timba.GUI.pixmaps import pixmaps
from BufferSizeDialog import *

# The ResultsRange class is directly adapted from the Qt/PyQt 
# tutorial code examples.
#
# It creates a simple spinbox and slider that is used to select a data
# set for display with the result plotter. It is rather similar to the
# AxisRange class used with the ND-Controller, but the layout is
# different.

results_range_help = \
'''
This widget displays a spinbox and a slider. The spinbox and the slider both have the same value. Changing one or the other causes an event to be sent to the visualization system with a request to change the array index of the displayed data. The visualization display is then updated. The spinbox is wrapped around so that one can go directly from the highest index to the lowest.<br><br>

When you click in the area of the widget with the right mouse button a context menu will be shown. In the case of the <b>3-dimensional display</b>, this context menu will allow you to select a new active plane - one of the X, Y or Z axes. It also gives you the possibility of switching back to the 2-dimensional display. In the case of the results <b>history sequence</b> display, the menu offers you the single option of changing the number of sequential records that can be stored. If you select this option, a small dialog will appear that allows you to modify the allowable number of records that can be stored. The default is 10.<br><br> 
'''

class ResultsRange(QWidget):
    def __init__(self, parent=None, name=""):
      QWidget.__init__(self, parent, name)

      self.menu_table = {
      'Adjust results buffer size': 301,
      'Display summary plot': 302,
      'X Axis': 303,
      'Y Axis': 304,
      'Z Axis': 305,
      'Show 2D Display': 306,
      'Update': 307,
      'Toggle ND Controller': 308,
      'Print to Postscript file': 309,
      }

      self.allow_emit = False
      self.allow_summary = False
      self.summary_request = True
      self.toggle_ND_Controller = 1
      self.menu = None
      self.maxVal = 10
      self.minVal = 1
      self.label_info = QLabel('', self)
      self.label_info1 = QLabel('          ', self)
      self.string_info =  ' '
      self.offset_index = -1
      self.spinbox = QSpinBox(self)
      self.spinbox.setMinValue(self.minVal)
      self.spinbox.setMaxValue(self.maxVal)
      self.spinbox.setWrapping(True)

      self.slider = QSlider(Qt.Horizontal, self, "slider")
      self.slider.setTickmarks(QSlider.Below)
      self.slider.setTickInterval(self.minVal)
      self.slider.setRange(self.minVal, self.maxVal)


      self.setValue()

      self.connect(self.slider, SIGNAL("valueChanged(int)"), self.update_slider)
      self.connect(self.spinbox, SIGNAL("valueChanged(int)"), self.update_spinbox)

      self.layout = QHBoxLayout(self)
      spacer = QSpacerItem(22,9,QSizePolicy.Expanding,QSizePolicy.Minimum)
      spacer1 = QSpacerItem(22,9,QSizePolicy.Expanding,QSizePolicy.Minimum)
      self.layout.addItem(spacer)
      self.layout.addWidget(self.label_info)
      self.layout.addWidget(self.spinbox)
#     self.layout.addItem(spacer1)
      self.layout.addWidget(self.label_info1)
      self.layout.addWidget(self.slider)

# add on-line help
      QWhatsThis.add(self, results_range_help)

    def setLabel(self, string_value= ''):
      """ set current displayed label """
      self.label_info.setText(string_value + self.string_info) 

    def setStringInfo(self, string_value= ''):
      """ assign a default leading string """
      self.string_info = string_value

    def setMinValue(self, min_value=0):
      """ reset allowed minimum value for spinbox and slider """
      self.minVal = min_value
      self.spinbox.setMinValue(self.minVal)
      self.slider.setRange(self.minVal, self.maxVal)

    def setMaxValue(self, max_value= 0, allow_shrink=True):
      """ reset allowed maximum value for spinbox and slider """
      if max_value < self.maxVal: 
        if allow_shrink:
          self.maxVal = max_value
          self.slider.setRange(self.minVal, self.maxVal)
          self.spinbox.setMaxValue(self.maxVal)
      else:
        if max_value > self.maxVal:
          self.maxVal = max_value
          self.slider.setRange(self.minVal, self.maxVal)
          self.spinbox.setMaxValue(self.maxVal)

    def setValue(self, value= 0):
      """ set current values shown in spinbox and slider """
      self.slider.setValue(value)
      self.spinbox.setValue(value)
      self.initContextmenu()

    def setRange(self, range_value, update_value = True):
      """ define range of values shown with slider """
      if range_value <= self.maxVal:
        self.slider.setRange(self.minVal, range_value)
        self.spinbox.setMaxValue(range_value)
        if update_value:
          self.setValue(range_value)

    def update_slider(self, slider_value):
      """ update spinbox value as function of slider value """
      self.spinbox.setValue(slider_value)

    def update_spinbox(self, spin_value):
      """ update displayed contents of spinbox """
      self.slider.setValue(spin_value)
      if self.allow_emit:
        self.emit(PYSIGNAL("result_index"),(spin_value + self.offset_index,))

    def set_emit(self, permission=True):
      """ flag to allow emitting of Qt signals """
      self.allow_emit = permission

    def X_Axis_Selected(self):
      """ emit signal to select X Axis for 3D display """
      if self.allow_emit:
        self.emit(PYSIGNAL("X_axis_selected"),(True,))

    def Y_Axis_Selected(self):
      """ emit signal to select Y Axis for 3D display """
      if self.allow_emit:
        self.emit(PYSIGNAL("Y_axis_selected"),(True,))

    def Z_Axis_Selected(self):
      """ emit signal to select Z Axis for 3D display """
      if self.allow_emit:
        self.emit(PYSIGNAL("Z_axis_selected"),(True,))

    def request_2D_display(self):
      """ emit signal to request 2D display """
      if self.allow_emit:
        self.emit(PYSIGNAL("twoD_display_requested"),(True,))

    def request_postscript(self):
      """ emit signal to request Postscript printout """
      if self.allow_emit:
        self.emit(PYSIGNAL("postscript_requested"),(True,))

    def requestUpdate(self):
      """ emit signal to request update to array (for testing) """
      if self.allow_emit:
        self.emit(PYSIGNAL("update_requested"),(True,))

    def toggle_ND_controller(self):
      """ emit signal to toggle ND Controller on or off """
      toggle_id = self.menu_table['Toggle ND Controller']
      if self.toggle_ND_Controller == 1:
        self.toggle_ND_Controller = 0
        self.menu.changeItem(toggle_id, 'Show ND Controller')
      else:
        self.toggle_ND_Controller = 1
        self.menu.changeItem(toggle_id, 'Hide ND Controller')
      if self.allow_emit:
        self.emit(PYSIGNAL("show_ND_Controller"),(self.toggle_ND_Controller,))

    def set_summary(self, summary=True):
      """ override default value for allowing summary plot """
      self.allow_summary = summary
      toggle_id = self.menu_table['Display summary plot']
      self.menu.setItemVisible(toggle_id, self.allow_summary)

    def set_offset_index(self, offset):
      """ override default value for offset index """
      self.offset_index = offset

    def setTickInterval(self, tick_interval):
      """ override default tick interval for slider """
      self.slider.setTickInterval(tick_interval)

    def handle_menu_request(self, menuid):
      """ handle requested menu option """
      if menuid == self.menu_table['Adjust results buffer size']:
        self.handleBufferSize(menuid)
      elif menuid == self.menu_table['Display summary plot']:
        self.requestSummary()
      elif menuid == self.menu_table['X Axis']:
        self.X_Axis_Selected()
      elif menuid == self.menu_table['Y Axis']:
        self.Y_Axis_Selected()
      elif menuid == self.menu_table['Z Axis']:
        self.Z_Axis_Selected()
      elif menuid == self.menu_table['Show 2D Display']:
        self.request_2D_display()
      elif menuid == self.menu_table['Toggle ND Controller']:
        self.toggle_ND_controller()
      elif menuid == self.menu_table['Update']:
        self.requestUpdate()
      elif menuid == self.menu_table['Print to Postscript file']:
        self.request_postscript()

    def initContextmenu(self):
      """Initialize the result buffer context menu """
      if self.menu is None:
        self.menu = QPopupMenu(self)
        QObject.connect(self.menu,SIGNAL("activated(int)"),self.handle_menu_request);

        toggle_id = self.menu_table['Adjust results buffer size']
        self.menu.insertItem("Adjust results buffer size", toggle_id)

# option for summary plot
        toggle_id = self.menu_table['Display summary plot']
        self.menu.insertItem("Display summary plot", toggle_id)
        self.menu.setItemVisible(toggle_id, False)

# options for 3D Display
        toggle_id = self.menu_table['X Axis']
        self.menu.insertItem("X Axis", toggle_id)
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Y Axis']
        self.menu.insertItem("Y Axis", toggle_id)
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Z Axis']
        self.menu.insertItem("Z Axis", toggle_id)
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Show 2D Display']
        self.menu.insertItem("Show 2D Display", toggle_id)
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Toggle ND Controller']
        self.menu.insertItem("Toggle ND Controller", toggle_id)
        self.menu.changeItem(toggle_id, 'Hide ND Controller')
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Update']
        self.menu.insertItem("Update", toggle_id)
        self.menu.setItemVisible(toggle_id, False)
        toggle_id = self.menu_table['Print to Postscript file']
        self.menu.insertItem("Print to Postscript file", toggle_id)
        self.menu.setItemVisible(toggle_id, False)

    def setXMenuLabel(self, text):
      """ update X axis context menu label """
      toggle_id = self.menu_table['X Axis']
      self.menu.changeItem(toggle_id, text)

    def setYMenuLabel(self, text):
      """ update Y axis context menu label """
      toggle_id = self.menu_table['Y Axis']
      self.menu.changeItem(toggle_id, text)

    def setZMenuLabel(self, text):
      """ update Z axis context menu label """
      toggle_id = self.menu_table['Z Axis']
      self.menu.changeItem(toggle_id, text)

    def HideNDOption(self):
      """ hide the Toggle ND Controller option """
      toggle_id = self.menu_table['Toggle ND Controller']
      self.menu.setItemVisible(toggle_id, False)

    def disableContextmenu(self):
      """ delete the result buffer context menu """
      if not self.menu is None:
          self.menu.reparent(QWidget(), 0, QPoint())
          self.menu = None

    def init3DContextmenu(self):
      """add 3D options to context menu """
      if self.menu is None:
        self.initContextmenu()
# display options for 3D Display
      toggle_id = self.menu_table['X Axis']
      self.menu.setItemVisible(toggle_id, True)
      toggle_id = self.menu_table['Y Axis']
      self.menu.setItemVisible(toggle_id, True)
      toggle_id = self.menu_table['Z Axis']
      self.menu.setItemVisible(toggle_id, True)
      toggle_id = self.menu_table['Show 2D Display']
      self.menu.setItemVisible(toggle_id, True)
      toggle_id = self.menu_table['Toggle ND Controller']
      self.menu.setItemVisible(toggle_id, True)
      toggle_id = self.menu_table['Print to Postscript file']
      self.menu.setItemVisible(toggle_id, True)

      toggle_id = self.menu_table['Adjust results buffer size']
      self.menu.setItemVisible(toggle_id, False)

    def displayUpdateItem(self):
        toggle_id = self.menu_table['Update']
        self.menu.setItemVisible(toggle_id, True)

    def setResultsBuffer(self, result_value):
      """ redefine the allowable maximum number of values """
      if result_value < 0:
        return
      self.maxVal = result_value
      self.slider.setRange(self.minVal, self.maxVal)
      self.spinbox.setMaxValue(self.maxVal)
      self.emit(PYSIGNAL("adjust_results_buffer_size"),(result_value,))

    def handleBufferSize(self, menuid):
      """ callback to handle 'Adjust buffer' request from the context menu """
      if menuid == self.menu_table['Adjust results buffer size']:
        results_dialog = BufferSizeDialog(self.maxVal, self)
        QObject.connect(results_dialog,PYSIGNAL("return_value"),self.setResultsBuffer)
        results_dialog.show()

    def requestSummary(self, menuid):
      """ callback to handle 'summary plot' request from the context menu """
      if menuid == self.menu_table['Display summary plot']:
        self.emit(PYSIGNAL("display_summary_plot"),(self.summary_request,))
        if self.summary_request:
          self.summary_request = False
          self.menu.changeItem(menuid, 'Discard summary plot')
        else:
          self.summary_request = True
          self.menu.changeItem(menuid, 'Display summary plot')

    def mousePressEvent(self, e):
      if Qt.RightButton == e.button():
        e.accept()
        self.menu.popup(e.globalPos());

#   def contextMenuEvent(self,ev):
#     """ The existence of this function should cause any 
#         higher-level context menu to be ignored when the 
#         right mouse button is clicked inside the widget.
#     """
#     ev.accept()



# the following tests the ResultsRange class
def make():
    demo = ResultsRange()
    demo.setRange(5)
    demo.show()
    demo.init3DContextmenu()
    return demo

# make()

def main(args):
    app = QApplication(args)
    demo = make()
    app.setMainWidget(demo)
    app.exec_loop()

# main()

# Admire
if __name__ == '__main__':
    main(sys.argv)

