script_name = 'MG_SBY_dipole_beam.py'
last_changed = '04oct2005'

# Short description:
#   using MXM's compiled funklet to model a linear dipole
#   on top of ground plane.
 
# Keywords: dipole, antenna, compiled funklet

# Copyright: The MeqTree Foundation 

# Full description:
# Implement a horizontal or a vertical dipole far field radiation
# pattern using MeqTrees. The height 'h' above the ground can be changed.
# There are two importable functions that can generated a MeqParm node
# with a compiled funklet to model a horizontal and a vertical dipole. They
# are called  '_create_dipole_beam_h()' and '_create_dipole_beam_v()', 
# respectively.
# Reference:
#  Balanis C.A., "Antenna Theory", 1997

# standard preamble
from Timba.TDL import *
from Timba.Meq import meq
from Timba.Meq import meqds
from numarray import *
# import MXM's code 
from Timba.Contrib.MXM import MG_MXM_functional
# import JEN code for bookmarks
from Timba.Contrib.JEN import MG_JEN_forest_state
from Timba.Contrib.JEN import MG_JEN_exec

import math
# enable cache
Settings.forest_state.cache_policy = 100;

# Make sure our solver root node is not cleaned up
Settings.orphans_are_roots = True;

##########################################################################
# Script control record (may be edited here):

MG = MG_JEN_exec.MG_init('MG_SBY_dipole_beam.py',
                         last_changed='$Date$',
                         trace=False) # If True, produce progress messages  
MG.parm = record(h=0.25, # dipole height from ground plane, in wavelengths
               debug_level=10)    # debug level

##########################################################################

def _define_forest (ns):
  """ We create two horizontal dipoles, perpendicular to one another
      and multiply their Voltage (not Power) beam shapes. The voltage
      beam is taken to be the positive square root of the power beam.
  """;
  # add Azimuth and Elevation axes as the 3rd and 4th axes
  MG_MXM_functional._add_axes_to_forest_state(['A','E']);
  # create the dummy node (needed for the funklet)
  ns.dummy<<Meq.Parm([[0,1],[1,0]],node_groups='Parm');

  # creation of a compiled funklet - using MXM code

  # use the following pair for a vertical dipole
  #par=['p0+p1*x0+p2*x1+p3*x0*x1','p4+p5*x0+p6*x1+p7*x0*x1',\
  #     'p8+p9*x0+p10*x1+p11*x0*x1','p12+p13*x0+p14*x1+p15*x0*x1',\
  #      'p16+p17*x0+p18*x1+p19*x0*x1']
  #coeff=[[1,0,0,0],[1,0,0,0],[1,0,0,0],[1,0,0,0],[1,0,0,0]]

  # use to following pair for a horizontal dipole
  par=['p0+p1*x0+p2*x1+p3*x0*x1','p4+p5*x0+p6*x1+p7*x0*x1',\
       'p8+p9*x0+p10*x1+p11*x0*x1','p12+p13*x0+p14*x1+p15*x0*x1']
  # polynomial coefficients
  coeff=[[1,0,0,0],[1,0,0,0],[1,0,0,0],[1,0,0,0]]

  # value of pi
  pi=str(math.pi)

  # dipole height from ground plane in wavelengths
  # make dipole height above ground=lambda/4 to get peak at top
  h=MG.parm['h']

  print par
  print coeff

  # create XX beam
  x_node=_create_dipole_beam_h(par,coeff,h)
  ns.x<<x_node
  # create bookmark for easy viewing
  MG_JEN_forest_state.bookmark(ns.x, page='main beam (XX)', viewer='Result Plotter')
  MG_JEN_forest_state.bookmark(ns.x, page='All beams', viewer='Result Plotter')

  # create YY beam
  y_node=_create_dipole_beam_h(par,coeff,h,'x2-'+pi+'/2')
  ns.y<<y_node
  # create bookmark for easy viewing
  MG_JEN_forest_state.bookmark(ns.y, page='cross beam (YY)', viewer='Result Plotter')
  MG_JEN_forest_state.bookmark(ns.y, page='All beams', viewer='Result Plotter')

  # create product beam as root
  ns.z<<Meq.Multiply(ns.x,ns.y)
  # create bookmark for easy viewing
  MG_JEN_forest_state.bookmark(ns.z, page='product beam', viewer='Result Plotter')
  MG_JEN_forest_state.bookmark(ns.z, page='All beams', viewer='Result Plotter')

  ns.Resolve()

def _test_forest (mqs,parent):
  """ evaluate beam pattern for the upper hemisphere
      for this create a grid in azimuth(phi) [0,2*pi], pi/2-elevation(theta) [0,pi/2]
  """;
  # run dummy first, to make python know about the extra axes (some magic)
  MG_MXM_functional._dummy(mqs,parent);
  

  request = MG_MXM_functional._make_request(Ndim=4,dom_range=[[0.,1.],[0.,1.],[0.,math.pi*2.0],[0.,math.pi/2.0]],nr_cells=[5,5,40,40]);
  a = mqs.meq('Node.Execute',record(name='z',request=request),wait=True);


#================================================================================
# Importable function(s): The essence of a MeqGraft (MG) script.
# To be imported into user scripts. 
#================================================================================
def _create_dipole_beam_v(tfpoly=['1','1','1','1','1'],coeff=[[1],[1],[1],[1],[1]],h=0.25,x='x2',y='x3'):
  """ Create Vertical Dipole beam:
      The theoretical (power) beam shape is:
      z=(cos(pi/2*cos(x))/sin(x)*sin(2*pi*h*sin(y)))^2;
      where x:azimuth angle
            y:elevation angle (both radians)
            h: dipole height from ground
      we create a voltage beam, using square root of power as the r.m.s.
      voltage, and add polynomials for time,freq as given by {TF}
      z=(cos(pi/2{TF0}cos({TF1}x))/sin({TF2}x)*sin(2*pi*h*{TF3}sin({TF4}y)))
      so we need 5 polynomials, which must be given as tfpoly array.
      The coefficients for these polynomials should be given by coeff array.
      x,y should be given as polynomials of x2 and x3 respectively.
  """
  if len(tfpoly)<5:
   print "Invalid No. of Polynomials, should be 5"
   return None

  h_str=str(h)
  pi=str(math.pi)
  # voltage beam, so do not take ^2
  beamshape='abs(cos('+pi+'/2*('+tfpoly[0]+')*cos(('+tfpoly[1]+')*('+x+')))/sin(('+tfpoly[2]+')*('+x+'))*sin(2*'+pi+'*'+h_str+'*('+tfpoly[3]+')*sin(('+tfpoly[4]+')*('+y+'))))'
  polc = meq.polc(coeff=coeff,subclass=meq._funklet_type)
  print beamshape
  print coeff
  polc.function = beamshape;

  root=Meq.Parm(polc,node_groups='Parm')

  return root

def _create_dipole_beam_h(tfpoly=['1','1','1','1'],coeff=[[1],[1],[1],[1]],h=0.25,x='x2',y='x3'):
  """ Create Horizontal Dipole beam:
      The theoretical (power) beam shape is:
      z=(1-sin(x)^2 sin(y)^2)*sin(2*pi*h*sin(y)))^2;
      where x:azimuth angle (phi)
            y:elevation angle (theta) (both in radians)
            h: dipole height from ground
      we create a voltage beam, using square root of power as the r.m.s.
      voltage, and add polynomials for time,freq as given by {TF}
      z=(1-sin({TF0}x)^2 sin({TF1}y)^2)*sin(2*pi*h*{TF2}sin({TF3}y))^2
      so we need 4 polynomials, which must be given as tfpoly array.
      The coefficients for these polynomials should be given by coeff array.
      x,y should be given as polynomials of x2 and x3 respectively.
  """
  if len(tfpoly)<4:
   print "Invalid No. of Polynomials, should be 4"
   return None

  h_str=str(h)
  pi=str(math.pi)
  # voltage beam, so do not take ^2
  beamshape='(1-(sin(('+tfpoly[0]+')*('+x+'))*sin(('+tfpoly[1]+')*('+y+')))^2)*(sin(2*'+pi+'*'+h_str+'*('+tfpoly[2]+')*cos(('+tfpoly[3]+')*('+y+'))))^2'
  polc = meq.polc(coeff=coeff,subclass=meq._funklet_type)
  print beamshape
  print coeff
  polc.function = beamshape;

  root=Meq.Parm(polc,node_groups='Parm')

  return root

      


# this is the testing branch, executed when the script is run directly
# via 'python script.py'
# Note: this script will fail when run standalone

if __name__ == '__main__':
#  from Timba.Meq import meqds 
  Timba.TDL._dbg.set_verbose(5);
  ns = NodeScope();
  _define_forest(ns);
  # resolves nodes
  ns.Resolve();
