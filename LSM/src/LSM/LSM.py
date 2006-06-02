#!/usr/bin/python
#
# The Local Sky Model (LSM)
#
# The code includes the LSM as well as other helper classes
# used within the LSM. For an outside user, the only classes
# needed are the LSM and the PUnit.
# 

import sys,time
import math,struct
import pickle # for serialization and file io
from Dummy import *

from common_utils import *
from LSM_inner import *
from Timba.Meq import meq
from Timba.TDL import *
from Timba.Trees import TDL_Sixpack
from Timba.Trees import TDL_ParmSet
from Timba.Meq import meq

from Timba.Apps import app_nogui
from Timba.Apps import assayer

###############################################
class PUnit:
 """p-Unit object 
 Attributes are
  name: will be a unique string like "3C48" or "patch#23". Note source 
    names are also stored in source table.
  type: point soure/ patch - integer, 0 - point soure, 1 - patch
  s_list: source list - list of sources in the source table
  cat: 1 - source is Cat I, 2 - Cat 2, etc (default 1)
  app_brightness: apparent brightness - used in sorting and peeling
  sp: the sixpack helper object
   {Root, Cell, sI: sQ: sU: sV: RA: Dec: }
  FOV_distance: relative OBSWIN size
  lsm: LSM using this PUnit

  _patch_name: if this PUnit is a point source, and belongs to a patch,
     remember the name of the patch here. If this is a patch or a point
     source that does not belong to a patch, this value is None.

  __sixpack: store the sixpack object
  """
 # Constructor
 def __init__(self,name,lsm):
  # p-Unit name has to be a string
  if type(name) != type(""):
    raise TypeError,"Name must be a string, not %s"  % type(name).__name__
  self.name=name
  self.lsm=lsm
  self.type=POINT_TYPE
  self.s_list=[]
  self.cat=1
  self.app_brightness=1
  self.sp=SpH(self.lsm)
  self.FOV_distance=0

  self._patch_name=None # FIXME: only temporary

  self.__sixpack=None
  self._nodes=None# buffer to store any nodes associated with this PUnit,
                   # useful for dealing with ParmSet and NodeSet objects
 
 # change type (point: flag=POINT_TYPE, patch: flag=PATCH_TYPE)
 def setType(self,flag):
  self.type=flag
 # return type
 def getType(self):
  return self.type
  
 # add a source to the source list, s = source name
 def addSource(self,s):
  self.s_list.append(s)
 # return the source list
 def getSources(self):
  return self.s_list
 
 # change Category 
 def setCat(self,cat):
  self.cat=cat
 # return category
 def getCat(self):
  return self.cat

 # change apparent brightness
 def setBrightness(self,brightness):
  self.app_brightness=brightness

 # return value
 # type='I','Q','U','V' or 'A' for app_brightness
 # f=freq_index, t=time_index
 def getBrightness(self,type='A',f=0,t=0):
  if type=='A':
   return self.app_brightness
  else:
    return self.sp.getValue(type,f,t)

 # change FOV distance
 def setFOVDist(self,distance):
  self.FOV_distance=distance
 def getFOVDist(self):
  return self.FOV_distance

 # get eX,eY,eP values of the sources in this PUnit
 # if all are point sources, return zeros
 def getExtParms(self):
  ll=[]
  for ss in self.s_list:
    ll.append(self.lsm.s_table[ss].extParms())

  return ll[0]


 # get RA,DEC if possible
 def getRADec(self,ns):
   mysixpack=self.__sixpack
   [ra,dec,br]=extract_parms(mysixpack,ns)
   return (ra,dec)

 # get I,Q,U,V if possible
 def getIQUV(self,ns):
   mysixpack=self.__sixpack
   [ra,dec,I]=extract_parms(mysixpack,ns)
   [I,Q,U,V,SI,f0]=extract_polarization_parms(mysixpack,ns,absolute=1)
   return (I,Q,U,V,SI,f0)



 def getEssentialParms(self,ns):
   (ra,dec)=self.getRADec(ns)
   (I,Q,U,V,SI,f0)=self.getIQUV(ns)

   return (ra,dec,I,Q,U,V,SI,f0)

 # if this PUnit is a patch, or a gaussian return the limits
 # of its boundary
 # [x_min,y_min,x_max,y_max]
 def getLimits(self):
  if self.type == POINT_TYPE:
    return [0,0,0,0]
  elif self.type == GAUSS_TYPE:
    ra=self.sp.getRA()
    dec=self.sp.getDec()
    (eX,eY,eP)=self.getExtParms()
    return [ra-eX/2,ra+eX/2,dec-eX/2,dec+eX/2]
  else: # this is a patch
   # traverse the source list 
   x_min=1e6
   y_min=1e6
   x_max=-1e6
   y_max=-1e6
   for sname in self.s_list:
    punit=self.lsm.p_table[sname]
    if punit != None:
     x=punit.sp.getRA()
     y=punit.sp.getDec()
     if x_min > x:
      x_min=x
     if x_max < x:
      x_max=x
     if y_min > y:
      y_min=y
     if y_max < y:
      y_max=y
   return [x_min,y_min,x_max,y_max]  
  # will not get here  
  return [0,0,0,0]

 # Print
 def __str__(self):
   temp_str="P-Unit: | Name="+str(self.name)
   temp_str+=", type="+str(self.type)
   temp_str+=",source_list="+str(self.s_list)
   temp_str+=",cat="+str(self.cat)
   temp_str+=",Brightness="+str(self.getBrightness())
   temp_str+=",sp="+str(self.sp)
   temp_str+=",FOV="+str(self.FOV_distance)
   temp_str+=",sixpack="+str(self.__sixpack)
   temp_str+=",FOV="+str(self.FOV_distance)
   temp_str+=",patch="+str(self._patch_name)
   temp_str+=" |"
   return temp_str


 # clone the PUnit without circular references to the LSM
 # or references to MeqTree systems so that it can be saved
 # if subscope is true, will strip names with a leading 'something'::
 def clone(self,subscope=None):
  newp=PUnit(self.name,None)
  newp.type=self.type
  newp.s_list=self.s_list
  newp.cat=self.cat
  newp.app_brightness=self.app_brightness
  # sixpack helper
  newp.sp=self.sp.clone()
  # instead of the Sixpack Object, we store the 
  # root node namse of the IQUV,Ra,Dec subtrees
  if self.__sixpack!=None:
   newp.__sixpack={}
   pset=self.__sixpack.ParmSet
   nodes=pset.NodeSet.MeqNode()
   # attach all nodes to the temp buffer
   nset_nodenames=nodes.keys()
   newp._nodes=[]
   # strip subscope from node names
   for nodename in nset_nodenames:
    if subscope: newp._nodes.append(strip_subscope(nodename))
    else: newp._nodes.append(nodename)

   # copy ParmSet
   newp.__sixpack['ParmSet']=pset.clone()
   #print newp.__sixpack['ParmsSt']
   if self.__sixpack.ispoint():
    newp.__sixpack['I']=self.__sixpack.stokesI().name
    if subscope: newp.__sixpack['I']=strip_subscope(newp.__sixpack['I'])
    newp.__sixpack['Q']=self.__sixpack.stokesQ().name
    if subscope: newp.__sixpack['Q']=strip_subscope(newp.__sixpack['Q'])
    newp.__sixpack['U']=self.__sixpack.stokesQ().name
    if subscope: newp.__sixpack['U']=strip_subscope(newp.__sixpack['U'])
    newp.__sixpack['V']=self.__sixpack.stokesV().name
    if subscope: newp.__sixpack['V']=strip_subscope(newp.__sixpack['V'])
    newp.__sixpack['ra']=self.__sixpack.ra().name
    if subscope: newp.__sixpack['ra']=strip_subscope(newp.__sixpack['ra'])
    newp.__sixpack['dec']=self.__sixpack.dec().name
    if subscope: newp.__sixpack['dec']=strip_subscope(newp.__sixpack['dec'])
    newp.__sixpack['label']=self.__sixpack.label()
    newp.__sixpack['pointroot']=self.__sixpack.sixpack().name
    if subscope: newp.__sixpack['pointroot']=strip_subscope(newp.__sixpack['pointroot'])
   else:
    newp.__sixpack['patchroot']=self.__sixpack.root().name
    if subscope: newp.__sixpack['patchroot']=strip_subscope(newp.__sixpack['patchroot'])
    newp.__sixpack['label']=self.__sixpack.label()
  else:
   newp.__sixpack=None
  newp.FOV_distance=self.FOV_distance
  newp._patch_name=self._patch_name
  return newp
 
 # set the LSM of this PUnit
 def setLSM(self,lsm):
  self.lsm=lsm
  self.sp.setLSM(lsm)

 # set the sixpack object
 def setSP(self,sp):
  self.__sixpack=sp
 # return a sixpack object (TDL_Sixpack) for this PUnit
 def getSP(self):
  return self.__sixpack
 # return a sixpack object (TDL_Sixpack) for this PUnit
 def getSixpack(self):
  return self.__sixpack
 # set the sixpack object
 def setSixpack(self,sp):
  self.__sixpack=sp

 # change RA,Dec of myself, 
 def change_location(self,new_ra,new_dec,ns):
   if self.getType()==POINT_TYPE or self.getType()==GAUSS_TYPE :
    my_sixpack=self.__sixpack
    change_radec(my_sixpack,new_ra,new_dec,ns)
   elif self.getType()==PATCH_TYPE:
    change_radec_patch(self.name,new_ra,new_dec,ns)
     #ra0:q='+patch_name

   # change static values
   self.sp.set_staticRA(new_ra)
   self.sp.set_staticDec(new_dec)

 # Try to recreate a TDL_ParmSet from a given dict.
 # Assume all needed nodes exist in the ns
 # Assume also the sixpack is present in this PUnit
 def setParmSet(self,tmp_dict,ns):
  #print tmp_dict
  if self.__sixpack==None or ns==None:
    print "WARNING: cannot reconstruct ParmSet"
    return
  # recreate ParmSet
  pset=TDL_ParmSet.ParmSet()
  pset.restore(tmp_dict,ns)
  #pset.display()
  # attach it to sixpack 
  self.__sixpack.ParmSet=pset
###############################################
class LSM:
 """LSM Object:
 Attributes are
  s_table: Source table
  m_table: MeqParm table
  tmpl_table: Template tree table
  p_table: p-Unit table

  helper attributes:
  __barr: array of p-Units sorted by brightness - private attribute
  __mqs: meqserver proxy
  __root: root of all subtrees of the LSM
  __file: currently opend file or recently saved file name
          If not using a file, this will be Empty
 """
 # Constructor
 # Does pretty much nothing so far
 def __init__(self):
  self.s_table={}
  self.m_table='thislsm.mep'
  self.tmpl_table={}
  self.p_table={}
  self.mqs=None
  # the request domain, just a cell right now
  self.cells=None
  # need to remember the forest
  self.__ns=None
  # counter to give unique names to patches
  self.__patch_count=0
 
  self.__barr=[] 
  # root of all subtrees
  self.__root=None
  # name of the root node
  self.__root_name=None

  # how to create phase center of patches
  # 'G': geometric center, 'C': centroid  (weighted)
  self.default_patch_center='C'
  # patch creation methods 1,2,
  self.default_patch_method=1

  # display window
  self.__win=None

  # filename
  self.__file="None"

  # undo buffer, stores a command and a variable if any
  self.__undo=None

  # a placeholder for extra nodes associated with the LSM
  # but not yet part of a tree
  self._extra_node_list=[]


 # Much more important method
 # Inserts a source to source table
 def add_source(self,s, **kw):
  """This will insert source s to stable,
    and search the MeqParm table for the params of the source
    (using the source name). Then will add relevent params from
    the mtable (row numbers) to the source param list
    Arguments:
    s: Source object
    **kw=variable list of keyword arguments such as
     brightness=10
     sixpack='Sixpack object, in a composed state'
     ra=100
     dec=100
  
     WARNING: this method will be phased out from public to private
  """ 
  # Source names have to be unique
  if self.s_table.has_key(s.name):
   # Print error
   #raise NameError, 'Source '+s.name+' is already present'
   # dont stop, just issue a warning
   print "WARNING: Source "+s.name+' is already present'
   return
  self.s_table[s.name]=s
  """ After inserting the source to source table,
      search the  MeqParm table if it has any parms of the source.
     Add these params to the source param list."""

  """Now create a p-unit object for this (point) source.
      the p-unit object will link to the template trees.
      Note that p-unit table has to be sorted by brightness.
      so the insertion has to done in a sorted way.
  """
  # Use the p-unit name to be the source name (point source) 
  p=PUnit(s.name,self)
  if s.getType()!=POINT_TYPE:
   p.setType(s.getType())

  # add the source to the source list of the p-unit
  p.addSource(s.name)
  
  # all other p-Unit parameters are given be key-word argument list
  if kw.has_key('brightness'):
   p.setBrightness(kw['brightness'])
  else:
   p.setBrightness(0)

  # set the sixpack object
  if kw.has_key('sixpack'):
   p.setSP(kw['sixpack'])
   # set the root
   my_sixpack=p.getSP()
   p.sp.setRoot(my_sixpack.sixpack())
   # add this to the root
   self.addToTree(my_sixpack.sixpack())

#  # FIXME for the moment use static RA,Dec
  if kw.has_key('ra'):
   p.sp.set_staticRA(kw['ra'])
  if kw.has_key('dec'):
   p.sp.set_staticDec(kw['dec'])



  # finally, insert p-Unit to p-Unit table
  self.insertPUnit(p)

 # Helper method 
 # inserts a p-unit into the p-Unit table, and 
 # orders according to the brightness
 def insertPUnit(self,p):
  if self.p_table.has_key(p.name):
   #raise NameError, 'PUnit '+p.name+' is already present'
   print "WARNING: PUnit '"+p.name+"' is already present. Ignoring insertion"
  else:
   self.p_table[p.name]=p
  # now do the sorting of the brightness array
  tmp_brightness=p.getBrightness() 
  if (len(self.__barr)==0):
   self.__barr.insert(0,p.name)
  else: # list is not empty
   for i in range(len(self.__barr)):
    if self.p_table[self.__barr[i]].getBrightness() < tmp_brightness:
     break


   # special check for end of list
   if i==0: 
    if self.p_table[self.__barr[i]].getBrightness() < tmp_brightness:
      self.__barr.insert(0,p.name)
    else:
      self.__barr.append(p.name)
   elif i==len(self.__barr)-1:
    if self.p_table[self.__barr[i]].getBrightness() < tmp_brightness:
     self.__barr.insert(i,p.name)
    else:
     self.__barr.append(p.name)
   else:
    self.__barr.insert(i,p.name)

 # method for printing to screen
 def dump(self):
  print "---------------------------------"
  print "Source Table:"
  for s in self.s_table.keys():
   print self.s_table[s]
  print "\n\n"
  print "P-Unit Table:\n"
  for p in self.p_table.keys():
   print self.p_table[p]
  print "\n\n"

  print "P-Units sorted in Brightness:\n"
  for p in self.__barr:
   print p, self.p_table[p].getBrightness()

  print "---------------------------------"

 # set the MeqServer Proxy
 def setMQS(self,mqs):
  self.mqs=mqs

 # set the Cells for the request
 def setCells(self,cells):
  self.cells=cells

 # get the range of ObsWin
 # [f0,f1,fstep,t0,t1,tstep]
 def getCellsRange(self):
  res={}
  if self.cells != None:
   res['f0']=self.cells.domain.freq[0]
   res['f1']=self.cells.domain.freq[1]
   res['fstep']=self.cells.segments.freq.end_index+1
   res['t0']=self.cells.domain.time[0]
   res['t1']=self.cells.domain.time[1]
   res['tstep']=self.cells.segments.time.end_index+1

  return res

 # method for visualization
 # app='create' will create own QApplication.
 # when NOT using MeqBrowser, use this option
 def display(self, **kw ):
  d=Dummy(self,sys.argv)
  if kw.has_key('app') and (kw['app']=='create'):
    d.display(app='create')
  else:
    d.display()
  self.__win=d.win

 # close the display, if any
 def close_display(self):
  if self.__win!=None:
    self.__win.close()

 # return number of sources
 def getSources(self):
  return len(self.s_table)
 # return no of columes in source table
 def getSourceColumns(self):
  return 3
 # return the named p-Unit from the p-Unit table 
 def getPUnit(self,pname):
  if self.p_table.has_key(pname):
   return self.p_table[pname]
  # else
  return None 

 # return number of p-Units in the p-Unit table 
 def getPUnits(self):
  # do not count points that belong to a PUnit
  count=0
  for pname in self.p_table.keys():
   pu=self.p_table[pname]
   if ((pu.getType()==POINT_TYPE or pu.getType()==GAUSS_TYPE) and pu._patch_name==None) or\
     pu.getType()==PATCH_TYPE:
    count+=1
  return count 

 # return no of columes in p-Unit table
 def getPUnitColumns(self):
  return 12
 # return max,min values of RA and Dec
 def getBounds(self):
  # handle empty case first
  if len(self.p_table)==0:
    result={}
    result['min_RA']=0
    result['max_RA']=math.pi-0.1
    result['min_Dec']=-math.pi/2
    result['max_Dec']=math.pi/2
    return result

  max_RA=-100
  min_RA=100
  max_Dec=-100
  min_Dec=100

  for p in self.p_table.keys():
   punit=self.p_table[p]
   if punit.getType()==POINT_TYPE :
    tmpval=punit.sp.getRA()
    if tmpval > max_RA:
     max_RA=tmpval
    if tmpval <  min_RA:
     min_RA=tmpval
    tmpval=punit.sp.getDec()
    if tmpval > max_Dec:
     max_Dec=tmpval
    if tmpval <  min_Dec:
     min_Dec=tmpval
   elif punit.getType()==GAUSS_TYPE :
    [x0,x1,y0,y1]=punit.getLimits()
    if x1 > max_RA:
     max_RA=x1
    if x0 <  min_RA:
     min_RA=x0
    if y1 > max_Dec:
     max_Dec=y1
    if y0 <  min_Dec:
     min_Dec=y0

  result={}
  result['min_RA']=min_RA 
  result['max_RA']=max_RA 
  result['min_Dec']=min_Dec
  result['max_Dec']=max_Dec

  return result

 # return max value of (brightness)
 # type='I','Q','U','V' or 'A' for app_brightness
 # f=freq_index, t=time_index
 def getMaxBrightness(self,type='A',f=0,t=0):
  if type=='A':
   if len(self.__barr)==0:
    return 0
   pname=self.__barr[0]
   return self.p_table[pname].getBrightness()
  else:
   # select the max value
   tmp_max=-1e6
   for pname in self.p_table.keys():
    mytype=self.p_table[pname].getType()
    if mytype==POINT_TYPE or mytype==GAUSS_TYPE :
     tmp_val=self.p_table[pname].sp.getValue(type,f,t)
     if tmp_max < tmp_val:
      tmp_max=tmp_val
   return tmp_max

  # else
  return 0

 # return min value of (brightness)
 # type='I','Q','U','V' or 'A' for app_brightness
 # f=freq_index, t=time_index
 def getMinBrightness(self,type='A',f=0,t=0):
  if type=='A':
   #if len(self.__barr)==0:
   # return 0
   #pname=self.__barr[len(self.__barr)-1]
   #return self.p_table[pname].getBrightness()
   # the Min value of brightness is not necessarily the 
   # last element in __barr because sources in patches
   # are removed from the __barr. Hence we need to do a 
   # scan of all punits
   tmp_min=1e6 # FIXME: a very large value
   for pname in self.p_table.keys():
    mytype=self.p_table[pname].getType()
    if mytype==POINT_TYPE or mytype==GAUSS_TYPE:
     tmp_val=self.p_table[pname].getBrightness()
     if tmp_min > tmp_val:
      tmp_min=tmp_val
   return tmp_min
  else:
   # select the min value
   tmp_min=1e6
   for pname in self.p_table.keys():
    mytype=self.p_table[pname].getType()
    if mytype==POINT_TYPE or mytype==GAUSS_TYPE :
     tmp_val=self.p_table[pname].sp.getValue(type,f,t)
     if tmp_min > tmp_val:
      tmp_min=tmp_val
   return tmp_min

  # else
  return 0

 # return max,min and abs(min) values 
 def getBrightnessLims(self,type='A',f=0,t=0):
  if type=='A':
   # scan of all punits
   tmp_min=1e6 # FIXME: a very large value
   tmp_max=-1e6
   tmp_abs_min=1e6
   for pname in self.p_table.keys():
    mytype=self.p_table[pname].getType()
    if mytype==POINT_TYPE or mytype==GAUSS_TYPE:
     tmp_val=self.p_table[pname].getBrightness()
     if tmp_min > tmp_val:
      tmp_min=tmp_val
     if tmp_abs_min > abs(tmp_val):
      tmp_abs_min=abs(tmp_val)
     if tmp_max < tmp_val:
      tmp_max=tmp_val
   return (tmp_max,tmp_min,tmp_abs_min)

  return (0,0,0)

 # return current frequency and time
 def getCurrentFreqTime(self,freq_index,time_index):
  if self.cells==None:
   return [0,0]
  if (self.cells.segments.freq.start_index > freq_index) or\
    (self.cells.segments.freq.end_index < freq_index):
    print "get Curr Index error, Frequency %d" %freq_index
    freq_index=self.cells.segments.freq.start_index
  if (self.cells.segments.time.start_index > time_index) or\
    (self.cells.segments.time.end_index < time_index):
    print "get Curr Index error, Time %d" %time_index
    time_index=self.cells.segments.time.start_index

  f=self.cells.grid.freq[freq_index]
  t=self.cells.grid.time[time_index]
  return [f,t]


 # update vellset values for the current cells
 def updateCells(self):
  for sname in self.p_table.keys(): 
   punit=self.p_table[sname]
   #if punit.getType()==POINT_TYPE:
   punit.sp.updateValues(sname)

 # save to a file
 # while saving, discard any existing vellsets because
 # they can be recalculated. 
 def save(self,filename):
  # add safeguard: do not save if the filename has 
  # a 'protected.lsm' term
  ii=string.find(filename,'protected.lsm')
  if ii!=-1:
   print "WARNING: the filename %s is protected. save failed!!!"%filename
   return
  try:
   f=open(filename,'wb') 
   p=pickle.Pickler(f)
   # create a new LSM from this LSM,
   # without reference to MeqServer or the forests
   g=LSM()
   g.s_table=self.s_table
   g.m_table=self.m_table
   g.tmpl_table=self.tmpl_table
   g.__barr=self.__barr
   g.mqs=None
   g.cells=None
   g.__patch_count=self.__patch_count
   g.default_patch_center=self.default_patch_center
   g.default_patch_method=self.default_patch_method


   # serialize the root
   gdict={}
   if self.__root!=None:
    # serialize the whole subtree
    traverse(self.__root,gdict,self.__ns._name)

   # if the nodescope has a subscope, strip the subscope 
   # name from the root name
   if self.__ns._name:
     g.__root_name=strip_subscope(self.__root_name)
   else: 
     g.__root_name=self.__root_name

   # remove circular references to the old LSM
   # serialize the PUnit table 
   g.p_table={}

   extra_node_list=[]
   for sname in self.p_table.keys(): 
    punit=self.p_table[sname]
    # this is just for testing, add a dummy node thats not in the LSM
    ####punit.getSixpack().ParmSet.NodeSet.set_MeqNode(self.__ns<<Meq.Parm(-1))
    g.p_table[sname]=punit.clone(self.__ns._name)
    g.p_table[sname].setLSM(g)
    # get the nodes of the NodeSet of the ParmSet of this PUnit
    # because we may need to save them with the LSM too.
    my_nodes=punit.getSixpack().ParmSet.NodeSet.MeqNode()
    # store them if they are not already saved by the LSM subtree
    for my_name in my_nodes.keys():
      # get stripped name without subscope
      last_name=my_name
      if self.__ns._name: last_name=strip_subscope(my_name)
      if not gdict.has_key(last_name):
       # we need to save this node
       traverse(my_nodes[my_name]['node'],gdict,self.__ns._name)
       extra_node_list.append(last_name)

   g.__root=pickle.dumps(gdict)
   g._extra_node_list=extra_node_list
   #print g._extra_node_list

   p.dump(g)
   f.close()

   self.__file=filename

  except IOError:
   print "file %s cannot be opened, save failed" % filename 
  
  # next step: save the MeqTrees
  if self.mqs != None:
   pass
   #forest_filename=filename+'.forest'
   #self.mqs.meq('Save.Forest',meq.record(file_name=forest_filename));

 # load from a file 
 # Note if the saved LSM was created using a Subscope
 # the new LSM will ignore that subscope, i.e. will change
 # all node names such that the subscope part is not present
 def load(self,filename,ns=None):
  try:
   f=open(filename,'rb') 
   p=pickle.Unpickler(f)
   tmpl=LSM()
   tmpl=p.load()
   self.s_table=tmpl.s_table
   self.m_table=tmpl.m_table
   self.tmpl_table=tmpl.tmpl_table
   self.__barr=tmpl.__barr

   self.__patch_count=tmpl.__patch_count
   self.default_patch_center=tmpl.default_patch_center
   self.default_patch_method=tmpl.default_patch_method

   self.__root_name=tmpl.__root_name
   #print "Root =",self.__root_name
   if tmpl.__root!=None:
    if ns==None:
     ns=NodeScope()
    self.__ns=ns
    my_dict=pickle.loads(tmpl.__root)
    #print my_dict[self.__root_name]
    # if there is already a node with the root name, we remove it from our dict
    # and change root name
    if ns[self.__root_name].initialized():
      # create a unique name
      new_root_name=ns.MakeUniqueName(self.__root_name)
      oldroot=my_dict.pop(self.__root_name)
      print "WARNING: changing name from %s to %s"%(self.__root_name,new_root_name)
      self.__root_name=new_root_name
      my_dict[self.__root_name]=oldroot

    my_dict=reconstruct(my_dict,ns)
    self.__root=my_dict[self.__root_name]
    #self.__ns.Resolve()
   else:
     self.__root=None
     print "WARNING: cannot find a root node in the LSM. load will fail!"

   # recreate the extra node list, if any
   if hasattr(tmpl,"_extra_node_list") and len(tmpl._extra_node_list)>0:
     print "Found extra nodes"
     extra_root_name=ns.MakeUniqueName(self.__root_name+"_extra")
     ns[extra_root_name]<<Meq.Composer(children=tmpl._extra_node_list)

   
   self.p_table=tmpl.p_table
   # reconstruct PUnits and Sixpacks if possible
   for sname in self.p_table.keys(): 
    punit=self.p_table[sname]
    punit.setLSM(self)
    # now create the sixpack
    tmp_dict=punit.getSP()
    #print tmp_dict
    if tmp_dict.has_key('patchroot'):
     my_sp=TDL_Sixpack.Sixpack(label=tmp_dict['label'],\
      ns=self.__ns, root=self.__ns[tmp_dict['patchroot']])
    else: 
     # NOTE: do not give the nodescope because then it tries to
     # compose, but the tree is already composed
     my_sp=TDL_Sixpack.Sixpack(label=tmp_dict['label'],\
       ra=cname_node_stub(self.__ns,tmp_dict['ra']),\
       dec=cname_node_stub(self.__ns,tmp_dict['dec']),\
       stokesI=cname_node_stub(self.__ns,tmp_dict['I']),\
       stokesQ=cname_node_stub(self.__ns,tmp_dict['Q']),\
       stokesU=cname_node_stub(self.__ns,tmp_dict['U']),\
      stokesV=cname_node_stub(self.__ns,tmp_dict['V']))
     # set the root node
     my_sp=my_sp.clone(sixpack=self.__ns[tmp_dict['pointroot']],ns=self.__ns)
    punit.setSP(my_sp)
    # recreate ParmSet for this sixpack
    punit.setParmSet(tmp_dict['ParmSet'],self.__ns)
    # recreate the NodeSet nodes, if any
    if hasattr(punit,"_nodes") and punit._nodes!=None:
       my_sp=punit.getSixpack()
       for nodename in punit._nodes:
         my_sp.ParmSet.NodeSet.set_MeqNode(cname_node_stub(self.__ns,nodename))
       punit._nodes=None
    # set the root
    punit.sp.setRoot(my_sp.sixpack())


   f.close()

   self.setFileName(filename)

  except IOError:
   print "file %s cannot be opened, load failed" % filename 
  # next step: Load the MeqTrees if possible 
  if self.mqs != None:
   pass
   #forest_filename=filename+'.forest'
   #self.mqs.meq('Load.Forest',meq.record(file_name=forest_filename),wait=True);
   #self.mqs.meq('Load.Forest',meq.record(file_name=forest_filename));


 # send a request to the LSM to give the p-units
 # with highest brightness, or p-unit with name ='name' etc.
 # returns a list of p-units satisfying the query
 # possible query formats are:
 # count=4 : gives first 4 brightest punits
 # names='list of names': gives a list of p units matching the names in the  'name_list'
 # name='name': gives the p unit matching the name 'name'
 # cat=1,2,.. : gives p units of given category
 def queryLSM(self,**kw):
  
  outlist=[]
  if kw.has_key('all') and kw['all']==1:
   for pname in self.p_table.keys():
     pu=self.p_table[pname]
     if (((pu.getType()==POINT_TYPE or pu.getType()==GAUSS_TYPE ) and pu._patch_name==None) or\
       pu.getType()==PATCH_TYPE):
       outlist.append(pu)
   return outlist
 
  if kw.has_key('name'):
   outlist.append(self.p_table[kw['name']])
   return outlist
  
  if kw.has_key('names'):
   for pname in kw['names']:
     if self.p_table.has_key(pname):
      outlist.append(self.p_table[pname])
   return outlist
 
  if kw.has_key('count'):
   for i in range(min(kw['count'],len(self.__barr))): 
    outlist.append(self.p_table[self.__barr[i]])
   return outlist

  if kw.has_key('cat'):
    for pname in self.p_table.keys():
     pu=self.p_table[pname]
     if pu.getCat()==kw['cat'] and\
      (((pu.getType()==POINT_TYPE or pu.getType()==GAUSS_TYPE ) and pu._patch_name==None) or\
       pu.getType()==PATCH_TYPE):
       outlist.append(pu)
    return outlist


 # from the given list of (point) source  names (slist),
 # create a patch, and add it to the PUnit table
 # if calling this in a batchwise manner, call this with
 # resolve_forst=False and sync_kernel=False
 # in all calls but the last one, to speed things up
 def createPatch(self,slist,resolve_forest=True,sync_kernel=True):
  # first browse the slist and 
  # remove any sources already in a patch,
  # also calculate min,max of (RA,Dec) to find the 
  # phase center of the patch.
  x_min=1e6
  x_max=-1e6
  y_min=1e6
  y_max=-1e6
  correct_slist=[]
  sum_brightness=0
  # calculate moments in fulx (app_brightness) to
  # determine the phase center
  sum_x_phi=0
  sum_y_phi=0
  for sname in slist:
    # select only sources without a patch 
    if (self.p_table.has_key(sname) and\
       self.p_table[sname]._patch_name ==None):
      correct_slist.append(sname)
      # remove this source from sorted patch list
      self.__barr.remove(sname)
      # get min,max coords
      ra=self.p_table[sname].sp.getRA() 
      dec=self.p_table[sname].sp.getDec() 
      if ra>x_max:
       x_max=ra
      if ra<x_min:
       x_min=ra
      if dec>y_max:
       y_max=dec
      if dec<y_min:
       y_min=dec
      # get apparent brightness of this source
      br=self.p_table[sname].getBrightness()
      sum_brightness+=br
      # calculate moments
      sum_x_phi+=ra*br
      sum_y_phi+=dec*br

  #print "Patch: [%f,%f]--[%f,%f]"%(x_min,y_min,x_max,y_max)
  #print correct_slist
  #print self.__ns

  # calculate RA,Dec of phase center
  if self.default_patch_center=='G':
   ra_0=(x_min+x_max)*0.5
   dec_0=(y_min+y_max)*0.5
  else: # 'C'
   # using moments
   ra_0=sum_x_phi/sum_brightness
   dec_0=sum_y_phi/sum_brightness
  #print sum_x_phi,sum_x_phi/sum_brightness
  #print sum_y_phi,sum_y_phi/sum_brightness
  #print ra_0,dec_0
  if self.__ns!=None and (len(correct_slist)> 0):
   patch_name='patch'+str(self.__patch_count)
   self.__patch_count=self.__patch_count+1
   stringRA='ra0:q='+patch_name
   meq_polc=meq.polc(ra_0)
   RA_root=self.__ns[stringRA]<<Meq.Parm(meq_polc)
   stringDec='dec0:q='+patch_name
   meq_polc=meq.polc(dec_0)
   Dec_root=self.__ns[stringDec]<<Meq.Parm(meq_polc) 
   # twopack for phase center
   twoname='radec:q='+patch_name
   tworoot=self.__ns[twoname]<<Meq.Composer(RA_root,Dec_root)
  
   child_list=[tworoot.name]
   # get the sixpack root of each source in slist
   # and add it to patch composer
   for sname in correct_slist:
     punit=self.getPUnit(sname)
     psixpack=punit.getSP()
     my_name=''
     if psixpack!=None:
      my_name=psixpack.sixpack().name
     elif punit.sp!=None:
      my_name='sixpack:q='+pname

     child_list.append(my_name)
     self.p_table[sname]._patch_name=patch_name
   #print child_list
   patch_root=self.__ns['sixpack:q='+patch_name]<<Meq.PatchComposer(method=self.default_patch_method,children=child_list)

   # add this to our root
   self.addToTree(patch_root)

   #patch_root=self.__ns[patch_name]<<Meq.Composer(children=child_list)
   #select_root=self.__ns['Select['+patch_name+']']<<Meq.Selector(children=patch_root,multi=True,index=[2,3,4,5])
   #stokes_root=self.__ns['Stokes['+patch_name+']']<<Meq.Stokes(children=select_root)
   #fft_root=self.__ns['FFT['+patch_name+']']<<Meq.FFTBrick(children=stokes_root)
   if self.__ns != None and resolve_forest==True:
    pass
    #self.__ns.Resolve()
    #print "Current forest has %d root nodes, of a total of %d nodes"% (len(self.__ns.RootNodes()),len(self.__ns.AllNodes()))

   #Timba.TDL._dbg.set_verbose(5);
   # try to run stuff
   if self.mqs != None and resolve_forest==True and\
      sync_kernel==True:
     self.__ns.Resolve()
     self.mqs.meq('Clear.Forest')
     self.mqs.meq('Create.Node.Batch',record(batch=map(lambda nr:nr.initrec(),self.__ns.AllNodes().itervalues())));
     #self.mqs.meq('Resolve.Batch',record(name=list(self.__ns.RootNodes().iterkeys())))
     # is a forest state defined?
     fst = getattr(Timba.TDL.Settings,'forest_state',record());
     self.mqs.meq('Set.Forest.State',record(state=fst));

   # create a new PUnit
   newp=PUnit(patch_name,self)
   newp.setType(PATCH_TYPE)
   newp.sp.setRoot(patch_root)
   newp.sp.set_staticRA(ra_0)
   newp.sp.set_staticDec(dec_0)
   newp.setBrightness(sum_brightness)


   # update vellsets
   #from Timba.Meq import meq
   #ftdom=meq.domain(startfreq=1e6, endfreq=3e6, starttime=0,endtime=1)
   #cc=meq.cells(domain=ftdom,num_freq=2, num_time=1)
   #req=meq.request(cells=cc,eval_mode=0)
   #args=meq.record(name=patch_name,request=req)
   #aa=self.mqs.meq('Node.execute',args,wait=True)
   for sname in correct_slist:
     newp.addSource(sname)

   # this PUnit is a Patch, so the traditional TDL_Sixpack
   # object does not apply here. However, we will create a dummy 
   # sixpack object.

   newp.setSP(TDL_Sixpack.Sixpack(root=patch_root,label=patch_root.name))

   # add new PUnit to table
   self.insertPUnit(newp)
   #print self.__barr
   #self.p_table[patch_name]=newp

   if resolve_forest==True and sync_kernel==True:
    pass
    #newp.sp.updateValues(patch_name)

   #Timba.TDL._dbg.set_verbose(0);
   # save the lsm
   # self.save('lsm_current.lsm')
   # return [patch name, x_min,y_min,x_max,y_max]
   # for the plotting method
   return [patch_name,x_min,y_min,x_max,y_max]

  # if we get here, an error
   return None


 # create patches from the grid, given by
 # an x_arry and y_array of grid points
 # note: x_array and y_array should be sorted in ascending order
 def createPatchesFromGrid(self,x_array,y_array,min_bright=0.0,max_bright=10.0,\
           min_sources=10):
  #from Timba.utils import verbosity
  #_dbg = verbosity(0,name='LSM')
  #_dprint = _dbg.dprint
  #_dprint(3,"Creating patches for",x_array,y_array)

  # add a margin to last elements to include points on the boundary
  x_array[len(x_array)-1]+=0.00001
  y_array[len(y_array)-1]+=0.00001

  # encapsulate arrays with large bounds
  # so we do not miss any points
  x_array.insert(0,x_array[0]-1e6)
  x_array.append(x_array[len(x_array)-1]+1e6)
  y_array.insert(0,y_array[0]-1e6)
  y_array.append(y_array[len(y_array)-1]+1e6)

  #print x_array
  #print y_array

  # now for each point source in p-unit list
  # if they are not already included in a patch
  # and also if they satisfy the criteria for including
  # in a patch, do a binary search and find correct grid position
  
  # set up bins to collect sorted sources
  xbins={}
  for ii in range(len(x_array)-1):
   xbins[ii]=[]
  ybins={}
  for ii in range(len(y_array)-1):
   ybins[ii]=[]

  #print xbins
  #print ybins


  for sname in self.p_table.keys(): 
    punit=self.p_table[sname]
    pb=punit.getBrightness('A')
    if  punit.getType()==POINT_TYPE and\
       punit._patch_name==None and\
       (pb<=max_bright) and (pb>=min_bright):
      # get RA and Dec
      xx=punit.sp.getRA()
      yy=punit.sp.getDec()
      k=bin_search(x_array,xx,0,len(x_array)-1)
      xbins[k].append(sname)
      k=bin_search(y_array,yy,0,len(y_array)-1)
      ybins[k].append(sname)

  #print xbins
  #print ybins
  # now create a reverse mapping hash table
  # indexed by source name, such that the pair
  # of indices [x_,y_] for each source (patch index)
  # is given
  p_id_x={}
  p_id_y={}
  # ignore bin indices 0 and the last_index
  # bacause these fall out of the range
  if len(xbins)>2:
   for ii in range(len(xbins)-2):
    ll=xbins[ii+1]
    # traverse list
    for sname in ll:
      p_id_x[sname]=ii+1
  if len(ybins)>2:
   for ii in range(len(ybins)-2):
    ll=ybins[ii+1]
    # traverse list
    for sname in ll:
      p_id_y[sname]=ii+1

  # now create the patches
  patch_bins={}
  for ii in range(len(xbins)-2):
   for jj in range(len(ybins)-2):
    patch_name="Patch#"+str(ii+1)+":"+str(jj+1)
    patch_bins[patch_name]=[]
 
  for sname in p_id_x.keys():
    ii=p_id_x[sname]
    if p_id_y.has_key(sname):
     jj=p_id_y[sname]
     patch_name="Patch#"+str(ii)+":"+str(jj)
     patch_bins[patch_name].append(sname)

  # create progree dialog
  if isinstance(qApp,QApplication):
    lpb = QProgressDialog("Creating Patches", "Close", len(patch_bins), self.__win, "progress", 1)
    lpb.setCaption("Please Wait")
    lpb.setMinimumDuration(0)
    lpb.show()
    i=0


  #print patch_bins
  # now call single patch creation function
  # remember return values from single patch creation
  retval_arr=[]
  new_punit_names=[]
  for pname in patch_bins.keys():
   # note: we do not send anything to the kernel
   # when we recreate the forest, that will be done later
   # note: create patches with at least two sources in it
   if len(patch_bins[pname]) >= min_sources and\
      len(patch_bins[pname]) >= 2: 
    retval=self.createPatch(patch_bins[pname],True,False)
   else:
    retval=None

   if retval !=None:
    retval_arr.append(retval)
    # remember PUnit name to update its value
    new_punit_names.append(retval[0])

   # update progress bar
   if isinstance(qApp,QApplication):
     lpb.setProgress(i)
     qApp.processEvents()
     i=i+1


  # now resolve forest and sync kernel
  #self.__ns.Resolve()
  #print "Resolved local NodeScope"
  #print "Current forest has %d root nodes, of a total of %d nodes"% (len(self.__ns.RootNodes()),len(self.__ns.AllNodes()))
  if self.mqs != None:
     #print "Sending request to kernel"
     self.__ns.Resolve()
     self.mqs.meq('Clear.Forest')
     self.mqs.meq('Create.Node.Batch',record(batch=map(lambda nr:nr.initrec(),self.__ns.AllNodes().itervalues())));
     self.mqs.meq('Resolve.Batch',record(name=list(self.__ns.RootNodes().iterkeys())))
     # is a forest state defined?
     fst = getattr(Timba.TDL.Settings,'forest_state',record());
     self.mqs.meq('Set.Forest.State',record(state=fst));
     # update vellset values for all newly created PUnits
     for pname in new_punit_names:
      print "Updating Punit ",pname
      punit=self.getPUnit(pname)
      #punit.sp.updateValues(pname)


  if isinstance(qApp,QApplication):
     lpb.cancel()
     del lpb
 
  return retval_arr


 # set the current NodeScope
 def setNodeScope(self,ns):
  #print dir(ns)
  #print ns._name
  self.__ns=ns
  # create a single root not to accomodate all subtrees
  # in the PUnit table, if id does not already exist
  if self.__root!=None:
   return
  child_list=[]
  for pname in self.p_table.keys():
   punit=self.getPUnit(pname)
   psixpack=punit.getSP()
   if psixpack!=None:
    if psixpack.ispoint():
     root_node=psixpack.sixpack()
    else: #Patch
     root_node=psixpack.root()
    child_list.append(root_node.name)
   elif punit.sp!=None:
    child_list.append('sixpack:q='+pname)
  #print child_list
  # create a common root
  if len(child_list)!=0:
   prefix=ns._name# true if ns is a sub scope
   if prefix!=None: 
    self.__root_name=ns._name+ns.MakeUniqueName('_lsmroot')
   else: 
    self.__root_name=ns.MakeUniqueName('_lsmroot')
   self.__root=self.__ns[self.__root_name]<<Meq.Composer(children=child_list)


 # add a child node (subtree) to the root node
 def addToTree(self,child):
  if(self.__root!=None):
   self.__root.add_children(child)
  elif self.__ns!=None:
    # no root node still exist so create one
    child_list=[]
    child_list.append(child.name)
    ns=self.__ns
    prefix=ns._name# true if ns is a sub scope
    if prefix!=None: 
      self.__root_name=ns._name+ns.MakeUniqueName('_lsmroot')
    else: 
      self.__root_name=ns.MakeUniqueName('_lsmroot')
    self.__root=self.__ns[self.__root_name]<<Meq.Composer(children=child_list)
  else:
   pass
   #print "WARNING: cannot create _lsm_root. please ignore this if you used add_sixpack() method."

 # return the current NodeScope
 def getNodeScope(self):
  return self.__ns

 # return the current Opened/Saved Filename
 def getFileName(self):
  return self.__file
 # get the filename with path stripped
 def getBaseFileName(self):
   # split the string
   sl=string.split(self.__file,'/')
   sl.reverse()
   # get the first non empty string
   gg=sl.pop(0)
   while (len(gg)==0) and len(sl)>0:
    gg=sl.pop(0)
   return gg

 # set the current Opened/Saved Filename
 def setFileName(self,fname):
  # truncate filename if too long
  self.__file=fname


 # read in a list of sixpacks (composed) for sources
 # and build the LSM using the MeqServer.
 # sixpack_list: list of sixpacks
 # ns: NodeScope of the sixpack trees
 # f0=rest frequency
 # mqs=MeqServer proxy, when run within MeqBrowser, this should
 #     be given. Else a MeqServer will be created.
 def build_from_sixpacks_assy(self,sixpack_list,ns,f0=1.6e6,mqs=None):
   if mqs==None:
    # fire up a server instance
    my_ass = assayer.assayer("LSM-"+time.strftime('%Y-%d-%H-%M-%S'));
    my_mqs=my_ass.mqs;
   else:
    my_mqs=mqs;
   my_ns=ns
   my_ns.Resolve()
   # form a request
   f1=f0+1.0
   t0=0.0
   t1=1.0
   nfreq=ntime=1
   freqtime_domain = meq.domain(startfreq=f0, endfreq=f1, starttime=t0, endtime=t1);
   cells =meq.cells(domain=freqtime_domain, num_freq=nfreq,  num_time=ntime);
   request = meq.request(cells,rqtype='e1');
   # populate tree
   # kernel will recreate the forest
   my_mqs.meq('Clear.Forest');
   my_mqs.meq('Create.Node.Batch',record(batch=map(lambda nr:nr.initrec(),my_ns.AllNodes().itervalues())));
   my_mqs.meq('Resolve.Batch',record(name=list(my_ns.RootNodes().iterkeys())))
   fst = getattr(Timba.TDL.Settings,'forest_state',record());
   my_mqs.meq('Set.Forest.State',record(state=fst));



   for my_sp in sixpack_list:
    # create a source object
    s=Source(my_sp.label())
    s_root=my_sp.sixpack()

    # get RA 
    b = my_mqs.meq('Node.Execute',record(name=my_sp.ra().name,request=request),wait=True);
    if hasattr(b.result.vellsets[0].value[0],'tolist'):
       source_RA=b.result.vellsets[0].value[0].tolist().pop(0)
    else:
       source_RA=b.result.vellsets[0].value[0]

    # get Dec 
    b = my_mqs.meq('Node.Execute',record(name=my_sp.dec().name,request=request),wait=True);
    if hasattr(b.result.vellsets[0].value[0],'tolist'):
       source_Dec=b.result.vellsets[0].value[0].tolist().pop(0)
    else:
       source_Dec=b.result.vellsets[0].value[0]

    # get Stokes I
    b = my_mqs.meq('Node.Execute',record(name=my_sp.stokesI().name,request=request),wait=True);
    if hasattr(b.result.vellsets[0].value[0],'tolist'):
       my_brightness=b.result.vellsets[0].value[0].tolist().pop(0)
    else:
       my_brightness=b.result.vellsets[0].value[0]


    # add this to the LSM
    self.add_source(s,brightness=my_brightness,
     sixpack=my_sp,
     ra=source_RA, dec=source_Dec)



   if mqs==None:
    # shutdown
    my_ass.finish()

 # read in a list of sixpacks (composed) for sources
 # and build the LSM by reading MeqParms.
 # sixpack_list: list of sixpacks
 # ns: NodeScope of the sixpack trees
 def build_from_sixpacks(self,sixpack_list,ns):
		for my_sp in sixpack_list:
		  self.add_sixpack(sixpack=my_sp,ns=ns)


 # Add just one sixpack to the LSM
 # input arguments are:
 # sixpack  =sixpack_object
 # ns       =nodescope, if not given the default one in LSM used
 def add_sixpack(self,**kw):
  if kw.has_key('sixpack'):
   my_sp=kw['sixpack']
   if kw.has_key('ns'):
    ns=kw['ns']
    if self.__ns==None:
     self.__ns=ns # update the LSM
   else:
    ns=self.__ns

   # extract params
   [ra,dec,br]=extract_parms(my_sp,ns)

   # insert
   s=Source(my_sp.label())
   self.add_source(s,brightness=br,
     sixpack=my_sp,
     ra=ra, dec=dec)
   # keep this nodescope

   #self.setNodeScope(ns)
   #add to self root
   #self.addToTree(my_sp.sixpack())
   #print self.__root
  else:
   print "WARNING: add_sixpack() called without giving a sixpack. Ignored!"
   pass


 # read in a text file to build the LSM
 # infile_name: file name, absolute path
 # ns: nodescope
 # The standard format of the file should be like this:
 #
 # cat     name            RA          eRA      Dec        eDec     freq   Flux(Jy)   eFl equi.
 #---------------------------------------------------------------------------------------------
 #NVSS  J163411+624953   16 34 11.868   0.73   62 49 53.72   8.3     1400    0.0030    .0005 J
 #
 def build_from_catalog(self,infile_name,ns):
  from Timba.Contrib.JEN import MG_JEN_Sixpack

  infile=open(infile_name,'r')
  all=infile.readlines()
  infile.close()

  # regexp pattern
  pp=re.compile(r"""
   ^(?P<col1>\S+)  # column 1 'NVSS'
   \s*             # skip white space
   (?P<col2>[A-Za-z]\w+\+\w+)  # source name i.e. 'J163002+631308'
   \s*             # skip white space
   (?P<col3>\d+)   # RA angle - hr 
   \s*             # skip white space
   (?P<col4>\d+)   # RA angle - min 
   \s*             # skip white space
   (?P<col5>\d+(\.\d+)?)   # RA angle - sec
   \s*             # skip white space
   (?P<col6>\d+(\.\d+)?)   # eRA angle - sec
   \s*             # skip white space
   (?P<col7>\d+)   # Dec angle - hr 
   \s*             # skip white space
   (?P<col8>\d+)   # Dec angle - min 
   \s*             # skip white space
   (?P<col9>\d+(\.\d+)?)   # Dec angle - sec
   \s*             # skip white space
   (?P<col10>\d+(\.\d+)?)   # eDec angle - sec
   \s*             # skip white space
   (?P<col11>\d+)   # freq
   \s*             # skip white space
   (?P<col12>\d+(\.\d+)?)   # brightness - Flux
   \s*             # skip white space
   (?P<col13>\d*\.\d+)   # brightness - eFlux
   \s*
   \S+
   \s*$""",re.VERBOSE)
 
  # read each source and insert to LSM
  for eachline in all:
   v=pp.search(eachline)
   if v!=None:
    s=Source(v.group('col2'))
    source_RA=float(v.group('col3'))+(float(v.group('col5'))/60.0+float(v.group('col4')))/60.0
    source_RA*=math.pi/12.0
    source_Dec=float(v.group('col7'))+(float(v.group('col9'))/60.0+float(v.group('col8')))/60.0
    source_Dec*=math.pi/180.0

    my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=eval(v.group('col12')), f0=1e6,RA=source_RA, Dec=source_Dec,trace=0)
   # first compose the sixpack before giving it to the LSM
    SourceRoot=my_sixpack.sixpack(ns)
    my_sixpack.display()
    self.add_source(s,brightness=eval(v.group('col12')),
     sixpack=my_sixpack,
     ra=source_RA, dec=source_Dec)
 
  self.setNodeScope(ns)
  self.setFileName(infile_name)


 # moves the punit (if it is a point) given
 # by the 'pname' to new location given by new RA,Dec
 def move_punit(self,pname,new_ra,new_dec):
   punit=self.getPUnit(pname)
   ns=self.getNodeScope()
   if ns==None:
    print "WARNING: need nodescope to move item", pname
   if punit.getType()==POINT_TYPE and ns!=None:
    # remember original location for undo()
    old_ra=punit.sp.getRA()
    old_dec=punit.sp.getDec()
    self.__undo={'action':'move_punit','pname':pname\
       ,'old_ra':old_ra,'old_dec':old_dec}
    punit.change_location(new_ra,new_dec,ns)

 # perform a linear transform on all sources
 # such that v_new=A v + b
 # where v_new is the 2x1 vector of new coordinates in radians.
 # A : 2x2 matrix
 # b : 2x1 vector
 # if patches are present, effect is undefined
 def linear_transform(self,A,b):
   ns=self.getNodeScope()
   if ns==None:
    print "WARNING: need nodescope to perform transform:",A,b
    return
   self.__undo=None # cannot undo this
   # try to create a progress window if under GUI mode
   if isinstance(qApp,QApplication):
    lpb = QProgressDialog("Updating MeqParms", "Close", len(self.p_table), self.__win, "progress", 1)
    lpb.setCaption("Please Wait")
    lpb.setMinimumDuration(0)
    lpb.show()
    i=0

   for pname in self.p_table.keys():
    pu=self.p_table[pname]
    old_ra=pu.sp.getRA()
    old_dec=pu.sp.getDec()
    # calculate new coords
    new_ra=A[0][0]*old_ra+A[0][1]*old_dec+b[0]
    new_dec=A[1][0]*old_ra+A[1][1]*old_dec+b[1]
    pu.change_location(new_ra,new_dec,ns)
    # update progress bar
    if isinstance(qApp,QApplication):
     lpb.setProgress(i)
     qApp.processEvents()
     i=i+1

   if isinstance(qApp,QApplication):
     lpb.cancel()
     del lpb
 


 # read in a saved .lsm file given by 'filename'
 # and merge the sources included in it to this one.
 # if we find sources with duplicate names, ignore them
 def merge(self,filename,ns=None):
  try:
   f=open(filename,'rb') 
   p=pickle.Unpickler(f)
   tmpl=LSM()
   tmpl=p.load()

   # recreate the sixpacks
   if tmpl.__root!=None:
    if ns==None:
     ns=self.__ns
    my_dict=pickle.loads(tmpl.__root)
    my_dict=reconstruct(my_dict,ns)
   else:
     tmpl.__root=self.__root
   
   # reconstruct PUnits and Sixpacks if possible
   for sname in tmpl.p_table.keys(): 
    if not self.p_table.has_key(sname):
       punit=tmpl.p_table[sname]
       punit.setLSM(self)
       # now create the sixpack
       tmp_dict=punit.getSixpack()
       #print tmp_dict
       if tmp_dict.has_key('patchroot'):
           my_sp=TDL_Sixpack.Sixpack(label=tmp_dict['label'],\
            ns=self.__ns, root=self.__ns[tmp_dict['patchroot']])
       else: 
       # NOTE: do not give the nodescope because then it tries to
       # compose, but the tree is already composed
          my_sp=TDL_Sixpack.Sixpack(label=tmp_dict['label'],\
            ra=cname_node_stub(self.__ns,tmp_dict['ra']),\
            dec=cname_node_stub(self.__ns,tmp_dict['dec']),\
            stokesI=cname_node_stub(self.__ns,tmp_dict['I']),\
            stokesQ=cname_node_stub(self.__ns,tmp_dict['Q']),\
            stokesU=cname_node_stub(self.__ns,tmp_dict['U']),\
            stokesV=cname_node_stub(self.__ns,tmp_dict['V']))
       # set the root node
       my_sp=my_sp.clone(sixpack=self.__ns[tmp_dict['pointroot']],ns=self.__ns)
       punit.setSP(my_sp)
       # recreate ParmSet for this sixpack
       punit.setParmSet(tmp_dict['ParmSet'],self.__ns)
       # set the root
       punit.sp.setRoot(my_sp.sixpack())
       # add the new PUnit to self
       self.insertPUnit(punit)
    else:
     print "WARNING: PUnit %s already found. Ignoring"%sname

   # reconstruct source table too...
   for sname in tmpl.s_table.keys():
    if not self.s_table.has_key(sname):
     # add source to source table
     self.s_table[sname]=Source(sname)
   f.close()

  except IOError:
   print "file %s cannot be opened, load failed" % filename 
  # next step: Load the MeqTrees if possible 
  if self.mqs != None:
   pass



 # build the LSM from a NewStar .MDL model file
 def build_from_newstar(self,infile_name,ns,verbose=1):
    from Timba.Contrib.JEN import MG_JEN_Sixpack

    ff=open(infile_name,mode="rb")
    #### read header -- 512 bytes
    gfh=numarray.fromfile(ff,'b',(512,1))
    gfh=gfh.flat
    ## type
    ftype=gfh[0:4].tostring()
    ## length
    fhlen=struct.unpack('i',gfh[4:8])
    fhlen=fhlen[0]
    ### version
    fver=struct.unpack('i',gfh[5:9])
    fver=fver[0]
    ### creation date
    crdate=gfh[12:23].tostring()
    ### creation time
    crtime=gfh[23:28].tostring()
    ### revision date
    rrdate=gfh[28:39].tostring()
    ### revision time
    rrtime=gfh[39:44].tostring()
    ### revision count
    rcount=struct.unpack('i',gfh[44:48])
    rcount=rcount[0]
    #### node name
    nname=gfh[48:128].tostring()

    ### the remaining info is not needed

    print "%s: read header type=%s, length=%d, version=%d, created=%s@%s, updated=%s@%s x %d, node name=%s"%(infile_name,ftype,fhlen,fver,crdate,crtime,rrdate,rrtime,rcount,nname)

    ####### Model Header -- 64 bytes 
    mdh=numarray.fromfile(ff,'b',(64,1))
    mdh=mdh.flat 

    ### Max. # of lines in model or disk version
    maxlin=struct.unpack('i',mdh[12:16])
    maxlin=maxlin[0]

    ### pointer to model ???
    modptr=struct.unpack('i',mdh[16:20])
    modptr=modptr[0]

    #### no of sources in model
    nsources=struct.unpack('i',mdh[20:24])
    nsources=nsources[0]

    ### model type(0: no ra,dec, 1=app, 2=epoch)
    mtype=struct.unpack('i',mdh[24:28])
    mtype=mtype[0]

    ### Epoch (e.g. 1950) if TYP=2 (float) : 4 bytes
    mepoch=struct.unpack('f',mdh[28:32])
    mepoch=mepoch[0]

    ###  Model centre RA (circles) : double
    ra0=struct.unpack('d',mdh[32:40])
    ra0=ra0[0]*math.pi*2

    ### Model centre DEC (circles)
    dec0=struct.unpack('d',mdh[40:48])
    dec0=dec0[0]*math.pi*2

    ### Model centre FRQ (MHz)
    freq0=struct.unpack('d',mdh[48:56])
    freq0=freq0[0]*1e6

    ###### the remaining is not needed


    print "%s: read model header lines=%d, pointer=%d, sources=%d, type=%d, epoch=%f RA=%f, DEC=%f (rad) Freq=%f Hz"%(infile_name,maxlin,modptr,nsources,mtype,mepoch,ra0,dec0,freq0)


    ########## Models -- 56 bytes
    for ii in range(0,nsources):
    #for ii in range(0,4):
       mdl=numarray.fromfile(ff,'b',(56,1))
       mdl=mdl.flat

       ### Amplitude (Stokes I)
       sI=struct.unpack('f',mdl[0:4])
       sI=sI[0]*0.005 # convert from WU to Jy (1WU=5mJy)

       ### L offset (mult by 60*60*180/pi to get arcsecs)
       ll=struct.unpack('f',mdl[4:8])
       ll=ll[0]

       ### M offset 
       mm=struct.unpack('f',mdl[8:12])
       mm=mm[0]

       ### Identification
       id=struct.unpack('i',mdl[12:16])
       id=id[0]

       ### Q fraction
       sQ=struct.unpack('f',mdl[16:20])
       sQ=sQ[0]
       ### U fraction
       sU=struct.unpack('f',mdl[20:24])
       sU=sU[0]
       ### V fraction
       sV=struct.unpack('f',mdl[24:28])
       sV=sV[0]

       ### extended source params: in arcsec, so multiply by ???
       eX=struct.unpack('f',mdl[28:32])
       eX=eX[0]
       eY=struct.unpack('f',mdl[32:36])
       eY=eY[0]
       eP=struct.unpack('f',mdl[36:40])
       eP=eP[0]

       ## the procedure is NMOEXT in nscan/nmoext.for
       if eP==0 and eX==eY:
         r0=0
       else:
         r0=0.5*(360/math.pi)*math.atan2(-eP,eY-eX)
       r1=math.sqrt(eP*eP+(eX-eY)*(eX-eY))
       r2=eX+eY
       
       # the real stuff
       # ex,eY (arcsec) (major,minor axes),  eP (deg) position angle
       #eX=math.sqrt(abs(0.5*(r2+r1)))*3600*360/math.pi
       #eY=math.sqrt(abs(0.5*(r2-r1)))*3600*360/math.pi
       #eP=r0/2
       # use radians directly
       eX=math.sqrt(abs(0.5*(r2+r1)))
       eY=math.sqrt(abs(0.5*(r2-r1)))
       eP=r0/(2*360)*math.pi

       #print id,r0,r1,r2,eX,eY,eP

       ### spectral index
       SI=struct.unpack('f',mdl[40:44])
       SI=SI[0]
       ### rotation measure
       RM=struct.unpack('f',mdl[44:48])
       RM=RM[0]

       ###### the remaining is not needed

       #print ii,id,ll,mm,sI,sQ,sU,sV,eX,eY,eP,SI,RM

       s=Source('NEWS'+str(id), major=eX, minor=eY, pangle=eP)
       (source_RA,source_Dec)=lm_to_radec(ra0,dec0,ll,mm)

       #print ii,id,ll,mm,source_RA,source_Dec
       if SI==0 and sQ==0 and sU==0 and sV==0 and RM==0:
        my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=freq0,RA=source_RA, Dec=source_Dec,trace=0)
       else:
        my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=freq0,RA=source_RA, Dec=source_Dec,SI=SI,Qpct=sQ, Upct=sU, Vpct=sV,RM=RM,trace=0)
       # first compose the sixpack before giving it to the LSM
       my_sixpack.sixpack(ns)
       self.add_source(s,brightness=sI,
                sixpack=my_sixpack,
                ra=source_RA, dec=source_Dec)
 
    ff.close()
    self.setNodeScope(ns)
    self.setFileName(infile_name+'.lsm')
    
    if verbose==1:
      print "Read %d sources from NewStar file %s created %s:%s"%(nsources,infile_name,crdate,crtime)


 ## build from a text file of clean components
 ## format:
 ## RA(deg) DEC(dec) sI sQ sU sV
 def build_from_complist(self,infile_name,ns):
  from Timba.Contrib.JEN import MG_JEN_Sixpack

  infile=open(infile_name,'r')
  all=infile.readlines()
  infile.close()

  # regexp pattern
  pp=re.compile(r"""
   ^(?P<col1>\d+(\.\d+)?)   # RA angle - degrees 
   \s*             # skip white space
   (?P<col2>\d+(\.\d+)?)   # Dec angle - degrees 
   \s*             # skip white space
   (?P<col3>(-)?\d+(\.\d+)?)   # Stokes I - Flux
   \s*             # skip white space
   (?P<col4>(-)?\d+(\.\d+)?)   # Stokes Q - Flux
   \s*             # skip white space
   (?P<col5>(-)?\d+(\.\d+)?)   # Stokes U - Flux
   \s*             # skip white space
   (?P<col6>(-)?\d+(\.\d+)?)   # Stokes V - Flux
   [\S\s]+
   \s*$""",re.VERBOSE)
 
  # read each source and insert to LSM
  kk=0
  for eachline in all:
   v=pp.search(eachline)
   if v!=None:
    s=Source("Comp_"+str(kk))
    kk=kk+1
    source_RA=float(v.group('col1'))*math.pi/180.0
    source_Dec=float(v.group('col2'))*math.pi/180.0
    sI=eval(v.group('col3'))
    sQ=eval(v.group('col4'))/(sI*100)
    sU=eval(v.group('col5'))/(sI*100)
    sV=eval(v.group('col6'))/(sI*100)

    #print sI,sQ,sU,sV
    freq0=1e6
    if (sQ==0 and sU==0 and sV==0):
     my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=1e6, RA=source_RA, Dec=source_Dec,trace=0)
    else:
     my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=freq0,RA=source_RA, Dec=source_Dec,Qpct=sQ, Upct=sU, Vpct=sV,trace=0)
   # first compose the sixpack before giving it to the LSM
    SourceRoot=my_sixpack.sixpack(ns)
    self.add_source(s,brightness=eval(v.group('col3')),
     sixpack=my_sixpack,
     ra=source_RA, dec=source_Dec)
 
  self.setNodeScope(ns)
  self.setFileName(infile_name)




 ## build from a text file with extended sources
 ## format:
 ## RA(deg) DEC(dec) sI sQ sU sV SI eX eY eP
 def build_from_extlist(self,infile_name,ns):
  from Timba.Contrib.JEN import MG_JEN_Sixpack
  infile=open(infile_name,'r')
  all=infile.readlines()
  infile.close()

  # regexp pattern
  pp=re.compile(r"""
   ^(?P<col1>[A-Za-z]\w+)  # column 1 name: must start with a character
   \s*             # skip white space
   (?P<col2>(-)?\d+(\.\d+)?)   # RA angle - rad
   \s*             # skip white space
   (?P<col3>(-)?\d+(\.\d+)?)   # Dec angle - rad
   \s*             # skip white space
   (?P<col4>(-)?\d+(\.\d+)?)   # Stokes I - Flux
   \s*             # skip white space
   (?P<col5>(-)?\d+(\.\d+)?)   # Stokes Q - Flux
   \s*             # skip white space
   (?P<col6>(-)?\d+(\.\d+)?)   # Stokes U - Flux
   \s*             # skip white space
   (?P<col7>(-)?\d+(\.\d+)?)   # Stokes V - Flux
   \s*             # skip white space
   (?P<col8>(-)?\d+(\.\d+)?)   # Spectral index 
   \s*             # skip white space
   (?P<col9>[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?)   # ext source major axis: rad
   \s*             # skip white space
   (?P<col10>[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?)   # ext source minor axis: rad
   \s*             # skip white space
   (?P<col11>[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?)   # ext source position angle : rad
   [\S\s]+""",re.VERBOSE)


  kk=0
  for eachline in all:
   v=pp.search(eachline)
   if v!=None:
    source_RA=float(v.group('col2'))
    source_Dec=float(v.group('col3'))
    sI=eval(v.group('col4'))
    sQ=eval(v.group('col5'))/(sI*100)
    sU=eval(v.group('col6'))/(sI*100)
    sV=eval(v.group('col7'))/(sI*100)
    SI=eval(v.group('col8'))

    eX=eval(v.group('col9'))
    eY=eval(v.group('col10'))
    eP=eval(v.group('col11'))

    s=Source(v.group('col1'), major=eX, minor=eY, pangle=eP)

    kk=kk+1

    #print sI,sQ,sU,sV
    freq0=1e6
    if (SI==0 and sQ==0 and sU==0 and sV==0):
     my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=1e6, RA=source_RA, Dec=source_Dec,trace=0)
    elif (SI==0):
     my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=freq0,RA=source_RA, Dec=source_Dec,Qpct=sQ, Upct=sU, Vpct=sV,trace=0)
    else :
     my_sixpack=MG_JEN_Sixpack.newstar_source(ns,punit=s.name,I0=sI, f0=freq0,RA=source_RA, Dec=source_Dec,Qpct=sQ, Upct=sU, Vpct=sV, SI=SI,trace=0)
 
   # first compose the sixpack before giving it to the LSM
    SourceRoot=my_sixpack.sixpack(ns)
    self.add_source(s,brightness=eval(v.group('col4')),
     sixpack=my_sixpack,
     ra=source_RA, dec=source_Dec)
 
  self.setNodeScope(ns)
  self.setFileName(infile_name)




#########################################################################
