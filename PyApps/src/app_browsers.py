#!/usr/bin/python

from qt import *
from qttable import *
from dmitypes import *
import sys
import time
import qt_threading
import app_pixmaps as pixmaps
import dmi_repr
import gridded_workspace 
import weakref

dmirepr = dmi_repr.dmi_repr();

class HierBrowser (object):
  # seqs/dicts with <= items than this are treated as "short"
  ShortSeq       = 5;
  # maximum number of sequence items to show in expanded view
  MaxExpSeq      = 20;
  # max number of dictionary items to show in expanded view
  MaxExpDict     = 100;
  
  class BrowserItem (QListViewItem):
    def __init__(self,*args):
#      print args;
      QListViewItem.__init__(self,*args);

    def _subitem (self,*args):
      return HierBrowser.subitem(self,*args);
      
    # caches content in an item: marks as expandable, ensures content is a dict
    # if viewable is None, decides if content is viewable based on its type
    # else, must be True or False to specify viewability
    def cache_content(self,content,viewable=None):
      self.setExpandable(True);
      # convert all content to dict
      if isinstance(content,(dict,list,tuple,array_class)):
        self._content = content;
      elif isinstance(content,message):
        self._content = {};
        for k in filter(lambda x:not x.startswith('_'),dir(content)):
          attr = getattr(content,k);
          if not callable(attr):
            self._content[k] = attr;
      else:
        self._content = {"":content};
      # set the viewable property
      if not self._udi:
        viewable = False;
      elif viewable is None:
        viewable = gridded_workspace.isViewable(content);
      self._viewable = viewable;
      if viewable:
        self.setPixmap(1,pixmaps.magnify.pm());
        self.setDragEnabled(True);
        
    # expands item content into subitems
    def expand_self (self):
      HierBrowser.expand_content(self,self._content);

  # init for HierBrowser
  def __init__(self,parent,name,name1='',udi_root=None):
    self._lv = gridded_workspace.DataDraggableListView(parent);
    self._lv.addColumn(name1);
    self._lv.addColumn('');
    self._lv.addColumn(name);
    self._lv.setRootIsDecorated(True);
    self._lv.setSorting(-1);
    self._lv.setResizeMode(QListView.NoColumn);
#    for col in (0,1,2):
#      self._lv.setColumnWidthMode(col,QListView.Maximum);
    self._lv.setFocus();
    self._lv.connect(self._lv,SIGNAL('expanded(QListViewItem*)'),
                     self._expand_item_content);
    self._lv.connect(self._lv,SIGNAL('mouseButtonClicked(int,QListViewItem*,const QPoint &,int)'),
                     self._process_item_click);
    self._lv.connect(self._lv,SIGNAL('contextMenuRequested(QListViewItem*,const QPoint &,int)'),
                     self._show_context_menu);
#    self._lv.connect(self._lv,SIGNAL('doubleClicked(QListViewItem*)'),
#                     self.display_item);
    # connect the get_data_item method for drag-and-drop
    self._lv.get_data_item = self.get_data_item;
    self.items = [];
    # enable UDIs, if udi root is not none
    self.set_udi_root(udi_root);
    # for debugging purposes
    QWidget.connect(self._lv,SIGNAL("clicked(QListViewItem*)"),self._print_item);
    
  def set_udi_root (self,udi_root):
    self._udi_root = udi_root;
    if udi_root is not None:
      if not udi_root.startswith('/'):
        udi_root = "/" + udi_root;
      self._lv._udi = udi_root;
      # map of UDIs to items
      self._content_map = self._lv._content_map = weakref.WeakValueDictionary();
    else:
      self._lv._udi = None;
    
  def _print_item (self,item):
    if item is not None:
      print 'item:',item.text(0),item.text(2);
      for attr in ('_udi','_udi_key','_viewable','_name','_desc'):
        if hasattr(item,attr):
          print ' ',attr+':',getattr(item,attr);
      try: 
        lencont = len(item._content_map);
        print '  _content_map: ',lencont,' items';
      except AttributeError: pass;
    
  def get_data_item (self,udi):
    return self.make_data_item(self._content_map.get(udi,None));
    
  def make_data_item (self,item,viewer=None):
    # extract relevant item attributes, return if not present
    try:
      content  = getattr(item,'_content');
      udi      = getattr(item,'_udi');
      viewable = getattr(item,'_viewable');
    except AttributeError: return None;
    # return item only if viewable, has udi and contents
    if content is not None and udi and viewable: 
      viewopts = getattr(item,'_viewopts',{});
      name = getattr(item,'_name','');
      desc = getattr(item,'_desc','');
      if not name and not desc:
        desc = udi;
      # make item and return
      return gridded_workspace.GridDataItem(udi,name,desc,
                data=content,viewer=viewer,viewopts=viewopts,
                refresh=getattr(self,'_refresh_func',None));
    return None;

  # helper static method to expand content into BrowserItems record 
  def expand_content(item,content):
    if hasattr(item,'_content_list'):
      return;
    item._content_list = [];
    # Setup content_iter as an iterator that returns (label,value)
    # pairs, depending on content type.
    # Apply limits here
    if isinstance(content,dict):
      n = len(content) - HierBrowser.MaxExpDict;
      if n > 0:
        keys = content.keys()[:HierBrowser.MaxExpDict];
        content_iter = map(lambda k:(k,content[k]),keys);
        content_iter.append(('...','...(%d items skipped)...'%n));
      else:
        content_iter = content.iteritems();
    elif isinstance(content,(list,tuple,array_class)):
      n = len(content) - HierBrowser.MaxExpSeq;
      if n > 0:
        content_iter = list(enumerate(content[:HierBrowser.MaxExpSeq-2]));
        content_iter.append(('...','...(%d items skipped)...'%(n+1)));
        content_iter.append((len(content)-1,content[-1]));
      else:
        content_iter = enumerate(content);
    else:
      content_iter = (("",content),);
    for (key,value) in content_iter:
      # simplest case: do we have an inlined to-string converter?
      # then the value is represented by a single item
      (itemstr,inlined) = dmirepr.inline_str(value);
      if itemstr is not None:
        item._content_list.append( HierBrowser.subitem(item,key,itemstr) );
        continue;
      # else get string representation, insert item with it
      (itemstr,inlined) = dmirepr.expanded_repr_str(value,False);
      i0 = HierBrowser.subitem(item,str(key),itemstr);
      item._content_list.append(i0);
      # cache value for expansion, if not inlined
      if isinstance(value,(list,tuple,array_class)):
        if not inlined:
          i0.cache_content(value);
      # dicts and messages always cached for expansion
      elif isinstance(value,(dict,message)):
        i0.cache_content(value);
      item._content_list.append(i0);
  expand_content = staticmethod(expand_content);
  
  def wlistview (self):
    return self._lv;
  def wtop (self):
    return self._lv;
  def clear (self):
    self._lv.clear();
    self.items = [];
    for attr in ('_content','_content_list'):
      if hasattr(self._lv,attr):
        delattr(self._lv,attr);
  # inserts a new item into the browser
  def new_item (self,key,value,udi_key=None):
    if self.items:
      item = self.BrowserItem(self._lv,self.items[-1],str(key),'',str(value));
    else:
      item = self.BrowserItem(self._lv,str(key),'',str(value));
    self.items.append(item);
    self._lv.ensureItemVisible(item);
    # generate udi key if none is specified
    if udi_key is None:
      item._udi_key = udi_key = str(key);
    elif udi_key is id:
      item._udi_key = udi_key = str(id(item));
    else:
      item._udi_key = udi_key = str(udi_key);
    # setup udi of item, if listview has a udi
    if self._lv._udi:
      item._udi = self._lv._udi + '/' + udi_key;
      self._content_map[item._udi] = item;
      item._content_map = self._content_map;
    else:
      item._udi = None;
    return item;
    
  def subitem (parent,key,value,udi_key=None):
    if hasattr(parent,'_content_list') and parent._content_list:
      item = HierBrowser.BrowserItem(parent,parent._content_list[-1],str(key),'',str(value));
    else:
      item = HierBrowser.BrowserItem(parent,str(key),'',str(value));
    # generate udi key if none is specified
    if udi_key is None:
      item._udi_key = udi_key = str(key);
    else:
      item._udi_key = udi_key = str(udi_key);
    # setup udi of item, if parent has a udi
    if parent._udi:
      item._udi = parent._udi + '/' + udi_key;
      parent._content_map[item._udi] = item;
      item._content_map = parent._content_map;
    else:
      item._udi = None;
    return item;
      
  subitem = staticmethod(subitem);
    
  # limits browser to last 'limit' items
  def apply_limit (self,limit):
    if limit>0 and len(self.items) > limit:
      for i in self.items[:len(self.items)-limit]:
        self._lv.takeItem(i);
      del self.items[:len(self.items)-limit];

  # if current item is displayable, creates a dataitem from it and
  # emits a displayDataItem(dataitem) signal
  # dum is used to allow this func to be used as a callback for context menus
  def display_item (self,item,dum=None,viewer=None,**kwargs):
    dataitem = self.make_data_item(item,viewer=viewer);
    if dataitem:
      self.wtop().emit(PYSIGNAL("displayDataItem()"),(dataitem,(),kwargs));
      
  # called when an item is expanded                    
  def _expand_item_content (self,item):
    try: cont = item._content;
    except AttributeError: return;
    if cont is not None:
      self.expand_content(item,cont);

  # slot: called when one of the items is clicked
  def _process_item_click (self,button,item,point,col):
    if button == 1 and col == 1:
      self.display_item(item);
  
  # slot: called to show a context menu for an item
  def _show_context_menu (self,item,point,col):
    try:
      menu = item._context_menu;
    except AttributeError:
      # get item content and description
      content  = getattr(item,'_content',None);
      label    = getattr(item,'_udi',None);
      viewable = getattr(item,'_viewable',False);
      if content is not None and label and viewable: 
        # get viewer list
        vlist = gridded_workspace.getViewerList(content);
        if not vlist:
          item._context_menu = None;
          return;
        # create item descrition
        name = getattr(item,'_name','');
        desc = getattr(item,'_desc','');
        if name or desc:
          label = ' '.join((name,desc));
        # create menu
        menu = item._context_menu = QPopupMenu(self._lv);
        menu.insertItem(label);
        menu.insertSeparator();
        menu1 = QPopupMenu(self._lv);
        menu2 = QPopupMenu(self._lv);
        menu.insertItem(pixmaps.view_split.iconset(),"Display with",menu1);
        menu.insertItem(pixmaps.view_right.iconset(),"New display with",menu2);
        menu._callbacks = [];
        for v in vlist:
          # create entry for viewer
          name = getattr(v,'viewer_name',v.__name__);
          try: icon = v.icon();
          except AttributeError: icon = QIconSet();
          # add entry to both menus ("Display with" and "New display with")
          func = curry(self.display_item,item,viewer=v);
          menu._callbacks.append(func);
          menu1.insertItem(icon,name,func);
          func = curry(self.display_item,item,viewer=v,newcell=True);
          menu._callbacks.append(func);
          menu2.insertItem(icon,name,func);
      else:
        menu = item._context_menu = None;
    # a None menu object indicates no context for this item 
    if menu is not None:
      menu.exec_loop(point);

  def get_open_items (self):
    """gets tree of currently open and selected items. Returns tuple of
    (dict,<str|None>), describing the state of top-level items. The dict keys
    are udi_keys of expanded items; the dict values are similar tuples
    describing the state of each sub-level. The second element of the tuple is
    the key of the currently selected item, or None if no items are selected at
    this level; normally, at most one entry in the entire tree has a selected
    item. A None value in place of a tuple indicates no open and no selected
    items.""";
    # recursive helper function implementing tree traversal
    def _get_open_items_impl (parent,current):
      openitems = {};
      current_key = None;
      item = parent.firstChild();
      while item is not None:
        if item is current:
          current_key = item._udi_key;
        if item.isOpen():
          openitems[item._udi_key] = _get_open_items_impl(item,current);
        item = item.nextSibling();
      if openitems or current_key:
        return (openitems,current_key);
      return None;
    return _get_open_items_impl(self._lv,self._lv.currentItem());
    
  def set_open_items (self,openspec):
    """sets currently open and selected items according to tree returned
    by a previous get_open_items() call.""";
    # recursive helper function implementing tree traversal
    def _set_open_items_impl (parent,openspec):
      if openspec is None:
        return;
      (openitems,current_key) = openspec;
      item = parent.firstChild();
      while item is not None:
        if item._udi_key == current_key:
          self._lv.setCurrentItem(item);
        # if item is open, expand it and go in recursively
        if item._udi_key in openitems:
          self._lv.setOpen(item,True);
          _set_open_items_impl(item,openitems[item._udi_key]);
        item = item.nextSibling();
    # call recursive helper on listview
    _set_open_items_impl(self._lv,openspec);
    
class BrowserPlugin (object):
  _icon = pixmaps.magnify;  # default icon
  def icon (_class):
    return _class._icon.iconset();
  icon = classmethod(icon);
  
  def viewer_name (_class):
    return getattr(_class,'_name',_class.__name__);
  viewer_name = classmethod(viewer_name);
    
class RecordBrowser(HierBrowser,BrowserPlugin):
  _icon = pixmaps.view_tree;
  viewer_name = "Record Browser";
  def is_viewable (data):
    return len(data) > 0;
  is_viewable = staticmethod(is_viewable);

  def __init__(self,parent,dataitem=None,default_open=None,**opts):
    HierBrowser.__init__(self,parent,"value","field",
        udi_root=(dataitem and dataitem.udi));
    self._rec = None;
    self._default_open = default_open;
    if dataitem and dataitem.data is not None:
      self.set_data(dataitem);
  
  def set_data (self,dataitem,default_open=None,**opts):
    # save currenty open tree
    if self._rec is not None:
      openitems = self.get_open_items();
    else: # no data, use default open tree if specified
      openitems = default_open or self._default_open;
    # clear everything and reset data as new
    self.clear();
    self.set_udi_root(dataitem.udi);
    self._rec = dataitem.data;
    self._refresh_func = dataitem.refresh_func;
    # expand first level of record
    self.expand_content(self._lv,self._rec);
    # apply saved open tree
    self.set_open_items(openitems);
    
class ArrayBrowser(BrowserPlugin):
  _icon = pixmaps.matrix;
  viewer_name = "Array Browser";
  def is_viewable (data):
    try: return 1 <= data.rank <=2;
    except: return False;
  is_viewable = staticmethod(is_viewable);
  
  class ArrayTable(QTable):
    def __init__(self,parent,**args):
      QTable.__init__(self,parent,*args);
      self.setSelectionMode(QTable.NoSelection);
      self._arr = None;
    def set_array (self,arr):
      if not 1<=arr.rank<=2:
        raise TypeError,"illegal array dimensionality";
      self._arr = arr;
      self._rank = arr.rank;
      self.setNumRows(arr.shape[0]);
      if self._rank == 1:   
        self.setNumCols(1);
      else:
        self.setNumCols(arr.shape[1]);
      self.repaint();
    # redefine paintCell method to paint on-the-fly
    def paintCell(self,painter,row,col,cr,selected):
      txt = str(self._arr[(row,col)[:self._rank]]);
      cg = QApplication.palette().active();
#      if selected:
#        qp.setPen(cg.highlightedText());
#        qp.setBackgroundColor(cg.highlight());
#      else:
#        qp.setPen(cg.text());
#        qp.setBackgroundColor(cg.background());
      rect = QRect(0,0,cr.width(),cr.height());
      if selected:
        painter.fillRect(rect,QBrush(cg.highlight()));
        painter.setPen(cg.highlightedText());
      else:
        painter.fillRect(rect,QBrush(cg.base()));
        painter.setPen(cg.text());
      painter.drawText(0,0,cr.width(),cr.height(),Qt.AlignLeft,txt);
    def resizeData(self,len):
      pass;
    
    
  def __init__(self,parent,dataitem=None,**opts):
#    HierBrowser.__init__(self,parent,"value","field",
#        udi_root=(dataitem and dataitem.udi));
    self._arr = None;
    self._tbl = self.ArrayTable(parent);
    if dataitem and dataitem.data is not None:
      self.set_data(dataitem);
      
  def wtop (self):
    return self._tbl;
  
  def set_data (self,dataitem,**opts):
    # save currenty open tree
#    if self._arr:
#      openitems = self.get_open_items();
#    else: # no data, use default open tree if specified
#      openitems = default_open or self._default_open;
    # clear everything and reset data as new
    self._tbl.set_array(dataitem.data);
    # apply saved open tree
#    self.set_open_items(openitems);


class ArrayPlotter(ArrayBrowser,BrowserPlugin):
  _icon = pixmaps.bars3d;
  viewer_name = "Array Plotter";






class ResultBrowser(RecordBrowser,BrowserPlugin):
  _icon = pixmaps.areas3d;
  viewer_name = "Result Browser";
gridded_workspace.registerViewer(dict,ResultBrowser,dmitype='meqresult');
  
gridded_workspace.registerViewer(array_class,ArrayBrowser);
gridded_workspace.registerViewer(array_class,ArrayPlotter);
# register the RecordBrowser as a viewer for the appropriate types
for tp in (dict,list,tuple,array_class):
  gridded_workspace.registerViewer(tp,RecordBrowser);
