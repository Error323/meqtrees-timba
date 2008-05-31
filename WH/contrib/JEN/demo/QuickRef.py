
# file: ../JEN/demo/QuickRef.py:
#
# Author: J.E.Noordam
#
# Short description:
#    A quick reference to all MeqTree nodes and subtrees.
#    It makes actual nodes, and prints help etc

#
# History:
#   - 23 may 2008: creation
#
# Remarks:
#
#   - Middle-clicking a node in the browser could display its quickref_help,
#     just like right-click option in the various plotter(s)....
#     Tony already has a popup uption for selecting from multiple vellsets,
#     which includes an expansion tree. The quickref_help popup needs the same.  
#   - NB: Left-clicking a node displays the state record, except the Composer...
#         It would be nice if it were easier to invoke the relevant plotter...
#         (at this moment it takes to many actions, and the new display is confusing)
#   - Can we plot the result of each request in a sequence while it is running....?

#   - TDLCompileMenu should have tick-box option (just like the TDLOption)
#     Or should I read the manual better?
#   - Meow.Bookmarks needs a folder option....
#   - Is there a way to attach fields like a quickref_help record to the
#     state record (initrec?) of an existing node?
#
# Description:
#


 
#********************************************************************************
# Initialisation:
#********************************************************************************

#
#% $Id$ 
#
#
# Copyright (C) 2002-2007
# The MeqTree Foundation & 
# ASTRON (Netherlands Foundation for Research in Astronomy)
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
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
# along with this program; if not, see <http://www.gnu.org/licenses/>,
# or write to the Free Software Foundation, Inc., 
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from Timba.TDL import *
from Timba.Meq import meq

Settings.forest_state.cache_policy = 100
Settings.forest_state.bookmarks = []

import Meow.Bookmarks
from Timba.Contrib.JEN.util import JEN_bookmarks

import math
import time
# import random


#********************************************************************************
# The function under the 'blue button':
#********************************************************************************

# NB: This QuickRef menu is included automatically in the menus of the QR_... modules,
#     since they import this QuickRef module for its functions....

TDLCompileMenu("QuickRef Categories:",
               TDLOption('opt_general',"general MeqTree",False),
               TDLOption('opt_MeqBrowser',"MeqBrowser features",False),
               TDLOption('opt_MeqNodes',"Available MeqNodes",True),
               # TDLOption('opt_pynodes',"General PyNodes",False),
               # TDLCompileMenu('Submenu:',
               #                TDLOption('first_item','1',True),
               #                TDLOption('second_item','2',True)
               #                ),
               # TDLOption('opt_visualization',"JEN", False)
               )
  
#-------------------------------------------------------------------------------

def standard_child_nodes (ns):
   """Helper function to make some child nodes with standard names,
   to be used in the various nodes""" 
   bb = []
   bb.append(ns << Meq.Constant(2.3))
   bb.append(ns << 2.4)
   bb.append(ns.x << Meq.Freq())
   bb.append(ns.y << Meq.Time())
   bb.append(ns.cxx << Meq.ToComplex(ns.x,ns.x))
   bb.append(ns.cyy << Meq.ToComplex(ns.y,ns.y))
   bb.append(ns.cxy << Meq.ToComplex(ns.x,ns.y))
   bb.append(ns.cyx << Meq.ToComplex(ns.y,ns.x))
   bb.append(ns.f << Meq.Freq())
   bb.append(ns.t << Meq.Time())
   bb.append(ns.ft << Meq.Multiply(ns.f,ns.t))
   bb.append(ns['f+t'] << Meq.Add(ns.f,ns.t))
   bb.append(ns.cff << Meq.ToComplex(ns.f,ns.f))
   bb.append(ns.ctt << Meq.ToComplex(ns.t,ns.t))
   bb.append(ns.cft << Meq.ToComplex(ns.f,ns.t))
   bb.append(ns.ctf << Meq.ToComplex(ns.t,ns.f))
   scn = ns['standard_child_nodes'] << Meq.Composer(children=bb)
   return scn

#-------------------------------------------------------------------------------

def _define_forest (ns, **kwargs):
   """Definition of a 'forest' of one or more trees"""

   trace = False
   # trace = True

   # Make some standard child-nodes with standard names
   # These are used in the various bundles below.
   # They are bundles to avoid browser clutter.
   scnodes = standard_child_nodes(ns)

   if trace:
      print '\n** Start of QuickRef _define_forest()'

   # Make bundles of (bundles of) categories of nodes/subtrees:
   rootnodename = 'QuickRef'                # The name of the node to be executed...
   path = rootnodename                      # Root of the path-string
   rider = CollatedHelpRecord()             # Helper class
   cc = []
   cc = [scnodes]
   if opt_MeqNodes:                         # specified in compile-options
      import QR_MeqNodes                    # import the relevant module
      cc.append(QR_MeqNodes.MeqNodes(ns, path, rider=rider))

   # Make the outer bundle (of node bundles):
   bundle_help = """
   The QuickRef module offers a quick reference to MeqTrees.
   When used in the meqbrowser, it generates example subtrees
   for user-selected categories, which can be executed (with
   user-defined request domains) to inspect the result.
   Lots of bookmarks are generated for easy inspection.
   In addition, the relevant section of the hierarchical
   help-string can be inspected at each level, by displaying
   any node in the tree with the Record Browser. Look for
   the field 'quickref_help'.
   QuickRef gets its information from an arbitrary number
   of contributing QR_... modules. These may be generated by
   any MeqTrees contributor, following a number of simple rules.
   (Look for instance at the module QR_MeqNodes.py)
   """
   bundle (ns, path, nodes=cc, help=bundle_help, rider=rider)

   if trace:
      rider.show('_define_forest()')

   # The run-time options may be used to change the request domain:
   TDLRuntimeMenu("parameters of the requested domain:",
                  TDLOption('runopt_nfreq',"nr of cells in freq direction",
                            [20,21,50,1,100,1000], more=int),
                  TDLOption('runopt_fmin',"min freq (domain/cell edge)",
                            [0.1,1.0,3.0,0.01,0.0,-1.0,-math.pi,-2*math.pi,100e6,1400e6], more=float),
                  TDLOption('runopt_fmax',"max freq (domain/cell edge)",
                            [2.0,1.0,math.pi,2*math.pi,110e6,200e6,1500e6], more=float),
                  TDLOption('runopt_separator',"",['']),
                  TDLOption('runopt_ntime',"nr of cells in time direction",
                            [1,20,21,50,100,1000], more=int),
                  TDLOption('runopt_tmin',"min time (domain/cell edge)",
                            [0.0,-1.0,-10.0], more=float),
                  TDLOption('runopt_tmax',"max time (domain/cell edge)",
                            [1.0,0.1,3.0,10.0,100.0,1000.0], more=float),
                  TDLOption('runopt_separator',"",['']),
                  TDLOption('runopt_seq_ntime',"nr of steps in time-sequence",
                            [1,5,10,20,100], more=int),
                  TDLOption('runopt_seq_tstep',"time-step (fraction of domain)",
                            [0.5,0.1,0.9,1.0,2.0,10.0,-0.5,-1.0], more=float),
                  TDLOption('runopt_separator',"",['']),
                  TDLOption('runopt_seq_nfreq',"nr of steps in freq-sequence",
                            [1,5,10,20,100], more=int),
                  TDLOption('runopt_seq_fstep',"freq-step (fraction of domain)",
                            [0.5,0.1,0.9,1.0,2.0,10.0,-0.5,-1.0], more=float),
                  TDLOption('runopt_separator',"",['']),
                  )

   # Finished:
   if trace:
      print '** end of QuickRef _define_forest()/n'
   return True
   


#********************************************************************************
# The function under the TDL Exec button:
#********************************************************************************

request_counter = 0
def make_request (cells, rqtype=None):
   """Make a request"""
   global request_counter
   request_counter += 1
   rqid = meq.requestid(request_counter)
   if isinstance(rqtype,str):
      # e.g. rqtype='ev' (for sequences, when the domain has changed)....
      return meq.request(cells, rqtype=rqtype)
      # return meq.request(cells, rqtype=rqtype, rqid=rqid)
   else:
      return meq.request(cells, rqid=rqid)

#----------------------------------------------------------------------------

def _tdl_job_execute_1D (mqs, parent):
   """Execute the forest with a 1D (freq) domain, starting at the named node.
   """
   domain = meq.domain(runopt_fmin,runopt_fmax,
                       runopt_tmin,runopt_tmax)       
   cells = meq.cells(domain, num_freq=runopt_nfreq, num_time=1)
   request = make_request(cells)
   result = mqs.meq('Node.Execute',record(name='QuickRef', request=request))
   return result

def _tdl_job_execute_2D (mqs, parent):
   """Execute the forest with a 2D domain, starting at the named node.
   """
   domain = meq.domain(runopt_fmin,runopt_fmax,
                       runopt_tmin,runopt_tmax)       
   cells = meq.cells(domain, num_freq=runopt_nfreq, num_time=runopt_ntime)
   request = make_request(cells)
   result = mqs.meq('Node.Execute',record(name='QuickRef', request=request))
   return result


def _tdl_job_sequence (mqs, parent):
   """Execute a sequence, moving the 2D domain.
   """
   for ifreq in range(runopt_seq_nfreq):
      foffset = (runopt_fmax - runopt_fmin)*ifreq*runopt_seq_fstep
      print '** ifreq =',ifreq,' foffset =',foffset
      for itime in range(runopt_seq_ntime):
         toffset = (runopt_tmax - runopt_tmin)*itime*runopt_seq_tstep
         print '   - itime =',itime,' toffset =',toffset
         domain = meq.domain(runopt_fmin+foffset,runopt_fmax+foffset,
                             runopt_tmin+toffset,runopt_tmax+toffset)       
         cells = meq.cells(domain, num_freq=runopt_nfreq, num_time=runopt_ntime)
         request = make_request(cells)
         result = mqs.meq('Node.Execute',record(name='QuickRef', request=request))
         # NB: It executes the entire sequence before showing any plots!
         # The things I have tried to make it display each result:
         # request = make_request(cells, rqtype='ev')
         # result = mqs.meq('Node.Execute',record(name='QuickRef', request=request), wait=True)
         # time.sleep(1)
   return result


if False:
   def _tdl_job_print_selected_help (mqs, parent):
      """Print the help-text of the selected categories"""
      print '\n** Not yet implemented **\n'
      return True

   def _tdl_job_popup_selected_help (mqs, parent):
      """Show the help-text of the selected categories"""
      print '\n** Not yet implemented **\n'
      return True







#================================================================================
# Helper functions (called externally from QR_... modules):
#================================================================================


def MeqNode (ns, path,
             meqclass=None, name=None,
             # quals=None, kwquals=None,
             children=None, help=None, rider=None,
             node=None,
             trace=False, **kwargs):
   """Define (make) the specified node an an organised way.
   NB: This function is called from all QR_... modules!
   """

   # Condition the help-string and update the CollatedHelpRecord (rider): 
   # First replace the dots(.) in the node-name (name): They cause trouble
   # in the browser (and elsewhere?)
   qname = str(name)
   qname = qname.replace('.',',')
   if isinstance(help, str):
      qhelp = help.split('\n')
      # print qname,qhelp[0]
      qhelp[0] = str(qname)+': '+str(qhelp[0])
   else:
      qhelp = str(qname)+': '+str(help)
   kwargs['quickref_help'] = qhelp

   if rider:
      rider.add(add2path(path,name), qhelp)

   if is_node(node):
      # The node already exists. Just attach the help-string....
      # node = ns << Meq.Identity(node, quickref_help=qhelp)         # confusing...
      # NB: Is there a way to attach it to the existing node itself...?
      # node.initrec.quickref_help = qhelp               # error....
      pass
      
   elif not isinstance(children,(list,tuple)):           # No children specified: 
      if isinstance(name,str):
         # node = ns[name] << getattr(Meq,meqclass)(quickref_help=qhelp, **kwargs)
         node = ns[name] << getattr(Meq,meqclass)(**kwargs)
      else:
         # node = ns << getattr(Meq,meqclass)(quickref_help=qhelp, **kwargs)
         node = ns << getattr(Meq,meqclass)(**kwargs)

   else:                           
      # Some nodes (Matrix22, ConjugateTranspose) insist on non-keyword args....!
      if isinstance(name,str):
         # node = ns[name] << getattr(Meq,meqclass)(children=children,
         node = ns[name] << getattr(Meq,meqclass)(*children,
                                                  # quickref_help=qhelp,
                                                  **kwargs)
      else:
         # node = ns << getattr(Meq,meqclass)(children=children,
         node = ns << getattr(Meq,meqclass)(*children,
                                            # quickref_help=qhelp,
                                            **kwargs)
   if trace:
      nc = None
      if isinstance(children,(list,tuple)):
         nc = len(children)
      print '- QR.MeqNode():',path,meqclass,name,'(nc=',nc,') ->',str(node)
   return node


#-------------------------------------------------------------------------------

def bundle (ns, path,
            nodes=None, help=None, rider=None,
            bookmark=True, viewer="Result Plotter",
            trace=False):
   """Make a single parent node, with the given nodes as children.
   Make bookmarks if required, and collate the help-strings.
   NB: This function is called from all QR_... modules!
   """

   # The name of the bundle (node, page, folder) is the last
   # part of the path string, i.e. after the last dot ('.')
   ss = path.split('.')
   name = ss[len(ss)-1]
      
   # Condition the help-string and update the CollatedHelpRecord (rider):
   if isinstance(help, str):
      qhelp = help.split('\n')
      qhelp[0] = name+': '+qhelp[0]
   else:
      qhelp = name+': '+str(help)
      
   if rider:
      rider.add(path, qhelp)                    # add qhelp to the rest
      # The relevant subset of help is attached to this bundle node:
      qhelp = rider.subrec(path, trace=trace)   # get the relevant sub-record
      # qhelp = rider.cleanup(qhelp)              # clean it up (use a copy!!)


   if True:
      # NB: When a Composer node is left-clicked in the browser,
      # it plots an inspector, not its state record (with help...)   
      parent = ns[name] << Meq.Composer(children=nodes,
                                        quickref_help=qhelp)
   else:
      # Alternative: ReqSeq?
      parent = ns[name] << Meq.Add(children=nodes,
                                   quickref_help=qhelp)

   # Make a meqbrowser bookmark for this bundle, if required:
   if bookmark:
      [page, folder] = rider.bookmark(path, trace=trace)
      if folder or page:
         if True:
            # Temporary, until Meow folder problem (?) is solved....
            # JEN_bookmarks.create(nodes, name, page=page, folder=folder, viewer=viewer)
            JEN_bookmarks.create(nodes, name=page, folder=folder, viewer=viewer)
         else:
            # NB: There does not seem to be a Meow way to assign a folder....
            bookpage = Meow.Bookmarks.Page(name, folder=bookfolder)
            for node in nodes:
               bookpage.add(node, viewer=viewer)

   if trace:
      print '** QR.bundle():',path,name,'->',str(parent),'\n'
   return parent

#-------------------------------------------------------------------------------

def add2path (path, name=None, trace=False):
   """Helper function to form the path to a specific bundle.
   NB: This function is called from all QR_... modules!
   """
   s = str(path)
   if isinstance(name,str):
      s += '.'+str(name)
   if trace:
      print '\n** QR.add2path(',path,name,') ->',s
   return s




#=================================================================================
# Helper Class:
#=================================================================================

class CollatedHelpRecord (object):
   """This object collects and handles the hierarchical set of QuickRef help strings
   into a record. This is controlled by the path, e.g. 'QuickRef.MeqNodes.unops'
   It is used in the functions .MeqNode() and .bundle() in this module, but has
   to be passed (as rider) through all contributing QR_... modules.
   """

   def __init__(self):
      self.clear()
      return None

   def clear (self):
      self._chrec = record(help=None, order=[])
      self._folder = record()
      return None

   def chrec (self):
      return self._chrec

   #---------------------------------------------------------------------

   def bookmark (self, path, trace=False):
      """A little service to determine [page,folder] from path.
      It is part of this class because it initializes each time.
      This is necessary to avoid extra pages/folders.
      """
      ss = path.split('.')
      page = ss[len(ss)-1]                  # the last one, always there
      folder = None
      if len(ss)>3:
         folder = ss[len(ss)-2]
      if folder:
         self._folder.setdefault(folder,0)
         self._folder[folder] += 1
      else:
         if self._folder.has_key(page):
            page = None
      # Finished:
      if trace:
         print '** .bookmark():',len(ss),ss,' page=',page,' folder=',folder
      return [page,folder]

   #---------------------------------------------------------------------

   def add (self, path=None, help=None, rr=None,
            level=0, trace=False):
      """Add a help-item (recursive)"""
      if level==0:
         rr = self._chrec
      if isinstance(path,str):
         path = path.split('.')

      key = path[0]
      if not rr.has_key(key):
         rr.order.append(key)
         rr[key] = record(help=None)
         if len(path)>1:
            rr[key].order = []

      if len(path)>1:                        # recursive
         self.add(path=path[1:], help=help, rr=rr[key],
                  level=level+1, trace=trace)
      else:
         rr[key].help = help                 # may be list of strings...
         if trace:
            prefix = self.prefix(level)
            print '.add():',prefix,key,':',help
      # Finished:
      return None

   #---------------------------------------------------------------------
   
   def prefix (self, level=0):
      """Indentation string"""
      return ' '+(level*'..')+' '

   #---------------------------------------------------------------------

   def show(self, txt=None, rr=None, full=False, key=None, level=0):
      """Show the record (recursive)"""
      if level==0:
         print '\n** CollatedHelpRecord.show(',txt,' full=',full,' rr=',type(rr),'):'
         if rr==None:
            rr = self._chrec
      prefix = self.prefix(level)

      if not rr.has_key('order'):                # has no 'order' key
         for key in rr.keys():
            if isinstance(rr[key], (list,tuple)):
               if len(rr[key])>1:
                  print prefix,key,':',rr[key][0]
                  for s in rr[key][1:]:
                     print prefix,len(key)*' ',s
               else:
                  print prefix,key,':',rr[key]
            else:
               print prefix,key,'(no order):',type(rr[key])

      else:                                      # has 'order' key
         for key in rr.keys():
            if isinstance(rr[key], (list,tuple)):
               if key in ['order']:              # ignore 'order'
                  if full:
                     print prefix,key,':',rr[key]
               elif len(rr[key])>1:
                  print prefix,key,':',rr[key][0]
                  for s in rr[key][1:]:
                     print prefix,len(key)*' ',s
               else:
                  print prefix,key,'(',len(rr[key]),'):',rr[key]
            elif not isinstance(rr[key], (dict,Timba.dmi.record)):
               print prefix,key,'(',type(rr[key]),'??):',rr[key]
               
         for key in rr['order']:
            if isinstance(rr[key], (dict,Timba.dmi.record)):
               self.show(rr=rr[key], key=key, level=level+1, full=full) 
            else:
               print prefix,key,'(',type(rr[key]),'??):',rr[key]

      if level==0:
         print '**\n'
      return None

   #---------------------------------------------------------------------

   def subrec(self, path, rr=None, trace=False):
      """Extract the specified (path) subrecord
      from the given record (if not specified, use self._chrec)
      """
      if trace:
         print '\n** .extract(',path,' rr=',type(rr),'):'
      if rr==None:
         rr = self._chrec

      ss = path.split('.')
      for key in ss:
         if trace:
            print '-',key,ss,rr.keys()
         if not rr.has_key(key):
            s = '** key='+key+' not found in: '+str(ss)
            raise ValueError,s
         else:
            rr = rr[key]
      if trace:
         self.show(txt=path, rr=rr)
      return rr
      
   #---------------------------------------------------------------------

   def cleanup (self, rr=None, level=0, trace=False):
      """Clean up the given record (rr)"""
      if level==0:
         if trace:
            print '\n** .cleanup(rr=',type(rr),'):'
         if rr==None:
            rr = self._chrec
            
      if isinstance(rr, dict):
         if rr.has_key('order'):
            rr.__delitem__('order')                   # remove the order field
            for key in rr.keys():
               if isinstance(rr[key], dict):          # recursive
                  rr[key] = self.cleanup(rr=rr[key], level=level+1)
      # Finished:
      if level==0:
         if trace:
            print '** finished .cleanup() -> rr=',type(rr)
      return rr


#====================================================================================
# Experimental....
#====================================================================================

def nodestub (ns, rootname, *quals, **kwquals):
   """Helper function that forms a unique node-name (incl qualifiers)
   from the given information. It checks for uniqueness by checking whether
   the proposed node has already been initialized in the given nodescope (ns).
   This may be a little unsafe when using unqualified nodes...."""

   # print '\n** help =',nodename.__doc__,'\n'

   trace = False
   trace = True

   # Decode the uniquifying parameter (see below):
   ss = rootname.split('|')
   n = 0
   rootroot = rootname
   if len(ss)==3:                       # assume: <rootroot>|<n>|
      n = int(ss[1])
      rootroot = ss[0]

   if trace:
      s1 = n*'--'
      s1 += ' QR.nodename('+str(rootname)+','+str(quals)+','+str(kwquals)+')'

   # Safety valve:
   if n>10:
      print s1
      raise ValueError,'** max of uniqueness parameter exceeded'

   # Make node-stub:
   stub = ns[rootname]
   if len(quals)>0:
      stub = stub(*quals)
   if len(kwquals)>0:
      stub = stub(**kwquals)


   # Testing:
   if True:
      if n<3:
         ns[stub] << n                        # .....!!
      s1 += ' '+str(ns[stub].initialized())
      s1 += ' '+str(ns[stub.name].initialized())

   if trace:
      print  s1,'  ->',str(stub)
   
   # Check whether the node already exists (i.e. initialized...):
   if ns[stub].initialized():
      # Recursive: Try again with a modified rootname.
      # (using the incremented uniquifying parameter n)
      newname = rootroot+'|'+str(n+1)+'|'
      return nodestub(ns, newname, *quals, **kwquals)

   # Return the unique (!) node-name:
   return stub.name
   



#=====================================================================================
# Standalone test (without the browser):
#=====================================================================================

if __name__ == '__main__':

   print '\n** Start of standalone test of: QuickRef.py:\n' 
   ns = NodeScope()

   if 0:
      rider = CollatedHelpRecord()
      if 0:
         path = 'aa.bb.cc.dd'
         help = 'xxx'
         rider.add(path=path, help=help, trace=True)

   if 0:
      import QR_MeqNodes
      QR_MeqNodes.MeqNodes(ns, 'test', rider=rider)
      rider.show('testing')

      if 0:
         path = 'test.MeqNodes.binops'
         # path = 'test.MeqNodes'
         rr = rider.subrec(path, trace=True)
         rider.show('subrec',rr, full=False)
         rider.show('subrec',rr, full=True)
         if 0:
            print 'before cleanup(): ',type(rr)
            rr = rider.cleanup(rr=rr)
            print 'after cleanup(): ',type(rr)
            rider.show('cleanup',rr, full=True)
            rider.show('cleanup',rr, full=False)
            
   if 0:
      name = nodestub(ns,'xxx',5,-7,c=8,h=9)
      if 1:
         stub = ns[name]
         print '\n',dir(stub)
         print '\n stub = ns[',name,'] ->',str(stub)
         print '- stub.name:',stub.name
         print '- stub.basename:',stub.basename
         print '- stub.classname:',stub.classname
         print '- stub.quals:',stub.quals
         print '- stub.kwquals:',stub.kwquals
         print '- stub.initialized():',stub.initialized()
      if 1:
         node = ns[name] << 3.4
         print '\n node = ns[',name,'] << 3.4   ->',str(node)
         print '- node.name:',node.name
         print '- node.basename:',node.basename
         print '- node.classname:',node.classname
         print '- node.quals:',node.quals
         print '- node.kwquals:',node.kwquals
         print '- node.initialized():',node.initialized()
      
   print '\n** End of standalone test of: QuickRef.py:\n' 

#=====================================================================================



