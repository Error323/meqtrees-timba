from Timba.TDL import *
from Timba.Meq import meq
from Meow import Parameterization
import Context


def gain_ap_matrix (jones,ampl=1.,phase=0.,tags=[],series=None):
  """Creates an amplitude-phase gain matrix of the form:
        ( ax*e^{i*px}       0      )
        (     0       ay*e^{i*p_y} )
  'jones' should be a node stub.
  'series' can be a list of qualifiers to make a series of matrices.
  The x/y amplitudes and phases are created as Meq.Parms (with initial 
  values 1 and 0, respectively) by qualifying 'jones' with 
  'xa','xp','ya','yp'. These Parm nodes will be tagged with the given set
  of 'tags', plus 'ampl' and 'phase'.
  """
  # create matrix per-station, or just a single matrix
  if series:
    for p in series:
      xa = Parameterization.resolve_parameter("ampl",jones(p,'xa'),ampl,tags=tags);
      xp = Parameterization.resolve_parameter("phase",jones(p,'xp'),phase,tags=tags);
      ya = Parameterization.resolve_parameter("ampl",jones(p,'ya'),ampl,tags=tags);
      yp = Parameterization.resolve_parameter("phase",jones(p,'yp'),phase,tags=tags);
      jones(p) << Meq.Matrix22(
        jones(p,"x") << Meq.Polar(xa,xp),
        0,0,
        jones(p,"y") << Meq.Polar(ya,yp)
      );
  else:
    xa = Parameterization.resolve_parameter("ampl",jones('xa'),ampl,tags=tags);
    xp = Parameterization.resolve_parameter("phase",jones('xp'),phase,tags=tags);
    ya = Parameterization.resolve_parameter("ampl",jones('ya'),ampl,tags=tags);
    yp = Parameterization.resolve_parameter("phase",jones('yp'),phase,tags=tags);
    jones << Meq.Matrix22(
      jones("x") << Meq.Polar(xa,xp),
      0,0,
      jones("y") << Meq.Polar(ya,yp)
    );
  return jones;


def define_rotation_matrix (angle):
  """Returns node definition for a rotation matrix, given an 'angle' node
  or value. Since this is a node _definition_, it must be bound to a node
  name with '<<', e.g.:
    ns.pa << Meq.ParAngle(...);
    ns.P << Jones.define_rotation_matrix(ns.pa);
  """
  cos = angle("cos") << Meq.Cos(angle);
  sin = angle("sin") << Meq.Sin(angle);
  return Meq.Matrix22(cos,-sin,sin,cos);
  

def apply_corruption (vis,vis0,jones,ifrs=None):
  """Creates nodes to corrupt with a set of Jones matrices.
  'vis' is the output node which will be qualified with (p,q)
  'vis0' is an input visibility node which will be qualified with (p,q2)
  'jones' is either one unqualified Jones matrix, or else a list/tuple of 
    Jones matrices. In either case each Jones term will be qualified with 
    the station index (p).
  'ifrs' should be a list of p,q pairs; by default Meow.Context is used.
  """;
  if not isinstance(jones,(list,tuple)):
    jones = (jones,);
  # multiply input visibilities by our jones list
  for p,q in (ifrs or Context.array.ifrs()):
    terms = [vis0(p,q)];
    # collect list of per-source station-qualified Jones terms
    for J in jones:
      J2c = J(q)('conj') ** Meq.ConjTranspose(J(q));
      terms = [J(p)] + terms + [J2c];
    # create multiplication node
    vis(p,q) << Meq.MatrixMultiply(*terms);
  return vis;


def apply_correction (vis,vis0,jones,ifrs=None):
  """Creates nodes to apply the inverse of a set of Jones matrices.
  'vis' is the output node which will be qualified with (sta1,sta2)
  'vis0' is an input visibility node which will be qualified with (sta1,sta2)
  'jones' is either one unqualified Jones matrix, or else a list/tuple of 
    Jones matrices. In either case each Jones term will be qualified with 
    the station index (p).
  'ifrs' should be a list of p,q pairs; by default Meow.Context is used.
  """;
  if not isinstance(jones,(list,tuple)):
    jones = (jones,);
  # multiply input visibilities by our jones list
  for p,q in (ifrs or Context.array.ifrs()):
    terms = [vis0(p,q)];
    # collect list of per-source station-qualified Jones terms
    for J in jones:
      J1i = J(p)('inv') ** Meq.MatrixInvert22(J(p));
      J2i = J(q)('inv') ** Meq.MatrixInvert22(J(q));
      J2ci = J2i('conj') ** Meq.ConjTranspose(J2i);
      terms = [J1i] + terms + [J2ci];
    # create multiplication node
    vis(p,q) << Meq.MatrixMultiply(*terms);
  return vis;
