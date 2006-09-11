# script to predict off-axis focal plane array responses
# the initial version is adapted from the old clar_source_predict.py script

from Timba.TDL import *
from Timba.Meq import meq
from Timba.Trees import TDL_Joneset
from numarray import *
from copy import deepcopy
import os

# bookmark
Settings.forest_state = record(bookmarks=[
  record(name='Predicts',page=[
    record(viewer="Result Plotter",udi="/node/clean_visibility:1:10:src_1",pos=(0,0)),
    record(viewer="Result Plotter",udi="/node/corrupted_vis:1:10:src_1",pos=(0,1)),
    record(viewer="Result Plotter",udi="/node/E:1:src_1",pos=(0,2)),
    record(viewer="Result Plotter",udi="/node/predict:1:2",pos=(1,0)),
    record(viewer="Result Plotter",udi="/node/predict:1:6",pos=(1,1)),
    record(viewer="Result Plotter",udi="/node/predict:1:14",pos=(1,2)),
    record(viewer="Result Plotter",udi="/node/predict:1:20",pos=(2,0)),
    record(viewer="Result Plotter",udi="/node/predict:1:25",pos=(2,1)),
    record(viewer="Result Plotter",udi="/node/predict:1:30",pos=(2,2)),
  ]),
]);

class PointSource:
    name = ''
    ra   = 0.0
    dec  = 0.0
    IQUV      = zeros(4)*0.0
    IQUVorder = zeros(4)*0.0
    table  = ''

    def __init__(self, name='', ra=0.0, dec=0.0,
                 I=0.0, Q=0.0, U=0.0, V=0.0,
                 Iorder=0, Qorder=0, Uorder=0, Vorder=0,
                 table=''):
        self.name   = name
        self.ra     = ra
        self.dec    = dec
        self.IQUV   = array([I,Q,U,V])
        self.IQUVorder = array([Iorder,Qorder,Uorder,Vorder])
        self.table  = table
        pass
    pass

def create_source_model(tablename=''):
    """ define model source positions and flux densities """
    source_model = []
    source_model.append( PointSource(name="src_1",I=1.0, Q=0.0, U=0.0, V=0.0,
#                   Iorder=0, ra=0.030543262, dec=-.85521133,
#                   Iorder=0, ra=0.030543262, dec=-.82030475,  #pos = 7m, -47deg
#                   Iorder=0, ra=0.030543262, dec=-.83775804,  #pos = 7m, -48deg
                    Iorder=0, ra=0.030543262, dec=-.80285146,  #pos = 7m, -46deg
                    table=tablename))

    return source_model

def create_source_model_all(tablename=''):
    """ define model source positions and flux densities """
    source_model = []
    source_model.append( PointSource(name="src_1",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.030272885, dec=0.575762621,
                    table=tablename))

    source_model.append( PointSource(name="src_2",  I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0306782675, dec=0.575526087,
                    table=tablename))

    source_model.append( PointSource(name="src_3",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0308948646, dec=0.5762655,
                    table=tablename))

    source_model.append( PointSource(name="src_4",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0308043705, dec=0.576256621,
                    table=tablename))

    source_model.append( PointSource(name="src_5",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.030120036, dec=0.576310965,
                    table=tablename))

    source_model.append( PointSource(name="src_6",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0301734016, dec=0.576108805,
                    table=tablename))

    source_model.append( PointSource(name="src_7",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0302269161, dec=0.576333355,
                    table=tablename))

    source_model.append( PointSource(name="src_8",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0304215356, dec=0.575777607,
                    table=tablename))

    source_model.append( PointSource(name="src_9",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0307416105, dec=0.576347166,
                    table=tablename))

    source_model.append( PointSource(name="src_10",I=1.0, Q=0.0, U=0.0, V=0.0,
                    Iorder=0, ra=0.0306878027, dec=0.575851951,
                    table=tablename))

    return source_model

def create_refparms (refnode):
  """For any given parm node, this creates:
  * a reference parms with the same name, linked to a "reference" MEP table called "mep-ref/<meptable>".
  * a Subtract node taking the difference between the two.
  The subtract node is made a child of a root node called "verifier".
  The idea is that it is then easy to execute the verifier node with a request
  corresponding to the entire MS (or a part thereof), and obtain comparisons
  for all parameters between the new solution, and an older solution saved
  in mep-ref/.
  """;
 # ### temp kludge!!!
 # for q in refnode.quals:
 # if isinstance(q,int) and q>3:
 #    return;
  nodename = refnode.name;
  mepname = refnode.initrec().table_name;
  r0 = refnode('ref') << Meq.Parm(0,table_name="mep-ref/"+mepname,node_groups='Ref',parm_name=nodename,cache_policy=100);
  d  = refnode('diff') << Meq.Subtract(r0,refnode,cache_policy=100);
  # create verifier node if not already created
  global _verifier;  # holding global ref to it ensures that it is not cleaned up as an orpan node
  _verifier = refnode.scope.verifier;
  if not _verifier.initialized():
    _verifier << Meq.VisDataMux(pre=\
      refnode.scope.vdc << Meq.DataCollect(cache_policy=100));
  # add to its children
  refnode.scope.vdc.add_children(d);


# define defaults for station locations, field centre etc
def forest_measurement_set_info(ns, num_ant):
    ns.ra0    << Meq.Constant(0.0)
    ns.dec0   << Meq.Constant(0.0)
    ns.radec0 << Meq.Composer(ns.ra0, ns.dec0)


    for i in range(num_ant):
        station= str(i+1)

        ns.x(station) << Meq.Constant(0.0)
        ns.y(station) << Meq.Constant(0.0)
        ns.z(station) << Meq.Constant(0.0)
        if i == 0:
            ns.xyz0 << Meq.Composer(ns.x(1), ns.y(1),ns.z(1))
            pass

        ns.xyz(station)  << Meq.Composer(ns.x(station),
                                         ns.y(station),
                                         ns.z(station))
        ns.uvw(station) << Meq.UVW(radec= ns.radec0,
                                   xyz_0= ns.xyz0,
                                   xyz  = ns.xyz(station))
        pass
    pass

def create_polc_ft(degree_f=0, degree_t=0, c00=0.0):
    polc = meq.polc(zeros((degree_t+1, degree_f+1))*0.0)
    polc.coeff[0,0] = c00
    return polc

### initial stuff for station
def forest_station_jones(ns, station, mep_table_name):
    """
    Station is a 1-based integer
    """

    for i in range(1,3):
        for j in range(1,3):
            elem      = str(i)+str(j)
            if i != j:
                gain_polc  = create_polc_ft(degree_f=0, degree_t=0, c00=0.0)
                phase_polc = create_polc_ft(degree_f=0, degree_t=0, c00=0.0)
            else:
                gain_polc  = create_polc_ft(degree_f=0, degree_t=1, c00=1.0)
                phase_polc = create_polc_ft(degree_f=0, degree_t=0, c00=0.0)
                pass
            ga = ns.GA(station, elem) << Meq.Parm(gain_polc,
                                             table_name=mep_table_name,
                                             node_groups='Parm',
                                             tiling=record(time=20))
            gp = ns.GP(station, elem) << Meq.Parm(phase_polc,
                                             table_name=mep_table_name,
                                             node_groups='Parm',
                                             tiling=record(time=1))
            ns.G(station, elem) << Meq.Polar(ga,gp);
            if i == j:
              create_refparms(ga);
              create_refparms(gp);
            pass # for j ...
        pass     # for i ...

    ns.G(station) << Meq.Matrix22(ns.G(station, '11'),
                                  ns.G(station, '12'),
                                  ns.G(station, '21'),
                                  ns.G(station, '22'))
    ns.ctG(station) << Meq.ConjTranspose(ns.G(station))

def forest_baseline_predict_trees(ns, interferometer_list, sources):
    """ create visibility for a source as seen by station combinations
        with original theoretical visibilities corrupted by Jones matrices
    """    
    for (ant1, ant2) in interferometer_list:
        corrupted_vis_list = []
        for source in sources:
            ns.corrupted_vis(ant1,ant2,source.name) << \
                    Meq.MatrixMultiply(ns.E(ant2,source.name),
                                 ns.clean_visibility(ant1,ant2, source.name),
                                 ns.ctE(ant1, source.name))
            corrupted_vis_list.append(ns.corrupted_vis(ant1,ant2,source.name))
            pass
        ns.predict(ant1, ant2) << Meq.Add(children=deepcopy(corrupted_vis_list))
        pass
    pass

def forest_baseline_correct_trees(ns, interferometer_list, sources):
    """ this generates a bunch of visibility 'correction factors' which
        one could apply to the observed or 'spigot' data. The script
        writes this stuff out to a CORRECTED_DATA column, but that
        is a misnomer.
    """
    for (ant1, ant2) in interferometer_list:
        ns.subtract(ant1, ant2) << (ns.spigot(ant1,ant2) - \
                                    ns.predict(ant1, ant2))
        corrected_vis_list = []
        for source in sources:
          ns.corrected(ant1,ant2,source.name) << \
                Meq.MatrixMultiply(Meq.MatrixInvert22(ns.E(ant1,source.name)), #                              Meq.MatrixInvert22(ns.G(ant1)),
                                   ns.subtract(ant1,ant2), #           Meq.MatrixInvert22(ns.ctG(ant2)),
                                   Meq.MatrixInvert22(ns.ctE(ant2, source.name)))
          pass
          corrected_vis_list.append(ns.corrected(ant1,ant2,source.name))
        ns.corrected(ant1, ant2) << Meq.Add(children=deepcopy(corrected_vis_list))
    pass

def forest_clean_predict_trees(ns, source, station_list):
    """ create visibility for a source as seen by station combinations
        without any corruption 
    """    
    for station in station_list:
# first define beam parameters (power pattern) for this station
# and source (note: the results of the following function call
# are used in the forest_baseline_predict_trees function
      sta_source_dft_tree(ns, station, source)

# compute station-based component of phase shift for this source and station
      ns.dft(station, source.name) << Meq.VisPhaseShift(
                                     lmn=ns.lmn_minus1(source.name),
                                     uvw=ns.uvw(station))
      ns.conjdft(station, source.name) << Meq.Conj(ns.dft(station, source.name))
      pass # for station
    
# Now for this source create baseline-based source visibilities that
# are not corrupted  
    for ant1 in range(len(station_list)):
        for ant2 in range(ant1+1, len(station_list)):
            ns.clean_visibility(station_list[ant1], station_list[ant2], source.name) << \
            Meq.MatrixMultiply(ns.dft(station_list[ant2], source.name),
                                  ns.conjdft(station_list[ant1], source.name),
                                  ns.coherency(source.name))
        pass # for ant2
    pass     # for ant1


def forest_station_source_jones(ns, station_list, source_name, mep_table_name):
    """
    create E-Jones (primary beam effects) matrices: station_list is 1-based 
    """
    
    for station in station_list:
      for i in range(1,3):
        for j in range(1,3):
            elem      = str(i)+str(j)
            phase_polc = create_polc_ft(degree_f=0, degree_t=0, c00=0.0)
            ep = ns.EP(station, source_name, elem) << Meq.Parm(phase_polc,
                                                          table_name=mep_table_name,
                                                          node_groups='Parm',
                                                          tiling=record(time=1))
            if i != j:
                gain_polc  = create_polc_ft(degree_f=0, degree_t=0, c00=0.0)
                ea = ns.EA(station, source_name, elem) << Meq.Parm(gain_polc,
                                                   table_name=mep_table_name,
                                                   node_groups='Parm',
                                                   tiling=record(time=1))
            else:
# I believe the following should be correct here
                ea = ns.EA(station, source_name, elem) << Meq.Sqrt(ns.exp_v_gain(station,source_name)) 
                pass
            ns.E(station, source_name, elem) << Meq.Polar(ea,ep);
#           if i == j:
#             create_refparms(ea);
#             create_refparms(ep);
            pass # for j ...
        pass     # for i ...
      pass
      ns.E(station,source_name) << Meq.Matrix22(ns.E(station, source_name, '11'),
                                             ns.E(station, source_name, '12'),
                                             ns.E(station, source_name, '21'),
                                             ns.E(station, source_name, '22'))
      ns.ctE(station, source_name) << Meq.ConjTranspose(ns.E(station,source_name))

def forest_sum_of_phases(ns, station_list, source_name, coeff):
    phase_list = []
    for station in station_list:
        phase_list.append("EP:"+str(station)+":"+source_name+":"+coeff)
        pass
    ns.SumOfPhases(source_name, coeff)  << Meq.Add(children=phase_list)
    ns.ce("Phases", source_name, coeff) << Meq.Condeq(0.0, ns.SumOfPhases(source_name, coeff))
    pass


def forest_solver(ns, interferometer_list, station_list, sources, input_column='DATA'):
    ce_list = []
    # Measurements
    for (ant1,ant2) in interferometer_list:
        ns.spigot(ant1, ant2) << Meq.Spigot(station_1_index=ant1-1,
                                            station_2_index=ant2-1,
                                            flag_bit=4,
                                            input_col=input_column)
        ns.ce(ant1, ant2) << Meq.Condeq(ns.spigot(ant1, ant2),
                                        ns.predict(ant1, ant2))
        ce_list.append(ns.ce(ant1, ant2))
        pass
    # Constraints
    # Phase constraints
    for source in sources:
        forest_sum_of_phases(ns, station_list, source.name, "11");
        forest_sum_of_phases(ns, station_list, source.name, "22");
        ce_list.append(ns.ce("Phases", source.name, "11"));
        ce_list.append(ns.ce("Phases", source.name, "22"));
        pass

    # set up a non-default child poll order for most efficient
    # parallelization
    # (i.e. poll child 1:2, 3:4, 5:6, ..., 13:14,
    # then the rest)
    cpo = [];
    for i in range(len(station_list)/2):
      (ant1,ant2) = station_list[i*2:(i+1)*2];
      cpo.append(ns.ce(ant1,ant2).name);

    ns.solver << Meq.Solver(children=ce_list,child_poll_order=cpo);
    pass


# creates common nodes (field centre):
def create_common_nodes(ns):
    """ set up various nodes with default or constant values """
# field centre: these two values will be over-written later with
# values obtained from the input MS
    ns.ra0 << Meq.Constant(0.0)
    ns.dec0 << Meq.Constant(0.0)

def create_constant_nodes(ns):
# numeric constants
    ns.one << Meq.Constant(1.0)
    ns.half << Meq.Constant(0.5)
    ns.ln_16 << Meq.Constant(-2.7725887)

# create constant parameters for beam nodes
# eventually these should be a function of frequency
# HPBW of 1 deg = 0.0174532 rad; 57.29578 = 1 / 0.0174532 
    ns.width_l << Meq.Constant(57.2957795)
    ns.width_m << Meq.Constant(57.2957795)
#   ns.width_l << Meq.Constant(28.5)
#   ns.width_m << Meq.Constant(28.5)
    ns.width_l_sq <<Meq.Sqr(ns.width_l)
    ns.width_m_sq <<Meq.Sqr(ns.width_m)
#   ns.feed_offset << Meq.Constant(0.052359878) # offset of 3 deg in Elevation
#   ns.feed_offset << Meq.Constant(0.043633231) # offset of 2.5 deg in Elevation
    ns.feed_offset << Meq.Constant(0.017453293) # offset of 1 deg in Elevation
#   ns.feed_offset << Meq.Constant(0.0)  

# creates source-related nodes for a given source
def forest_source_subtrees (ns, source):
  print 'source.name ', source.name
  IQUVpolcs =[None]*4
  STOKES=["I","Q","U","V"]
  for (i,stokes) in enumerate(STOKES):
    if(source.IQUV[i] != None):
      print 'i source.IQUV[i] source.IQUVorder ', i, ' ', source.IQUV[i], ' ', source.IQUVorder[i]
      IQUVpolcs[i] = create_polc_ft(degree_f=source.IQUVorder[i], 
					c00= source.IQUV[i])
      pass
    st = ns.stokes(stokes, source.name) << Meq.Parm(IQUVpolcs[i],
					table_name=source.table,
					node_groups='Parm')
#   create_refparms(st);
    pass    
  ns.xx(source.name) << (ns.stokes("I",source.name)+ns.stokes("Q",source.name))*0.5
  ns.yx(source.name) << Meq.ToComplex(ns.stokes("U",source.name),ns.stokes("V",source.name))*0.5
  ns.xy(source.name) << Meq.Conj(ns.yx(source.name))
  ns.yy(source.name) << (ns.stokes("I",source.name)-ns.stokes("Q",source.name))*0.5

# add in noise for xx, yy
  ns.xx_noisy(source.name) << Meq.GaussNoise(ns.xx(source.name), stddev=0.1)
  ns.yy_noisy(source.name) << Meq.GaussNoise(ns.yy(source.name), stddev=0.1)

  ra = ns.ra(source.name) << Meq.Parm(source.ra, table_name=source.table,
			node_groups='Parm')
  dec= ns.dec(source.name) << Meq.Parm(source.dec, table_name=source.table,
			node_groups='Parm')
  radec = ns.radec(source.name) << Meq.Composer(ra, dec)
  lmn   = ns.lmn  (source.name) << Meq.LMN(radec_0 = ns.radec0, radec = radec)
  n     = ns.n    (source.name) << Meq.Selector(lmn, index=2)

  ns.lmn_minus1(source.name) << Meq.Paster(lmn, n-1, index=2)
# ns.coherency(source.name) << Meq.Matrix22(ns.xx_noisy(source.name),
#                                  ns.xy(source.name),
#                                  ns.yx(source.name),
#                                  ns.yy_noisy(source.name))/ns.n(source.name)
  ns.coherency(source.name) << Meq.Matrix22(ns.xx(source.name),
                                   ns.xy(source.name),
                                   ns.yx(source.name),
                                   ns.yy(source.name))/ns.n(source.name)
  pass


def create_station_subtrees(ns,st):
  # create nodes used to calculate AzEl of field centre as seen
  # from a specific station

  # first create AzEl node for field_centre as seen from this station
  ns.AzEl_fc(st) << Meq.AzEl(radec=ns.radec0, xyz=ns.xyz(st))

  # then get elevation of FC as seen from this station as separate element
  ns.AzEl_el0(st) << Meq.Selector(ns.AzEl_fc(st),index=1)

  # then get azimuth of FC as seen from this station as separate element
  ns.AzEl_az0(st) << Meq.Selector(ns.AzEl_fc(st),index=0)

  # then compute elevation of offset feed as seen from this station 
  ns.AzEl_el_offset(st) << Meq.Subtract(ns.AzEl_el0(st), ns.feed_offset )

  # now create azimuth-elevation node for the off-axis feed
  ns.AzEl_offset(st) << Meq.Composer(ns.AzEl_az0(st), ns.AzEl_el_offset(st))

def sta_source_dft_tree(ns, st,src):
# builds an init-record for a "dft" tree for one station (st)
#
# we first build up the mathematical expression of a voltage
# pattern for a source using the equations
# log16 =  (-1.0) * log(16.0)
# L,M give direction cosines of the source wrt field centre in
# AzEl coordinate frame
# L_gain = (L * L) / (widthl_ * widthl_)
# M_gain = (M * M ) / (widthm_ * widthm_)
# voltage_gain = sqrt(exp(log16 * (L_gain + M_gain)))

# see the create_station_subtrees function for creation
# of nodes used to compute Az, El of field centre

  # create AzEl node for source as seen from this station
  ns.az_el(st,src.name) << Meq.AzEl(radec=ns.radec(src.name), xyz=ns.xyz(st))

  # do computation of LMN of source wrt field centre in AzEl frame
  ns.lmn_azel(st,src.name) << Meq.LMN(radec_0=ns.AzEl_offset(st), radec=ns.az_el(st,src.name))
  ns.l_azel(st,src.name) << Meq.Selector(ns.lmn_azel(st,src.name),index=0)
  ns.m_azel(st,src.name) << Meq.Selector(ns.lmn_azel(st,src.name),index=1)
			    
  # compute voltage gain as seen for this source at this station
  # first square L and M
  ns.l_sq(st,src.name) << Meq.Sqr(ns.l_azel(st,src.name))
  ns.m_sq(st,src.name) << Meq.Sqr(ns.m_azel(st,src.name))

  # then multiply by width squared, for L, M
  ns.l_vpsq(st,src.name) << Meq.Multiply(ns.l_sq(st,src.name), ns.width_l_sq)
  ns.m_vpsq(st,src.name) << Meq.Multiply(ns.m_sq(st,src.name), ns.width_m_sq)

  # add L and M gains together
  ns.l_and_m_sq(st,src.name) << Meq.Add(ns.l_vpsq(st,src.name), ns.m_vpsq(st,src.name))
  # then multiply by log 16
  ns.v_gain(st,src.name) << Meq.Multiply(ns.l_and_m_sq(st,src.name), ns.ln_16)
  # raise to exponent
  ns.exp_v_gain(st,src.name) << Meq.Exp(ns.v_gain(st,src.name))

  # Note: this final node represents a source seen in a 'power pattern'
  # we take the square root of this value, so as to have a voltage response,
  # when computing Jones matrix responses - see forest_station_source_jones
# ---

def forest_create_sink_sequence(ns, interferometer_list, output_column='PREDICT'):
    ns.VisDataMux << Meq.VisDataMux;
    for (ant1, ant2) in interferometer_list:
        ns.sink(ant1,ant2) << Meq.Sink(station_1_index=ant1-1,
                                       station_2_index=ant2-1,
                                       flag_bit=4,
                                       corr_index=[0,1,2,3],
                                       flag_mask=-1,
                                       output_col=output_column,
                                       children= ns.predict(ant1, ant2)
                                       )
        pass
    pass
    ns.VisDataMux.add_children(*[ns.sink(ant1,ant2) for (ant1, ant2) in interferometer_list]);
#   ns.VisDataMux.add_stepchildren(*[ns.spigot(ant1,ant2) for (ant1, ant2) in interferometer_list]);


def create_inputrec(msname, tile_size=1500,short=False):
    boioname = "boio."+msname+"."+str(tile_size);
    # if boio dump for this tiling exists, use it to save time
    # but watch out if you change the visibility data set!
    if not short and os.access(boioname,os.R_OK):
      rec = record(boio=record(boio_file_name=boioname,boio_file_mode="r"));
    # else use MS, but tell the event channel to record itself to boio file
    else:
      rec = record();
      rec.ms_name          = msname
      rec.data_column_name = 'DATA'
      rec.tile_size        = tile_size
      rec.selection = record(channel_start_index=0,
                             channel_end_index=0,
                             channel_increment=1,
                             selection_string='')
      if short:
        rec.selection.selection_string = '';
      else:
        rec.record_input = boioname;
      rec = record(ms=rec);
    rec.python_init='AGW_read_msvis_header.py';
    return rec;


def create_outputrec(output_column='CORRECTED_DATA'):
    rec=record()

    rec.write_flags=False
    rec.predict_column=output_column

    return record(ms=rec);

def create_solver_defaults(num_iter=30,epsilon=1e-4,convergence_quota=0.9,solvable=[]):
    solver_defaults=record()
    solver_defaults.num_iter     = num_iter
    solver_defaults.epsilon      = epsilon
    solver_defaults.convergence_quota = convergence_quota
    solver_defaults.save_funklets= True
    solver_defaults.last_update  = True
#See example in TDL/MeqClasses.py
    solver_defaults.solvable     = record(command_by_list=(record(name=solvable,
                                         state=record(solvable=True)),
                                         record(state=record(solvable=False))))
    return solver_defaults

def set_AGW_node_state (mqs, node, fields_record):
    """helper function to set the state of a node specified by name or
    nodeindex""";
    rec = record(state=fields_record);
    if isinstance(node,str):
        rec.name = node;
    elif isinstance(node,int):
        rec.nodeindex = node;
    else:
        raise TypeError,'illegal node argument';
# pass command to kernel
    mqs.meq('Node.Set.State',rec);
    pass


def publish_node_state(mqs, nodename):
    mqs.meq('Node.Set.Publish.Level',record(name=nodename,level=1))
    pass

########### new-style TDL stuff ###############

def _tdl_job_xntd_predict(mqs,parent,write=True):
    msname          = 'TEST_XNTD_30_960.MS'
#   inputrec        = create_inputrec(msname, tile_size=6000)
    inputrec        = create_inputrec(msname, tile_size=960)
    outputrec       = create_outputrec()
    print 'input record ', inputrec
    print 'output record ', outputrec
    req = meq.request();
    req.input  = inputrec;
    if write:
      req.output = outputrec;
    mqs.clearcache('VisDataMux');
    print 'VisDataMux request is ', req
    mqs.execute('VisDataMux',req,wait=(parent is None));
    pass

####################
def _define_forest(ns):

# Note: To create a predictor:just eliminate the ReqSeqs, Spigots, Solver,
# Condeqs and Subtracts, and make each predict node (i.e. the non-spigot
# side of the condeq) a direct child of the corresponding Sink

# define default field centre
    create_common_nodes(ns)

# create constant value nodes for simulation
    create_constant_nodes(ns)

# create default antenna station parameters (location, UVW)
    num_antennas = 30
    station_list = range(1, num_antennas+1)
    forest_measurement_set_info(ns, len(station_list))

# create source list
    source_mep_tablename= 'sourcemodel.mep'
    source_model = create_source_model(tablename=source_mep_tablename)

# create nodes specific to individual sources in the source list
    for source in source_model:
        forest_source_subtrees(ns, source)
        pass
        
    mep_table_name      = 'xNTD.mep'
    for station in station_list:
# first create nodes used to calculate AzEl of field centre 
# as seen from a specific station
      create_station_subtrees(ns, station)

# Create Jones matrix default gains for a station
# Is this useful for anything?
#     forest_station_jones(ns, station, mep_table_name)
      pass
        
    for source in source_model:
# First, compute beam parameters (power pattern) for all 
# stations and source. 
# Then compute uncorrupted visibilities for the source as seen by each
# baseline pair
      forest_clean_predict_trees(ns, source, station_list)

# Now compute Jones matrix components for this source and all stations
      forest_station_source_jones(ns, station_list, source.name, mep_table_name)
      pass

# Now using Jones Matrices, compute corrupted visibilities for sources 
# and baselines. Essentially we are predicting that the observed
# visibilities should look like those computed in this step.
    interferometer_list = [(ant1, ant2) for ant1 in station_list for ant2 in station_list if ant1 < ant2]
    forest_baseline_predict_trees(ns, interferometer_list, source_model)

# create sinks to drive system
    forest_create_sink_sequence(ns, interferometer_list)
    pass


Settings.forest_state.cache_policy = 100  # 1 for smart caching, 100 for full caching
Settings.orphans_are_roots = False

if __name__ == '__main__':


    Timba.TDL._dbg.set_verbose(5);
    ns = NodeScope();
    _define_forest(ns);


    ns.Resolve();
    pass
              