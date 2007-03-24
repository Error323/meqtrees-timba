# JEN_nodenames.py:

# Demonstrates the following MeqTree features:
# - The various ways that node names can be defined
# - Including qualifiers



 
#********************************************************************************
# Initialisation:
#********************************************************************************

from Timba.TDL import *
from Timba.Meq import meq

import Meow

Settings.forest_state.cache_policy = 100
Settings.forest_state.bookmarks = []



#********************************************************************************
# The function under the 'blue button':
#********************************************************************************

def _define_forest (ns, **kwargs):
   """Definition of a 'forest' of one or more trees"""

   # Organise in groups (cc) of related nodes.
   # These are bundled by supplying the cc as children to a MeqComposer node.
   # Bundle the groups in the same way into a child-list (gg):

   gg = []

   #--------------------------------------------------------------------------
   group = 'user_specified_name'
   cc = [
      ns.xxx << 1.0,
      ns['yyy'] << 1.0,
      ]
   gg.append(ns[group] << Meq.Composer(children=cc))

   #--------------------------------------------------------------------------
   # Automatic generation of node-names:
   group = 'automatic_name'
   x = ns.x << 1.0
   y = ns.y << -1.0
   cc = [
      ns << 1.0,
      ns << -1.0,
      ns << x+y,
      ns << Meq.Cos(x+y),
      ns << x-2/y,
      ]
   gg.append(ns[group] << Meq.Composer(children=cc))


   #--------------------------------------------------------------------------
   # Qualifiers:
   group = 'name_qualifiers'
   sp1 = ns.station_phase(s=3) << 2.2
   sp2 = ns.station_phase(s=4) << -5.1
   cc = [sp1,sp2,
         ns.xxx('a')(2)(b='c')('d','e') << 1,
         ns.yyy('a','b',-3.5,'d',a='e') << 1,
         ns.ifr_phase(s1=3, s2=4) << Meq.Subtract(sp1,sp2),
         ns.qmerge.qmerge(sp1,sp2) << Meq.Subtract(sp1,sp2),
         ns.qadd(q=8).qadd(sp1,sp2) << Meq.Subtract(sp1,sp2),
         ns.list('a','b',7) << 1.0,
         ns.kwargs(a='a',b='b',c=7) << 1.0,
         ns['list+kwargs']('a','b',a='a',b='b',c=7) << 1.0,
         ns.dict(**dict(a='a',b='b',c=7)) << 1.0,
         ns.dict2(dict(a='a',b='b',c=7)) << 1.0,
         ]
   gg.append(ns[group] << Meq.Composer(children=cc))


   #--------------------------------------------------------------------------
   # The use of unqualified nodes:
   group = 'unqualified'
   unqual = ns.unqual                   # create an (uninitialized) node-stub
   cc = []
   for s in range(3):
      cc.append(unqual(s) << 1)         # initialize a node from the node-stub 

   # Access existing nodes in the same way:
   for s in range(3):
      cc.append(ns.unqual(s))           #  
   # cc.append(ns.unqual)                 #  

   cc.append(ns.unqual << Meq.Parm(2))  # NB: unqual is NOT a node, so can be defined again  

   gg.append(ns[group] << Meq.Composer(children=cc))

   #--------------------------------------------------------------------------
   # Creating node families by successive qualification:
   group = 'family'
   node = ns.ancestor << 1              # create an (uninitialized) node-stub
   cc = []
   cc.append(node('q1') << 1)
   cc.append(node('q2') << 1)
   cc.append(node('q1')('q11') << 1)
   gg.append(ns[group] << Meq.Composer(children=cc))


   #--------------------------------------------------------------------------
   # The use of the Meow QualScope object:
   group = 'QualScope'
   cc = []
   ns1 = Meow.QualScope(ns, quals=['q1','q2'], kwquals=dict(q2='kw2'))
   name = 'ns1'
   # cc.append(ns1 << 1)                # temporary problem
   cc.append(ns1[name] << 1)
   cc.append(ns1[name](*[1,2]) << 1)
   cc.append(ns1[name]([1,2]) << 1)
   cc.append(ns1[name](1)(2) << 1)
   cc.append(ns1[name](s1=1)(s2=2) << 1)

   # The QualScope is cumulative, of course. Note the merging rules for quals and kwquals.
   ns11 = Meow.QualScope(ns1, quals=['q3'], kwquals=dict(q4='kw4'))
   cc.append(ns11['ns11'] << 1)
   ns12 = Meow.QualScope(ns1, quals=['q2'])
   cc.append(ns12['ns12'] << 1)
   ns13 = Meow.QualScope(ns1, kwquals=dict(q4='kw44'))
   cc.append(ns13['ns13'] << 1)
   ns14 = Meow.QualScope(ns1, kwquals=dict(q2='kw22'))
   cc.append(ns14['ns14'] << 1)

   gg.append(ns[group] << Meq.Composer(children=cc))


   #--------------------------------------------------------------------------
   # The use of Subscope:
   group = 'Subscope'
   nsub1 = ns.Subscope('ssc')
   nsub2 = ns.Subscope('ssc',['a','b'])
   cc = [
      nsub1.zzz << 1.0,
      nsub1.list('a','b',7) << 1.0,
      nsub2.qual_list << 1.0,
      ]
   gg.append(ns[group] << Meq.Composer(children=cc))


   #--------------------------------------------------------------------------
   # Node-name conflict (two nodes with the same (qualified) name):
   group = 'name_conflict'
   name = 'name'
   cc = [
      ns[name] << 1.0,             # define a node
      ns[name]('qual') << 2.0,     # no conflict because different total name
      ns[name] << 1.0,             # no conflict because same value (rather clever)
      nsub1[name] << 1.0           # no conflict because different scope 
      # ns[name] << 2.0,             # conflict because different values
      ]
   gg.append(ns[group] << Meq.Composer(children=cc))

   # The root node of the tree can have any name, but in this example it
   # should be named 'result', because this name is used in the default
   # execute command (see below), and the bookmark.
   result = ns.result << Meq.Composer(children=gg)

   # Finished:
   return True






#********************************************************************************
# The function under the TDL Exec button:
#********************************************************************************

def _tdl_job_execute (mqs, parent):
    """Execute the forest, starting at the named node"""
    domain = meq.domain(1,10,1,10)                            # (f1,f2,t1,t2)
    cells = meq.cells(domain, num_freq=10, num_time=11)
    request = meq.request(cells, rqtype='ev')
    result = mqs.meq('Node.Execute',record(name='result', request=request))
    return result
       

#********************************************************************************
# Comments:
#********************************************************************************

# - All the information is in the Trees panel:
#   - Expand the various (groups of) nodes
#   - Check in _define_forest() how their names were generated

#********************************************************************************
#********************************************************************************

#=======================================================================
# Test program (standalone):
# This is a useful thing to have at the bottom of the script, it allows
# us to check the tree for consistency simply by running 'python script'
#=======================================================================


if __name__ == '__main__':
  ns = NodeScope();
  _define_forest(ns);
  ns.Resolve();  
  print len(ns.AllNodes()),'nodes defined';



