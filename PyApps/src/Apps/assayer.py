from Timba.Apps import meqserver
from Timba.TDL import Compile
from Timba.Meq import meqds
from Timba.utils import *
from Timba import dmi
from Timba import octopussy

import sys
import traceback
import time
import cPickle
import os

_dbg = verbosity(0,name='assayer');
_dprint = _dbg.dprint;
_dprintf = _dbg.dprintf;

MISMATCH = 1;
MISSING_DATA = 2;
TIMING_ERROR = 9;
OTHER_ERROR = 99;


class AssayError (RuntimeError):
  pass;

class AssaySetupError (AssayError):
  pass;
  
class DataMismatch (AssayError):
  pass;
  
class logger (file):
  def __init__ (self,filename):
    file.__init__(self,filename,'w');
    
  def prefix (self):
    return time.strftime("%d/%m/%y %H:%M:%S: ",time.localtime())
  
  def log (self,*args):
    """prints arguments to log, a-la print(). Trailing newline added.""";
    self.write(self.prefix());
    self.write(' '.join(args));
    self.write('\n');
  
  def logf (self,format,*args):
    """printf's arguments to log. Trailing newline added.""";
    return self.log(format%args);
    
  def logs (self,*args):
    """prints lines to log. Arguments must be strings. No newlines added.""";
    prefix = self.prefix();
    return self.writelines([prefix+line for line in args]);
    
  def logsp (self,prefix,*args):
    """prints lines to log, with prefix. Arguments must be strings. No newlines added.""";
    prefix = self.prefix() + prefix;
    return self.writelines([prefix+line for line in args]);
    
class assayer (object):
  def __init__ (self,name,log=True,nokill=None):
    self.recording = "-assayrecord" in sys.argv;
    # if nokill is not explicitly specified, leave kernel running when recording
    if nokill is None:
      nokill = self.recording;
    self.name = name;
    self.mqs = meqserver.default_mqs(wait_init=10,nokill=True);
    self.mqs.whenever("*",self._kernel_event_handler);
    self.mqs.whenever("node.result",self._node_snapshot_handler);
    self.tdlmod = self.logger = self.testname = None;
    self.watching = [];
    self.testname = None;
    self.default_tol = 1e-6;   # default comparison tolerance
    self.time_tol    = .2;     # default time tolerance
    self.hostname = os.popen('hostname').read().rstrip();
    # open log and dump initial messages
    if log:
      self.logger = logger(self.name+".assaylog");
      self.logf("start of log for assayer %s",self.name);
      
  def __del__ (self):
    if self.mqs is not None:
      _dprint(0,"stopping meqserver");
      self.mqs.halt();
      self.mqs.disconnect();
      octopussy.stop();
      
  def log (self,*args):
    _dprint(1,*args+('\n',));
    if self.logger:
      self.logger.log(*args);
      
  def logf (self,*args):
    _dprintf(1,args[0]+"\n",*args[1:]);
    if self.logger:
      self.logger.logf(*args);
  
  def logs (self,*args):
    _dprint(1,*args+('\n',));
    if self.logger:
      self.logger.logs(*args);
      
  def logexc (self):
    exc_info = sys.exc_info();
    exc_lines = traceback.format_exception(*exc_info);
    _dprint(1,*exc_lines);
    if self.logger:
      self.logger.log("EXCEPTION:",str(exc_info[0]));
      self.logger.logsp("    ",*exc_lines);

  def set_default_tolerance (self,tol):
    self.default_tol = tol;
      
  def set_time_tolerance (self,tol):
    self.time_tol = tol;
    
  def compile (self,script):
    try:
      self.script = script;
      _dprint(0,"compiling",script);
      (self.tdlmod,msg) = Compile.compile_file(self.mqs,script);
      _dprintf(0,"compiled %s: %s",script,msg);
      lines = ["compiled TDL script %s: "%script]+msg.rstrip().split('\n');
      self.logs(*[ s+'\n' for s in lines ]);
    except:
      self.logexc();
      raise;
      
  def init_test (self,name):
    try:
      if self.testname is not None:
        self.finish_test();
      self._assay_stat = 0;
      self.watching = [];
      self.testname = name;
      self.logf("START: test '%s'",name);
      if not self.tdlmod:
        raise AssaySetupError("FAIL: can't init_test because no script is compiled");
      # load assay data for the sake of per-host timings
      self.datafile = '.'.join((self.name,name,'data-assay'));
      if not self._load_assay_data(self.datafile):
        if self.recording:
          self._recorded_time = {};
        else:
          raise AssaySetupError("FAIL: no assay data "+self.datafile);
      if self.recording:
        self.log("RECORDING assay data, no comparisons will be done");
        self._sequences = {};
        self._inspections = {};
    except:
      self.logexc();
      raise;
      
  def watch_node (self,node,field,tolerance=None):
    try:
      if tolerance is None:
        tolerance = self.default_tol;
      if self.testname is None:
        raise AssaySetupError,"can't watch nodes: no test specified";
      self.watching.append((node,tuple(field.split(".")),tolerance));
      self.logf("will watch node '%s' %s",node,field);
    except:
      self.logexc();
      raise;

  def watch (self,nodespec):
    try:
      self.watch_node(*nodespec.split("/"));
    except:
      self.logexc();
      raise;
    
  def run (self,procname="_test_forest",**kwargs):
    try:
      if self.tdlmod is None:
        raise AssaySetupError,"no TDL script compiled";
      self._assay_stat = 0;
      # check that procedure exists
      proc = getattr(self.tdlmod,procname,None);
      if not callable(proc):
        raise AssaySetupError,"no "+procname+"() in compiled script";
      # now, enable publishing for specified watch nodes
      if self.watching:
        for (node,field,tol) in self.watching:
          self.mqs.publish(node);
      # run the specified procedure
      self.logf("running %s(), test %s",procname,self.testname);
      dt = time.time();
      retval = proc(self.mqs,None,**kwargs);
      if not self._assay_stat:
        self._assay_time(time.time() - dt);
      # inspect return value
      if self.recording:
        self._inspections['retval'] = normalize_value(retval);
        self.logf("recorded %s() return value",procname);
      else:
        try:
          expected = self._inspections.get('retval');
        except KeyError:
          self._assay_stat = MISSING_DATA;
          self.logf("ERROR: no assay data recorded for return value");
        else:
          try:
            compare_value(expected,retval,self.default_tol,field=procname+"()");
          except Exception,exc:
            self._assay_stat = MISMATCH;
            self.logf("ERROR: assay fails on %s() return value",procname);
            self.log("  error is: ",exc.__class__.__name__,*map(str,exc.args));
          else:
            self.logf("%s() return value ok",procname);
    except:
      self._assay_stat = OTHER_ERROR;
      self.logexc();
      raise;
    # return assay status
    if self.logger:
      self.logger.flush();
    return self._assay_stat;
    
  def finish_test (self):
    if not self._assay_stat:
      if self.recording:
        self._record_assay_data(self.datafile);
        self.logf("SUCCESS: test '%s' assay data recorded to %s",self.testname,self.datafile);
      else:
        self.logf("SUCCESS: test '%s' completed successfully",self.testname);
    else: 
      self.logf("FAIL: test '%s', code %d",self.testname,self._assay_stat);
    self.testname = None;
    self.watching = [];
    return self._assay_stat;
    
  def finish (self):
    if self.testname is not None:
      self.finish_test();
    self.logger = None;
    # in recording mode, pause before exiting
    if self.recording and "-nopause" not in sys.argv:
      self.mqs.disconnect();
      octopussy.stop();
      if self._assay_stat:
        print """\n*** ERROR ***: Assay data recording failed, please review the log.\n""";
      a = raw_input("""\n\n
Since you're running the assayer in recording mode, we have disconnected 
from the meqserver without stopping it. You may wish to run the browser to
ensure that tree state is correct. Run the browser now (Y/n)? """).rstrip();
      if not a or a[0].lower() == 'y':
        os.system("meqbrowser.py");
      print """\n\nReminder: you may need to kill the meqserver manually.""";
    else:
      self.mqs.halt();
      self.mqs.disconnect();
      octopussy.stop();
    self.mqs = None;
    return self._assay_stat;
    
  def inspect (self,nodespec,tolerance=None):
    try:
      self.inspect_node(*nodespec.split("/"));
    except:
      self.logexc();
      raise;
  
  def inspect_node (self,node,field,tolerance=None):
    try:
      field = tuple(field.split('.'));
      nodestate = self.mqs.getnodestate(node,wait=2);
      val = extract_value(nodestate,field);
      if self.recording:   # collect value
        self._inspections[(node,field)] = normalize_value(val);
        self.logf("recorded inspection for node '%s' %s",node,'.'.join(field));
      else:                # assay value
        if tolerance is None:
          tolerance = self.default_tol;
        try:
          expected = self._inspections.get((node,field),None);
        except KeyError:
          self._assay_stat = MISSING_DATA;
          self.logf("ERROR: no assay data recorded for node '%s' %s",node,'.'.join(field));
          return;
        try:
          compare_value(expected,val,tolerance,field=node+'/'+'.'.join(field));
        except Exception,exc:
          self._assay_stat = MISMATCH;
          self.logf("ERROR: assay fails on node '%s' %s",node,'.'.join(field));
          self.log("  error is: ",exc.__class__.__name__,*map(str,exc.args));
          return False;
        else:
          self.logf("node '%s' %s ok",node,'.'.join(field));
          return True;
    except:
      self.logexc();
      self._assay_stat = OTHER_ERROR;
      self.logf("failed to inspect node '%s' %s",node,'.'.join(field));
      self.log("assay will fail");
      return False;
    
  def _assay_time (self,dt):
    if self.recording:
      self._recorded_time[self.hostname] = dt;
      self.logf("runtime is %.2f seconds (none recorded)",dt);
    else:
      # see if we have a timing for this host
      t0 = self._recorded_time.get(self.hostname,None);
      if t0 is None:
        self.logf("runtime is %.2f seconds (none recorded)",dt);
        self.logf("WARNING: no expected runtime recorded for host %s",self.hostname);
        self.log("   you may want to re-run this test with -assayrecord");
        return;
      else:
        self.logf("runtime is %.2f seconds vs. %.2f recorded",dt,t0);
      t0 = max(t0,1e-10);
      dt = max(dt,1e-10);
      if dt > 2 and dt > t0*(1+self.time_tol):
        self.logf("ERROR: runtime too slow by factor of %g",dt/t0)
        self.log("assay will fail");
        self._assay_stat = TIMING_ERROR;
      elif dt > 2 and dt < t0*(1-self.time_tol):
        self.logf("SURPISE: runtime faster by a factor of %g",t0/dt);
        
      
  def _load_assay_data (self,fname):
    # catch file-open errors and return none
    try:
      pfile = file(fname,"r");
    except:
      return None;
    # load stuff
    unpickler = cPickle.Unpickler(pfile);
    name = unpickler.load();
    if name != self.testname:
      raise AssaySetupError,"test name in data file "+fname+" does not match";
    self._recorded_time = unpickler.load();
    self._sequences = unpickler.load();
    self._inspections = unpickler.load();
    self.logf("loaded assay data from file %s",fname);
    for (host,t0) in self._recorded_time.iteritems():
      self.logf("  host %s recorded runtime is %.2f seconds",host,t0);
    return True;
      
  def _record_assay_data (self,fname):
    if not self.recording or not self.testname:
      return;
    pfile = file(fname,"w");
    pickler = cPickle.Pickler(pfile);
    pickler.dump(self.testname);
    pickler.dump(self._recorded_time);
    pickler.dump(self._sequences);
    pickler.dump(self._inspections);

  def _node_snapshot_handler (self,msg):
    try: 
      # self.log("got node snapshot",str(msg));
      nodestate = getattr(msg,'payload',None);
      name = nodestate.name;
      # are we watching this node?
      for (node,field,tolerance) in self.watching:
        if node == name:
          if self.recording:   # collect value
            seq = self._sequences.setdefault((node,field),[]);
            val = extract_value(nodestate,field);
            seq.append(normalize_value(val));
            self.logf("recorded value #%d for node '%s' %s",len(seq),name,'.'.join(field));
          else:                # assay value
            # extract value from nodestate
            val = extract_value(nodestate,field);
            # get request id (for informational purposes)
            try:
              rqid = nodestate.cache.request_id;
            except:
              rqid = '';
            # look for sequence data
            try:
              seq = self._sequences[(node,field)];
            except:
              self._assay_stat = MISSING_DATA;
              self.logf("ERROR: no recorded sequence for node '%s' %s",node,'.'.join(field));
              return;
            # get first item from sequence
            if not seq:
              self._assay_stat = MISSING_DATA;
              self.logf("ERROR: end of recorded sequence on node '%s' %s (rqid %s)",node,'.'.join(field),rqid);
              return;              
            expected = seq.pop(0);
            try:
              compare_value(expected,val,tolerance,field=node+'/'+'.'.join(field));
            except Exception,exc:
              self._assay_stat = MISMATCH;
              self.logf("ERROR: assay fails on node '%s' %s (rqid %s)",node,'.'.join(field),rqid);
              self.log("  error is: ",exc.__class__.__name__,*map(str,exc.args));
            else:
              self.logf("node '%s' %s (rqid %s) ok",node,'.'.join(field),rqid);
    except:
      self.logexc();
      self._assay_stat = OTHER_ERROR;
      self.log("assay will fail");

  def _kernel_event_handler (self,msg):
    try:
      value = getattr(msg,'payload',None);
      if isinstance(value,dmi.record):
        for f in ("text","message","error"):
          if value.has_field(f):
            self.logf("meqserver %s: %s",f,value[f]);
    except:
      self.logexc();
      self.log("last error non-fatal, assay will continue");

def normalize_value (value):
  """helper function to convert a value from dmi types to standard python""";
  if isinstance(value,dmi.record):
    res = {};
    for field,val1 in value.iteritems():
      res[field] = normalize_value(val1);
    return res;
  elif isinstance(value,(list,tuple)):
    res = [];
    for val1 in value:
      res.append(normalize_value(val1));
    return res;
  elif isinstance(value,dmi.array_class):
    cp = value.copy();
    cp.__class__ = dmi.array_class;
    return cp;    # returns normal numarray
  else:
    return value;

def extract_value (record,field):
  """helper function to recursively extract a sequence of fields""";
  value = record;
  for f in field:
    value = value[f];
  return value;

_numtypes = (int,long,float,complex);
_seqtypes = (list,tuple);

def compare_value (a,b,tol=1e-6,field=None): 
  try:
    if isinstance(a,_numtypes):
      if abs(a-b) <= max(abs(a),abs(b))*tol:
        return True;
      raise DataMismatch(field,a,b);
    elif isinstance(a,dict):
      if len(a) != len(b):
        raise DataMismatch(field,"lengths",len(a),len(b));
      for (key,value) in a.iteritems():
        try:
          val2 = b[key];
        except KeyError:
          raise KeyError(field,"missing field",key);
        compare_value(value,b[key],tol,field=field+'.'+key);
      return True;
    elif isinstance(a,(list,tuple)):
      if len(a) != len(b):
        raise DataMismatch(field,"lengths",len(a),len(b));
      iterb = iter(b);
      n = 0;
      for value in a:
        compare_value(value,iterb.next(),tol,field="%s[%d]"%(field,n));
        n+=1;
      return True;
    elif isinstance(a,dmi.array_class):
      if a.shape != b.shape:
        raise DataMismatch(field,"shapes",a.shape,b.shape);
      diff = abs(a-b).max();
      maxdiff = max(abs(a).max(),abs(b).max())*tol;
      if diff <= maxdiff:
        return True;
      raise DataMismatch(field,"diff %g max %g"%(diff,maxdiff));
    else:
      if a == b:
        return True;
      raise DataMismatch(field,str(a)[:32],str(b)[:32]);
  except DataMismatch:
    raise;
  except:
    _dprint(2,'compare_value() fails on',a,b);
    excinfo = sys.exc_info();
    if _dbg.verbose > 1:
      traceback.print_exception(*excinfo);
    raise excinfo[0](field,*excinfo[1].args);
