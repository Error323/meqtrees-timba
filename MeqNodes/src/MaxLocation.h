//# MaxLocation.h: Calculate station MaxLocation from station position and phase center
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
//# $Id: MaxLocation.h 3498 2006-04-27 12:37:39Z smirnov $

#ifndef MEQNODES_MaxLocation_H
#define MEQNODES_MaxLocation_H
    
#include <MEQ/TensorFunction.h>

#include <MeqNodes/TID-MeqNodes.h>
#pragma aidgroup MeqNodes
#pragma types #Meq::MaxLocation

namespace Meq {    

class MaxLocation : public TensorFunction
{
public:
  MaxLocation();

  virtual ~MaxLocation();

  virtual TypeId objectType() const
    { return TpMeqMaxLocation; }

protected:
  // method required by TensorFunction
  // Returns shape of result.
  // Also check child results for consistency
  virtual LoShape getResultDims (const vector<const LoShape *> &input_dims);
    
  // method required by TensorFunction
  // Evaluates MaxLocation for a given set of children values
  virtual void evaluateTensors (std::vector<Vells> & out,   
       const std::vector<std::vector<const Vells *> > &args );

  // virtual method to figure out the cells of the result object, based
  // on child cells.
  // Default version simply uses the first child cells it can find,
  // or the Request cells if no child cells are found, else none.
  virtual void computeResultCells (Cells::Ref &ref,const std::vector<Result::Ref> &childres,const Request &request);

private:
 //remember Cells
 Cells::Ref cells_;
};

} // namespace Meq

#endif
