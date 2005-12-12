#!/usr/bin/python

from qt import *
from qwt import *

class PrintFilter(QwtPlotPrintFilter):
    def __init__(self):
        QwtPlotPrintFilter.__init__(self)

    # __init___()
    
    def color(self, c, item, i):
        if not (self.options() & QwtPlotPrintFilter.PrintCanvasBackground):
            if item == QwtPlotPrintFilter.MajorGrid:
                return Qt.darkGray
            elif item == QwtPlotPrintFilter.MinorGrid:
                return Qt.gray
        if item == QwtPlotPrintFilter.Title:
            return Qt.red
        elif item == QwtPlotPrintFilter.AxisScale:
            return Qt.green
        elif item == QwtPlotPrintFilter.AxisTitle:
            return Qt.blue
        return c

    # color()

    def font(self, f, item, i):
        result = QFont(f)
        result.setPointSize(int(f.pointSize()*1.25))
        return result

    # font()

# class PrintFilter

class plot_printer:
  def __init__(self, plotter, colorbar=None):

    self.plotter = plotter
    self.colorbar = colorbar
  
# The following 3 functions are adapted from the 'scicraft'
# visualization package

  def _get_qpainter(self, qprinter, hor_widgets, vert_widgets):
    """Returns a qpainter using the given qprinter and geometry."""
    qpainter = QPainter(qprinter)
    metrics = QPaintDeviceMetrics(qpainter.device())
    width = metrics.width()
    height = (width / hor_widgets) * vert_widgets
    qpainter.setClipRect(0, 0, width, height, qpainter.CoordPainter)
    return qpainter

  def _print_plots(self, qprinter, filter, hor_widgets, vert_widgets, is_complex):
    """Prints all plots with the given qprinter.
    """
    qpainter = self._get_qpainter(qprinter, hor_widgets, vert_widgets)
    # get width and height for each plot 
    metrics = QPaintDeviceMetrics(qpainter.device())
    if hor_widgets > 1:
      if metrics.width() > metrics.height():
        # width of plots in x-direction is the largest (wrt. paintdevice)
        width = metrics.width() / hor_widgets
        height = width # quadratically sized plots
      else:
        # height of plots in x-direction is the largest (wrt. paintdevice)
        height = metrics.height() / hor_widgets
        width = height # quadratically sized plots
      if not self.colorbar is None:
        self.colorbar[0].printPlot(qpainter,
          QRect(0, 0, 0.12 * width, height), filter)
        if is_complex:
          self.colorbar[1].printPlot(qpainter,
            QRect(0.16* width, 0, 0.12 * width, height), filter)
      self.plotter.printPlot(qpainter,
        QRect(0.35 * width, 0, 1.4 * width, height), filter)
    else:
      width = metrics.width()
      if metrics.width() > metrics.height():
        width =  metrics.height()
      height = width
      self.plotter.printPlot(qpainter,
        QRect(0, 0, width, height), filter)
    qpainter.end()

  def do_print(self, is_single, is_complex):
    """Sends plots in this window to the printer.
    """
    try:
        qprinter = QPrinter(QPrinter.HighResolution)
    except AttributeError:
        qprinter = QPrinter()
    qprinter.setOrientation(QPrinter.Landscape)
    qprinter.setColorMode(QPrinter.Color)
    qprinter.setOutputToFile(True)
    qprinter.setOutputFileName('image_plot.ps')
    if qprinter.setup():
        filter = PrintFilter()
        if (QPrinter.GrayScale == qprinter.colorMode()):
            filter.setOptions(QwtPlotPrintFilter.PrintAll
                  & ~QwtPlotPrintFilter.PrintCanvasBackground)
# we have 'two' horizontal widgets - colorbar(s) and the display area
        hor_widgets = 2
        if is_single:
          hor_widgets = 1
        self._print_plots(qprinter, filter, hor_widgets, 1, is_complex)

  def add_colorbar(self, colorbar):
    self.colorbar = colorbar

# class plot_printer
