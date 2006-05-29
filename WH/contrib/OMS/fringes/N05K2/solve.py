from Timba.TDL import *
from Timba.Meq import meq
from numarray import *
import os
import random

import models
from Timba.Contrib.OMS.IfrArray import IfrArray
from Timba.Contrib.OMS.Observation import Observation
from Timba.Contrib.OMS.Patch import Patch
from Timba.Contrib.OMS.CorruptComponent import CorruptComponent 
from Timba.Contrib.OMS.SkyComponent import create_polc 
from Timba.Contrib.OMS.PointSource import PointSource 
from Timba.Contrib.OMS.GaussianSource import GaussianSource 
from Timba.Contrib.OMS import Jones
from Timba.Contrib.OMS import Bookmarks


# MS name
TDLRuntimeOption('msname',"MS",["n05k2.ms"]);

TDLRuntimeOption('input_column',"Input MS column",["DATA","MODEL_DATA","CORRECTED_DATA"],default=0);
TDLRuntimeOption('output_column',"Output corrected data to MS column",[None,"DATA","MODEL_DATA","CORRECTED_DATA"],default=3);
TDLRuntimeOption('tile_size',"Tile size (timeslots)",[1,2,5,30,60,120,180,360]);

TDLRuntimeOption('field_index',"Field ID",[0,1,2,3,4]);
TDLRuntimeOption('ddid_index',"Data description ID (band)",[0,1,2,3]);
TDLRuntimeOption('channel_select',"Channel selection",[None,[4,59]]);

# how much to perturb starting values of solvables
TDLRuntimeMenu('Parameter options',
  TDLOption('flux_perturbation',"Perturb fluxes by (rel.)",["random",.1,.2,-.1,-.2]),
  TDLOption('pos_perturbation',"Perturb positions by (arcsec)",[.1,.25,1,2]),
  TDLOption('use_previous',"Reuse solution from previous time interval",False,
  doc="""If True, solutions for successive time domains will start with
the solution for a previous domain. Normally this speeds up convergence; you
may turn it off to re-test convergence at each domain."""),
  TDLOption('use_mep',"Reuse solutions from MEP table",False,
  doc="""If True, solutions from the MEP table (presumably, from a previous
run) will be used as starting points. Turn this off to solve from scratch.""")
);

# solver runtime options
TDLRuntimeMenu("Solver options",
  TDLOption('solver_debug_level',"Solver debug level",[0,1,10]),
  TDLOption('solver_lm_factor',"Initial solver LM factor",[1,.1,.01,.001]),
  TDLOption('solver_epsilon',"Solver convergence threshold",[.01,.001,.0001,1e-5,1e-6]),
  TDLOption('solver_num_iter',"Max number of solver iterations",[30,50,100,1000])
);
TDLRuntimeOption('imaging_mode',"Imaging mode",["mfs","channel"]);
  
TDLCompileOption('stations_list',"Station list",[[1,2,3,4,7,8],[1,2,7]]);
TDLCompileOption('source_model',"Source model",[
    models.cps_3C345,
    models.cgs_3C345
  ],default=0);
TDLCompileMenu("Fitting options",
  TDLOption('fringe_deg_time',"Polc degree (time) for fringe fitting",[0,1,2,3,4,5,6]),
  TDLOption('fringe_deg_freq',"Polc degree (freq) for fringe fitting",[0,1,2,3,4]),
  TDLOption('gain_deg_time',"Polc degree (time) for gain fitting",[0,1,2,3,4]),
  TDLOption('gain_deg_freq',"Polc degree (freq) for gain fitting",[0,1,2,3,4]),
  TDLOption('flux_constraint',"Flux constraint",[None,[0.0,5.0],[1.,5.0],[2.,5.]]),
  TDLOption('constraint_weight',"Weight of flux constraint",["intrinsic",100,1000,10000])
);

TDLCompileOption('output_type',"Output visiblities",["corrected","residual"]);

source_table = "sources.mep";
mep_table = "calib.mep";

def get_source_table ():
  return msname+"/"+source_table;

def get_mep_table ():
  return msname+"/"+mep_table;


### MS input queue size -- must be at least equal to the no. of ifrs
ms_queue_size = 500

ms_selection = None
#or record(channel_start_index=0,
#          channel_end_index=0,
#          channel_increment=1,
#          selection_string='')

ms_output = True     # if True, outputs to MS, else to BOIO dump   Tony

selection_string = "TIME < 4637030700";


# bookmarks
Settings.forest_state = record(bookmarks=[
  record(name='Predicted visibilities',page=Bookmarks.PlotPage(
      ["visibility:all:G:1:2","spigot:1:2","residual:1:2"],
      ["visibility:all:G:1:7","spigot:1:7","residual:1:7"],
      ["visibility:all:G:2:7","spigot:2:7","residual:2:7"]
  )), 
  record(name='Corrected visibilities',page=Bookmarks.PlotPage(
      ["corrected:1:2","corrected:1:7"],
      ["corrected:2:7"]
  )), 
  record(name='Source solutions',page=Bookmarks.PlotPage(
      ["I:3C345","sigma1:3C345"],
      ["sigma2:3C345","phi:3C345"],
      ["solver"]
  )),
  record(name='Flux and phase solutions',page=Bookmarks.PlotPage(
      ["I:3C345","phase:L:1"],
      ["phase:L:2","phase:L:7"],
      ["solver"]
  )),
  record(name='Baseline phase solutions',page=Bookmarks.PlotPage(
      ['phase:R:1:2','phase:L:1:2'],
      ['phase:R:1:7','phase:L:1:7'],
      ['phase:R:2:7','phase:L:2:7']
  )),
  record(name='Gain solutions',page=Bookmarks.PlotPage(
      ['gain:R:1','gain:R:2'],
      ['gain:R:7','gain:L:1'],
      ['gain:L:2','gain:L:7']
  )),
]);

def gain_parm (tdeg,fdeg):
  """helper function to create a t/f parm for gain.
  """;
  polc = meq.polc(zeros((tdeg+1,fdeg+1))*0.0);
  polc.coeff[0,0] = 1;
  return Meq.Parm(polc,shape=shape,real_polc=polc,node_groups='Parm',
                  table_name=get_mep_table());


def phase_parm (tdeg,fdeg):
  """helper function to create a t/f parm for phase, including constraints.
  Placeholder until Maaijke implements periodic constraints.
  """;
  polc = meq.polc(zeros((tdeg+1,fdeg+1))*0.0,
            scale=array([3600.,8e+8,0,0,0,0,0,0]));
  shape = [tdeg+1,fdeg+1];
  # work out constraints on coefficients
  # maximum excursion in freq is pi/2
  # max excursion in time is pi/2
  dt = .2;
  df = .5;
  cmin = [];
  cmax = [];
  for it in range(tdeg+1):
    for jf in range(fdeg+1):
      mm = math.pi/(dt**it * df**jf );
      cmin.append(-mm);
      cmax.append(mm);
  cmin[0] = -1e+9;
  cmax[0] = 1e+9;
  return Meq.Parm(polc,shape=shape,real_polc=polc,node_groups='Parm',
                  constrain_min=cmin,constrain_max=cmax,
                  table_name=get_mep_table());


def _define_forest(ns):
  # create array model
  array = IfrArray(ns,stations_list);
  observation = Observation(ns,circular=True);
  
  # create source model
  global source_list;
  source_list = source_model(ns,observation,get_source_table());
  # create all-sky patch for source model
  allsky = Patch(ns,'all',observation.phase_centre);
  allsky.add(*source_list);
  
  # Add solvable G jones terms
  for station in array.stations():
    gr = ns.gain('R',station) << gain_parm(gain_deg_time,gain_deg_freq);
    gl = ns.gain('L',station) << gain_parm(gain_deg_time,gain_deg_freq);
    pr = ns.phase('R',station) << phase_parm(fringe_deg_time,fringe_deg_freq);
    pl = ns.phase('L',station) << phase_parm(fringe_deg_time,fringe_deg_freq);
    ns.G(station) << Meq.Matrix22(Meq.Polar(gr,pr),0,0,Meq.Polar(gl,pl));
    
  # attach the G Jones series to the all-sky patch
  corrupt_sky = CorruptComponent(ns,allsky,label='G',station_jones=ns.G);

  # create simulated visibilities for the sky
  predict = corrupt_sky.visibilities(array,observation);
  
  # create a "clean" predict for the sky
  # clean_predict = allsky.visibilities(array,observation);
  
  # now create spigots, condeqs and residuals
  condeqs = [];
  for sta1,sta2 in array.ifrs():
    spigot = ns.spigot(sta1,sta2) << Meq.Spigot( station_1_index=sta1-1,
                                                 station_2_index=sta2-1,
                                                 flag_bit=4,
                                                 input_col='DATA');
    weight = ns.weight(sta1,sta2) << Meq.Spigot( station_1_index=sta1-1,
                                                 station_2_index=sta2-1,
                                                 flag_mask=0,
                                                 input_col='WEIGHT');
    pred = predict(sta1,sta2);
    ce = ns.ce(sta1,sta2) << Meq.Condeq(spigot,pred) * weight / Meq.Sum(weight);
    condeqs.append(ce);
    # subtract nodes compute residuals
    if output_type == "residual":
      ns.residual(sta1,sta2) << spigot - pred;
      
  # now create nodes to apply correction
  # in residual mode we apply it to the residual data only
  # in corrected mode, apply directly to spigot
  if output_type == "residual":
    Jones.apply_correction(ns.corrected,ns.residual,ns.G,array.ifrs());
  else:
    Jones.apply_correction(ns.corrected,ns.spigot,ns.G,array.ifrs());
    
  # set up a non-default condeq poll order for efficient parallelization 
  # (i.e. poll child 1:2, 3:4, 5:6, ..., 25:26, then the rest)
  cpo = [];
  for i in range(array.num_stations()/2):
    (sta1,sta2) = array.stations()[i*2:(i+1)*2];
    cpo.append(ns.ce(sta1,sta2).name);
  if constraint_weight != "intrinsic":
    ns.flux_constraint << flux_constraint;
    # create boundary constraints for fluxes
    for src in source_list:
      sti = src.stokes("I");
      base = ns.base_constr("I",src.name) << \
        (src.stokes("I") - ns.flux_constraint)*constraint_weight;
      bound = ns.constraint(src.name) << Meq.Condeq(
        Meq.Sqr(base) - Meq.Abs(base)*base,0
      );
      condeqs.append(bound);
      
  # create baseline phases (for visualization purposes only)
  visnodes = [];
  for sta1,sta2 in array.ifrs():
    for pol in ('R','L'):
      p = ns.phase(pol,sta1,sta2) << ns.phase(pol,sta1) - ns.phase(pol,sta2);
      visnodes.append(p);
  for sta in array.stations():
    for pol in ('R','L'):
      visnodes.append(ns.gain(pol,sta));
  ns.vis = Meq.ReqMux(*visnodes);
    
  # create solver node
  ns.solver << Meq.Solver(children=condeqs,child_poll_order=cpo);
  
  # create sinks and reqseqs 
  for sta1,sta2 in array.ifrs():
    reqseq = Meq.ReqSeq(ns.solver,ns.vis,ns.corrected(sta1,sta2),
                  result_index=2,cache_num_active_parents=1);
    ns.sink(sta1,sta2) << Meq.Sink(station_1_index=sta1-1,
                                   station_2_index=sta2-1,
                                   flag_bit=4,
                                   corr_index=[0,1,2,3],
                                   flag_mask=-1,
                                   output_col='PREDICT',
                                   children=reqseq
                                   );
                                   
  # create visdatamux
  global _vdm;
  _vdm = ns.VisDataMux << Meq.VisDataMux;
  ns.VisDataMux.add_children(*[ns.sink(*ifr) for ifr in array.ifrs()]);
  ns.VisDataMux.add_stepchildren(*[ns.spigot(*ifr) for ifr in array.ifrs()]);
  ns.VisDataMux.add_stepchildren(*[ns.weight(*ifr) for ifr in array.ifrs()]);
  
  
def create_solver_defaults(num_iter=60,convergence_quota=0.9,solvable=[]):
  solver_defaults=record()
  solver_defaults.num_iter      = solver_num_iter
  solver_defaults.epsilon       = solver_epsilon
  solver_defaults.epsilon_deriv = solver_epsilon
  solver_defaults.lm_factor     = solver_lm_factor
  solver_defaults.convergence_quota = convergence_quota
  solver_defaults.balanced_equations = False
  solver_defaults.debug_level = solver_debug_level;
  solver_defaults.save_funklets= True
  solver_defaults.last_update  = True
#See example in TDL/MeqClasses.py
  solver_defaults.solvable     = record(command_by_list=(record(name=solvable,
                                       state=record(solvable=True)),
                                       record(state=record(solvable=False))))
  return solver_defaults
  
def set_node_state (mqs,node,fields_record):
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
  

def create_inputrec ():
  rec = record();
  rec.ms_name          = msname
  rec.data_column_name = input_column;
  rec.tile_size        = tile_size
  rec.selection =  record();
  rec.selection.ddid_index       = ddid_index;
  rec.selection.field_index      = field_index;
  rec.selection.selection_string = selection_string;
  if channel_select is not None:
    rec.selection.channel_start_index = channel_select[0];
    rec.selection.channel_end_index = channel_select[1];
  rec = record(ms=rec);
  rec.python_init='Timba.Contrib.OMS.ReadVisHeader';
  rec.mt_queue_size = ms_queue_size;
  return rec;


def create_outputrec (outcol):
  rec=record()
  rec.mt_queue_size = ms_queue_size;
  if ms_output:
    rec.write_flags=False
    rec.predict_column=outcol;
    return record(ms=rec);
  else:
    rec.boio_file_name = "boio."+msname+".solve."+str(tile_size);
    rec.boio_file_mode = 'W';
    return record(boio=rec);


def _run_solve_job (mqs,solvables):
  """common helper method to run a solution with a bunch of solvables""";
  req = meq.request();
  req.input  = create_inputrec();
  if output_column is not None:
    req.output = create_outputrec(output_column);

  # set solvables list in solver
  solver_defaults = create_solver_defaults(solvable=solvables)
  set_node_state(mqs,'solver',solver_defaults)

  # req.input.max_tiles = 1;  # this can be used to shorten the processing, for testing
  mqs.execute('VisDataMux',req,wait=False);
  pass

def _perturb_parameters (mqs,solvables,pert="random",
                        absolute=False,random_range=[0.2,0.3],constrain=None):
  global perturbation;
  for name in solvables:
    polc = mqs.getnodestate(name).real_polc;
    if absolute:  # absolute pert value given
      polc.coeff[0,0] += pert;
    elif pert == "random":  # else random pert
      polc.coeff[0,0] *= 1 + random.uniform(*random_range)*random.choice([-1,1]);
    else: # else perturb in relative terms
      polc.coeff[0,0] *= (1 + pert);
    parmstate = record(init_funklet=polc,
      use_previous=use_previous,reset_funklet=not use_mep);
    if constrain is not None:
      parmstate.constrain = constrain;
    print name,parmstate;
    set_node_state(mqs,name,parmstate);
  return solvables;
    
def _reset_parameters (mqs,solvables,value=None,use_table=False,constrain=None,reset=False):
  for name in solvables:
    polc = mqs.getnodestate(name).real_polc;
    if value is not None:
      polc.coeff[()] = 0;
      polc.coeff[0,0] = value;
    reset_funklet = reset or not (use_table or use_mep);
    parmstate = record(init_funklet=polc, \
                use_previous=use_previous,reset_funklet=reset_funklet);
    if constrain is not None:
      parmstate.constrain = constrain;
    set_node_state(mqs,name,parmstate);
  return solvables;

arcsec_to_rad = math.pi/(180*3600);

def _solvable_source (mqs,src):
  if constraint_weight == "intrinsic":
    constrain = flux_constraint;
  else:
    constrain = None;
  solvables = _reset_parameters(mqs,['I0:'+src.name],constrain=constrain);
  _reset_parameters(mqs,['Q:'+src.name for src in source_list],constrain=[0.,.5]);
  _reset_parameters(mqs,['U:'+src.name for src in source_list],constrain=[0.,.5]);
  _reset_parameters(mqs,['V:'+src.name for src in source_list],constrain=[0.,.5]);
  if isinstance(src,GaussianSource):
    solvables += _reset_parameters(mqs,['sigma1:'+src.name]);
    solvables += _reset_parameters(mqs,['sigma2:'+src.name]);
    solvables += _reset_parameters(mqs,['phi:'+src.name]);
  return solvables;
    
def _reset_gains (mqs):
  _reset_parameters(mqs,['gain:L:'+str(sta) for sta in stations_list],1);
  _reset_parameters(mqs,['gain:R:'+str(sta) for sta in stations_list],1);

def _solvable_gains (mqs):
  # gain of station 1 is fixed
  _reset_parameters(mqs,['gain:L:'+str(stations_list[0])],1);
  _reset_parameters(mqs,['gain:R:'+str(stations_list[0])],1);
  # other gains solvable
  solvables = _reset_parameters(mqs,['gain:L:'+str(sta) for sta in stations_list[1:]],1);
  solvables += _reset_parameters(mqs,['gain:R:'+str(sta) for sta in stations_list[1:]],1);
  return solvables;

def _solvable_phases (mqs):
  solvables = _reset_parameters(mqs,['phase:L:'+str(sta) for sta in stations_list],0);
  solvables += _reset_parameters(mqs,['phase:R:'+str(sta) for sta in stations_list],0);
  return solvables;
  
def _tdl_job_1_solve_for_flux_and_phases (mqs,parent,**kw):
  solvables = [];
  for src in source_list:
    solvables += _solvable_source(mqs,src);
  solvables += _solvable_phases(mqs,);
  _run_solve_job(mqs,solvables);

def _tdl_job_3_solve_for_flux_and_phases_and_gains (mqs,parent,**kw):
  solvables = [];
  for src in source_list:
    solvables += _solvable_source(mqs,src);
  solvables += _solvable_gains(mqs);
  solvables += _solvable_phases(mqs);
  _run_solve_job(mqs,solvables);

def _tdl_job_8_clear_out_all_previous_solutions (mqs,parent,**kw):
  os.system("rm -fr "+get_source_table());
  os.system("rm -fr "+get_mep_table());

def _tdl_job_9a_make_corrected_image (mqs,parent,**kw):
  os.spawnvp(os.P_NOWAIT,'glish',['glish','-l','make_image.g',output_column,
      'ms='+msname,'mode='+imaging_mode]);
  pass
  
def _tdl_job_9b_make_residual_image (mqs,parent,**kw):
  os.spawnvp(os.P_NOWAIT,'glish',['glish','-l','make_image.g','RESIDUAL',
      'ms='+msname,'mode='+imaging_mode]);
  pass


Settings.forest_state.cache_policy = 100  # -1 for minimal, 1 for smart caching, 100 for full caching
Settings.orphans_are_roots = True

if __name__ == '__main__':


    Timba.TDL._dbg.set_verbose(5);
    ns = NodeScope();
    _define_forest(ns);


    ns.Resolve();
    pass
              
