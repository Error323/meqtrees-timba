from Timba.TDL import *
from Timba.Meq import meq
from SkyComponent import *

class CorruptComponent(SkyComponent):
  """A CorruptComponent represents an SkyComponent, plus a set of
  associated Jones matrices that corrupt the SkyComponent's visibilities.
  """;
  def __init__(self,ns,skycomp,label='corrupt',station_jones=None,jones=None):
    """Initializes a corrupt component. skycomp is a SkyComponent
    object. 
    'label' is used to qualify visibilities.
    """;
    SkyComponent.__init__(self,ns,skycomp.name+':'+label,skycomp.direction);
    self.label    = label;
    self.skycomp  = skycomp;
    self._jones = [];
    if station_jones is not None:
      self.add_station_jones(station_jones);
    if jones is not None:
      self.add_jones(jones);
    
  def add_station_jones (self,jones,prepend=False):
    """adds a per-station image-plane effect represented by a Jones
    matrix. 'jones' should be a callable object (e.g. an unqualified node)
    such that jones(x) returns the Jones matrix node for station x, or None
    if no matrix is to be applied""";
    # prepend to list
    if prepend:
      self._jones.insert(0,jones);
    else:
      self._jones.append(jones);
    
  def add_jones (self,jones,prepend=False):
    """adds an station-independent image-plane effect represented by the 
    given Jones matrix. Argument should be an valid node.""";
    # emulate a per-station jones so that we may jones matrices uniformly 
    # in visibility()
    self.add_station_jones(lambda sta : jones,prepend);
    
  def jones_list (self):
    return self._jones;

  def apply_jones (self,vis,vis0,ifr_list):
    """Creates nodes to apply the Jones chain associated with this 
    component.
    'ifr_list' should be a list of (sta1,sta2) pairs
    'vis' is the output node which will be qualified with (sta1,sta2)
    'vis0' is an input visibility node which will be qualified with (sta1,sta2)
    """;
    # multiply input visibilities by our jones list
    for (sta1,sta2) in ifr_list:
      # collect list of per-source station-qualified Jones terms
      terms = [ jones(sta1) for jones in self.jones_list() if jones(sta1) is not None ];
      # reverse list since they are applied in reverse order
      # first (J2*J1*C*...)
      terms.reverse();
      terms.append(vis0(sta1,sta2));
      # collect list of conjugate terms. The '**' operator
      # is for init-if-not-initialized
      terms += [ jones(sta2)('conj') ** Meq.ConjTranspose(jones(sta2))
                 for jones in self.jones_list() if jones(sta2) is not None ];
      # create multiplication node
      vis(sta1,sta2) << Meq.MatrixMultiply(*terms);
    return vis;
    
  def make_visibilities  (self,nodes,array,observation):
    """Creates nodes computing visibilities of component corrupted by
    attached Jones terms.
    """;
    nomvis = self.skycomp.visibilities(array,observation);
    # do we have extra jones terms?
    if self.jones_list():
      self.apply_jones(nodes,nomvis,array.ifrs());
    # no jones terms, use nominal visibilities directly
    # (pass through MeqSelector for consistency of naming)
    else:
      for ifr in array.ifrs():
        nodes(*ifr) << Meq.Selector(nomvis(*ifr));
    return nodes;