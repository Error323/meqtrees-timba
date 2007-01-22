from Timba.TDL import *
from Timba.Meq import meq
from numarray import *
import os
import random

import Meow

from Meow import Bookmarks
from Meow import Utils

# number of stations
TDLCompileOption('num_stations',"Number of stations",[14,3],more=int);

# enable standard MS options from Meow
Utils.include_ms_options(
  tile_sizes=[1,10,100],
  channels=[[15,40,1]]
);

TDLRuntimeMenu("Solver options",*Utils.solver_options());

# include standard imaging menu
TDLRuntimeMenu("Make image",*Utils.imaging_options(npix=512,arcmin=72));
  
 

def _define_forest(ns):
  # create array model
  array = Meow.IfrArray(ns,range(1,num_stations+1));
  observation = Meow.Observation(ns);
  # setup Meow global context
  Meow.Context.set(array=array,observation=observation);
  
  # create 343 source model
  I = ns.I("3C343") << Meq.Parm(1,shape=(1,4),table_name='sources.mep');
  Q = ns.Q("3C343") << Meq.Parm(0,shape=(1,4),table_name='sources.mep');
  I1 = ns.I("3C343.1") << Meq.Parm(1,shape=(1,2),table_name='sources.mep');
  Q1 = ns.Q("3C343.1") << Meq.Parm(0,shape=(1,2),table_name='sources.mep');
  
  sources = [
    Meow.PointSource(ns,name="3C343.1",I=I1,Q=Q1,
                     direction=(4.356645791155902,1.092208429052697)),
    Meow.PointSource(ns,name='3C343',I=I,Q=Q,
                     direction=(4.3396003966265599,1.0953677174056471)),
  ];
  
  # create all-sky patch for source model
  allsky = Meow.Patch(ns,'all',observation.phase_centre);
  allsky.add(*sources);
  
  # create simulated visibilities for the sky
  predict = allsky.visibilities();

  # create spigots, condeqs, residuals
  for p,q in array.ifrs():
    ns.spigot(p,q) << Meq.Spigot(station_1_index=p-1,station_2_index=q-1);
    ns.ce(p,q) << Meq.Condeq(ns.spigot(p,q),predict(p,q));
    ns.residual(p,q) << ns.spigot(p,q) - predict(p,q);
    
  # create solver
  ns.solver << Meq.Solver(*[ns.ce(p,q) for p,q in array.ifrs()]);
  
  # create sequencer and sinks
  for p,q in array.ifrs():
    ns.sink(p,q) << Meq.Sink(
      ns.reqseq(p,q) << Meq.ReqSeq(ns.solver,ns.residual(p,q),result_index=1),
    station_1_index=p-1,station_2_index=q-1);
    
  # create visualizers for spigots and residuals
  ns.inspect_spigots << Meq.Composer(
    dims=[array.num_ifrs(),2,2],
    plot_label=["%s-%s"%(p,q) for p,q in array.ifrs()],
    *[ns.spigot(p,q) for p,q in array.ifrs()]
  );
  ns.inspect_residuals << Meq.Composer(
    dims=[array.num_ifrs(),2,2],
    plot_label=["%s-%s"%(p,q) for p,q in array.ifrs()],
    *[ns.reqseq(p,q) for p,q in array.ifrs()]
  );
    
  # create VisDataMux
  ns.VisDataMux = Meq.VisDataMux(pre=ns.inspect_spigots,post=ns.inspect_residuals,*[ns.sink(p,q) for p,q in array.ifrs()]);

  # add bookmarks
  bk = Bookmarks.Page("Fluxes and coherencies",2,3);
  bk.add(I);
  bk.add(I1);
  bk.add(Q);
  bk.add(Q1);
  bk.add(ns.solver);
  pg = Bookmarks.Page("Inspectors",1,2);
  pg.add(ns.inspect_spigots,viewer="Collections Plotter");
  pg.add(ns.inspect_residuals,viewer="Collections Plotter");


def _tdl_job_1_run_flux_solution (mqs,parent,**kw):
  solvables = [ "I:3C343","I:3C343.1","Q:3C343","Q:3C343.1" ];
  Utils.run_solve_job(mqs,solvables);
  
  
def _tdl_job_2_clear_out_all_previous_solutions (mqs,parent,**kw):
  from qt import QMessageBox
  if QMessageBox.warning(parent,"Clearing solutions","This will clear out <b>all</b> previously obtained calibrations. Are you sure?",
        QMessageBox.Yes,QMessageBox.No|QMessageBox.Default|QMessageBox.Escape) == QMessageBox.Yes:
    try:    os.system("rm -fr sources.mep");
    except: pass;
  
  
  


Settings.forest_state.cache_policy = 1  # -1 for minimal, 1 for smart caching, 100 for full caching

if __name__ == '__main__':


    Timba.TDL._dbg.set_verbose(5);
    ns = NodeScope();
    _define_forest(ns);


    ns.Resolve();
    pass
              
