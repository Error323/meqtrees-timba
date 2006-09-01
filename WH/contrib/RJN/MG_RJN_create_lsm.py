script_name = 'MG_RJN_LSM.py'

# Short description:
#   First try at generating a LSM and connecting Point and Patch P-Units

# Keywords: LSM


# History:
# - 12 Sep 2005: creation
# - 26 Oct 2005: adaptation from /SBY/MG_LSM_test.py

# Copyright: The MeqTree Foundation 

#================================================================================
# Import of Python modules:

from Timba import utils
_dbg = utils.verbosity(0, name='LSM_Test')
_dprint = _dbg.dprint                    # use: _dprint(2, "abc")
_dprintf = _dbg.dprintf                  # use: _dprintf(2, "a = %d", a)
# run the script with: -dtutorial=3
# level 0 is always printed


from Timba.TDL import *
from Timba.TDL import Settings
from Timba.Meq import meq
from Timba.LSM.LSM import *
from Timba.LSM.LSM_GUI import *

from Timba.Contrib.RJN import RJN_sixpack_343

from random import *
# to force caching put 100
Settings.forest_state.cache_policy = 100


# Create Empty LSM - global
lsm=LSM()
#================================================================================
# Tree definition routine (may be executed from the browser):
# To be used as example, for experimentation, and automatic testing.
#================================================================================

def _define_forest (ns):
 global lsm
 home_dir = os.environ['HOME']
 infile_name = home_dir + '/Timba/WH/contrib/RJN/3C343_nvss_large.txt'
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
 
 linecount=0
 # read each source and insert to LSM
 for eachline in all:
  v=pp.search(eachline)
  if v!=None:
   linecount+=1
   #print v.group('col2'), v.group('col12')
   s=Source(v.group('col2'))
   source_RA=float(v.group('col3'))+(float(v.group('col5'))/60.0+float(v.group('col4')))/60.0
   source_RA*=math.pi/12.0
   source_Dec=float(v.group('col7'))+(float(v.group('col9'))/60.0+float(v.group('col8')))/60.0
   source_Dec*=math.pi/180.0

#   my_sixpack=MG_JEN_Sixpack.newstar_source(ns,name=s.name,I0=eval(v.group('col12')), SI=[random()],f0=1e6,RA=source_RA, Dec=source_Dec,trace=0)
   
   sisif = math.log10( eval(v.group('col12')) );
   qin = 0.0;
   uin = 0.0;
   vin = 0.0;

   my_sixpack = RJN_sixpack_343.make_sixpack(srcname=s.name,
                                      RA = source_RA,
                                      Dec = source_Dec,
                                      ISIF0 = sisif,
                                      Qpct = qin,
                                      Upct = uin,
                                      Vpct = vin,
                                      ns=ns);

   # first compose the sixpack before giving it to the LSM
   SourceRoot=my_sixpack.sixpack(ns)
   my_sixpack.display()
   lsm.add_source(s,brightness=eval(v.group('col12')),
     sixpack=my_sixpack,
     ra=source_RA, dec=source_Dec)
 
 print "Inserted %d sources" % linecount 
 #remember node scope
 lsm.setNodeScope(ns)

########################################################################





#================================================================================
# Optional: Importable function(s): To be imported into user scripts.
#================================================================================





#********************************************************************************
# Initialisation and testing routines
# NB: this section should always be at the end of the script
#********************************************************************************


#-------------------------------------------------------------------------
# Meqforest execution routine (may be called from the browser):
# The 'mqs' argument is a meqserver proxy object.

def _test_forest (mqs, parent):
 global lsm
 #display LSM within MeqBrowser
 #l.display()
 # set the MQS proxy of LSM
 lsm.setMQS(mqs)

 

 f0 = 1200e6
 f1 = 1600e6
 t0 = 0.0
 t1 = 1.0
 nfreq = 3
 ntime = 2
 # create cells
 freqtime_domain = meq.domain(startfreq=f0, endfreq=f1, starttime=t0, endtime=t1);
 cells =meq.cells(domain=freqtime_domain, num_freq=nfreq,  num_time=ntime);
 # set the cells to LSM
 lsm.setCells(cells)
 # query the MeqTrees using these cells
 lsm.updateCells()
 # display results
 lsm.display()

##############################################################
#### test routine to query the LSM and get some Sixpacks from   
#### PUnits
def _tdl_job_query_punits(mqs, parent):
 global lsm
 # obtain the punit list of the 3 brightest ones
 plist=lsm.queryLSM(count=3)
 for pu in plist:
  my_sp=pu.getSP()
  my_sp.display()

#####################################################################
#-------------------------------------------------------------------------
# Test routine to check the tree for consistency in the absence of a server

if __name__ == '__main__':
  print '\n*******************\n** Local test of:',script_name,':\n'
  ns=NodeScope()
  _define_forest(ns)
  ns.Resolve()
  print "Added %d nodes" % len(ns.AllNodes())
  #display LSM without MeqBrowser
  # create cell
  freqtime_domain = meq.domain(10,1000,0,1);
  cells =meq.cells(domain=freqtime_domain, num_freq=2,  num_time=3);
  lsm.setCells(cells)
  lsm.display(app='create')
#********************************************************************************
#********************************************************************************




