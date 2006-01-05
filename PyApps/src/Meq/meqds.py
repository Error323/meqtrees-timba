#!/usr/bin/python

# MEQ Data Services

from Timba.dmi import *
from Timba.GUI.pixmaps import pixmaps

import weakref
import types
import new
import sets
import re
import time
import copy
import math
from qt import *
import traceback

_dbg = verbosity(0,name='meqds');
_dprint = _dbg.dprint;
_dprintf = _dbg.dprintf;


_meqnode_nodeclass = dmi_type('MeqNode',record);

_NodeClassDict = { 'meqnode':_meqnode_nodeclass };

# this function returns (creating as needed) the "Node class" class object
# for a given classname
def NodeClass (nodeclass=None):
  global _NodeClassDict;
  if nodeclass is None:
    return _meqnode_nodeclass;
  elif not isinstance(nodeclass,str):
    nodeclass = getattr(nodeclass,'classname',None) or getattr(nodeclass,'class');
  return dmi_type(nodeclass,_meqnode_nodeclass);
#  nodeclass = nodeclass.lower();
#  cls = _NodeClassDict.get(nodeclass,None);
#  if cls is None:
#    cls = _NodeClassDict[nodeclass] = new.classobj(nodeclass,(_meqnode_nodeclass,),{});
#  return cls;

# this is copied verbatim from the ControlStates definition in MEQ/Node.h
CS_ACTIVE              = 0x0001;
CS_MASK_CONTROL        = 0x000F;
CS_RES_MASK            = 0x0070;
CS_RES_NONE            = 0x0000;
CS_RES_OK              = 0x0010;
CS_RES_WAIT            = 0x0020;
CS_RES_EMPTY           = 0x0030;
CS_RES_MISSING         = 0x0040;
CS_RES_FAIL            = 0x0050;
CS_PUBLISHING          = 0x0100;
CS_CACHED              = 0x0200;
CS_RETCACHE            = 0x0400;
CS_BREAKPOINT          = 0x0800;
CS_BREAKPOINT_SS       = 0x1000;
CS_STOP_BREAKPOINT     = 0x2000;

CS_LSB_EXECSTATE       = 16;  # first bit of exec-state segment
CS_MASK_EXECSTATE      = 0xF<<CS_LSB_EXECSTATE;

CS_ES_statelist = [ (0<<CS_LSB_EXECSTATE,'IDLE' ,'-','idle',pixmaps.node_idle),
                    (1<<CS_LSB_EXECSTATE,'REQ'  ,'R','received request',pixmaps.node_request),
                    (2<<CS_LSB_EXECSTATE,'CMD'  ,'C','processing command rider',pixmaps.node_command),
                    (3<<CS_LSB_EXECSTATE,'POLL' ,'P','polling children',pixmaps.node_poll),
                    (4<<CS_LSB_EXECSTATE,'EVAL' ,'E','evaluating result',pixmaps.node_eval) ];
                    
# define CS_ES_XXX constants for the listed states, and
# BP_XXX constants to represent breakpoint masks
for st in CS_ES_statelist:
  globals()['CS_ES_'+st[1]] = st[0];
  globals()['BP_'+st[1]] = int(1<<st[0]);

# mask of all breakpoints
BP_ALL = 0xFF;
                    
def CS_ES_state (statusword):
  "returns tuple describing exec-state based on the given status word";
  return CS_ES_statelist[(statusword&CS_MASK_EXECSTATE)>>CS_LSB_EXECSTATE];

def breakpoint_mask (es=-1):
  """for a given exec-state, returns corresponding breakpoint mask, or ALL if argument is <0""";
  if es<0:
    return BP_ALL;
  else:
    return 1<<(es>>CS_LSB_EXECSTATE);
                     
# map of result types                 
CS_RES_map = {  CS_RES_NONE:     ('-','valid result'),
                CS_RES_OK:       ('o','valid result'),
                CS_RES_WAIT:     ('w','WAIT code returned'),
                CS_RES_EMPTY:    ('e','empty result returned'),
                CS_RES_FAIL:     ('!','fail result returned')   };
 
# this class defines and manages a node list
class NodeList (QObject):
  NodeAttrs = ('name','class','children','step_children','control_status');
  RequestRecord = record(**dict.fromkeys(NodeAttrs,True));
  RequestRecord.nodeindex=True;
  RequestRecord.get_forest_status = True;
  RequestRecord.get_forest_state  = True;
  
  class Node (QObject):
    def __init__ (self,ni,parent=None):
      QObject.__init__(self,parent,"meqds.Node");
      self.nodeindex = ni;
      self.name = None;
      self.classname = None;
      self.children = [];
      self.step_children = [];
      self.parents  = [];
      self.request_id = None;
      self.breakpoint = 0;
      self.control_status = 0;
      self.control_status_string = '';
      self.profiling_stats = self.cache_stats = 0;
    def child_label_format (self):
      try: format = self._child_label_format;
      except AttributeError:
        if self.children:
          if isinstance(self.children[0][0],int):
            format = '%%0%dd: %%s' % (math.floor(math.log10(len(self.children)))+1,);
          else:
            format = '%s: %s';
        else:
          format = '';
        self._child_label_format = format;
      return format;
    def is_active (self):
      return bool(self.control_status&CS_ACTIVE);
    def is_publishing (self):
      return bool(self.control_status&CS_PUBLISHING);
    def has_breakpoints (self):
      return bool(self.control_status&CS_BREAKPOINT);
    def exec_state (self):
      return self.control_status&CS_MASK_EXECSTATE;
    def exec_state_str (self):
      return CS_ES_state(self.control_status)[1];
    def is_idle (self):
      return self.exec_state() == CS_ES_IDLE;
    def update_status (self,status,rqid=False):
      old_status = self.control_status;
      self.control_status = status;
      s = ['-'] * 8;
      s[0] = CS_ES_state(status)[2];
      if status&CS_STOP_BREAKPOINT:   s[0] = ">"+s[0];
      if status&CS_BREAKPOINT_SS:     s[1] = "b";
      if status&CS_BREAKPOINT:        s[1] = "B";
      if status&CS_ACTIVE:            s[2] = "A";
      if status&CS_PUBLISHING:        s[3] = "P";
      if status&CS_CACHED:            s[4] = "C";
      if status&CS_RETCACHE:          s[5] = "c";
      s[6] = CS_RES_map[status&CS_RES_MASK][0];
      s = ''.join(s);
      if not isinstance(rqid,bool):
        self.request_id = rqid;
      self.control_status_string = s;
      _dprint(6,"node",self.name,"update status %X"%(status,));
      self.emit(PYSIGNAL("status()"),(self,old_status));
    def update_state (self,state,event=None):
      try: self.breakpoint = state.breakpoint;
      except AttributeError: pass;
      self.update_status(state.control_status,state.get('request_id',None));
      _dprint(5,"node",self.name,"update state (event ",event,")");
      self.emit(PYSIGNAL("state()"),(self,state,event));
    # Adds a subscriber to node status changes
    def subscribe_status (self,callback):
      _dprint(4,"connecting status of node ",self.name," to ",callback);
      QObject.connect(self,PYSIGNAL("status()"),callback);
    # Adds a subscriber to node state changes
    def subscribe_state (self,callback):
      _dprint(4,"connecting state of node ",self.name," to ",callback);
      QObject.connect(self,PYSIGNAL("state()"),callback);
    def unsubscribe_status (self,callback):
      _dprint(4,"disconnecting status of node ",self.name," from ",callback);
      QObject.disconnect(self,PYSIGNAL("status()"),callback);
    # Adds a subscriber to node state changes
    def unsubscribe_state (self,callback):
      _dprint(4,"disconnecting state of node ",self.name," from ",callback);
      QObject.disconnect(self,PYSIGNAL("state()"),callback);

  # init node list
  def __init__ (self,meqnl=None,parent=None):
    QObject.__init__(self,parent,"meqds.NodeList");
    self.serial = 0;
    if meqnl:
      self.load_meqlist(meqnl);
    else:
      self.clear();
      
  def clear (self):
    self._nimap = self._namemap = self._classmap = {};
    self._rootnodes = [];
    self.serial = 0;
  
  # initialize from a MEQ-produced nodelist
  def load (self,meqnl):
    if not self.is_valid_meqnodelist(meqnl):
      raise ValueError,"not a valid meqnodelist";
    self.serial = getattr(meqnl,'forest_serial',0);
    # check that all list fields are correct
    num = len(meqnl.nodeindex);
    # form sequence of iterators
    iter_name     = iter(meqnl.name);
    iter_class    = iter(meqnl['class']);
    iter_children = iter(meqnl.children);
    iter_step_children = iter(meqnl.step_children);
    iter_cstate   = iter(meqnl.control_status);
    # profiling into is optional
    if hasattr(meqnl,'profiling_stats'):
      self._has_profiling = True;
      iter_prof   = iter(meqnl.profiling_stats);
      iter_cache  = iter(meqnl.cache_stats);
    else:
      iter_prof = iter_cache = None;
      self._has_profiling = False;
    self._nimap = {};
    self._namemap = {};
    self._classmap = {};
    # iterate over all nodes in list
    # (0,) is a special case of an empty list (see bug in DMI/DataField.cc)
    if meqnl.nodeindex != (0,):
      for ni in meqnl.nodeindex:
        # insert node into list (or use old one: may have been inserted below)
        node = self._nimap.setdefault(ni,self.Node(ni,self));
        node.name      = iter_name.next();
        node.classname = iter_class.next();
        node.update_status(iter_cstate.next());
        children  = iter_children.next();
        step_children  = iter_step_children.next();
        # set children
        if children is None:
          node.children = ();
        elif isinstance(children,dict):
          node.children = tuple(children.iteritems());
        else:
          node.children = tuple(enumerate(children));
        # set step_children
        if step_children is None:
          node.step_children = ();
        else:
          node.step_children = step_children;
        # set profiling stats, form them into 2D arrays for easier accounting
        if iter_prof is not None:
          ps = iter_prof.next();
          try: node.profiling_stats = array([ps.total[0:2],ps.children[0:2],ps.get_result[0:2]]);
          except KeyError: node.profiling_stats = sys.exc_info();
          cs = iter_cache.next();
          try: node.cache_stats = array([cs.all_requests,cs.new_requests]);
          except KeyError: node.cache_stats = sys.exc_info();
        # for all children, init node entry in list (if necessary), and
        # add to parent list
        for (i,ch_ni) in node.children:
          if ch_ni > 0: # ignore missing children
            self._nimap.setdefault(ch_ni,self.Node(ch_ni)).parents.append(ni);
        for ch_ni in node.step_children:
          self._nimap.setdefault(ch_ni,self.Node(ch_ni)).parents.append(ni);
        # add to name map
        self._namemap[node.name] = node;
        # add to class map
        self._classmap.setdefault(node.classname,[]).append(node);
    # compose list of root (i.e. parentless) nodes
    self._rootnodes = [ node for node in self._nimap.itervalues() if not node.parents ];
    # emit signal
    self.emit(PYSIGNAL("loaded()"),(meqnl,));
    
#  __init__ = busyCursorMethod(__init__);
  # return list of root nodes
  def rootnodes (self):
    return self._rootnodes;
  # return map of classes
  def classes (self):
    return self._classmap;
  def iteritems (self):
    return self._nimap.iteritems();
  def iternodes (self):
    return self._nimap.itervalues();
  def has_profiling (self):
    return self._has_profiling;
  # mapping methods
  def __len__ (self):
    try: return len(self._nimap);
    except AttributeError: return 0;
  # helper method: selects name or nodeindex map depending on key type
  def _map_ (self,key):
    if not hasattr(self,'_namemap'):
      raise KeyError,"nodelist is empty";
    if isinstance(key,str):      return self._namemap;
    elif isinstance(key,int):    return self._nimap;
    else:                        raise TypeError,"invalid node key "+str(key);
  def __getitem__ (self,key):
    return self._map_(key).__getitem__(key);
  def __contains__ (self,key):
    return self._map_(key).__contains__(key);
  def __setitem__ (self,key,node):
    if __debug__:
      if isinstance(key,string):  assert value.name == key;
      elif isinstance(key,int):   assert value.nodeindex == key;
      else:                       raise TypeError,"invalid node key "+str(key);
    self._nimap[node.nodeindex] = self._namemap[node.name] = node;
  def __iter__(self):
    return iter(self._nimap);

  # return True if this is a valid meqNodeList (i.e. node list object from meq kernel)
  def is_valid_meqnodelist (nodelist):
    for f in ('nodeindex',) + NodeList.NodeAttrs:
      if f not in nodelist:
        return False;
    return True;
  is_valid_meqnodelist = staticmethod(is_valid_meqnodelist);


def _node_subudi (name,nodeindex):
  """creates UDI sub-string using node name (if not empty) or
  nodeindex (if no name)."""
  return name or ("#%d" % (nodeindex,));

def node_udi (node,suffix=None):
  """creates a UDI from a node record or node index or node name""";
  try: (name,index) = (node.name,node.nodeindex);
  except AttributeError,KeyError: 
    node = nodelist[node];
    (name,index) = (node.name,node.nodeindex);
  udi = "/node/" + _node_subudi(name,index);
  if suffix:
    udi += "/" + suffix;
  return udi;

def snapshot_udi (node,rqid='',count='',suffix=None):
  """creates a snapshot UDI from a node state record.""";
  try: (name,index) = (node.name,node.nodeindex);
  except AttributeError,KeyError: 
    node = nodelist[node];
    (name,index) = (node.name,node.nodeindex);
  udi = "/snapshot/%s:%s/%s"%(rqid,count,_node_subudi(name,index));
  if suffix:
    udi += "/" + suffix;
  return udi;

def set_meqserver (mqs1):
  global _mqs;
  _mqs = weakref.proxy(mqs1);

def reclassify_nodestate (nodestate):
  nodestate.__class__ = NodeClass(nodestate['class']);
  
def nodeindex (node):
  if isinstance(node,int):
    return node;
  elif isinstance(node,str):
    return nodelist[node].nodeindex;
  else:
    return node.nodeindex;

def nodeobject (node):
  if isinstance(node,NodeList.Node):
    return node;
  else:
    return nodelist[nodeindex(node)];

def mqs ():
  mqs1 = _mqs or (callable(_mqs) and _mqs());
  if mqs1 is None:
    raise RuntimeError,"meqserver not initialized or not running";
  return mqs1;


# ----------------------------------------------------------------------
# --- UDI management
# ----------------------------------------------------------------------

class UDI(str):
  pass;

_patt_Udi_NodeState = re.compile("^/(node|snapshot/[^/]+)/([^/]+)(/.*)?$");
def parse_node_udi (udi):
  match = _patt_Udi_NodeState.match(udi);
  if match is None:
    return (None,None);
  (prefix,name_or_ni,rest) = match.groups();
  if name_or_ni[0] == '#':
    return (None,int(name_or_ni[1:]));
  else:
    return (name_or_ni,None);
  
def parse_udi (udi):
  """Parses UDI, returns tuple of (category,trailer)""";
  # parse udi
  ff = udi.split('/',3);
  if ff[0] != '' or len(ff)<2:
    raise ValueError,"invalid UDI: "+udi;
  cat = ff[1];
  if cat == 'forest':
    return (cat,'','/'.join(ff[2:]));
  else:
    name = trailer = '';
    if len(ff)>2:
      name = ff[2];
    if len(ff)>3:
      trailer = ff[3];
  return (cat,name,trailer);
  
def make_udi_node_caption (node,trailer):
  namestr = node.name or '#'+str(node.nodeindex);
  if not trailer:
    name = "%s (%s)" % (namestr,node.classname);
    caption = "<b>%s</b> <small><i>(%s)</i></small>" % (namestr,node.classname);
  else:
    namestr = node.name or '#'+str(node.nodeindex);
    name = "%s %s" % (namestr,trailer);
    caption = "<b>%s</b> <small>%s</small>" % (namestr,trailer);
  return (name,caption);  
  
_patt_Udi_NodeName = re.compile("([^#/]+)?(#[0-9]+)?$");
def make_parsed_udi_caption (cat,name,trailer):
  """generates UDI caption (with Qt Rich Text tags) for a given UDI
  category, name and trailer.
  Returns tuple of (name,caption).""";
  if cat == 'node':
    match = _patt_Udi_NodeName.match(name);
    if not match:
      raise ValueError,"invalid udi "+'/'.join((cat,name,trailer));
    # check name or node index
    (name,nodeindex) = match.groups();
    node = nodelist[name or nodeindex];
    return make_udi_node_caption(node,trailer);
  elif cat == 'forest':
    if not trailer:
      name = "Forest state";
      caption ="<b>Forest state</b>";
    else:
      name = "Forest %s" % (trailer,);
      caption = "<b>Forest</b> <small>%s</small>" % (trailer,);
  else:
    name = '/'.join(('',cat,name,trailer));
    caption = '<small>'+name+'</small>';
  return (name,caption)
    
def make_udi_caption (udi):
  """generates UDI caption (with Qt Rich Text tags) for a given UDI""";
  return make_parsed_udi_caption(*parse_udi(udi));
  
# ----------------------------------------------------------------------
# --- Forest state record management
# ----------------------------------------------------------------------
_forest_state = {};
_forest_state_obj = QObject();

def get_forest_state ():
  """Returns current forest state.""";
  global _forest_state;
  return _forest_state;
  
def request_forest_state ():
  """Sends a request to the kernel to return the forest state.""";
  mqs().meq('Get.Forest.State',record(),wait=False);

def subscribe_forest_state (callback):
  """Adds a subscriber to node state changes. Callback must take one 
  argument: the new forest state""";
  global _forest_state_obj;
  QObject.connect(_forest_state_obj,PYSIGNAL("state()"),callback);
  
def update_forest_state (fst,merge=False):
  """Updates forest state record and notifies subscribers.""";
  global _forest_state;
  global _forest_state_obj;
  if merge:
    _forest_state.update(fst);
  else:
    _forest_state = fst;
  _forest_state_obj.emit(PYSIGNAL("state()"),(_forest_state,));
  
def set_forest_state (field,value):
  mqs().meq('Set.Forest.State',record(state=record(**{field:value})),wait=False);

# ----------------------------------------------------------------------
# --- Node state management
# ----------------------------------------------------------------------

def clear_forest ():
  mqs().meq('Clear.Forest',record(),wait=False);
  nodelist.clear();
  nodelist.emit(PYSIGNAL("cleared()"),());

def request_nodelist (profiling_stats=False):
  """Sends a request to the kernel to return a nodelist.""";
  rec = NodeList.RequestRecord;
  if profiling_stats:
    rec.forest_serial = 0;
    rec = copy.copy(rec);
    rec.profiling_stats = True;
  else:
    rec.forest_serial = nodelist.serial;
  nodelist.emit(PYSIGNAL("requested()"),());
  mqs().meq('Get.Node.List',rec,wait=False);
  _dprint(2,"nodelist requested",rec);
  # traceback.print_stack();
  
def subscribe_nodelist (callback):
  QObject.connect(nodelist,PYSIGNAL("loaded()"),callback);

def ubsubscribe_nodelist (callback):
  QObject.disconnect(nodelist,PYSIGNAL("loaded()"),callback);

def enable_node_publish (node,enable=True,get_state=True):
  ni = nodeindex(node);
  mqs().meq('Node.Publish.Results',record(nodeindex=ni,get_state=get_state,enable=enable),wait=False);

def disable_node_publish (node,disable=True):
  return enable_node_publish(node,not disable);
  
def subscribe_node_state (node,callback):
  """Adds a subscriber to node state changes""";
  nodelist[nodeindex(node)].subscribe_state(callback);

_holding_requests = None;

def hold_node_state_requests ():
  """starts holding node state requests. Requests will be accumulated in 
  a set, to be all released at the same time later. This is basically an 
  optimization for the case of repeated requests of the same node.
  """;
  global _holding_requests;
  if _holding_requests is None:
    _holding_requests = sets.Set();

def resume_node_state_requests ():
  """releases held requests.""";
  global _holding_requests;
  if _holding_requests is not None:
    for ni in _holding_requests:
      mqs().meq('Node.Get.State',record(nodeindex=ni),wait=False);
    _holding_requests = None;

def request_node_state (node):
  """requests state update for given node.
  If requests are being held (see functions above), adds to holding set""";
  global _holding_requests;
  ni = nodeindex(node);
  if _holding_requests is None:
    mqs().meq('Node.Get.State',record(nodeindex=ni),wait=False);
  else:
    _holding_requests.add(ni);

def set_node_breakpoint (node,bp=BP_ALL,oneshot=False):
  mqs().meq('Node.Set.Breakpoint',\
    record(nodeindex=nodeindex(node),breakpoint=bp,single_shot=oneshot,get_state=True),wait=False);

def clear_node_breakpoint (node,bp=BP_ALL,oneshot=False):
  mqs().meq('Node.Clear.Breakpoint',\
    record(nodeindex=nodeindex(node),breakpoint=bp,single_shot=oneshot,get_state=True),wait=False);

def set_node_state (node,**kwargs):
  ni = nodeindex(node);
  newstate = record(kwargs);
  mqs().meq('Node.Set.State',record(nodeindex=ni,get_state=True,state=newstate),wait=False);
  
def update_node_state (state,event):
  ni = state.nodeindex;
  _dprint(5,"updating state of node ",state.name);
  if nodelist:
    nodelist[ni].update_state(state,event);

def add_node_snapshot (state,event):
  ni = state.nodeindex;
  _dprint(5,"adding snapshot for node ",state.name);
  # update state
  try: node = nodelist[ni];
  except KeyError: pass;
  else: node.update_state(state,event);
  # get list of snapshots and filter it to eliminate dead refs
  sslist = filter(lambda s:s[0]() is not None,snapshots.get(ni,[]));
  if len(sslist) and sslist[-1][0]() == state:
    state.__nochange = True;
    return;
  sslist.append((weakref.ref(state),event,time.time()));
  snapshots[ni] = sslist;
  
def get_node_snapshots (node):
  ni = nodeindex(node);
  sslist0 = snapshots.get(ni,[]);
  # filter out dead refs, reset list if it changes
  sslist = filter(lambda s:s[0]() is not None,sslist0);
  if len(sslist) != len(sslist0):
    snapshots[ni] = sslist;
  return sslist;

# create global node list
snapshots = {};
nodelist = NodeList();

_mqs = None;
