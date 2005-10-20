//# Resampler.cc: resamples result resolutions
//#
//# Copyright (C) 2003
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

#include <MeqNodes/Resampler.h>
#include <MEQ/MeqVocabulary.h>
#include <MEQ/Request.h>
#include <MEQ/Result.h>
//#include <MEQ/ResampleMachine.h>
#include <MEQ/AID-Meq.h>
#include <MeqNodes/AID-MeqNodes.h>


namespace Meq {

//#define VERBOSE 

const HIID FFlagDensity = AidFlag|AidDensity;

const HIID FNumCells =AidNum|AidCells;
const HIID FFactor=AidFactor;

//##ModelId=400E5355029C
Resampler::Resampler()
: Node(1), // 1 child expected
  flag_mask(-1),flag_bit(0),flag_density(0.5),
	nx_(0),ny_(0),do_resample_(0)
{}

//##ModelId=400E5355029D
Resampler::~Resampler()
{}

void Resampler::setStateImpl (DMI::Record::Ref &rec,bool initializing)
{
  Node::setStateImpl(rec,initializing);
//  rec[FIntegrate].get(integrate,initializing);
  rec[FFlagMask].get(flag_mask,initializing);
  rec[FFlagBit].get(flag_bit,initializing);
  rec[FFlagDensity].get(flag_density,initializing);

	std::vector<int> numcells;
	if (rec[FNumCells].get_vector(numcells)) {
#ifdef VERBOSE
			cout<<"Initializing "<<numcells.size()<<" Cells ";
			for (int i=0;i<numcells.size();i++) cout<<numcells[i]<<", ";
			cout<<endl;
#endif
			if (numcells.size()>0) {
					do_resample_=1;
					nx_=numcells[0];
			}
			if (numcells.size()>1) 
					ny_=numcells[1];
	}
#ifdef VERBOSE
	cout<<"Initializing do_resample: "<<do_resample_<<endl;
	cout<<"Initializing flag_bit: "<<flag_bit<<endl;
#endif
}


int Resampler::getResult (Result::Ref &resref, 
                           const std::vector<Result::Ref> &childres,
                           const Request &request,bool)
{
  Assert(childres.size()==1);
  const Result &chres = *(childres.front());
	if (!do_resample_ || !chres.hasCells() || (flag_bit !=0)) {
	 //bail out: do nothing
	 //if flag_bit!=0, no change in result
   resref=childres[0];
	 return 0;
	}
  const Cells &incells = chres.cells();
	blitz::Array<double,1> xax=incells.center(0);
	blitz::Array<double,1> yax=incells.center(1);

	int nx=xax.extent(0);
	int ny=yax.extent(0);
	//bail out if we have any fails
	if (((nx==1)&&(ny==1)) ||(childres[0]->numFails()>0) || (flag_density<=0)) {
   resref=childres[0];
	 return 0;
	}
	//determine the resampling to be done
	int nx1=nx_;//(int)((double)nx*flag_density);
	int ny1=ny_;//(int)((double)ny*flag_density);
	//sanity check
	if (nx1<1) nx1=1;
	if (ny1<1) ny1=1;
#ifdef VERBOSE
	cout<<"new size "<<nx1<<" x "<<ny1<<" "<<flag_density<<endl;
#endif
  Cells::Ref outcells1; //<<= new Cells(request.cells().domain(),nx1,ny1);
  Cells &outcells = outcells1<<=new Cells(request.cells().domain(),nx1,ny1);
  int nvs = chres.numVellSets();
  Result & result = resref <<= new Result(nvs,chres.isIntegrated());
	//result.setCells(outcells);
  //result.setVellSet(0,new VellSet(outcells.shape()));
	//return 0;
	//VellSet *vs= new VellSet(outcells.shape());
	//vs->setValue(new Vells(double(-1.0),outcells.shape(),true));
  //result.setVellSet(0,vs);
	//return 0;
	blitz::Array<double,1> xaxs=outcells.center(0);
	blitz::Array<double,1> yaxs=outcells.center(1);
	double xstart=outcells.domain().start(0);
	double xend=outcells.domain().end(0);
	double ystart=outcells.domain().start(1);
	double yend=outcells.domain().end(1);

  for( int ivs=0; ivs<nvs; ivs++ )
  {
    VellSet::Ref ref;
		//VellSet &vs= ref<<= new VellSet(outcells.shape());
		Vells invl=chres.vellSet(ivs).getValue();
	  VellSet invs=chres.vellSet(ivs);
	  VellSet &vs= ref<<= new VellSet(invs.numSpids(),invs.numPertSets());
		if (invl.isReal()) {
		 blitz::Array<double,2> A=invl.as<double,2>()(LoRange::all(),LoRange::all());
#ifdef VERBOSE
		 cout<<A<<endl;
#endif
		 //decide here if we have only 1D vells
		 //if so, only do 1D resampling in time or frequency
		 int nx_real=A.extent(blitz::firstDim);
		 int ny_real=A.extent(blitz::secondDim);
		 //if we have a scalar, do nothing
		 if (nx_real==1 && ny_real==1) {
			 //just copy original data
#ifdef VERBOSE
			 cout<<"Case 1"<<endl;
#endif
       vs.setValue(new Vells(A));
		 } else if (nx_real==1) {
			/* no time dependence */
#ifdef VERBOSE
			cout<<"Case 2"<<endl;
#endif
			blitz::Array<double,1> B(ny1);
			blitz::Array<double,1> AA=A(1,LoRange::all());
      splint(yax,ystart,yend,AA,ny,yaxs,ny1,B);
			blitz::Array<double,2> BB(B.data(), blitz::shape(1,ny1),blitz::deleteDataWhenDone);   
		  Vells outvl=vs.setValue(new Vells(BB));
#ifdef VERBOSE
		 cout<<B<<endl;
#endif
		 } else if (ny_real==1) {
      /* no frequency dependence */
#ifdef VERBOSE
			cout<<"Case 3"<<endl;
#endif
			blitz::Array<double,1> B(nx1);
			blitz::Array<double,1> AA=A(LoRange::all(),1);//I get invalid read from this
      splint(xax,xstart,xend,AA,nx,xaxs,nx1,B);
			//blitz::Array<double,2> BB=B.transpose(nx1,1);
			blitz::Array<double,2> BB(B.data(), blitz::shape(nx1,1),blitz::deleteDataWhenDone);   
		  Vells outvl=vs.setValue(new Vells(BB));
			//vs.setShape(nx1,1);
			//vs.verifyShape(true);
#ifdef VERBOSE
		 cout<<B<<endl;
#endif
		 } else {
		  /* else we are here */
#ifdef VERBOSE
			cout<<"Case 4"<<endl;
#endif
		  blitz::Array<double,2> B(xaxs.extent(0),yaxs.extent(0));
		  int flag=resample(A,xax,yax,B,xaxs,yaxs,xstart,xend,ystart,yend);
		  Vells outvl=vs.setValue(new Vells(B));
#ifdef VERBOSE
		 cout<<B<<endl;
		 cout<<"Finished Sampling "<<flag<<endl;
#endif
		 }
		 cout.flush();
		} else {// Complex 
#ifdef VERBOSE
		 cout<<"Complex Data"<<endl;
#endif
		 blitz::Array<dcomplex,2> A=invl.as<dcomplex,2>()(LoRange::all(),LoRange::all());
#ifdef VERBOSE
		 cout<<A<<endl;
#endif
		 //decide here if we have only 1D vells
		 //if so, only do 1D resampling in time or frequency
		 int nx_real=A.extent(blitz::firstDim);
		 int ny_real=A.extent(blitz::secondDim);
		 //if we have a scalar, do nothing
		 if (nx_real==1 && ny_real==1) {
			 //just copy original data
#ifdef VERBOSE
			 cout<<"Case 1"<<endl;
#endif
       vs.setValue(new Vells(A));
		 } else if (nx_real==1) {
			/* no time dependence */
#ifdef VERBOSE
			cout<<"Case 2"<<endl;
#endif
			blitz::Array<dcomplex,1> B(ny1);
			blitz::Array<dcomplex,1> AA=A(1,LoRange::all());
      splint(yax,ystart,yend,AA,ny,yaxs,ny1,B);
			blitz::Array<dcomplex,2> BB(B.data(), blitz::shape(1,ny1),blitz::deleteDataWhenDone);   
		  Vells outvl=vs.setValue(new Vells(BB));
#ifdef VERBOSE
		 cout<<B<<endl;
#endif
		 } else if (ny_real==1) {
      /* no frequency dependence */
#ifdef VERBOSE
			cout<<"Case 3"<<endl;
#endif
			blitz::Array<dcomplex,1> B(nx1);
			blitz::Array<dcomplex,1> AA=A(LoRange::all(),1);
      splint(xax,xstart,xend,AA,nx,xaxs,nx1,B);
			//blitz::Array<double,2> BB=B.transpose(nx1,1);
			blitz::Array<dcomplex,2> BB(B.data(), blitz::shape(nx1,1),blitz::deleteDataWhenDone);   
		  Vells outvl=vs.setValue(new Vells(BB));
			//vs.setShape(nx1,1);
			//vs.verifyShape(true);
#ifdef VERBOSE
		 cout<<B<<endl;
#endif
		 } else {
		  /* else we are here */
#ifdef VERBOSE
			cout<<"Case 4"<<endl;
#endif

		 blitz::Array<dcomplex,2> B(xaxs.extent(0),yaxs.extent(0));
		 blitz::Array<double,2> A1=A.extractComponent(double(),0,2);
		 blitz::Array<double,2> B1=B.extractComponent(double(),0,2);
		 int flag=resample(A1,xax,yax,B1,xaxs,yaxs,xstart,xend,ystart,yend);
		 blitz::Array<double,2> A2=A.extractComponent(double(),1,2);
		 blitz::Array<double,2> B2=B.extractComponent(double(),1,2);
		 flag+=resample(A2,xax,yax,B2,xaxs,yaxs,xstart,xend,ystart,yend);

		 Vells outvl=vs.setValue(new Vells(B));
#ifdef VERBOSE
		 cout<<"Finished Sampling "<<flag<<endl;
		 cout<<A<<endl;
		 cout<<B<<endl;
		 cout.flush();
#endif
		 }
		}
    result.setVellSet(ivs,ref);
  }

	result.setCells(outcells);

  return 0;
}

///// poll children
int Resampler::pollChildren (std::vector<Result::Ref> &chres,
                          Result::Ref &resref,const Request &request)
{
   if ( do_resample_ && (flag_bit !=0) && request.hasCells()) {
		//modify request cells
	  //if flag_bit!=0, change the request 
		 Request::Ref newreq(request);
  const Cells &incells = request.cells();

	int nx=incells.center(0).extent(0);
	int ny=incells.center(1).extent(0);
	//determine the resampling to be done
	int nx1=nx_;//(int)((double)nx*flag_density);
	int ny1=ny_;//(int)((double)ny*flag_density);
	//sanity check
	if (nx1<1) nx1=1;
	if (ny1<1) ny1=1;
#ifdef VERBOSE
	cout<<"Resampling Request new size "<<nx1<<" x "<<ny1<<" "<<flag_density<<endl;
#endif
  Cells::Ref outcells1; 
 	Cells &outcells = outcells1<<=new Cells(request.cells().domain(),nx1,ny1);
  newreq().setCells(outcells);
     return Node::pollChildren(chres,resref,newreq);
		} else {
		//do nothing
     return Node::pollChildren(chres,resref,request);
		}
	// will not get here
	return 0;
}
/*** old code 
int Resampler::getResult (Result::Ref &resref, 
                           const std::vector<Result::Ref> &childres,
                           const Request &request,bool)
{
  std::vector<Thread::Mutex::Lock> child_reslock(numChildren());
  lockMutexes(child_reslock,childres);
  Assert(childres.size()==1);
  const Result &chres = *( childres.front() );
  const Cells &incells = chres.cells();
  const Cells &outcells = request.cells();
  // create resampler
  ResampleMachine resampler(outcells,incells);
  // return child result directly if nothing is to be done
  if( resampler.isIdentical() )
  {
    resref.copy(childres.front());
    return 0;
  }
  // do the resampling  
  resampler.setFlagPolicy(flag_mask,flag_bit,flag_density);
  int nvs = chres.numVellSets();
  Result & result = resref <<= new Result(request,nvs,chres.isIntegrated());
  for( int ivs=0; ivs<nvs; ivs++ )
  {
    VellSet::Ref ref;
    resampler.apply(ref,chres.vellSetRef(ivs),chres.isIntegrated());
    result.setVellSet(ivs,ref);
  }
  return 0;
}
****/

//binary search
int
 Resampler::bin_search(blitz::Array<double,1> xarr,double x,int i_start,int i_end) {
	/*
	 * xarr: array of sorted values, make sure x is within the range 
	 * x: value to search
	 * i_start: starting index of array to search 
	 * i_end: end index of array to search 
	 *
	 * return value: index k, such that xarr[k]<= x< xarr[k+1]
	 * for errors: return negative values
	 */
	//trivial case
	if (i_start==i_end) {
		if (xarr(i_start)==x)
				return i_start;
	  else {
			cerr<<"bin search error 1"<<endl;
	    return -1;
    }
	}

	//trivial case with length 2 array
	if (i_end==i_start+1) {
		if (x>=xarr(i_start) && x<xarr(i_end)) {
				return i_start;
		} else {
			cerr<<"bin search error 2"<<endl;
	    return -2;
    }
	}

	//compare the mid point
	int i=(int)((i_start+i_end)/2);
	if (x>=xarr(i) && x<xarr(i+1)) {
		 return i;
	} else {
		//go to lower half of the upper half of the array
		if (x<xarr(i))
			return bin_search(xarr,x,i_start,i);
		else 
			return bin_search(xarr,x,i,i_end);
	}

	//will not reach here
  cerr<<"bin search error 3"<<endl;
  return -3;
}

//bicubic interpolation
template<typename T> T
 Resampler::bicubic_interpolate(int p,int q,blitz::Array<double,1> xax,blitz::Array<double,1> yax,double x,double y,blitz::Array<T,2> A) {
 /*
	* we have a 4 by 4 grid
	*   q+2   .      .     .     .
	*   q+1   .      .     .     .
	*   q     .      . x   .     .
	*   q-1   .      .     .     .
	*         p-1    p     p+1   p+2
	*
	*   the point of interpolation is given as 'x'.
	*/
 
	//we number the 4 grid points in the center	as 0,1,2,3
	//and at each point, calculate gradients (d/dx, d/dy) and 
	//cross derivative d^2/dxdy
	/*
	 *  q+1 .    .
	 *   q  .    .
	 *      p    p+1
	 */
	T yy[4], dyy1[4], dyy2[4], dyy12[4];
	//this is just the function values
	yy[0]=A(p,q);
	yy[1]=A(p+1,q);
	yy[2]=A(p+1,q+1);
	yy[3]=A(p,q+1);
	//FIXME: in regular grids denominator is fixed, so
	// no need to recalculate this
	//this is the first derivative 
	dyy1[0]=(A(p+1,q)-A(p-1,q))/(xax(p+1)-xax(p-1));
	dyy1[1]=(A(p+2,q)-A(p,q))/(xax(p+2)-xax(p));
	dyy1[2]=(A(p+2,q+1)-A(p,q+1))/(xax(p+2)-xax(p));
	dyy1[3]=(A(p+1,q+1)-A(p-1,q+1))/(xax(p+1)-xax(p-1));
	//this is the first derivative along the second axis
	dyy2[0]=(A(p,q+1)-A(p,q-1))/(yax(q+1)-yax(q-1));
	dyy2[1]=(A(p+1,q+1)-A(p+1,q-1))/(yax(q+1)-yax(q-1));
	dyy2[2]=(A(p+1,q+2)-A(p+1,q))/(yax(q+2)-yax(q));
	dyy2[3]=(A(p,q+2)-A(p,q))/(yax(q+2)-yax(q));
	//this is the cross derivative
	dyy12[0]=(A(p+1,q+1)+A(p-1,q-1)-A(p+1,q-1)-A(p-1,q+1))
					/((xax(p+1)-xax(p-1))*(yax(q+1)-yax(q-1)));
	dyy12[1]=(A(p+2,q+1)+A(p,q-1)-A(p,q+1)-A(p+2,q-1))
					/((xax(p+2)-xax(p))*(yax(q+1)-yax(q-1)));
	dyy12[2]=(A(p+2,q+2)+A(p,q)-A(p,q+2)-A(p+2,q))
					/((xax(p+2)-xax(p))*(yax(q+2)-yax(q)));
	dyy12[3]=(A(p+1,q+2)+A(p-1,q)-A(p-1,q+2)-A(p+1,q))
					/((xax(p+1)-xax(p-1))*(yax(q+2)-yax(q)));

	blitz::Array<T,2> c(4,4);
	bcubic_coeff(yy,dyy1,dyy2,dyy12,xax(p+1)-xax(p),yax(q+1)-yax(q),c);
  
	//FIXME: only need the grid size here
  T t=(x-xax(p))/(xax(p+1)-xax(p));	
  T u=(y-yax(q))/(yax(q+1)-yax(q));	

  T ans=c(3,0)+(c(3,1)+(c(3,2)+c(3,3)*u)*u)*u;
	 ans=ans*t+c(2,0)+(c(2,1)+(c(2,2)+c(2,3)*u)*u)*u;
	 ans=ans*t+c(1,0)+(c(1,1)+(c(1,2)+c(1,3)*u)*u)*u;
	 ans=ans*t+c(0,0)+(c(0,1)+(c(0,2)+c(0,3)*u)*u)*u;
	return ans;
}
//helper function to calculate the coefficients
template<typename T> void
 Resampler::bcubic_coeff(T *yy, T *dyy1, T *dyy2, T *dyy12, double d1, double d2, blitz::Array<T ,2> c) {
	/* yy, dyy1, dyy2, dyy12 are 4x1 arrays of
	 * function value, 1st derivarives, cross derivatives at grid points
	 * d1 = size in x direction
	 * d2 = size in y direction
	 * c = 4x4 matrix of coefficients
	 */
	 static int wt[16][16] =
	 {{1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
		{0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0},
		{-3,0,0,3,0,0,0,0,-2,0,0,-1,0,0,0,0},
		{2,0,0,-2,0,0,0,0,1,0,0,1,0,0,0,0},
		{0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0},
	  {0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0},
		{0,0,0,0,-3,0,0,3,0,0,0,0,-2,0,0,-1},
		{0,0,0,0,2,0,0,-2,0,0,0,0,1,0,0,1},
		{-3,3,0,0,-2,-1,0,0,0,0,0,0,0,0,0,0},
		{0,0,0,0,0,0,0,0,-3,3,0,0,-2,-1,0,0},
		{9,-9,9,-9,6,3,-3,-6,6,-6,-3,3,4,2,1,2},
		{-6,6,-6,6,-4,-2,2,4,-3,3,3,-3,-2,-1,-1,-2},
		{2,-2,0,0,1,1,0,0,0,0,0,0,0,0,0,0},
		{0,0,0,0,0,0,0,0,2,-2,0,0,1,1,0,0},
		{-6,6,-6,6,-3,-3,3,3,-4,4,2,-2,-2,-2,-1,-1},
		{4,-4,4,-4,2,2,-2,-2,2,-2,-2,2,1,1,1,1}};

	  int k,i,j;
		T cl[16],x[16];
		double dd=d1*d2;
		for (i=0;i<4;i++) {
			x[i]=yy[i];
			x[i+4]=dyy1[i]*d1;
			x[i+8]=dyy2[i]*d2;
			x[i+12]=dyy12[i]*dd;
		}
    for (i=0; i<16;i++) {
			cl[i]=0.0;
			for (k=0;k<16;k++) cl[i]+=wt[i][k]*x[k];
		}
		k=0;
		for(i=0;i<4;i++) 
		  for (j=0;j<4;j++)
				c(i,j)=cl[k++];
}

//bilinear interpolation
template<typename T> T
 Resampler::bilinear_interpolate(int p,int q,blitz::Array<double,1> xax,blitz::Array<double,1> yax,double x,double y,blitz::Array<T,2> A) {
 /*
	* we have a 2 by 2 grid
	*   q+1   .     .
	*   q     . x   .
	*         p     p+1
	*
	*   the point of interpolation is given as 'x'.
	*/
  T t,u;
	//FIXME: only need the grid size here
  t=(x-xax(p))/(xax(p+1)-xax(p));	
  u=(y-yax(q))/(yax(q+1)-yax(q));	

	return (1-t)*(1-u)*A(p,q)+t*(1-u)*A(p+1,q)+t*u*A(p+1,q+1)+(1-t)*u*A(p,q+1);
}

//resampling routine
template<typename T> int 
 Resampler::resample(blitz::Array<T,2> A,blitz::Array<double,1> xax,blitz::Array<double,1> yax,
			blitz::Array<T,2> B,blitz::Array<double,1> xaxs,blitz::Array<double,1> yaxs, 
			double xstart, double xend, double ystart, double yend) {
 /*
	* Resample the array given by A, with grid points given by 
	* xax, yax to form a new array B, with new grid points given by
	* xaxs, yaxs
	* the limits of the domain is given by [xstart,xend], and [ystart,yend]
	*/

	int nx=xax.extent(0);
	int ny=yax.extent(0);
	int nxs=xaxs.extent(0);
	int nys=yaxs.extent(0);
	// bin sorting
	blitz::Array<double,1> tempx(nx+2);
	tempx(blitz::Range(1,nx))=xax;
	tempx(0)=xstart;
	tempx(nx+1)=xend;
	//store indices
	blitz::Array<int,1> xindex(nxs);
	for (int i=0; i<nxs;i++) 
			xindex(i)=bin_search(tempx,xaxs(i),0,nx+1);

	blitz::Array<double,1> tempy(ny+2);
	tempy(blitz::Range(1,ny))=yax;
	tempy(0)=ystart;
	tempy(ny+1)=yend;
	//store indices
	blitz::Array<int,1> yindex(nys);
	for (int i=0; i<nys;i++) 
			yindex(i)=bin_search(tempy,yaxs(i),0,ny+1);
#ifdef VERBOSE
	cout<<"Old X:"<<xax<<endl;
	cout<<"Old Y:"<<yax<<endl;
	cout<<"New X:"<<xaxs<<endl;
	cout<<"New Y:"<<yaxs<<endl;
#endif
	//cout<<"X index:"<<xindex<<endl;
	//cout<<"Y index:"<<yindex<<endl;
	/* depending on the index given in array xindex, decide what to do
	 * at new grid point i, say
	 * index 0: linear extrapolate using points 0,1
	 * index 1: linear interpolate using points 0,1
	 * index 2 or higher: cubic interpolate using points 0,1, 2, 3 
	 * ...
	 * index k: cubit interpolate using points k-2,k-1,k,k+1
	 * index nx-2 or lower: cubit interpolate using points nx-4,nx-3,nx-2,nx-1
	 * index nx-1: linear interpolate using points nx-2,nx-1
	 * index nx: linear extrapolate using points nx-2, nx-1
	 *
	 * note that we need nx=>4 for all the above to work, i.e. at least 4 
	 * points in the original grid. If we have lower number of points ??
	 */

	int x_l_limit=0;
	while((xindex(x_l_limit)<2) && (x_l_limit<nxs-1))
				x_l_limit++;
	int x_u_limit=nxs-1;
	while((xindex(x_u_limit)>nx-2) && (x_u_limit>0))
		    x_u_limit--;
	cout<<"Limits ["<<x_l_limit<<","<<x_u_limit<<"]"<<endl;
	int y_l_limit=0;
	while((yindex(y_l_limit)<2) && (y_l_limit<nys-1))
				y_l_limit++;
	int y_u_limit=nys-1;
	while((yindex(y_u_limit)>ny-2) && (y_u_limit>0))
		    y_u_limit--;
	cout<<"Limits ["<<y_l_limit<<","<<y_u_limit<<"]"<<endl;

	//within these limits do bicubic interpolation
	for (int i=x_l_limit; i<=x_u_limit;i++)
			for(int j=y_l_limit; j<=y_u_limit; j++)
         B(i,j)=bicubic_interpolate(xindex(i)-1,yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
         //B(i,j)=bilinear_interpolate(xindex(i)-1,yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);

	//the remaining points, do linear interpolation or extrapolation
	/*
	 *
	 *            0     idx>=1   idx>=2                 idx<=nx-2  idx<=nx-1  nx
	 *
	 * ny         +............................................................
	 *            |       |        |                      |           |       |
	 *            |  E    |        |                      |           |  E    |
	 * idy<=ny-1  |.......|........|......................|...........|.......|
	 *            |       |        |                      |           |       |
	 *            |       |        |                      |           |       |
	 * idy<=ny-2  |.......|........|......................|...........|.......|
	 *            |       |        |                      |           |       |
	 *            |       |        |                      |           |       |
	 *            |       |        |    Cubic  I          |           |       |
	 *            |       |        |                      |           |       |
	 *            |       |        |                      |           |       |
	 * idy>=2     |.......|........|......................|...........|.......|
	 *            |       |        |                      |           |       |
	 *            |       |        |                      |           |       |
	 * idy>=1     |.......|........|......................|...........|.......|
	 *            |       |        |                      |           |       |
	 *            |       |        |                      |           |       |
	 *            |   E   |        |                      |           |  E    |
	 *            |       |        |                      |           |       |
	 * 0          +.......|........|......................|...........|.......+
	 *                 x_ll_limit  x_l_limit              x_u_limit   x_uu_limit
	 */

	//the remaining points, do linear interpolation or extrapolation
	//we need 4 more limits for this
	int x_ll_limit=0;
	while((xindex(x_ll_limit)<1) && (x_ll_limit<nxs-1))
				x_ll_limit++;
	int x_uu_limit=nxs-1;
	while((xindex(x_uu_limit)>nx-1) && (x_uu_limit>0))
		    x_uu_limit--;
	int y_ll_limit=0;
	while((yindex(y_ll_limit)<1) && (y_ll_limit<nys-1))
				y_ll_limit++;
	int y_uu_limit=nys-1;
	while((yindex(y_uu_limit)>ny-1) && (y_uu_limit>0))
		    y_uu_limit--;


	cout<<"extrapolate(+1) X [0,"<<x_ll_limit-1<<"], interpolate (-1) ["<<x_ll_limit<<","<<x_l_limit-1<<"]";
	cout<<" ["<<x_u_limit+1<<","<<x_uu_limit<<"], extrapolate (-2) ["<<x_uu_limit+1<<","<<nxs-1<<"]"<<endl;
	cout<<"extrapolate(+1) Y [0,"<<y_ll_limit-1<<"], interpolate (-1) ["<<y_ll_limit<<","<<y_l_limit-1<<"]";
	cout<<" ["<<y_u_limit+1<<","<<y_uu_limit<<"], extrapolate (-2) ["<<y_uu_limit+1<<","<<nys-1<<"]"<<endl;


	//x - extrapolate, index add+1
	for (int i=0;i<x_ll_limit;i++) {
		for (int j=0;j<y_ll_limit;j++) {
				//y extrapolate
         B(i,j)=bilinear_interpolate(xindex(i)-1+1,
												 yindex(j)-1+1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_ll_limit;j<y_l_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1+1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_l_limit;j<=y_u_limit;j++) {
				//y cubic interpolate 
         B(i,j)=bilinear_interpolate(xindex(i)-1+1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_u_limit+1;j<=y_uu_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1+1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_uu_limit+1;j<nys;j++) {
				//y extrapolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1+1,
												 yindex(j)-1-1,xax,yax,xaxs(i),yaxs(j),A);
		}
	}
	//x - linear interpolate
	for (int i=x_ll_limit;i<x_l_limit;i++) {
		for (int j=0;j<y_ll_limit;j++) {
				//y extrapolate
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1+1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_ll_limit;j<y_l_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_l_limit;j<=y_u_limit;j++) {
				//y cubic interpolate 
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_u_limit+1;j<=y_uu_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_uu_limit+1;j<nys;j++) {
				//y extrapolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1-1,xax,yax,xaxs(i),yaxs(j),A);
		}
	}
	//x - cubic interpolate
	for (int i=x_l_limit;i<=x_u_limit;i++) {
		for (int j=0;j<y_ll_limit;j++) {
				//y extrapolate
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1+1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_ll_limit;j<y_l_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		//cubic interpolation is already done
		for (int j=y_u_limit+1;j<=y_uu_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_uu_limit+1;j<nys;j++) {
				//y extrapolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1-1,xax,yax,xaxs(i),yaxs(j),A);
		}
	}

	//x -linear interpolate
	for (int i=x_u_limit+1;i<=x_uu_limit;i++) {
		for (int j=0;j<y_ll_limit;j++) {
				//y extrapolate
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1+1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_ll_limit;j<y_l_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_l_limit;j<=y_u_limit;j++) {
				//y cubic interpolate 
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_u_limit+1;j<=y_uu_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_uu_limit+1;j<nys;j++) {
				//y extrapolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-1,
												 yindex(j)-1-1,xax,yax,xaxs(i),yaxs(j),A);
		}
	}
	//x - extrapolate -2
	for (int i=x_uu_limit+1;i<nxs;i++) {
		for (int j=0;j<y_ll_limit;j++) {
				//y extrapolate
         B(i,j)=bilinear_interpolate(xindex(i)-2,
												 yindex(j)-1+1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_ll_limit;j<y_l_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-2,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_l_limit;j<=y_u_limit;j++) {
				//y cubic interpolate 
         B(i,j)=bilinear_interpolate(xindex(i)-2,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_u_limit+1;j<=y_uu_limit;j++) {
				//y interpolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-2,
												 yindex(j)-1,xax,yax,xaxs(i),yaxs(j),A);
		}
		for (int j=y_uu_limit+1;j<nys;j++) {
				//y extrapolate (linear)
         B(i,j)=bilinear_interpolate(xindex(i)-2,
												 yindex(j)-1-1,xax,yax,xaxs(i),yaxs(j),A);
		}
	}


	return 0; // no error
}

//1 D cubic spline interpolation
//ripped from numerical recipes
template<class T> void
 Resampler::spline(blitz::Array<double,1> x, blitz::Array<T,1> y, int n, blitz::Array<T,1> y2) {
	/* x,y,y2: n x 1 arrays
	 * input: x,y: ordinate and abcissa arrays
	 * output: y2: array of second derivatives of the function
	 * at the first and last points, natural boundary conditions
	 * are assumed
	 */
	 T p,sig;

	 blitz::Array<T,1> u(n);

	 //natural boundary conditions, so 
	 y2(0)=u(0)=0;
	 for (int i=1; i<n-1;i++) {
			sig=(x(i)-x(i-1))/(x(i+1)-x(i-1));
			p=sig*y2(i-1)+2.0;
			y2(i)=(sig-1.0)/p;
			//cout<<"DEBUG "<<i<<" of "<<n<<endl;
			u(i)=(y(i+1)-y(i))/(x(i+1)-x(i))-(y(i)-y(i-1))/(x(i)-x(i-1));
			u(i)=(6.0*u(i)/(x(i+1)-x(i-1))-sig*u(i-1))/p;
	 }

	 y2(n-1)=0;

	 for(int i=n-2;i>=0;i--) {
			y2(i)=y2(i)*y2(i+1)+u(i);
	 }
}

template<class T> void
 Resampler::splint(blitz::Array<double,1> xax,double xstart, double xend, blitz::Array<T,1> yax, int n, blitz::Array<double,1> xaxs, int ns, blitz::Array<T,1> y) {
	assert(n>=2);
	//calculate second derivatives
  blitz::Array<T,1> y2(n);
  spline(xax, yax, n, y2);

	double h;
	T a,b;
	// bin sorting
  blitz::Array<double,1> tempx(n+2);
	tempx(blitz::Range(1,n))=xax;
	tempx(0)=xstart;
	tempx(n+1)=xend;
	//store indices
	blitz::Array<int,1> xindex(ns);
	for (int i=0; i<ns;i++)  {
			xindex(i)=bin_search(tempx,xaxs(i),0,n+1);
	}
#ifdef VERBOSE
	cout<<"index "<<xindex<<endl;
#endif
	//now find ranges for interpolation and extrapolation
  int x_l_limit=0;
	while((xindex(x_l_limit)<1) && (x_l_limit<ns-1))
				x_l_limit++;
	int x_u_limit=ns-1;
	while((xindex(x_u_limit)>n-1) && (x_u_limit>0))
		    x_u_limit--;
 
	cout<<"Limits : interp["<<x_l_limit<<","<<x_u_limit<<"]"<<endl;
	cout<<"extrap : [0,"<<x_l_limit-1<<"],["<<x_u_limit+1<<","<<ns-1<<"]"<<endl;
	for (int i=x_l_limit; i<=x_u_limit;i++) {
      h=xax(xindex(i))-xax(xindex(i)-1);
			if (h==0) h=0.1;
			a=(xax(xindex(i))-xaxs(i))/h;
			b=(xaxs(i)-xax(xindex(i)-1))/h;
			y(i)=a*yax(xindex(i)-1)+b*yax(xindex(i))
						+((a*a*a-a)*y2(xindex(i)-1)+(b*b*b-b)*y2(xindex(i)))*(h*h)/6.0;
	}
	//Extrapolation : Linear
	for (int i=0;i<x_l_limit; i++) {
		y(i)=yax(0)+(xaxs(i)-xaxs(0))/(xax(1)-xax(0))*(yax(1)-yax(0));
	}
	for (int i=x_u_limit+1;i<ns; i++) {
		y(i)=yax(n-2)+(xaxs(i)-xaxs(n-2))/(xax(n-1)-xax(n-2))*(yax(n-1)-yax(n-2));
	}
}




} // namespace Meq
