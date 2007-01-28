from Timba.TDL import *
import Context

_wsrt_list = [ str(i) for i in range(10)] + ['A','B','C','D','E','F'];
_vla_list = [ str(i) for i in range(1,28) ];

class IfrArray (object):
  def __init__(self,ns,station_list,station_index=None,uvw_table=None,mirror_uvw=False):
    """Creates an IfrArray object, representing an interferometer array.
    'station_list' is a list of station IDs, not necessarily numeric.
    'station_index' is an optional list of numeric station indices. If not given,
      [0,...,N-1] will be used. If the array represents a subset of an MS,
      then correct indices indicating the subset should be given.
    'uvw_table' is a path to a MEP table containing station UVWs. If not given,
      UVWs will be computed explicitly with a Meq.UVW node.
    'mirror_uvw' can be True to use the VLA UVW deifnition (sign flip)
    """;
    self.ns = ns;
    # make list of station pairs: (0,p0),(1,p1),... etc.
    if station_index:
      if len(station_list) != len(station_index):
        raise ValueError,"'station_list' and 'station_index' must have the same length";
      self._station_index = zip(station_index,station_list);
    else:
      self._station_index = list(enumerate(station_list));
    # now make some other lists
    self._stations = station_list;
    self._ifr_index = [ (px,qx) for px in self._station_index 
                                for qx in self._station_index if px[0]<qx[0] ];
    self._ifrs = [ (px[1],qx[1]) for px,qx in self._ifr_index ];
    self._uvw_table = uvw_table;
    self._mirror_uvw = mirror_uvw;
    self._jones = [];
    
  def WSRT (ns,stations=14,uvw_table=None,mirror_uvw=False):
    """Creates and returns an IfrArray for WSRT, i.e., with proper labels.
    The 'stations' argument can be either a number of stations (then only
    the first N antennas will be used), or a list of station indices.
    If not given, then the full WSRT array is used.
    """;
    if isinstance(stations,int):
      stations = _wsrt_list[:stations];
      index = None;
    elif isinstance(stations,(list,tuple)):
      index = stations;
      stations = [ _wsrt_list[i] for i in stations ];
    else:
      raise TypeError,"WSRT 'stations' argument must be a list of stations, or a number";
    return IfrArray(ns,stations,station_index=index,uvw_table=uvw_table,mirror_uvw=mirror_uvw);
  WSRT = staticmethod(WSRT);
  
  def VLA (ns,stations=27,uvw_table=None,mirror_uvw=False):
    """Creates and returns an IfrArray for VLA, i.e., with proper labels.
    The 'stations' argument can be either a number of stations (then only
    the first N antennas will be used), or a list of station indices.
    If not given, then the full WSRT array is used.
    """;
    if isinstance(stations,int):
      stations = _vla_list[:stations];
      index = None;
    elif isinstance(stations,(list,tuple)):
      index = stations;
      stations = [ _vla_list[i] for i in stations ];
    else:
      raise TypeError,"VLA 'stations' argument must be a list of stations, or a number";
    return IfrArray(ns,stations,station_index=index,uvw_table=uvw_table,mirror_uvw=mirror_uvw);
  VLA = staticmethod(VLA);

  def stations (self):
    return self._stations;
    
  def station_index (self):
    return self._station_index;
    
  def num_stations (self):
    return len(self._stations);
    
  def ifrs (self):
    return self._ifrs;
    
  def ifr_index (self):
    return self._ifr_index;
    
  def num_ifrs (self):
    return len(self._ifrs);
    
  def spigots (self,node=None,**kw):
    """Creates (if necessary) and returns spigots, as an unqualified node.
    Extra keyword arguments will be passed to Spigot node."""
    if node is None:
      node = self.ns.spigot;
    (ip0,p0),(iq0,q0) = self.ifr_index()[0];
    if not node(p0,q0).initialized():
      for (ip,p),(iq,q) in self.ifr_index():
        node(p,q) << Meq.Spigot(station_1_index=ip,station_2_index=iq,**kw);
    return node;
    
  def sinks (self,children,node=None,**kw):
    """Creates (if necessary) and returns sinks, as an unqualified node.
    The 'children' argument should be a list of child nodes, which
    will be qualified with an interferometer pair.
    Extra keyword arguments will be passed to Sink node."""
    if node is None:
      node = self.ns.sink;
    (ip0,p0),(iq0,q0) = self.ifr_index()[0];
    if not node(p0,q0).initialized():
      for (ip,p),(iq,q) in self.ifr_index():
        node(p,q) << Meq.Sink(children=children(p,q),
                               station_1_index=ip,station_2_index=iq,
                               **kw);
    return node;
    
  def xyz0 (self):
    """Returns array reference position node""";
    self.xyz();
    return self.ns.xyz0;
    
  def xyz (self,*quals):
    """Returns unqualified station position nodes,
    If a station is supplied, returns XYZ node for that station""";
    xyz0 = self.ns.xyz0;
    if not xyz0.initialized():
      for (ip,p) in self.station_index():
        # since the Meow.ReadVisHeader script knows nothing about
        # our station labels, the x/y/z nodes themselves are
        # indexed with station _numbers_ instead.
        # to avoid confusion, we call them "x:num0", etc.
        num = 'num'+str(ip);
        # create XYZ nodes
        xyz = self.ns.xyz(p) << Meq.Composer(
          self.ns.x(num) << Meq.Constant(0.0),
          self.ns.y(num) << Meq.Constant(0.0),
          self.ns.z(num) << Meq.Constant(0.0)
        );
        if not xyz0.initialized():
          xyz0 << Meq.Selector(xyz); # xyz0 == xyz first station essentially
    return self.ns.xyz(*quals);
    
  def uvw (self,dir0,*quals):
    """returns station UVW node(s) for a given phase centre direction,
    or using the global phase center if None is given.
    If a station is supplied, returns UVW node for that station""";
    radec0 = Context.get_dir0(dir0).radec();
    uvw = self.ns.uvw.qadd(radec0);
    if not uvw(self.stations()[0]).initialized():
      if not self._uvw_table:
        xyz0 = self.xyz0();
        xyz = self.xyz();
      for station in self.stations():
        # create UVW nodess
        # if a table is specified, UVW will be read in directly
        if self._uvw_table:
          uvw_def = Meq.Composer(
            self.ns.u.qadd(radec0)(station) << Meq.Parm(table_name=self._uvw_table),
            self.ns.v.qadd(radec0)(station) << Meq.Parm(table_name=self._uvw_table),
            self.ns.w.qadd(radec0)(station) << Meq.Parm(table_name=self._uvw_table)
          );
        # else create MeqUVW node to compute them
        else:
          uvw_def = Meq.UVW(radec = radec0,
                            xyz_0 = xyz0,
                            xyz   = xyz(station));
        # do UVW need to be mirrored?
        if self._mirror_uvw:
          uvw(station) << Meq.Negate(self.ns.m_uvw(station) << uvw_def );
        else:
          uvw(station) << uvw_def;
    return uvw(*quals);
  
  def uvw_ifr (self,dir0,*quals):
    """returns interferometer UVW node(s) for a given phase centre direction,
    or using the global phase center if None is given.
    If an IFR is supplied, returns UVW node for that IFR""";
    dir0 = Context.get_dir0(dir0);
    radec0 = dir0.radec();
    uvw_ifr = self.ns.uvw_ifr.qadd(radec0);
    if not uvw_ifr(*(self.ifrs()[0])).initialized():
      uvw = self.uvw(dir0);
      for sta1,sta2 in self.ifrs():
        uvw_ifr(sta1,sta2) << uvw(sta2) - uvw(sta1);
    return uvw_ifr(*quals);
    
  def uv (self,dir0,*quals):
    """returns station UV node(s) for a given phase centre direction,
    or using the global phase center if None is given.
    If a station is supplied, returns UV node for that station""";
    dir0 = Context.get_dir0(dir0);
    radec0 = dir0.radec();
    uv = self.ns.uv.qadd(radec0);
    if not uv(self.stations()[0]).initialized():
      uvw = self.uvw(dir0);
      for station in self.stations():
        uv(station) << Meq.Selector(uvw(station),index=(0,1),multi=True);
    return uv(*quals);

  def uv_ifr (self,dir0,*quals):
    """returns interferometer UV node(s) for a given phase centre direction.
    or using the global phase center if None is given.
    If an IFR is supplied, returns UVW node for that IFR""";
    dir0 = Context.get_dir0(dir0);
    radec0 = dir0.radec();
    uv_ifr = self.ns.uv_ifr.qadd(radec0);
    if not uv_ifr(*(self.ifrs()[0])).initialized():
      uvw_ifr = self.uvw_ifr(dir0);
      for ifr in self.ifrs():
        uv_ifr(*ifr) << Meq.Selector(uvw_ifr(*ifr),index=(0,1),multi=True);
    return uv_ifr(*quals);
