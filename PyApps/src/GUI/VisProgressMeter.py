import time
from qt import *

from Timba import dmi
from Timba.utils import PersistentCurrier

def hms_str (tm):
  """helper method, converts time in seconds to H:MM:SS string""";
  (tm,secs) = divmod(int(tm),60);
  (tm,mins) = divmod(tm,60);
  return "%d:%02d:%02d"%(tm,mins,secs);

class VisProgressMeter (QHBox):
  """VisProgressMeter implements a one-line progress meter
  to track progress messages from a VisDataMux. It is normally meant
  to be part of a status bar
  """;
  def __init__ (self,parent):
    QHBox.__init__(self,parent);
    self.setSpacing(5);
    self._wtime = QLabel(self);
    self._wtime.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum);
    self._wtime.setAlignment(Qt.AlignLeft|Qt.AlignVCenter);
    self._wtime.setIndent(5);
    self._wtime.setTextFormat(Qt.RichText);
    self._wprog = QProgressBar(self);
    self._wprog.setCenterIndicator(True);
    self._wprog.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum);
    self._wlabel = QLabel(self);
    self._wlabel.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum);
    self._wlabel.setIndent(5);
    self._wlabel.setTextFormat(Qt.RichText);
    self._wlabel.setAlignment(Qt.AlignLeft|Qt.AlignVCenter);
    self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum);
    self._app = None;
    self._vis_output = False;
    self._vis_inittime = None;
    self._timerid = None;
    self._currier = PersistentCurrier();
    self.curry = self._currier.curry;
    self.xcurry = self._currier.xcurry;
    self._reset_stats();
    
  class TSStats (object):
    """helper class to contain secs/timeslot stats""";
    def __init__ (self):
      self.reset(None,0);
    def reset (self,tm,nt=None):
      """resets to time0, and optionally a number of timeslots""";
      self.time0 = tm;
      self.nt = nt or 0;
      self.rate = None;
    def mark (self,tm):
      """marks current time and computes rate""";
      if self.nt and self.time0 is not None:
        self.rate = (tm-self.time0)/self.nt;
      return self.rate;
    def update (self,nt):
      """adds number of timeslots""";
      self.nt += nt;
  
  def _reset_stats (self):
    self._stats = self.TSStats();  # total stats
    self._pstats = self.TSStats(); # previous tile's stats
    self._vis_nt = self._vis_time0 = self._vis_rtime0 = self._vis_rtime1 = None;
    
  def connect_app_signals (self,app):
    """connects standard app signals to appropriate methods."""
    self._app = app;
    QObject.connect(app,PYSIGNAL("vis.channel.open"),self.xcurry(self.start,_argslice=slice(1,2)));
    QObject.connect(app,PYSIGNAL("vis.header"),self.xcurry(self.header,_argslice=slice(1,2)));
    QObject.connect(app,PYSIGNAL("vis.num.tiles"),self.xcurry(self.update,_argslice=slice(1,2)));
    QObject.connect(app,PYSIGNAL("vis.footer"),self.xcurry(self.footer,_argslice=slice(1,2)));
    QObject.connect(app,PYSIGNAL("vis.channel.closed"),self.xcurry(self.close,_argslice=slice(1,2)));
    QObject.connect(app,PYSIGNAL("isConnected()"),self.xcurry(self.reset));
  
  def start (self,rec):
    """initializes and shows meter. Usually connected to a Vis.Channel.Open signal""";
    if isinstance(self.parent(),QStatusBar):
      self.parent().clear();
    self._wlabel.setText("<nobr>opening dataset</nobr>"); 
    self._wlabel.show();
    self._wprog.reset();
    self._wprog.show();
    self.show();
    self._vis_output = rec.get("output");
    self._vis_inittime = time.time();
    self._wtime.setText(" 0:00:00");
    self._wtime.show();
    self.killTimers();
    self.startTimer(1000);
    self._reset_stats();
    
  def timerEvent (self,ev):
    """redefined to keep clock display ticking"""
    if self._vis_inittime is not None:
      self._wtime.setText(hms_str(time.time()-self._vis_inittime));
  
  def header (self,rec):
    """processes header record. Usually connected to a Vis.Header signal""";
    if isinstance(self.parent(),QStatusBar):
      self.parent().clear();
    times = rec.header.time_extent;
    nt = int(times[1] - times[0]);
    self._vis_time0 = times[0];
    self._wprog.setTotalSteps(nt);
    if nt:
      timestr = "received header, dataset length is " + hms_str(nt);
    else:
      timestr = "received header";
    self._wlabel.setText("<nobr>"+timestr+"</nobr>"); 
    self._wprog.show();
    self.show();
    self._stats.reset(time.time());
       
  def update (self,rec):
    """indicates progress based on a Vis.Num.Tiles signal""";
    nt = self._vis_nt = rec.num_tiles;
    ts = rec.timeslots;
    time0 = int(rec.time[0]-self._vis_time0);
    time1 = int(rec.time[1]-self._vis_time0);
    self._wprog.setProgress(time0);
    # compute rates
    tm = time.time();
    nts = ts[1]-ts[0]+1;
    self._stats.mark(tm);
    self._pstats.mark(tm);
    # form message
    timestr = self._vis_rtime1 = hms_str(time0);
    if self._vis_rtime0 is None:
      self._vis_rtime0 = timestr;
    if time1 != time0:
      timestr1 = self._vis_rtime1 = hms_str(time1);
      timestr += " to " + timestr1;
    msg = " tile <b>%d</b>, timeslots %d to %d, relative time %s" \
      % (nt-1,ts[0],ts[1],timestr);
    if self._stats.rate is not None:
      msg = msg+"; avg <b>%.2f</b> sec/ts" % self._stats.rate;
    if self._pstats.rate is not None:
      msg = msg+"; last %.2f sec/ts" % self._pstats.rate;
    self._wlabel.setText("<nobr>"+msg+"</nobr>"); 
    # update stat counters
    self._stats.update(nts);
    self._pstats.reset(tm,nts);
    
  def footer (self,rec):
    """processes footer record. Usually connected to a Vis.Footer signal""";
    if self._vis_output:
      msg = "received footer, writing to output";
    else:
      msg = "received footer";
    tm = time.time();
    self._stats.mark(tm);
    self._pstats.mark(tm);
    if self._stats.rate is not None:
      msg = msg+"; avg <b>%.2f</b> sec/ts" % self._stats.rate;
    if self._pstats.rate is not None:
      msg = msg+"; last %.2f sec/ts" % self._pstats.rate;
    self._wlabel.setText("<nobr>"+msg+"</nobr>"); 
    self._wprog.setProgress(99,100);
    
  def close (self,rec):
    """closes meter, posts message describing elapsed time and rate.
    Usually connected to a Vis.Channel.Closed signal.""";
    if self._app:
      msg = "dataset complete";
      rec = dmi.record();
      if self._vis_inittime is not None:
        elapsed = time.time()-self._vis_inittime;
        rec.elapsed = hms_str(elapsed);
        msg += " in "+rec.elapsed;
      else:
        elapsed = None;
      if self._stats.rate is not None:
        rec.secs_per_ts = self._stats.rate;
        msg = msg+"; avg %.2f sec/ts" % rec.secs_per_ts;
      if self._vis_nt is not None:
        rec.num_tiles = self._vis_nt;
        if elapsed is not None:
          rec.secs_per_tile = elapsed/self._vis_nt;
          msg = msg+"; avg %.2f sec/tile" % rec.secs_per_tile;
      if self._vis_rtime0 is not None:
        rec.start_time_rel = self._vis_rtime0;
      if self._vis_rtime1 is not None:
        rec.end_time_rel = self._vis_rtime1;
      self._app.log_message(msg,content=rec);
    self.reset();
    
  def reset (self):
    """resets and hides meter."""
    self.killTimers();
    self._vis_inittime = None;
    self._wprog.reset();
    self._wprog.hide();
    self._wlabel.setText(""); 
    self._wlabel.hide();
    self._wtime.setText(""); 
    self._wtime.hide();
    self.hide();
    
    
