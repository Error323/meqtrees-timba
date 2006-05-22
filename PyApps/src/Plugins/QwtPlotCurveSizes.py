from qt import *
from numarray import *
from qwt import *

class QwtPlotCurveSizes(QwtPlotCurve):
    """ A QwtCurve with adjustable Symbols """

    def __init__(self,parent=None, title=None):
      QwtPlotCurve.__init__(self,parent, title)
      self.symbolSizes = None
      self.symbolList = None

    # __init__()

    def setData(self, xData, yData, symbolSizes=None):
      """ Override default QwtCurve setData method """
      self.symbolSizes = symbolSizes
      QwtPlotCurve.setData(self,xData,yData)
      QwtPlotCurve.curveChanged(self)

    def setSymbolList(self, symbolList):
      """ Override default QwtCurve symbols """
      self.symbolList = symbolList

    def drawSymbols(self, painter, symbol, xMap, yMap, start, to):
      if self.symbolList is None and self.symbolSizes is None:
        print 'QwtPlotCurveSizes fail: you must specify a symbol list or an array of symbol sizes'
        return
      painter.setBrush(symbol.brush());
      painter.setPen(symbol.pen())
      rect = QRect()
      for i in range(start, to+1):
        if not self.symbolList is None:
          painter.setBrush(self.symbolList[i].brush());
          painter.setPen(self.symbolList[i].pen())
# the following screenToLayout call should work but does not
#       symbol_size = QSize(self.symbolSizes[i], self.symbolSizes[i])
#       rect.setSize(QwtPainter.metricsMap().screenToLayout(symbol_size));

# so we do the following 
        if not self.symbolList is None:
          width = self.symbolList[i].size().width()
          height = self.symbolList[i].size().height()
          sizex = QwtPainter.metricsMap().screenToLayoutX(width)
          sizey = QwtPainter.metricsMap().screenToLayoutY(height)
        else:
          sizex = QwtPainter.metricsMap().screenToLayoutX(self.symbolSizes[i])
          sizey = QwtPainter.metricsMap().screenToLayoutY(self.symbolSizes[i])
        rect.setSize(QSize(sizex, sizey))

        xi = xMap.transform(self.x(i));
        yi = yMap.transform(self.y(i));
        rect.moveCenter(QPoint(xi, yi));
        if not self.symbolList is None:
          self.symbolList[i].draw(painter, rect);
        else:
          symbol.draw(painter, rect);
    # drawSymbols()

# class QwtPlotCurveSizes()

def make():
    demo = QwtPlot('symbols demo')
    curve = QwtPlotCurveSizes(demo)
    curve_a = QwtPlotCurveSizes(demo)
    # need to create a default symbol for the curves due to inner
    # workings of QwtCurve 
    curve.setSymbol(QwtSymbol(QwtSymbol.Ellipse,
             QBrush(Qt.black), QPen(Qt.black), QSize(5,5)))
    curve.setPen(QPen(Qt.blue, 2))
    curve_a.setSymbol(QwtSymbol(QwtSymbol.Ellipse,
             QBrush(Qt.black), QPen(Qt.black), QSize(5,5)))
    curve_a.setPen(QPen(Qt.blue, 2))

    # create some data
    x_array = zeros(20, Float32)
    y_array = zeros(20, Float32)
    symbol_sizes = zeros(20, Int32)
    symbolList=[]
    for i in range(20):
      x_array[i] = 1.0 * i
      y_array[i] = 2.0 * i
      symbol_sizes[i] = 3 + i
      if i%2 == 0:
        symbolList.append(QwtSymbol(QwtSymbol.UTriangle,
             QBrush(Qt.black), QPen(Qt.black), QSize(3+i,3+i)))
      else:
        symbolList.append(QwtSymbol(QwtSymbol.DTriangle,
             QBrush(Qt.red), QPen(Qt.red), QSize(3+i,3+i)))
    curve.setData(x_array,y_array,symbol_sizes)
    demo.insertCurve(curve)
    x_array = x_array + 10
    curve_a.setData(x_array,y_array)
    curve_a.setSymbolList(symbolList)
    demo.insertCurve(curve_a)
    demo.replot()
    return demo

def main(args):
    app = QApplication(args)
    demo = make()
    demo.show()
    app.setMainWidget(demo)
    app.exec_loop()

# Admire
if __name__ == '__main__':
    main(sys.argv)
