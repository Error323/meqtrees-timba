//# UVInterpol.cc
//#
//# Copyright (C) 2002
//# ASTRON (Netherlands Foundation for Research in Astronomy)
//# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands, seg@astron.nl
//#
//# This program is free software; you can redistribute it and/or modify
//# it under the terms of the GNU General Public License as published by
//# the Free Software Foundation; either version 2 of the License, or
//# (at your option) any later version.
//#
//# This program is distributed in the hope that it will be useful,
//# but WITHOUT ANY WARRANTY; without even the implied warranty of
//# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//# GNU General Public License for more details.
//#
//# You should have received a copy of the GNU General Public License
//# along with this program; if not, write to the Free Software
//# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//#
//# $Id$

// This version of the UVInterpol node interpolates a UVBrick in meters.
// The interpolation point is found for the first frequency plane and then
// used for all the other frequency planes.

#include <MeqNodes/UVInterpol.h>
#include <MEQ/Request.h>
#include <MEQ/VellSet.h>
#include <MEQ/Cells.h>
#include <MEQ/Vells.h>
#include <MEQ/AID-Meq.h>
#include <MEQ/VellsSlicer.h>
#include <MeqNodes/AID-MeqNodes.h>
#include <casa/aips.h>
#include <casa/BasicSL/Constants.h>
#include <casa/BasicMath/Math.h>


namespace Meq {

  static const HIID child_labels[] = { AidBrick, AidUVW };
  static const int num_children = sizeof(child_labels)/sizeof(child_labels[0]);
  
#define VERBOSE

  UVInterpol::UVInterpol():
    Node(num_children,child_labels),
    _additional_info(false),
    _method(1)
  {
    disableAutoResample();
    _in1_axis_id.resize(3);
    _in1_axis_id[0] = "FREQ";
    _in1_axis_id[1] = "U";
    _in1_axis_id[2] = "V";
    _out1_axis_id.resize(2);
    _out1_axis_id[0] = "TIME";
    _out1_axis_id[1] = "FREQ";
    _in2_axis_id.resize(1);
    _in2_axis_id[0] = "TIME";
    _out2_axis_id.resize(2);
    _out2_axis_id[0] = "U";
    _out2_axis_id[1] = "V";

  };
  
  UVInterpol::~UVInterpol()
  {
  };

  void UVInterpol::setStateImpl (DMI::Record::Ref& rec, bool initializing)
  {
    Node::setStateImpl(rec,initializing);
    rec["Additional.Info"].get(_additional_info,initializing);
    rec["Method"].get(_method,initializing);

    std::vector<HIID> in1 = _in1_axis_id;
    if( rec[FAxesIn1].get_vector(in1,initializing) || initializing )
      {
	FailWhen(in1.size() !=3,FAxesIn1.toString()+" field must have 3 elements");
	_in1_axis_id = in1;
	Axis::addAxis(_in1_axis_id[0]);
	Axis::addAxis(_in1_axis_id[1]);
	Axis::addAxis(_in1_axis_id[2]);
      };
    std::vector<HIID> out1 = _out1_axis_id;
    if( rec[FAxesOut1].get_vector(out1,initializing) || initializing )
      {
	FailWhen(out1.size() !=2,FAxesOut1.toString()+" field must have 2 elements");
	_out1_axis_id = out1;
	Axis::addAxis(_out1_axis_id[0]);
	Axis::addAxis(_out1_axis_id[1]);
      };

    std::vector<HIID> in2 = _in2_axis_id;
    if( rec[FAxesIn2].get_vector(in2,initializing) || initializing )
      {
	FailWhen(in2.size() !=1,FAxesIn2.toString()+" field must have 1 elements");
	_in2_axis_id = in2;
	Axis::addAxis(_in2_axis_id[0]);
      };
    std::vector<HIID> out2 = _out2_axis_id;
    if( rec[FAxesOut2].get_vector(out2,initializing) || initializing )
      {
	FailWhen(out2.size() !=2,FAxesOut2.toString()+" field must have 2 elements");
	_out2_axis_id = out2;
	Axis::addAxis(_out2_axis_id[0]);
	Axis::addAxis(_out2_axis_id[1]);
      };

  }
  
  int UVInterpol::getResult (Result::Ref &resref,
			  const std::vector<Result::Ref> &childres,
			  const Request &request,bool newreq)
  {  

    // Get the request cells
    const Cells& rcells = request.cells();
    const Cells brickcells = childres.at(0)->cells();
    
    if( rcells.isDefined(Axis::TIME) && brickcells.isDefined(Axis::FREQ))
      {
	
	// Set input and output axes
	_in1axis0 = Axis::axis(_in1_axis_id[0]);
	_in1axis1 = Axis::axis(_in1_axis_id[1]);
	_in1axis2 = Axis::axis(_in1_axis_id[2]);
	_out1axis0 = Axis::axis(_out1_axis_id[0]);
	_out1axis1 = Axis::axis(_out1_axis_id[1]);
	_in2axis0 = Axis::axis(_in2_axis_id[0]);
	_out2axis0 = Axis::axis(_out2_axis_id[0]);
	_out2axis1 = Axis::axis(_out2_axis_id[1]);

	// Create the Interpolated UVdata 
	// (Integration is not implemented. This is ok for small 
	//   time/freq cells. For larger Cells a 2D Integration Routine 
	//   (Romberg?) must be implemented). 
	    
	// Create Result object and attach to the Ref that was passed in.
	resref <<= new Result(4);                 // 4 planes
	VellSet& vs0 = resref().setNewVellSet(0);  // create new object for plane 0
	VellSet& vs1 = resref().setNewVellSet(1);  // create new object for plane 0
	VellSet& vs2 = resref().setNewVellSet(2);  // create new object for plane 0
	VellSet& vs3 = resref().setNewVellSet(3);  // create new object for plane 0

	//
	// Make the Result (based on the frequency domain of the UVBrick!)
	//		
	    
	// Make the Vells (Interpolation)
	Vells::Shape tfshape;
	Axis::degenerateShape(tfshape,2);
	int nt = tfshape[Axis::TIME] = rcells.ncells(Axis::TIME);
	int nf = tfshape[Axis::FREQ] = brickcells.ncells(Axis::FREQ);
	double tmin = min(rcells.cellStart(Axis::TIME));
	double tmax = max(rcells.cellEnd(Axis::TIME));
	double fmin = min(brickcells.cellStart(Axis::FREQ));
	double fmax = max(brickcells.cellEnd(Axis::FREQ));

	Domain::Ref tfdomain(new Domain());
	tfdomain().defineAxis(Axis::axis("TIME"),tmin,tmax);
	tfdomain().defineAxis(Axis::axis("FREQ"),fmin,fmax);
	Cells::Ref tfcells(new Cells(*tfdomain));
	tfcells().setCells(Axis::axis("TIME"),tmin,tmax,nt);
	tfcells().setCells(Axis::axis("FREQ"),fmin,fmax,nf);
	    
	// Make a new Vells and fill with zeros
	Vells & vells0 = vs0.setValue(new Vells(dcomplex(0),tfshape,true));
	Vells & vells1 = vs1.setValue(new Vells(dcomplex(0),tfshape,true));
	Vells & vells2 = vs2.setValue(new Vells(dcomplex(0),tfshape,true));
	Vells & vells3 = vs3.setValue(new Vells(dcomplex(0),tfshape,true));
	    
	// Fill the Vells (this is were the interpolation takes place)
	fillVells(childres,vells0,vells1,vells2,vells3,tfcells);	
	    
	// Attach the request Cells to the result
	resref().setCells(*tfcells);
	resref().setDims(LoShape(2,2));
      
	if (_additional_info){
	  
	  // Make Additional Info on UV-plane coverage.
	  
	  // Make the Additional Vells
	  
	  Result& res2 = resref["UVInterpol.Map"] <<= new Result(1); 
	  VellSet& vs2 = res2.setNewVellSet(0); 
	  
	  //
	  // Make the Result
	  //		
	  
	  // Make a uv-shape
	  Result::Ref uvpoints;
	  uvpoints = childres.at(1);    
	  
	  // uv grid from UVBrick
	  int nu = brickcells.ncells(Axis::axis("U"));
	  int nv = brickcells.ncells(Axis::axis("V"));
	  const LoVec_double uu = brickcells.center(Axis::axis("U"));
	  const LoVec_double vv = brickcells.center(Axis::axis("V"));
	  const double umin = min(brickcells.cellStart(Axis::axis("U")));
	  const double umax = max(brickcells.cellEnd(Axis::axis("U")));
	  const double vmin = min(brickcells.cellStart(Axis::axis("V")));
	  const double vmax = max(brickcells.cellEnd(Axis::axis("V")));
	  
	  // uv image domain
	  Domain::Ref uvdomain(new Domain());
	  uvdomain().defineAxis(Axis::axis("U"),umin,umax);
	  uvdomain().defineAxis(Axis::axis("V"),vmin,vmax);
	  Cells::Ref uvcells(new Cells(*uvdomain));
	  uvcells().setCells(Axis::axis("U"),umin,umax,nu);
	  uvcells().setCells(Axis::axis("V"),vmin,vmax,nv);    
	  
	  Vells::Shape uvshape;
	  Axis::degenerateShape(uvshape,uvcells->rank());
	  uvshape[Axis::axis("U")] = brickcells.ncells(Axis::axis("U"));
	  uvshape[Axis::axis("V")] = brickcells.ncells(Axis::axis("V"));
	  
	  // Make the new Vells

	  Vells& vells2 = vs2.setValue(new Vells(double(0),uvshape,false));
	  
	  // Fill the Vells 

	  // Determine the mapping onto the uv plane of the time-freq. cell

	  VellsSlicer<double,2> uv_slicer(vells2,_out2axis0,_out2axis1);
	  blitz::Array<double,2> arr2 = uv_slicer();
	  arr2 = 0.0;

	  // u,v values from UVW-Node
	  VellSet uvs = uvpoints->vellSet(0);
	  VellSet vvs = uvpoints->vellSet(1);
	  Vells uvells = uvs.getValue();
	  Vells vvells = vvs.getValue();

	  VellsSlicer<double,1> utime_slicer(uvells,_in2axis0);
	  VellsSlicer<double,1> vtime_slicer(vvells,_in2axis0);
	  blitz::Array<double,1> uarr = utime_slicer();
	  blitz::Array<double,1> varr = vtime_slicer();

	  int imin, jmin;

	  for (int i = 0; i < nt; i++){
        
	    imin = 0;
	    jmin = 0;
	      
	    for (int i1 = 0; i1 < nu-1; i1++){
	      if ((uu(i1)<=uarr(i)) && (uu(i1+1)>uarr(i))) {imin = i1;};
	    };
	    for (int j1 = 0; j1 < nv-1; j1++){
	      if ((vv(j1)<=varr(i)) && (vv(j1+1)>varr(i))) {jmin = j1;};
	    };
	      
	    arr2(imin,jmin) = 1.0;
	      
	  }; // i
	  
	  // Attach a Cells to the result
	  res2.setCells(*uvcells);

	};
	
      }; 
    
    return 0;
    
  };

  void UVInterpol::fillVells(const std::vector<Result::Ref> &fchildres, 
			     Vells &fvells0, Vells &fvells1, Vells &fvells2, Vells &fvells3, const Cells &fcells)
  {
    // Definition of constants
    const double c0 = casa::C::c;  // Speed of light

    // If method has incorrect value, use default method
    if ((_method < 1) || (_method > 4)) _method = 1;

    // Time-Freq boundaries of Result to be produced
    int nt = fcells.ncells(Axis::TIME);
    int nf = fcells.ncells(Axis::FREQ);
    const LoVec_double freq = fcells.center(Axis::FREQ); 
    const LoVec_double time = fcells.center(Axis::TIME); 

    // Get the Child Results: brickresult, brickcells for UVBrick-Node
    //                        uvpoints for UVW-Node
    Result::Ref brickresult;
    Cells brickcells; 
    Result::Ref uvpoints;

    brickresult = fchildres.at(0);
    brickcells = brickresult->cells();
    uvpoints = fchildres.at(1);

    // u, v values from UVW-Node
    VellSet uvs = uvpoints->vellSet(0);
    VellSet vvs = uvpoints->vellSet(1);
    Vells uvells = uvs.getValue();
    Vells vvells = vvs.getValue();

    VellsSlicer<double,1> utime_slicer(uvells,_in2axis0);
    VellsSlicer<double,1> vtime_slicer(vvells,_in2axis0);
    blitz::Array<double,1> uarr = utime_slicer();
    blitz::Array<double,1> varr = vtime_slicer();

    // uv grid from UVBrick
    int nu = brickcells.ncells(Axis::axis("U"));
    int nv = brickcells.ncells(Axis::axis("V"));
    const LoVec_double uu = brickcells.center(Axis::axis("U"));
    const LoVec_double vv = brickcells.center(Axis::axis("V"));
    
    
    // uv-data from UVBrick
    // UVImage data
    VellSet vsfXX = brickresult->vellSet(0);
    Vells vellsfXX = vsfXX.getValue(); 
    VellSet vsfXY = brickresult->vellSet(4);
    Vells vellsfXY = vsfXY.getValue(); 
    VellSet vsfYX = brickresult->vellSet(8);
    Vells vellsfYX = vsfYX.getValue(); 
    VellSet vsfYY = brickresult->vellSet(12);
    Vells vellsfYY = vsfYY.getValue(); 
    
    VellsSlicer<dcomplex,3> XX_slicer(vellsfXX,_in1axis0,_in1axis1,_in1axis2);
    VellsSlicer<dcomplex,3> XY_slicer(vellsfXY,_in1axis0,_in1axis1,_in1axis2);
    VellsSlicer<dcomplex,3> YX_slicer(vellsfYX,_in1axis0,_in1axis1,_in1axis2);
    VellsSlicer<dcomplex,3> YY_slicer(vellsfYY,_in1axis0,_in1axis1,_in1axis2);

    blitz::Array<dcomplex,3> farrXX = XX_slicer();
    blitz::Array<dcomplex,3> farrXY = XY_slicer();
    blitz::Array<dcomplex,3> farrYX = YX_slicer();
    blitz::Array<dcomplex,3> farrYY = YY_slicer();

    // Output
    // Make an array, connected to the Vells, with which we fill the Vells.
    VellsSlicer<dcomplex,2> XXtf_slicer(fvells0,_out1axis0,_out1axis1);
    blitz::Array<dcomplex,2> arrXX = XXtf_slicer();
    VellsSlicer<dcomplex,2> XYtf_slicer(fvells1,_out1axis0,_out1axis1);
    blitz::Array<dcomplex,2> arrXY = XYtf_slicer();
    VellsSlicer<dcomplex,2> YXtf_slicer(fvells2,_out1axis0,_out1axis1);
    blitz::Array<dcomplex,2> arrYX = YXtf_slicer();
    VellsSlicer<dcomplex,2> YYtf_slicer(fvells3,_out1axis0,_out1axis1);
    blitz::Array<dcomplex,2> arrYY = YYtf_slicer();

    arrXX = dcomplex(0.0);
    arrXY = dcomplex(0.0);
    arrYX = dcomplex(0.0);
    arrYY = dcomplex(0.0);

    double uc,vc;
    int    ia,ib,ja,jb;
    double t,s;

    // Method 3
    dcomplex value, dvalue;
    blitz::Array<double,1> x1(4), x2(4);
    blitz::Array<dcomplex,2> yXX(4,4),yXY(4,4),yYX(4,4),yYY(4,4);

    // Think about order of time and frequency.
    // Can the grid search for the next (i,j) tile be optimised 
    //   by using the previous one as starting position?

    for (int i = 0; i < nt; i++){
	
      // Determine the uv-coordinates
      
      uc = uarr(i);
      vc = varr(i);


      // For all methods: the grid search can still be optimised

      if (_method == 1) {

	// Additional input data Vells

	VellSet vsfuXX = brickresult->vellSet(1);
	Vells fuvellsXX = vsfuXX.getValue(); 
	VellsSlicer<dcomplex,3> uXX_slicer(fuvellsXX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuarrXX = uXX_slicer();
	
	VellSet vsfvXX = brickresult->vellSet(2);
	Vells fvvellsXX = vsfvXX.getValue(); 
	VellsSlicer<dcomplex,3> vXX_slicer(fvvellsXX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fvarrXX = vXX_slicer();
	
	VellSet vsfuvXX = brickresult->vellSet(3);
	Vells fuvvellsXX = vsfuvXX.getValue(); 
	VellsSlicer<dcomplex,3> uvXX_slicer(fuvvellsXX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuvarrXX = uvXX_slicer();
	
	VellSet vsfuXY = brickresult->vellSet(5);
	Vells fuvellsXY = vsfuXY.getValue(); 
	VellsSlicer<dcomplex,3> uXY_slicer(fuvellsXY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuarrXY = uXY_slicer();
	
	VellSet vsfvXY = brickresult->vellSet(6);
	Vells fvvellsXY = vsfvXY.getValue(); 
	VellsSlicer<dcomplex,3> vXY_slicer(fvvellsXY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fvarrXY = vXY_slicer();
	
	VellSet vsfuvXY = brickresult->vellSet(7);
	Vells fuvvellsXY = vsfuvXY.getValue(); 
	VellsSlicer<dcomplex,3> uvXY_slicer(fuvvellsXY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuvarrXY = uvXY_slicer();
	
	VellSet vsfuYX = brickresult->vellSet(9);
	Vells fuvellsYX = vsfuYX.getValue(); 
	VellsSlicer<dcomplex,3> uYX_slicer(fuvellsYX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuarrYX = uYX_slicer();
	
	VellSet vsfvYX = brickresult->vellSet(10);
	Vells fvvellsYX = vsfvYX.getValue(); 
	VellsSlicer<dcomplex,3> vYX_slicer(fvvellsYX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fvarrYX = vYX_slicer();
	
	VellSet vsfuvYX = brickresult->vellSet(11);
	Vells fuvvellsYX = vsfuvYX.getValue(); 
	VellsSlicer<dcomplex,3> uvYX_slicer(fuvvellsYX,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuvarrYX = uvYX_slicer();
	
	VellSet vsfuYY = brickresult->vellSet(13);
	Vells fuvellsYY = vsfuYY.getValue(); 
	VellsSlicer<dcomplex,3> uYY_slicer(fuvellsYY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuarrYY = uYY_slicer();

	VellSet vsfvYY = brickresult->vellSet(14);
	Vells fvvellsYY = vsfvYY.getValue(); 
	VellsSlicer<dcomplex,3> vYY_slicer(fvvellsYY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fvarrYY = vYY_slicer();
	
	VellSet vsfuvYY = brickresult->vellSet(15);
	Vells fuvvellsYY = vsfuvYY.getValue(); 
	VellsSlicer<dcomplex,3> uvYY_slicer(fuvvellsYY,_in1axis0,_in1axis1,_in1axis2);
	blitz::Array<dcomplex,3> fuvarrYY = uvYY_slicer();
	
	// Bi-Cubic Hermite Interpolation, where the derivatives are
	//  approximated by central finite differences (already 
	//  determined in the UVBrick node).

	ia = 0;
	ib = nu-1;
	ja = 0;
	jb = nv-1;

	for (int i1 = 0; i1 < nu-1; i1++){
	  if ((uu(i1)<=uc) && (uu(i1+1)>uc)) {ia = i1;ib = i1+1;};
	};
	for (int j1 = 0; j1 < nv-1; j1++){
	  if ((vv(j1)<=vc) && (vv(j1+1)>vc)) {ja = j1; jb=j1+1;};
	};

	s = (uc-uu(ia))/(uu(ib)-uu(ia));
	t = (vc-vv(ja))/(vv(jb)-vv(ja));
	
	for (int j = 0; j < nf; j++){

	  arrXX(i,j) = (1-t)*(1-s)*farrXX(j,ia,ja) 
	    + s*(1-t)*farrXX(j,ib,ja) 
	    + (1-s)*t*farrXX(j,ia,jb)
	    + t*s*farrXX(j,ib,jb)
	    + t*s*s*(1-s)*(farrXX(j,ib,jb)-fuarrXX(j,ib,jb))
	    + t*s*(1-s)*(1-s)*(farrXX(j,ia,jb)-fuarrXX(j,ia,jb))
	    + (1-t)*s*s*(1-s)*(farrXX(j,ib,ja)-fuarrXX(j,ib,ja))
	    + (1-t)*s*(1-s)*(1-s)*(farrXX(j,ia,ja)-fuarrXX(j,ia,ja))
	    + t*t*s*(1-t)*(farrXX(j,ib,jb)-fvarrXX(j,ib,jb))
	    + t*t*(1-t)*(1-s)*(farrXX(j,ia,jb)-fvarrXX(j,ia,jb))
	    + (1-t)*s*t*(1-t)*(farrXX(j,ib,ja)-fvarrXX(j,ib,ja))
	    + t*(1-t)*(1-t)*(1-s)*(farrXX(j,ia,ja)-fvarrXX(j,ia,ja))
	    + t*t*(1-t)*s*s*(1-s)*(farrXX(j,ib,jb) - fvarrXX(j,ib,jb) - fuarrXX(j,ib,jb) + fuvarrXX(j,ib,jb))
	    + t*t*(1-t)*s*(1-s)*(1-s)*(farrXX(j,ia,jb) - fvarrXX(j,ia,jb) - fuarrXX(j,ia,jb) + fuvarrXX(j,ia,jb))
	    + t*(1-t)*(1-t)*s*s*(1-s)*(farrXX(j,ib,ja) - fvarrXX(j,ib,ja) - fuarrXX(j,ib,ja) + fuvarrXX(j,ib,ja))
	    + t*(1-t)*(1-t)*s*(1-s)*(1-s)*(farrXX(j,ia,ja) - fvarrXX(j,ia,ja) - fuarrXX(j,ia,ja) + fuvarrXX(j,ia,ja));

	  arrXY(i,j) = (1-t)*(1-s)*farrXY(j,ia,ja) 
	    + s*(1-t)*farrXY(j,ib,ja) 
	    + (1-s)*t*farrXY(j,ia,jb)
	    + t*s*farrXY(j,ib,jb)
	    + t*s*s*(1-s)*(farrXY(j,ib,jb)-fuarrXY(j,ib,jb))
	    + t*s*(1-s)*(1-s)*(farrXY(j,ia,jb)-fuarrXY(j,ia,jb))
	    + (1-t)*s*s*(1-s)*(farrXY(j,ib,ja)-fuarrXY(j,ib,ja))
	    + (1-t)*s*(1-s)*(1-s)*(farrXY(j,ia,ja)-fuarrXY(j,ia,ja))
	    + t*t*s*(1-t)*(farrXY(j,ib,jb)-fvarrXY(j,ib,jb))
	    + t*t*(1-t)*(1-s)*(farrXY(j,ia,jb)-fvarrXY(j,ia,jb))
	    + (1-t)*s*t*(1-t)*(farrXY(j,ib,ja)-fvarrXY(j,ib,ja))
	    + t*(1-t)*(1-t)*(1-s)*(farrXY(j,ia,ja)-fvarrXY(j,ia,ja))
	    + t*t*(1-t)*s*s*(1-s)*(farrXY(j,ib,jb) - fvarrXY(j,ib,jb) - fuarrXY(j,ib,jb) + fuvarrXY(j,ib,jb))
	    + t*t*(1-t)*s*(1-s)*(1-s)*(farrXY(j,ia,jb) - fvarrXY(j,ia,jb) - fuarrXY(j,ia,jb) + fuvarrXY(j,ia,jb))
	    + t*(1-t)*(1-t)*s*s*(1-s)*(farrXY(j,ib,ja) - fvarrXY(j,ib,ja) - fuarrXY(j,ib,ja) + fuvarrXY(j,ib,ja))
	    + t*(1-t)*(1-t)*s*(1-s)*(1-s)*(farrXY(j,ia,ja) - fvarrXY(j,ia,ja) - fuarrXY(j,ia,ja) + fuvarrXY(j,ia,ja));

	  arrYX(i,j) = (1-t)*(1-s)*farrYX(j,ia,ja) 
	    + s*(1-t)*farrYX(j,ib,ja) 
	    + (1-s)*t*farrYX(j,ia,jb)
	    + t*s*farrYX(j,ib,jb)
	    + t*s*s*(1-s)*(farrYX(j,ib,jb)-fuarrYX(j,ib,jb))
	    + t*s*(1-s)*(1-s)*(farrYX(j,ia,jb)-fuarrYX(j,ia,jb))
	    + (1-t)*s*s*(1-s)*(farrYX(j,ib,ja)-fuarrYX(j,ib,ja))
	    + (1-t)*s*(1-s)*(1-s)*(farrYX(j,ia,ja)-fuarrYX(j,ia,ja))
	    + t*t*s*(1-t)*(farrYX(j,ib,jb)-fvarrYX(j,ib,jb))
	    + t*t*(1-t)*(1-s)*(farrYX(j,ia,jb)-fvarrYX(j,ia,jb))
	    + (1-t)*s*t*(1-t)*(farrYX(j,ib,ja)-fvarrYX(j,ib,ja))
	    + t*(1-t)*(1-t)*(1-s)*(farrYX(j,ia,ja)-fvarrYX(j,ia,ja))
	    + t*t*(1-t)*s*s*(1-s)*(farrYX(j,ib,jb) - fvarrYX(j,ib,jb) - fuarrYX(j,ib,jb) + fuvarrYX(j,ib,jb))
	    + t*t*(1-t)*s*(1-s)*(1-s)*(farrYX(j,ia,jb) - fvarrYX(j,ia,jb) - fuarrYX(j,ia,jb) + fuvarrYX(j,ia,jb))
	    + t*(1-t)*(1-t)*s*s*(1-s)*(farrYX(j,ib,ja) - fvarrYX(j,ib,ja) - fuarrYX(j,ib,ja) + fuvarrYX(j,ib,ja))
	    + t*(1-t)*(1-t)*s*(1-s)*(1-s)*(farrYX(j,ia,ja) - fvarrYX(j,ia,ja) - fuarrYX(j,ia,ja) + fuvarrYX(j,ia,ja));

	  arrYY(i,j) = (1-t)*(1-s)*farrYY(j,ia,ja) 
	    + s*(1-t)*farrYY(j,ib,ja) 
	    + (1-s)*t*farrYY(j,ia,jb)
	    + t*s*farrYY(j,ib,jb)
	    + t*s*s*(1-s)*(farrYY(j,ib,jb)-fuarrYY(j,ib,jb))
	    + t*s*(1-s)*(1-s)*(farrYY(j,ia,jb)-fuarrYY(j,ia,jb))
	    + (1-t)*s*s*(1-s)*(farrYY(j,ib,ja)-fuarrYY(j,ib,ja))
	    + (1-t)*s*(1-s)*(1-s)*(farrYY(j,ia,ja)-fuarrYY(j,ia,ja))
	    + t*t*s*(1-t)*(farrYY(j,ib,jb)-fvarrYY(j,ib,jb))
	    + t*t*(1-t)*(1-s)*(farrYY(j,ia,jb)-fvarrYY(j,ia,jb))
	    + (1-t)*s*t*(1-t)*(farrYY(j,ib,ja)-fvarrYY(j,ib,ja))
	    + t*(1-t)*(1-t)*(1-s)*(farrYY(j,ia,ja)-fvarrYY(j,ia,ja))
	    + t*t*(1-t)*s*s*(1-s)*(farrYY(j,ib,jb) - fvarrYY(j,ib,jb) - fuarrYY(j,ib,jb) + fuvarrYY(j,ib,jb))
	    + t*t*(1-t)*s*(1-s)*(1-s)*(farrYY(j,ia,jb) - fvarrYY(j,ia,jb) - fuarrYY(j,ia,jb) + fuvarrYY(j,ia,jb))
	    + t*(1-t)*(1-t)*s*s*(1-s)*(farrYY(j,ib,ja) - fvarrYY(j,ib,ja) - fuarrYY(j,ib,ja) + fuvarrYY(j,ib,ja))
	    + t*(1-t)*(1-t)*s*(1-s)*(1-s)*(farrYY(j,ia,ja) - fvarrYY(j,ia,ja) - fuarrYY(j,ia,ja) + fuvarrYY(j,ia,ja));

	};

      } else {
	if (_method == 2) {

	  // 4th order polynomial interpolation
	  // Numerical Recipes, Sec. 3.6

	  ia = 0;
	  ib = nu-1;
	  ja = 0;
	  jb = nv-1;

	  for (int i1 = 0; i1 < nu-1; i1++){
	    if ((uu(i1)<=uc) && (uu(i1+1)>uc)) {ia = i1-1; ib = i1+2;};
	  };
	  for (int j1 = 0; j1 < nv-1; j1++){
	    if ((vv(j1)<=vc) && (vv(j1+1)>vc)) {ja = j1-1; jb = j1+2;};
	  };

	  for (int j = 0; j < nf; j++){ 

	    for (int i1 =0; i1<4; i1++){
	      x1(i1) = uu(ia+i1);
	      for (int j1=0; j1<4; j1++){
		x2(j1) = vv(ja+j1);
		yXX(i1,j1) = farrXX(j,ia+i1, ja+j1);
		yXY(i1,j1) = farrXY(j,ia+i1, ja+j1);
		yYX(i1,j1) = farrYX(j,ia+i1, ja+j1);
		yYY(i1,j1) = farrYY(j,ia+i1, ja+j1);
	      };
	    };
	    
	    value = dcomplex(0.0);
	    dvalue = dcomplex(0.0);
	    UVInterpol::mypolin2(x1,x2,yXX,4,4,uc,vc,value, dvalue);
	    arrXX(i,j) = value;

	    value = dcomplex(0.0);
	    dvalue = dcomplex(0.0);
	    UVInterpol::mypolin2(x1,x2,yXY,4,4,uc,vc,value, dvalue);
	    arrXY(i,j) = value;

	    value = dcomplex(0.0);
	    dvalue = dcomplex(0.0);
	    UVInterpol::mypolin2(x1,x2,yYX,4,4,uc,vc,value, dvalue);
	    arrYX(i,j) = value;

	    value = dcomplex(0.0);
	    dvalue = dcomplex(0.0);
	    UVInterpol::mypolin2(x1,x2,yYY,4,4,uc,vc,value, dvalue);
	    arrYY(i,j) = value;

	  };

	} else {
	  if (_method == 3) {
	    
	    // Bi-linear interpolation (Num. Rec. Sec. 3.6)
	    
	    ia = 0;
	    ib = nu-1;
	    ja = 0;
	    jb = nv-1;
	    
	    for (int i1 = 0; i1 < nu-1; i1++){
	      if ((uu(i1)<=uc) && (uu(i1+1)>uc)) {ia = i1;ib = i1+1;};
	    };
	    for (int j1 = 0; j1 < nv-1; j1++){
	      if ((vv(j1)<=vc) && (vv(j1+1)>vc)) {ja = j1; jb=j1+1;};
	    };
	    
	    s = (uc-uu(ia))/(uu(ib)-uu(ia));
	    t = (vc-vv(ja))/(vv(jb)-vv(ja));
	    
	    for (int j = 0; j < nf; j++){

	      arrXX(i,j) = (1-t)*(1-s)*farrXX(j,ia,ja) 
		+ s*(1-t)*farrXX(j,ib,ja) 
		+ t*(1-s)*farrXX(j,ia,jb)
		+ t*s*farrXX(j,ib,jb);

	      arrXY(i,j) = (1-t)*(1-s)*farrXY(j,ia,ja) 
		+ s*(1-t)*farrXY(j,ib,ja) 
		+ t*(1-s)*farrXY(j,ia,jb)
		+ t*s*farrXY(j,ib,jb);

	      arrYX(i,j) = (1-t)*(1-s)*farrYX(j,ia,ja) 
		+ s*(1-t)*farrYX(j,ib,ja) 
		+ t*(1-s)*farrYX(j,ia,jb)
		+ t*s*farrYX(j,ib,jb);

	      arrYY(i,j) = (1-t)*(1-s)*farrYY(j,ia,ja) 
		+ s*(1-t)*farrYY(j,ib,ja) 
		+ t*(1-s)*farrYY(j,ia,jb)
		+ t*s*farrYY(j,ib,jb);	  
	      
	    };
	  };
	};
      }; // End filling arr(i,j) by one of the 3 Methods
	
    }; // End of time loop
      
      
  };


    

  //--------------------------------------------------------------------------

  void UVInterpol::interpolate(int &j, int &ni,int &imin, int &nj, int &jmin, LoMat_dcomplex &coeff, blitz::Array<dcomplex,3> &barr,LoVec_double uu,LoVec_double vv)
  {

    // Find a complex 2D Interpolating polynimial of order ni * nj
    // I(u,v) = sum_{i,j} c(i,j) * u^i * v^j

    blitz::Array<double,2> A(ni*nj,ni*nj);
    blitz::Array<dcomplex,1> B(ni*nj);
    blitz::Array<int,1> indx(ni*nj);

    double uav = (uu(imin+ni-1) - uu(imin))/2.;
    double vav = (vv(jmin+nj-1) - vv(jmin))/2.;
    double ur = uu(imin+ni-1)-uav;
    double vr = vv(jmin+nj-1)-vav;

    for (int k = 0; k < ni; k++){
      for (int l = 0; l < nj; l++){
	for (int i = 0; i < ni; i++){
	  for (int j = 0; j < nj; j++){

	    A(k*nj+l,i*nj+j) = pow((uu(imin+k)-uav)/ur,i) 
	                     * pow((vv(jmin+l)-vav)/vr,j);

	  };
	};
	B(k*nj+l) = barr(j,imin+k,jmin+l);
      };
    };

    myludcmp(A,ni*nj,indx);
    mylubksb(A,ni*nj,indx,B);

    for (int i = 0; i < ni; i++){
      for (int j = 0; j < nj; j++){
	
	coeff(i,j) = B(i*nj+j);
	  
      };
    };

  };


  void UVInterpol::myludcmp(blitz::Array<double,2> &A,int n,blitz::Array<int,1> &indx)
  // My version of the Numerical Recipes's ludcmp routine
  {
    const double tiny = 1.0e-20; 

    double big, temp, sum, dum;
    int imax(0);
    blitz::Array<double,1> vv(n);

    // Loop over rows to get the implicit scaling information
    for (int i=0;i<n;i++){
      big = 0.0;
      for (int j=0;j<n;j++){
	if ((temp=fabs(A(i,j))) > big)
	  { 
	    big = temp;
	  };
	FailWhen(big==0.0,"Singular Matrix in UVInterpol::myludcmp");
	vv(i) = 1.0/big;
      };
    };

    //This is the loop over columns of Crout's method
    for (int j=0; j<n; j++){

      for (int i=0; i<j; i++){
	sum = A(i,j);
	for (int k=0; k<i; k++) sum -= A(i,k)*A(k,j);
	A(i,j) = sum;
      };

      big = 0.0;
      for (int i=j; i<n; i++){
	sum = A(i,j);
	for (int k=0; k<j; k++) sum -= A(i,k)*A(k,j);
	A(i,j) = sum;
	if ( (dum=vv(i)*fabs(sum)) >= big) {
	  big = dum;
	  imax = i;
	};
      };

      if (j != imax) {
	for (int k=0; k<n; k++){
	  dum = A(imax,k);
	  A(imax,k) = A(j,k);
	  A(j,k) = dum;
	};
	vv(imax) = vv(j);
      };

      indx(j)=imax;
      if (A(j,j) == 0.0) A(j,j) = tiny;
      if (j!=n-1){
	dum=1.0/A(j,j);
	for (int i=j+1;i<n;i++) A(i,j) *= dum;
      };

    };

  };


  void UVInterpol::mylubksb(blitz::Array<double,2> &A,int n,blitz::Array<int,1> &indx, blitz::Array<dcomplex,1> &B)
  // My version of the Numerical Recipes's lubksb routine
  {
    int ip, ii=-1;
    dcomplex sum;

    for (int i=0; i<n; i++){
      ip = indx(i);
      sum = B(ip);
      B(ip) = B(i);
      if (ii!=-1)
	for (int j=ii; j<=i-1;j++) sum -= A(i,j)*B(j);
      else if (abs(sum)!=0.0) ii=i;
      B(i) = sum;
    };

    for (int i=n-1; i>-1; i--){
      sum = B(i);
      for (int j = i+1; j<n; j++) sum -= A(i,j)*B(j);
      B(i) = sum / A(i,i);
    };

  };

  //---------------------------------------------------------------------------

  void UVInterpol::mysplie2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, int &m, int &n, blitz::Array<dcomplex,2> &y2a)
  // My version of splie2 from the Numerical Recipes (Sec. 3.6)
  {
    blitz::Array<dcomplex,1> ytmp(n), yytmp(n);

    for (int j=0; j<m; j++){
      for (int i=0; i<n; i++){
	ytmp(i) = ya(j,i);
      };
      UVInterpol::myspline(x2a,ytmp,n,1.0e30,1.0e30,yytmp);
      for (int i=0; i<n; i++){
	y2a(j,i) = yytmp(i);
      };
    };

  };

  void UVInterpol::mysplin2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, blitz::Array<dcomplex,2> &y2a, int &m, int &n, double &x1, double &x2, dcomplex &y)
  // My version of splin2 from the Numerical Recipes (Sec. 3.6)
  {
    blitz::Array<dcomplex,1> ytmp(n), yytmp(m), y2tmp(n);

    for (int j=0; j<m; j++){
      for (int i=0; i<n; i++){
	ytmp(i) = ya(j,i);
	y2tmp(i) = y2a(j,i);
      };
      UVInterpol::mysplint(x2a,ytmp,y2tmp,n,x2,yytmp(j));
    };
    UVInterpol::myspline(x1a,yytmp,m,1.0e30,1.0e30,y2tmp);
    UVInterpol::mysplint(x1a,yytmp,y2tmp,m,x1,y);

  };

  void UVInterpol::myspline(blitz::Array<double,1> &x, blitz::Array<dcomplex,1> &y,int &n, double yp1, double ypn, blitz::Array<dcomplex,1> &y2)
  // My version of spline from the Numerical Recipes (Sec. 3.3)
  // Using natural splines only 
  {
    blitz::Array<dcomplex,1> u(n);
    double sig, qn, un;
    dcomplex p;

    // Natural spline
    y2(0) = u(0) = make_dcomplex(0.0);

    for (int i=1;i<n-1;i++){
      sig = (x(i)-x(i-1))/(x(i+1)-x(i-1));
      p = sig*y2(i-1)+2.0;
      y2(i)=(sig-1.0)/p;
      u(i)=(y(i+1)-y(i))/(x(i+1)-x(i)) - (y(i)-y(i-1))/(x(i)-x(i-1));
      u(i)=(6.0*u(i)/(x(i+1)-x(i-1))-sig*u(i-1))/p;
    };
    
    // Natural spline
    qn = un = 0.0;

    y2(n-1) = (un-qn*u(n-2))/(qn*y2(n-2)+1.0);

    for (int k=n-2; k>-1; k--){
      y2(k) = y2(k)*y2(k+1) + u(k);
    };

  };

  void UVInterpol::mysplint(blitz::Array<double,1> &xa, blitz::Array<dcomplex,1> &ya, blitz::Array<dcomplex,1> &y2a, int &n, double &x, dcomplex &y)
  // My version of splint from the Numerical Recipes (Sec. 3.3)
  {
    int klo, khi, k;
    double h, a, b;

    klo = 0;
    khi = n-1;

    while (khi-klo > 1){
      k = (khi+klo)/2;
      if (xa(k) > x) khi = k;
      else klo = k;
    };

    h=xa(khi)-xa(klo);
    FailWhen(h==0.0,"Bad xa input to routine UVInterpol::mysplint");
    a = (xa(khi)-x)/h;
    b = (x-xa(klo))/h;

    y=a*ya(klo) + b*ya(khi) + ((a*a*a-a)*y2a(klo) + (b*b*b-b)*y2a(khi))/(h*h)/6.0;
  };

  //---------------------------------------------------------------------------

  void UVInterpol::mypolin2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, int m, int n, double &x1, double &x2, dcomplex &y, dcomplex &dy)
  // My version of polin2 from the Numerical Recipes (Sec. 3.6)
  {
    blitz::Array<double,1> ymtmp(m),yatmp(n);
    double ytmp, dytmp;

    for (int j=0; j<m; j++){
      for (int i=0; i<n; i++){
       	yatmp(i) = creal(ya(j,i));
      };
      ytmp=0.0;
      dytmp=0.0;
      UVInterpol::mypolint(x2a,yatmp,n,x2,ytmp,dytmp);
      ymtmp(j)=ytmp;
    };
    ytmp=0.0;
    dytmp=0.0;
    UVInterpol::mypolint(x1a,ymtmp,m,x1,ytmp,dytmp);

    y = dcomplex(ytmp);
    dy = dcomplex(dytmp);

    for (int j=0; j<m; j++){
      for (int i=0; i<n; i++){
       	yatmp(i) = cimag(ya(j,i));
      };
      ytmp=0.0;
      dytmp=0.0;
      UVInterpol::mypolint(x2a,yatmp,n,x2,ytmp,dytmp);
      ymtmp(j)=ytmp;
    };
    ytmp=0.0;
    dytmp=0.0;
    UVInterpol::mypolint(x1a,ymtmp,m,x1,ytmp,dytmp);

    y = y + make_dcomplex(0.0,ytmp);
    dy = dy + make_dcomplex(0.0,dytmp);

  };

  void UVInterpol::mypolint(blitz::Array<double,1> &xa, blitz::Array<double,1> &ya, int n, double &x, double &y, double &dy)
  // My version of polint from the Numerical Recipes (Sec. 3.2)
  {
    int ns=1;
    double dif, dift, ho, hp, den;
    blitz::Array<double,1> c(n), d(n);
    double w;

    dif = fabs(x-xa(0));
    for (int i=1; i<=n; i++){
      dift = fabs(x-xa(i-1));
      if (dift < dif){
	ns = i;
	dif = dift;
      };
      c(i-1) = ya(i-1);
      d(i-1) = ya(i-1);
    };
    y=ya(ns-1);
    ns=ns-1;
    for (int m=1; m<=n-1; m++){
      for (int i=1; i<=n-m; i++){
	ho = xa(i-1)-x;
	hp = xa(i+m-1)-x;
	w=c(i)-d(i-1);
	den = ho-hp;
	FailWhen(den==0.0,"Error in routine UVInterpol::mypolint");
	den = w/den;
	d(i-1) = hp*den;
	c(i-1) = ho*den;
      };
      if (2*ns < n-m) {
	dy = c(ns);
      } else {
	dy = d(ns-1);
	ns = ns-1;
      };
      y = y + dy;
    };

  };


} // namespace Meq
