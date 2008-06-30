from Timba.TDL import *
import Meow
from Meow import Context
from Meow import ParmGroup,Bookmarks
import ZJones_ivb


Settings.forest_state.cache_policy = 0;
mssel = Context.mssel = Meow.MSUtils.MSSelector(has_input=True,tile_sizes=[1,10,50],flags=False);

# MS compile-time options
TDLCompileOptions(*mssel.compile_options());
TDLCompileOption('N_ANT',"Number of stations",[20,31,36,49],more=float)
# MS run-time options
TDLRuntimeMenu("MS/data selection options",*mssel.runtime_options());
# output mode menu
CORRELATIONS = [ "XX","XY","YX","YY" ];
CORR_INDICES = dict([(corr,index) for index,corr in enumerate(CORRELATIONS)]);
ALL_CORRS = "XX XY YX YY";
DIAG_CORRS = "XX YY";
CROSS_CORRS = "YX XY";
SINGLE_CORR = "XX";
    
run_model=TDLCompileOption('run_option',"What do we want to do",['calibrate','simulate'])

calibrate_options= TDLCompileMenu("Existing UV data Options",
                                  TDLOption('do_solve',"Calibrate",True),
                                  TDLOption('cal_corr',"Use correlations",
                                            [ALL_CORRS,DIAG_CORRS,CROSS_CORRS,SINGLE_CORR]),
                                  TDLOption('do_subtract',"Subtract sky model and generate residuals",True),
                                  TDLMenu("Correct the data or residuals",
                                          TDLMenu("include sky-Jones correction",
                                                  TDLOption('src_name',"name of the source (if None, first source in list is used)",[None,"S+0+0"],more=str),
                                                  toggle='do_correct_sky',open=True),
                                          toggle='do_correct',open=True))

simulate_options= TDLCompileMenu("Simulation Options",
                                 # noise option
                                 TDLOption('do_add',"Add sky model to existing data to increase number of sources",False),
                                 TDLOption("noise_stddev","Add noise, Jy",[None,1e-6,1e-3],more=float))


do_not_simulate=(run_option=='calibrate');

def change_run_option(model):
    global do_not_simulate;
    simulate_options.show(model=='simulate');
    calibrate_options.show(model=='calibrate');
    do_not_simulate=(model=='calibrate');

run_model.when_changed(change_run_option);


# now load optional modules for the ME maker
from Meow import MeqMaker
meqmaker = MeqMaker.MeqMaker(solvable=do_solve and run_option=='calibrate');

# specify available sky models
# these will show up in the menu automatically
#import central_point_source
from Timba.Contrib.OMS.Siamese import gridded_sky
from Timba.Contrib.IVB.MimModule import gridded_sky_ivb
import Meow.LSM
lsm = Meow.LSM.MeowLSM(include_options=False);
meqmaker.add_sky_models([lsm,gridded_sky,gridded_sky_ivb]);

from Timba.Contrib.OMS.Calico import solvable_jones
meqmaker.add_uv_jones('G','receiver gains/phases',
  [ solvable_jones.DiagAmplPhase(),
    solvable_jones.FullRealImag() ]);

#meqmaker.add_uv_jones('B','bandpass',
#  [ solvable_jones.DiagBandPass()]);

meqmaker.add_sky_jones('Z','iono',[ZJones_ivb.ZJones()]);
from Timba.Contrib.MXM.MimModule import solvable_sky_jones;
meqmaker.add_sky_jones('GD','directional receiver gains/phases',
  [ solvable_sky_jones.DiagAmplPhase(),
    solvable_sky_jones.FullRealImag() ]);
# very important -- insert meqmaker's options properly
TDLCompileOptions(*meqmaker.compile_options());


def _define_forest(ns):
    #make pynodes, xyzcomponent for sources
    ANTENNAS = mssel.get_antenna_set(range(1,N_ANT+1));
    array = Meow.IfrArray(ns,ANTENNAS,mirror_uvw=True,ms_uvw=False);
    observation = Meow.Observation(ns);
    Meow.Context.set(array,observation);
    # make a predict tree using the MeqMaker
    if do_solve or do_subtract or not do_not_simulate:
        outputs=predict = meqmaker.make_tree(ns);

    #make a list of selected corrs
    selected_corrs = cal_corr.split(" ");

    # make spigot nodes
    if not do_not_simulate and do_add:
        spigots = spigots0 = outputs = array.spigots();
        sums = ns.sums;
        for p,q in array.ifrs():
            sums(p,q) << spigots(p,q) + predict(p,q);
        outputs = sums;

    # make spigot nodes
    if do_not_simulate:
        spigots = spigots0 = outputs = array.spigots();
        # make nodes to compute residuals
        

        # make nodes to compute residuals
        if do_subtract:
            residuals = ns.residuals;
            for p,q in array.ifrs():
                residuals(p,q) << spigots(p,q) - predict(p,q);
            outputs = residuals;

        # and now we may need to correct the outputs
        if do_correct:
            if do_correct_sky:
                if src_name:
                    sky_correct = src_name;
                else:
                    srcs = meqmaker.get_source_list(ns);
                    sky_correct = srcs and srcs[0];

                
            else:
                sky_correct = None;
            outputs = meqmaker.correct_uv_data(ns,outputs,sky_correct=sky_correct);

        # make solve trees
        if do_solve:
            # extract selected correlations
            if cal_corr != ALL_CORRS:
                index = [ CORR_INDICES[c] for c in selected_corrs ];
                for p,q in array.ifrs():
                    ns.sel_predict(p,q) << Meq.Selector(predict(p,q),index=index,multi=True);
                    ns.sel_spigot(p,q)  << Meq.Selector(spigots(p,q),index=index,multi=True);
                spigots = ns.sel_spigot;
                predict = ns.sel_predict;
            model    = predict;
            observed = spigots;

            # make a solve tree
            solve_tree = Meow.StdTrees.SolveTree(ns,model);
            # the output of the sequencer is either the residuals or the spigots,
            # according to what has been set above
            outputs = solve_tree.sequencers(inputs=observed,outputs=outputs);


    # throw in a bit of noise
    if not do_not_simulate and noise_stddev:
        # make two complex noise terms per station (x/y)
        noisedef = Meq.GaussNoise(stddev=noise_stddev)
        noise_x = ns.sta_noise('x');
        noise_y = ns.sta_noise('y');
        for p in array.stations():
            noise_x(p) << Meq.ToComplex(noisedef,noisedef);
            noise_y(p) << Meq.ToComplex(noisedef,noisedef);
        # now combine them into per-baseline noise matrices
        for p,q in array.ifrs():
            noise = ns.noise(p,q) << Meq.Matrix22(
                noise_x(p)+noise_x(q),noise_x(p)+noise_y(q),
                noise_y(p)+noise_x(q),noise_y(p)+noise_y(q)
                );
            ns.noisy_predict(p,q) << outputs(p,q) + noise;
        outputs = ns.noisy_predict;
    # make sinks and vdm.
    # The list of inspectors comes in handy here
    Meow.StdTrees.make_sinks(ns,outputs,spigots=None,post=meqmaker.get_inspectors());

    if not do_not_simulate:
        #add simulate job
        TDLRuntimeJob(job_simulate,"Simulate");


    # very important -- insert meqmaker's runtime options properly
    # this should come last, since runtime options may be built up during compilation.
    #TDLRuntimeOptions(*meqmaker.runtime_options(nest=False));
    # and insert all solvejobs
    TDLRuntimeOptions(*ParmGroup.get_solvejob_options());
    # finally, setup imaging options
    imsel = mssel.imaging_selector(npix=512,arcmin=meqmaker.estimate_image_size());
    TDLRuntimeMenu("Imaging options",*imsel.option_list());

    
def job_simulate(mqs,parent,wait=False):
    mqs.execute('VisDataMux',mssel.create_io_request(),wait=wait);

#def _tdl_job_1_simulate_MS (mqs,parent,wait=False):
#  mqs.execute('VisDataMux',mssel.create_io_request(),wait=wait);

# some bit to run the script from the command line
# to call the script from the command line, type
#> python scriptname.py -r
#
# to get verbose output add: -dmeqserver=3

if __name__ == '__main__':

    if '-r' in sys.argv:
        from Timba.Apps import meqserver
        from Timba.TDL import Compile
        
        mqs = meqserver.default_mqs(wait_init=10);
        TDLOptions.config.read(".tdl.conf");
        
        (mod,ns,msg) = Compile.compile_file(mqs,__file__)
        mod._define_forest(mqs,None,wait=True)
        
    else:
        Timba.TDL._dbg.set_verbose(5)
        ns = NodeScope();
        _define_forest(ns)
        ns.Resolve();