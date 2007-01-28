import math
from Timba.TDL import *
from Timba.Meq import meq
from PointSource import *
import Context
  
STOKES = ("I","Q","U","V");

class GaussianSource(PointSource):
  def __init__(self,ns,name,direction,
               I=0.0,Q=None,U=None,V=None,
               spi=None,freq0=None,
               RM=None,
               size=None,phi=0,symmetric=False):
    PointSource.__init__(self,ns,name,direction,I,Q,U,V,
                        spi,freq0,RM);
    # create polc(s) for size
    self._symmetric = symmetric;
    if symmetric:
      self._add_parm('sigma',size,tags='shape');
    else:
      # setup orientation
      # note: the orientation angle, phi, of the major axis
      # is defined in the direction East through South; i.e.
      # an angle of zero defines a Gaussian oriented east-west
      self._add_parm('phi',phi,tags='shape');
      if isinstance(size,(int,float)):
        s1 = s2 = size;
      elif isinstance(size,(tuple,list)):
        if len(size) != 2:
          raise TypeError,"size: one or two numeric values expected";
        s1,s2 = size;
      else:
        raise TypeError,"size: one or two numeric values expected";
      self._add_parm('sigma1',s1,tags="shape");
      self._add_parm('sigma2',s2,tags="shape");
    
  def is_symmetric (self):
    return self._symmetric;
    
  def sigma (self):
    """Returns the size for this source (single node for symmetric,
    two-pack for elliptic).""";
    if self._symmetric:
      return self._parm('sigma');
    else:
      return self.ns.sigma ** Meq.Composer(self._parm("sigma1"),self._parm("sigma2"));
    return size;
      
  def phi (self):
    """Returns the orientation node for this source""";
    return self._parm("phi");
    
  def transformation_matrix (self):
    # for a symmetric case, the transformation matrix is just multiplication 
    # by sigma
    if self.is_symmetric():
      return self._parm("sigma");
    # else build up full rotation-scaling matrix
    xfm = self.ns.xfmatrix;
    if not xfm.initialized():
      phi = self.phi();
      # get direction sin/cos
      cos_phi = self.ns.cos_phi << Meq.Cos(phi);
      sin_phi = self.ns.sin_phi << Meq.Sin(phi);
      # get sigma parameters
      (a,b) = (self._parm("sigma1"),self._parm("sigma2"));
      xfm << Meq.Matrix22(
          a*cos_phi,Meq.Negate(a*sin_phi),
          b*sin_phi,b*cos_phi);
    return xfm;

  def make_visibilities (self,nodes,array,observation):
    array = Contxt.get_array(array);
    observation = Context.get_observation(observation);
    dir0 = observation.phase_centre;
    radec0 = dir0.radec();
    # 1/wl = freq/c
    iwl = self.ns0.inv_wavelength << ((self.ns0.freq<<Meq.Freq) / 2.99792458e+8);
    # -1/(wl^2): scaling factor applied to exp() argument below
    m_iwlsq = self.ns0.m_inv_wavelength_sq << Meq.Negate(Meq.Sqr(iwl));
    # scaling factor of gaussian for unit flux
    gscale = self.ns0.gaussiancomponent_scale << Meq.Constant(0.5*math.pi);
    # baseline UVs
    uv_ifr = array.uv_ifr(dir0);
    # rotation matrix
    xfm = self.transformation_matrix();
    # flux scale -- coherency multiplied by scale constant above
    fluxscale = self.ns.fluxscale.qadd(radec0()) \
          << self.coherency(observation) * gscale;
    # transformed uv's (rotated and scaled)
    uv1sq = self.ns.uv1sq.qadd(radec0);
    u1sq = self.ns.u1sq.qadd(radec0);
    v1sq = self.ns.v1sq.qadd(radec0);
    # gaussian coherencies go here
    gcoh = self.ns.gauss_coh.qadd(radec0);
    # now generate nodes
    for ifr in array.ifrs():
      # rotate uvs and scale to wavelength
      uv1s = uv1sq(*ifr) << Meq.Sqr(Meq.MatrixMultiply(xfm,uv_ifr(*ifr)));
      u1s = u1sq(*ifr) << Meq.Selector(uv1s,index=0); 
      v1s = v1sq(*ifr) << Meq.Selector(uv1s,index=1); 
      gcoh(*ifr) << fluxscale * Meq.Exp((u1s+v1s)*m_iwlsq);
    # phase shift to source position
    self.direction.make_phase_shift(nodes,gcoh,array,dir0);
