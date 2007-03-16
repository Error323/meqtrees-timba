# standard preamble
from Timba.TDL import *
from Timba import pynode
from Timba import dmi
from Timba import utils
from Timba.Meq import meq
from Timba import mequtils

import pyfits
import PIL.Image
import re
import math
import os
import Meow

import floptix

Settings.forest_state.cache_policy = 1;

_dbg = utils.verbosity(0,name='fit_image');
_dprint = _dbg.dprint;
_dprintf = _dbg.dprintf;

TDLCompileOption('static_filename',"Static filename (enables static mode for testing)",[None,'test.pgm'],more=str);
TDLCompileOption('filename_pattern',"Image filename pattern",["test.pgm-.*","test.pgm"],more=str);
TDLCompileOption('directory_name',"Directory name",["."],more=str);
TDLCompileOption('scaling_factor',"Rescale image",[.25,.5,1],more=float);
background_order = None;
TDLCompileOption('background_order',"Polc order for background fit",[None,2,3],more=int);
TDLCompileOption('fit_bg_lsm',"Fit background with LSM",False);
TDLCompileOption('ideal_fwhm',"Ideal FWHM",[3],more=float);
TDLCompileOption('initial_fit_fwhm',"Initial fitted FWHM",[5],more=float);
TDLCompileOption('initial_fit_flux',"Initial fitted flux",[500],more=float);
TDLCompileOption('masking_radius',"Radius of box around sources",[20],more=int);

def read_lsm (filename):
  """Reads catalog file produced by sextractor, returns a list
  of (id,x,y) tuples""";
  sources = [];
  for line in open(filename).readlines():
    _dprint(0,"catalog line",line);
    if not line.startswith('#'):
      fields = re.split('[^\d.-]+',line);
      _dprint(0,"catalog fields",len(fields),fields);
      src = fields[1];
      x,y = float(fields[6]),float(fields[5]);
      sources.append((src,x,y));
  return sources;

def make_lsm (ns,sources,support=False):    
  """Creates an LSM tree from a catalog file""";
  # create xy coordinate node
  ns.xy << Meq.Composer(
    ns.x << Meq.Grid(axis=floptix.image_xaxis),
    ns.y << Meq.Grid(axis=floptix.image_yaxis)
  );
  # make two sets of sources: with a solvable fwhm, and
  # with a static fwhm
  ns.fwhm('fit') << Meq.Parm(initial_fit_fwhm,constrain_min=0.,constrain_max=20.,tags="lsm fwhm");
  ns.fwhm('ideal') << Meq.Parm(ideal_fwhm);
  for tp in ('fit','ideal'):
    ns.sigma(tp) << ns.fwhm(tp)/2.3548; 
    ns.sigsq_2(tp) << 2*Meq.Sqr(ns.sigma(tp));
  #  now make the other nodes
  ns.vec11 << Meq.Composer(1,1,dims=[1,2]); # (1,1) row vector: (1,1)*(x,y)^t = x+y
  xy_nodes = [];
  source_nodes = [];
  # now loop over sources
  first_source = True;
  for src,x,y in sources:
    _dprint(0,"source at",x,y);
    ns.flux(src) << Meq.Parm(initial_fit_flux,constrain_min=100.,tags="lsm flux")
    if first_source:
      first_source = False;
      tags = "lsm pos0";
    else: 
      tags = "lsm pos";
    ns.xy0(src) << Meq.Composer(
      ns.x0(src) << Meq.Parm(x,constrain_min=x-10,constrain_max=x+10,tags=tags),
      ns.y0(src) << Meq.Parm(y,constrain_min=y-10,constrain_max=y+10,tags=tags)
    );
    xy_nodes.append(ns.xy0(src));
    # create support
    if support:
      supp = ns.supp(src) << Meq.Parm(0,tags="lsm supp");
    # create gaussian at x0,y0
    xy2 = ns.dxy2(src) << Meq.Sqr(ns.xy - ns.xy0(src));
    xy2sum = ns.xy2sum(src) << Meq.MatrixMultiply(ns.vec11,xy2);
    for tp in ('fit','ideal'):
      gaussian = ns.flux(src)*Meq.Exp(-xy2sum/ns.sigsq_2(tp))/(math.pi*ns.sigsq_2(tp));
      if support:
        ns.img(src,tp) << gaussian + supp;
      else:
        ns.img(src,tp) << gaussian;
      
  # sum things up for the two types of lsm
  for tp in ('fit','ideal'):
    ns.lsm(tp) << Meq.Add(mt_polling=True,*[ns.img(src,tp) for src,x,y in sources]);
  
  # add node to flag everything except sources
  ns.lsm('mask') << Meq.PyNode(class_name="floptix.PyMakeLsmMask",
                               radius=masking_radius,*xy_nodes);
                               
  return ns.lsm('fit'),ns.lsm('ideal'),ns.lsm('mask');            

def _define_forest (ns,**kwargs):
  # run source finding on current image
  if static_filename is not None:
    fname = filename_pattern = static_filename;
    directory_name = ".";
  else:
    fname = floptix.acquire_imagename(filename_pattern,directory=directory_name);
  _dprint(0,"running source finding on",fname);
  if scaling_factor == 1:
    os.system("pnmtofits %s >%s.fits"%(fname,fname))
  else:
    os.system("pnmscale %f %s | pnmtofits >%s.fits"%(scaling_factor,fname,fname))
  # get image shape
  global image_nx;
  global image_ny;
  image_nx,image_ny = pyfits.open("%s.fits"%fname)[0].data.shape;
  os.system("rm -f %s.fits"%fname);
  _dprint(0,"scaled image size is",image_nx,image_ny);

  # now make the tree
  ns.img << Meq.PyNode(class_name="floptix.PyCameraImage",
                       directory_name=directory_name,
                       file_name=filename_pattern,
                       static_mode=(static_filename is not None),
                       rescale=scaling_factor,
                       node_groups=['Parm'],
                       tags="actuators"
                       );
  # make LSM
  sources = read_lsm('test.cat');
  lsm_fit,lsm_ideal,lsm_mask = make_lsm(ns,sources,support=(background_order is None));
  
  sbk = Meow.Bookmarks.Page("Solvers");
  
  # make background, if specified, and make a branch to solve for it
  if background_order is not None:
    backgr = ns.lsm('background') << Meq.Parm(0,shape=[background_order+1,background_order+1],tags="background");
    lsm_fit = ns.lsm('fit1') << lsm_fit + backgr;
    lsm_ideal = ns.lsm('ideal1') << lsm_ideal + backgr;
    bk = Meow.Bookmarks.Page("Background fit");
    ns.ce_bg << Meq.Condeq(ns.img,backgr);
    ns.residual_bg << Meq.Subtract(ns.img,backgr,cache_policy=100);
    ns.solver_bg << Meq.Solver(ns.ce_bg,num_iter=20,epsilon=1e-4,last_update=True,solvable=lsm_fit.search(tags="background"));
    bk.add(ns.img);
    bk.add(backgr);
    bk.add(ns.ce_bg);
    bk.add(ns.residual_bg);
    sbk.add(ns.solver_bg);
    ns.reqseq_bg << Meq.ReqSeq(ns.solver_bg,ns.residual_bg);
 
  # apply mask to incoming image
  masked_image = ns.masked_img << Meq.MergeFlags(ns.img,lsm_mask);
  
  # make branch to solve for LSM sources
  bk = Meow.Bookmarks.Page("LSM fit");
  ns.ce_lsm << Meq.Condeq(masked_image,lsm_fit);
  ns.residual_lsm << Meq.Subtract(ns.img,lsm_fit,cache_policy=100);
  solvables = lsm_fit.search(tags="lsm");
  if fit_bg_lsm:
    solvables += lsm_fit.search(tags="background");
  ns.solver_lsm << Meq.Solver(ns.ce_lsm,
                    colin_factor=1e-6,
                    lm_factor=1e-4,
                    num_iter=20,
                    epsilon=1e-4,
                    last_update=True,solvable=lsm_fit.search(tags="lsm"));
  bk.add(masked_image);
  bk.add(lsm_fit);
  bk.add(ns.ce_lsm);
  bk.add(ns.residual_lsm);
  sbk.add(ns.solver_lsm);
  ns.reqseq_lsm << Meq.ReqSeq(ns.solver_lsm,ns.residual_lsm);
  
  # make branch to solve for actuators
  bk = Meow.Bookmarks.Page("Optical calibration");
  ns.ce_cal << Meq.Condeq(masked_image,lsm_ideal);
  ns.residual_cal << Meq.Subtract(ns.img,lsm_ideal,cache_policy=100);
  solvable = masked_image.search(tags="actuators");
  # also solve for lsm fluxes and positions (but not pos0)
  solvable += lsm_ideal.search(tags="lsm (flux|pos|supp|background)");
  ns.solver_cal << Meq.Solver(ns.ce_cal,
         num_iter=20,
	 epsilon=1e-4,
	 lm_factor=1e-4,
	 last_update=True,
	 solvable=solvable);
  bk.add(masked_image);
  bk.add(lsm_ideal);
  bk.add(ns.ce_cal);
  bk.add(ns.residual_cal);
  sbk.add(ns.solver_cal);
  ns.reqseq_cal << Meq.ReqSeq(ns.solver_cal,ns.residual_cal);
  
def _tdl_job_1_run_source_extraction (mqs,parent,**kwargs):
  # run source finding on current image
  if static_filename is not None:
    filename = static_filename;
    directory_name = '.';
  else:
    filename = floptix.acquire_imagename(filename_pattern,directory=directory_name);
  _dprint(0,"running source finding on",filename);
  if scaling_factor == 1:
    os.system("pnmtofits %s >tmp.fits"%(filename,))
  else:
    os.system("pnmscale %f %s | pnmtofits >tmp.fits"%(scaling_factor,filename))
  os.system("sextractor tmp.fits");

if background_order is not None:
  def _tdl_job_2_solve_for_background (mqs,parent,**kwargs):
    # run tests on the forest
    cells = floptix.make_cells(image_nx,image_ny,'time','freq');
    request = meq.request(cells,rqtype='ev');
    mqs.execute('reqseq_bg',request);

def _tdl_job_3_solve_for_LSM (mqs,parent,**kwargs):
  # run tests on the forest
  cells = floptix.make_cells(image_nx,image_ny,'time','freq');
  request = meq.request(cells,rqtype='ev');
  mqs.execute('reqseq_lsm',request);

def _tdl_job_4_calibrate_optics (mqs,parent,**kwargs):
  # run tests on the forest
  cells = floptix.make_cells(image_nx,image_ny,'time','freq');
  request = meq.request(cells,rqtype='ev');
  mqs.execute('reqseq_cal',request);
