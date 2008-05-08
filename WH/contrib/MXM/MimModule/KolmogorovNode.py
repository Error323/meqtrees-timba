# standard preamble
from Timba.TDL import *
from Timba import pynode
from Timba import dmi
from Timba import utils
from Timba.Meq import meq
from Timba.Contrib.MXM.MimModule import PhaseScreen
from Timba.Contrib.MXM.MimModule import Kolmogorov_MIM

Settings.forest_state.cache_policy = 100;

_dbg = utils.verbosity(0,name='test_pynode');
_dprint = _dbg.dprint;
_dprintf = _dbg.dprintf;

initialized=False;

# This class is meant to illustrate the pynode interface. All pynodes
# need to be derived from the Timba.pynode.PyNode class.
class KolmogorovNode (pynode.PyNode):
    # An __init__ method is not necessary at all. If you do define your 
    # own for some reason, make sure you call pynode.PyNode.__init__() 
    def __init__ (self,*args):
        pynode.PyNode.__init__(self,*args);
        self.set_symdeps('domain');
 
        

    def update_state (self,mystate):
        global initialized;
        # mystate is a magic "state helper" object is used both to set up
        # initial/default state, and to update state on the fly later.
        
        # This does the following:
        #  - checks the incoming state record for field 'a'
        #  - if present, sets self.a = staterec.a
        #  - if not present but we're initializing the node, sets self.a = 3,
        #    and also sets staterec.a = 3 on the C++ side
        #  - if not present and not initializing, does nothing
        mystate('scale',200); #scale in km.
        mystate('speedx',0.); #speed in m/s.
        mystate('speedy',0.); #speed in m/s.
        mystate('grid_size',10); #scale in km.
        mystate('beta',5./3.); #scale in km.

        if not initialized:
            PhaseScreen.init_phasescreen(self.grid_size,self.beta);
            initialized=True;
        
    def get_result (self,request,*children):
        if len(children)<1:
            raise TypeError,"this is NOT a leaf node, At least 1  child with piercepoints expected!";
        res1=children[0];
        vs1=res1.vellsets; #pierce_points, vector of length 2 or 3 (x,y(,z))
        vector_size=len(vs1);
        #for now use fist two:
        if vector_size<2:
            raise TypeError,"vector size of child 1 too small, at leat x/y expected";
        xv=vs1[0].value[0];
        yv=vs1[1].value[0];
        if vs1[0].has_field('shape'):
            shapex=vs1[0].shape;
        else:
            shapex=(1,);
        if vs1[1].has_field('shape'):
            shapey=vs1[1].shape;
        else:
            shapey=(1,);
            
        
        cells=request.cells;
        seg=cells.segments.time;
        startt=seg.start_index;
        endt=seg.end_index;
        time=cells.grid.time;
        if startt>=endt:
            time=[time,];
        val=[];
        for it in range(startt,endt+1):
            if shapex[0]>1:   
                xv=vs1[0].value[it];
            if shapey[0]>1:   
                yv=vs1[1].value[it];



                xshift=(time[it]-time[0])*self.speedx;
                yshift=(time[it]-time[0])*self.speedy;
                xn=((xv+xshift)/self.scale)*self.grid_size+self.grid_size;
                yn=((yv+yshift)/self.scale)*self.grid_size+self.grid_size;
                xn=int(xn)%(self.grid_size*2)  # zorg dat xn een integer tussen 0 en 2*grid_size is
                yn=int(yn)%(self.grid_size*2)  # zorg dat xn een integer tussen 0 en 2*grid_size is
                
                val.append(PhaseScreen.phasescreen[xn][yn]);
        #fill result
        res = meq.result(0,cells);
        val2=meq.vells(shape=meq.shape(endt+1,));
        val2[:]=val;
        vs=meq.vellset(val2);
        res.vellsets=[vs,]
        return res;
