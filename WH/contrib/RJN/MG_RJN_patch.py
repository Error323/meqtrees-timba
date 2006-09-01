#!/usr/bin/python

########
## This script needs to be run in the MeqBrowser,

# The script compares resut from the UVBrick / UVInterpolate with that of the DFT node.
# There is a solver node that solves for the source position in the DFT node
# The CondEq node compares the Result form the UVInterpolate and the DFT nodes
# BEWARE: the PatchComposer node has the source positions in frequency DEPENDENT l'  and m' coordinates,
#                  and the sources are put on the nearest pixel.
#                  the DFT node has the source positions in frequency INDEPENDENT l and m coordinates.
#                  For this reason the Solver will not be able to accurately solve for the DFT source position.

# In the define_forest function the Tree is defined, including the position of the (only) source and the baseline 
#      under consideration.
# In the test_forest function the Frequency / Time domain is defined

# Get the Sixpack definition from RJN. 
from Timba.Contrib.RJN import RJN_sixpack

# Get some Python modules
import re
import math
import random

# for Bookmarks get JEN's forest state script
from Timba.Contrib.JEN import MG_JEN_forest_state

# Get TDL and Meq for the Kernel
from Timba.TDL import * 
from Timba.Meq import meq

# to force caching put 100
Settings.forest_state.cache_policy = 100

# List of source names, initiated to be empty
srcnames = []


########################################################
def _define_forest(ns):
 # srcnames is global: to be used inside _define_forest, _test_forest, and outside of them
 global srcnames   
 # we need pi=3.1415...
 import math
    
 # Read the sources from a text file
 # The test_sources file contains only sources with zero flux strength. In this way a Patch of 
 #    certain extent is obtained. Later a non-zero flux source is added.
 #
 # please change this according to your setup
 home_dir = os.environ['HOME']
 infile_name = home_dir + '/Timba/WH/contrib/RJN/test_sources.txt'
 infile=open(infile_name,'r')
 all=infile.readlines()
 infile.close()

 # regexp pattern
 pp=re.compile(r"""
   ^(?P<col1>\S+)  # column 1 'NVSS'
   \s*             # skip white space
   (?P<col2>[A-Za-z]\w+\+\w+)  # source name i.e. 'J163002+631308'
   \s*             # skip white space
   (?P<col3>\d+)   # RA angle - hr 
   \s*             # skip white space
   (?P<col4>\d+)   # RA angle - min 
   \s*             # skip white space
   (?P<col5>\d+(\.\d+)?)   # RA angle - sec
   \s*             # skip white space
   (?P<col6>\d+(\.\d+)?)   # eRA angle - sec
   \s*             # skip white space
   (?P<col7>\d+)   # Dec angle - hr 
   \s*             # skip white space
   (?P<col8>\d+)   # Dec angle - min 
   \s*             # skip white space
   (?P<col9>\d+(\.\d+)?)   # Dec angle - sec
   \s*             # skip white space
   (?P<col10>\d+(\.\d+)?)   # eDec angle - sec
   \s*             # skip white space
   (?P<col11>\d+)   # freq
   \s*             # skip white space
   (?P<col12>\d+(\.\d+)?)   # brightness - Flux
   \s*             # skip white space
   (?P<col13>\d*\.\d+)   # brightness - eFlux
   \s*
   \S+
   \s*$""",re.VERBOSE)


 # Construction of a Phase Center Two-Pack (RA, DEC)
 # For now this is done manually
 #
 # RA and Dec coordinates of the Patch Phase Center
 RA_0 = 4.35664870004
 Dec_0 = 1.09220644132

 pc_name = 'Phase Center';
 twoname = 'twopack['+pc_name+']';

 RA_root = RJN_sixpack.make_RA(pc_name,RA_0,ns);
 Dec_root = RJN_sixpack.make_Dec(pc_name,Dec_0,ns);
 tworoot = ns[twoname] << Meq.Composer(RA_root,Dec_root);
 
 child_rec = [twoname];

 lmax = 0
 mmax = 0
 linecount=0
 random.seed(0)

 # read each source and add a Sixpack to the child_rec
 for eachline in all:
  v=pp.search(eachline)
  if v!=None:
   linecount+=1
   print v.group('col2'), v.group('col12')
   sname=v.group('col2')
   srcnames.append(sname)
   
   # Go from RA and Dec to radians
   source_RA=float(v.group('col3'))+(float(v.group('col5'))/60.0+float(v.group('col4')))/60.0
   source_RA*=math.pi/12.0
   source_Dec=float(v.group('col7'))+(float(v.group('col9'))/60.0+float(v.group('col8')))/60.0
   source_Dec*=math.pi/180.0

   #sisif = math.log10( eval(v.group('col12')) )
   sisif = eval(v.group('col12')) 
   
   # Definition of Q%, U%, V%
   # However, since I=0.0 for all sources in test_sources.txt, this has no effect: Q,U,V are all zero.
   #qin = random.uniform(-0.2,0.2)
   #uin = random.uniform(-0.2,0.2)
   #vin = random.uniform(-0.01,0.01)
   #qin = 0.0;
   #uin = 0.0;
   #vin = 0.0;
   qin = 1.0;
   uin = 2.0;
   vin = 0.0;

   sixroot = RJN_sixpack.make_sixpack(srcname=sname,RA=source_RA,Dec=source_Dec,ISIF0=sisif,Qpct=qin,Upct=uin,Vpct=vin,ns=ns)

   sixname = 'sixpack[q='+sname+']';
   child_rec.append(sixname);

   # Determine the size of the grid. Hence, determine larges l and m values. 
   lc = math.cos(source_Dec)*math.sin(RA_0-source_RA)
   lm = math.cos(Dec_0)*math.sin(source_Dec) - math.sin(Dec_0)*math.cos(source_Dec)*math.cos(RA_0-source_RA)
   
   lmax = max(lmax,abs(lc))
   mmax = max(mmax,abs(lm))
 
 # Add one non-zero source (q=testsource) to the Patch
 # I=Q=U=V=1.0
 sname = 'testsource';
 source_RA = RA_0 + 4*0.0000183944088323;
 source_Dec = Dec_0 + 2*0.0000183944088323;
 sisif = 1.0;
 qin = 1.0;
 uin = 1.0;
 vin = 1.0;

 sixroot = RJN_sixpack.make_sixpack(srcname=sname,RA=source_RA,Dec=source_Dec,ISIF0=sisif,Qpct=qin,Upct=uin,Vpct=vin,ns=ns)

 sixname = 'sixpack[q='+sname+']';
 child_rec.append(sixname);

 print "Inserted %d sources" % linecount 
 print "maximum l and m out of Phase Center", lmax, mmax

 # At this point the Phase Center and all sources are combined into a "source list": child_rec.

 # For the UVW coordinates define X0,Y0,Z0, and delta 
 # (see UVBrick document and Thompson, Moran, and Swenson)
 X0 = 0.0;   # m
 Y0 = 2000.0; #m
 Z0 = 0.0;   #m

 delta  = math.pi/2;

 # Create the SixPack for the Patch Image
 # PatchComposer (SixPack)
 patch_root = ns['Patch['+pc_name+']'] << Meq.PatchComposer(children=child_rec);

 # Select the 4 Stokes planes
 #Selector (FourPack)
 select_root = ns['Select['+pc_name+']']<<Meq.Selector(children=patch_root,multi=True,index=[2,3,4,5]);

 # Go from 4 Stokes planes to 4 Correlation planes
 #Stokes
 stokes_root = ns['Stokes['+pc_name+']'] << Meq.Stokes(children=select_root);

 # FFT the 4 correlations
 #FFTBrick
 fft_root = ns['FFT['+pc_name+']']<<Meq.FFTBrick(children=stokes_root);

 # Now we can start interpolating the UV-plane.
 # For this we need a UVW coordinate Node
 #
 # X0, Y0, Z0
 x0_root = ns['X0']<<Meq.Constant(X0);
 y0_root = ns['Y0']<<Meq.Constant(Y0);
 z0_root = ns['Z0']<<Meq.Constant(Z0);

 # Sin(delta), Cos(delta)
 sd_root = ns['sindelta']<<Meq.Constant(math.sin(delta));
 cd_root = ns['cosdelta']<<Meq.Constant(math.cos(delta));

 # H(t) = 2 pi t / (24*3600)
 t_root = ns['time']<<Meq.Time();
 c_root = ns['time_c']<<Meq.Constant(2.0*math.pi/3600/24);
 t2_root = ns['time2']<<Meq.Multiply(children=[t_root,c_root]);

 # Cos(H(t)), Sin(H(t))
 c_root = ns['cos']<<Meq.Cos(children=[t2_root]);
 s_root = ns['sin']<<Meq.Sin(children=[t2_root]);

 # X0*cos(H), X0*sin(H), Y0*cos(H), Y0*sin(H)
 xc_root = ns['xc']<<Meq.Multiply(children=[x0_root,c_root]);
 xs_root = ns['xs']<<Meq.Multiply(children=[x0_root,s_root]);
 yc_root = ns['yc']<<Meq.Multiply(children=[y0_root,c_root]);
 ys_root = ns['ys']<<Meq.Multiply(children=[y0_root,s_root]);

 # u
 u_root = ns['U'] << Meq.Add(children=[xs_root,yc_root]);

 #v
 v1_root = ns['v1']<<Meq.Subtract(children=[ys_root,xc_root]);
 v2_root = ns['v2'] << Meq.Multiply(children=[v1_root,sd_root]);
 cz_root = ns['cz'] << Meq.Multiply(children=[cd_root,z0_root]);
 v_root = ns['V'] << Meq.Add(children=[v2_root,cz_root]);

 #w
 w2_root = ns['w2'] << Meq.Multiply(children=[v1_root,cd_root]);
 sz_root = ns['sz'] << Meq.Multiply(children=[sd_root,z0_root]);
 w_root = ns['W'] << Meq.Subtract(children=[sz_root,w2_root]);

 #uvw
 uvw_root = ns['UVW']<<Meq.Composer(children=[u_root,v_root,w_root]);

 # The actual Interpolation
 #  Method = 1: Bi-Cubic Hermite Interpolation (most accurate)
 #  Method = 2: 4th order polynomial interpolation
 #  Method = 3: Bi-linear interpolation
 #
 # If (Additional_Info = True) the UV interpolation tracks are plotted on the UV plane
 #
 #UVInterpol
 interpol_root = ns['UVInterpol['+pc_name+']']<<Meq.UVInterpol(Method=1,children=[fft_root,uvw_root],additional_info=True);
 
 # Now create the DFT node, to which we will compare the UVInterpol result.
 #
 #RA,Dec,RA_0,Dec_0
 ra_array = array([source_RA/0.001]);
 dec_array=array([source_Dec/0.001]);
 ra_polc=meq.polc(coeff=ra_array);
 dec_polc=meq.polc(coeff=dec_array);
 nRA_root = ns['nRA']<<Meq.Parm(ra_polc,node_groups='Parm');
 nDec_root = ns['nDec']<<Meq.Parm(dec_polc,node_groups='Parm');
 dRA_root = ns['dRA']<<Meq.Constant(0.001);
 dDec_root = ns['dDec']<<Meq.Constant(0.001);
 RA_root = ns['RA']<<Meq.Multiply(children=[nRA_root,dRA_root]);
 Dec_root = ns['Dec']<<Meq.Multiply(children=[nDec_root,dDec_root]);
 RA0_root = ns['RA0']<<Meq.Constant(RA_0);
 Dec0_root = ns['Dec0']<<Meq.Constant(Dec_0);

 #Projection
 cdec_root=ns['Cos(Dec)']<<Meq.Cos(children=Dec_root);
 sdec_root=ns['Sin(Dec)']<<Meq.Sin(children=Dec_root);
 cdec0_root=ns['Cos(Dec0)']<<Meq.Cos(children=Dec0_root);
 sdec0_root=ns['Sin(Dec0)']<<Meq.Sin(children=Dec0_root);
 RARA0_root=ns['RA0-RA']<<Meq.Subtract(children=[RA0_root,RA_root]);
 crara_root=ns['Cos(RA0-RA)']<<Meq.Cos(children=RARA0_root);
 srara_root=ns['Sin(RA0-RA)']<<Meq.Sin(children=RARA0_root);

 m1_root=ns['M1']<<Meq.Multiply(children=(cdec0_root,sdec_root));
 m2_root=ns['m2']<<Meq.Multiply(children=(sdec0_root,cdec_root,crara_root));

 #Alternative
 l_array = array([0.0]);
 m_array=array([0.0]);
 l_polc=meq.polc(coeff=l_array);
 m_polc=meq.polc(coeff=m_array);
 #l_root = ns['L']<<Meq.Parm(l_polc,node_groups='Parm',pert=1e-8);
 #m_root = ns['M']<<Meq.Parm(m_polc,node_groups='Parm');

 #LMN
 l_root = ns['L']<<Meq.Multiply(children=(cdec_root,srara_root));
 m_root = ns['M']<<Meq.Subtract(children=[m1_root,m2_root]);
 n_root = ns['N']<<Meq.Constant(0.0);
 lmn_root = ns['LMN']<<Meq.Composer(children=[l_root, m_root, n_root]);

 # DFT
 #dft_root = ns['DFT']<<Meq.Multiply(children=[Meq.Constant(-1.0),Meq.VisPhaseShift(lmn=lmn_root,uvw=uvw_root)]);
 dft_root = ns['DFT']<<Meq.VisPhaseShift(lmn=lmn_root,uvw=uvw_root);

 # Compare the XX result between UVInterpol and DFT
 #
 # Condeq
 #
 # Select XX result plane from UVInterpol node
 select2_root = ns['Select2']<<Meq.Selector(children=interpol_root,multi=True,index=[0]);

 cond_root = ns['Condeq'] << Meq.Condeq(children=[select2_root,dft_root]);
 #cond_root = ns['Condeq'] << Meq.Condeq(children=[interpol_root,interpol2_root]);

 # Solve for the RA and / or Dec position of the source in the DFT branch
 # Solver
 solvables = [];
 solvables.append('nRA');
 solvables.append('nDec');
 #solvables.append('L');
 #solvables.append('M');
 solver_root = ns['Solver']<<Meq.Solver(children=[cond_root],num_iter=100,debug_level=20,solvable=solvables);

 # Define Bookmarks
 MG_JEN_forest_state.bookmark(cond_root,page="CondEq",viewer="Result Plotter");
 MG_JEN_forest_state.bookmark(select2_root,page="FT-Result",viewer="Result Plotter");
 MG_JEN_forest_state.bookmark(dft_root,page="FT-Result",viewer="Result Plotter");
 MG_JEN_forest_state.bookmark(fft_root,page="UVBrick",viewer="Result Plotter");
 MG_JEN_forest_state.bookmark(interpol_root,udi="cache/result/uvinterpol_map",page="UVBrick",viewer="Result Plotter");
 MG_JEN_forest_state.bookmark(patch_root,page="Patch Image",viewer="Result Plotter");

########################################################################

def _test_forest(mqs,parent):
 # srcnames is global: to be used inside _define_forest, _test_forest, and outside of them
 global srcnames   
 
 # Not sure why this is repeated here
 from Timba.Meq import meq

 # Create the Request Cells
 f0 = 1349.999e6
 f1 = 1350.0010e6
 t0 = 0.0
 t1 = 86400.0
 nfreq = 1
 ntime = 1000
 
 # create cell
 freqtime_domain = meq.domain(startfreq=f0, endfreq=f1, starttime=t0, endtime=t1);
 cells =meq.cells(domain=freqtime_domain, num_freq=nfreq,  num_time=ntime);

 # create request
 request1 = meq.request(cells=cells, eval_mode=0 );

 # And execute the Tree ...
 args=record(name='Solver', request=request1);
 mqs.meq('Node.execute', args, wait=False);
   

#####################################################################

if __name__=='__main__':
  ns=NodeScope()
  define_forest(ns)
  ns.Resolve()
  print "Added %d nodes" % len(ns.AllNodes())
  #display LSM without MeqBrowser
  #l.display(app='create')
