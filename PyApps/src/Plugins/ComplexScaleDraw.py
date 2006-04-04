from qt import *
from qwt import *

class ComplexScaleDraw(QwtScaleDraw):
    """ override default behaviour of QwtScaleDraw class """
    def __init__(self,start_value=None,end_value=None, divisor=None):
        QwtScaleDraw.__init__(self)
        self.do_separator = True
        self.start_value = start_value
        self.end_value = end_value
        self.divisor = divisor
        if not self.start_value is None and not self.end_value is None:
          self.delta = self.end_value - self.start_value
          self.separator = self.end_value
          self.divisor = None
        else:
          self.separator = self.divisor
          self.delta = None
          self.start_value = None
          self.end_value = None
    
    # __init__()

    def label(self, v):
        """ Override default QwtScaleDraw generation of labels along axis """
        if not self.end_value is None:
          if v >= self.end_value:
              v = v - self.delta
        else:
          if not self.divisor is None:
	    v = v % self.divisor
        return QwtScaleDraw.label(self, v)

    def draw_separator(self, separator_flag=True):
        """ test to draw major tick mark at separation location """
        self.do_separator = separator_flag

    def draw(self, painter):
        """ Override default QwtScaleDraw generation of tickmarks """
        # 1. paint real value ticks as done in C++ code
        # 2. paint imag value ticks with the shift depending on
        #    the dimension and tick spacing
        # 3. draw backbone, if needed

        step_eps = 1.0e-6    # constant value in the c++ equivalent
        scldiv = QwtScaleDraw.scaleDiv(self)
        majLen, medLen, minLen = QwtScaleDraw.tickLength(self)
        self.offset = 0
        # calculate and plot major ticks
        for i in range(scldiv.majCnt()):
            val = scldiv.majMark(i)
            if not self.end_value is None:
              v = val
              if val >= self.end_value:
                v = val - self.delta
            else:
              if not self.divisor is None:
                v = val % self.divisor
            if self.offset == 0 and v != val:
              self.offset = scldiv.majStep() - v % scldiv.majStep()
            val = val + self.offset
            QwtScaleDraw.drawTick(self, painter, val, majLen)
            QwtScaleDraw.drawLabel(self, painter, val)

        # also, optionally plot a major tick at the dividing point
        if self.do_separator:
          QwtScaleDraw.drawTick(self,painter, self.separator, majLen)
          QwtScaleDraw.drawLabel(self,painter,self.separator)

        # probably can't handle logs properly??
        if scldiv.logScale():
            for i in range(scldiv.minCnt()):
                QwtScaleDraw.drawTick(
                    self, painter, scldiv.minMark(i), minLen)
        else:
            # do minor ticks - no changs here compared to QwtScaleDraw
            kmax = scldiv.majCnt() - 1
            if kmax > 0:
                majTick = scldiv.majMark(0)
                hval = majTick - 0.5 * scldiv.majStep()
                k = 0
                for i in range(scldiv.minCnt()):
                    val = scldiv.minMark(i)
                    if  val > majTick:
                        if k < kmax:
                            k = k + 1
                            majTick = scldiv.majMark(k)
                        else:
                            majTick += (scldiv.majMark(kmax)
                                        + scldiv.majStep())
                        hval = majTick - 0.5 * scldiv.majStep()
                    if abs(val-hval) < step_eps * scldiv.majStep():
                        QwtScaleDraw.drawTick(self,painter, val, medLen)
                    else:
                        QwtScaleDraw.drawTick(self, painter, val, minLen)

        if QwtScaleDraw.options(self) & QwtScaleDraw.Backbone:
            QwtScaleDraw.drawBackbone(self, painter)

    # draw()
# class ComplexScaleDraw()
