//# UVInterpol.h
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

#ifndef MEQNODES_UVINTERPOL_H
#define MEQNODES_UVINTERPOL_H

//# Includes
#include <MEQ/Node.h>
//#include <MeqNodes/ReductionFunction.h>


#include <MeqNodes/TID-MeqNodes.h>
#include <MeqNodes/AID-MeqNodes.h>

#pragma aidgroup MeqNodes
#pragma types #Meq::UVInterpol

#pragma aid UVW Brick
#pragma aids UVInterpol Map Count Additional Info UVImage UVZ UVDelta UVCurvature Method

namespace Meq {

  static const HIID FAxesIn1 = AidAxes|AidIn|1;
  static const HIID FAxesOut1 = AidAxes|AidOut|1;
  static const HIID FAxesIn2 = AidAxes|AidIn|2;
  static const HIID FAxesOut2 = AidAxes|AidOut|2;


class UVInterpol: public Node
	       //class UVInterpol: public ReductionFunction
  {
  public:
    // The default constructor.
    // The object should be filled by the init method.
    UVInterpol();

    virtual ~UVInterpol();

    virtual TypeId objectType() const
    { return TpMeqUVInterpol; }
    
    /*
    // Evaluate the value for the given request.
    virtual Vells evaluate (const Request&,const LoShape &,
    const vector<const Vells*>& values);
    */

    // Get the requested result of the Node.
    virtual int getResult (Result::Ref &resref, 
			   const std::vector<Result::Ref> &childres,
			   const Request &req,bool newreq);
  
  protected:

    virtual void setStateImpl (DMI::Record::Ref &rec,bool initializing);

  private:

    bool _additional_info;  
    int _method;

    // note that there are two sets of in and out axes
    // which axes are treated as input and output planes?
    std::vector<HIID> _in1_axis_id;
    std::vector<HIID> _in2_axis_id;
    std::vector<HIID> _out1_axis_id;
    std::vector<HIID> _out2_axis_id;
    
    // axis numbers -- filled in by getResult()
    uint _in1axis0;
    uint _in1axis1;
    uint _in1axis2;
    uint _out1axis0;
    uint _out1axis1;
    
    uint _in2axis0;
    uint _out2axis0;
    uint _out2axis1;
    
    void UVInterpol::fillVells(const std::vector<Result::Ref> &fchildres, 
			       Vells &fvells0, Vells &fvells1, Vells &fvells2, 
			       Vells &fvells3, const Cells &fcells);
    
    bool UVInterpol::line(double u1, double v1, double u2, double v2, double u3, double v3, double u4, double v4);
    
    bool UVInterpol::arc(double u1, double v1, double u2, double v2, double u3, double v3, double u4, double v4, double freq);

    void UVInterpol::fillVells2(const std::vector<Result::Ref> &fchildres, 
				Vells &fvells1, Vells &fvells2, Vells &fvells3, 
				Vells &fvells4, Vells &fvells5, const Cells &fcells);
    
    void UVInterpol::fillVells3(const std::vector<Result::Ref> &fchildres, 
				Vells &fvells1, Vells &fvells2, Vells &fvells3, 
				Vells &fvells4, Vells &fvells5, const Cells &fcells);
    
    void UVInterpol::interpolate(int &j, int &ni,int &imin, int &nj, int &jmin, LoMat_dcomplex &coeff, blitz::Array<dcomplex,3> &barr,LoVec_double uu,LoVec_double vv);
    
    void UVInterpol::myludcmp(blitz::Array<double,2> &A,int n,blitz::Array<int,1> &indx);
    
    void UVInterpol::mylubksb(blitz::Array<double,2> &A,int n,blitz::Array<int,1>&indx,blitz::Array<dcomplex,1> &B);
    
    void UVInterpol::mysplie2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, int &m, int &n, blitz::Array<dcomplex,2> &y2a);
    
    void UVInterpol::mysplin2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, blitz::Array<dcomplex,2> &y2a, int &m, int &n, double &x1, double &x2, dcomplex &y);
    
    void UVInterpol::myspline(blitz::Array<double,1> &x, blitz::Array<dcomplex,1> &y,int &n, double yp1, double ypn, blitz::Array<dcomplex,1> &y2);
    
    void UVInterpol::mysplint(blitz::Array<double,1> &xa, blitz::Array<dcomplex,1> &ya, blitz::Array<dcomplex,1> &y2a, int &n, double &x, dcomplex &y);
    
    void UVInterpol::mypolin2(blitz::Array<double,1> &x1a, blitz::Array<double,1> &x2a, blitz::Array<dcomplex,2> &ya, int m, int n, double &x1, double &x2, dcomplex &y, dcomplex &dy);
    
    void UVInterpol::mypolint(blitz::Array<double,1> &xa, blitz::Array<double,1> &ya, int n, double &x, double &y, double &dy);
    
    dcomplex UVInterpol::scheme1(double s, double t, dcomplex fiaja, dcomplex fiajb, dcomplex fibjb, dcomplex fibja, dcomplex fuiaja, dcomplex fuiajb, dcomplex fuibjb, dcomplex fuibja, dcomplex fviaja, dcomplex fviajb, dcomplex fvibjb, dcomplex fvibja, dcomplex fuviaja, dcomplex fuviajb, dcomplex fuvibjb, dcomplex fuvibja );
    
    dcomplex UVInterpol::scheme3(double s, double t, dcomplex fiaja, dcomplex fiajb, dcomplex fibjb, dcomplex fibja );
    
    void UVInterpol::fill1Vells(Vells &vellsin, Vells &vellsin1, Vells &vellsin2, Vells &vellsin3, Vells &vellsout, const Result::Ref &uvpoints, const Cells &tfcells, const Cells &brickcells);
    
  };  
  
} // namespace Meq

#endif
