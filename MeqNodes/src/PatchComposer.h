//# PatchComposer.h: First version of the Node
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

#ifndef MEQNODES_PATCHCOMPOSER_H
#define MEQNODES_PATCHCOMPOSER_H

//# Includes
#include <MEQ/Node.h>
//#include <images/Images/PagedImage.h>
//#include <MeqNodes/ReductionFunction.h>


#include <MeqNodes/TID-MeqNodes.h>
#pragma aidgroup MeqNodes
#pragma types #Meq::PatchComposer

namespace Meq {


class PatchComposer: public Node
	       //class PatchComposer: public ReductionFunction
{
public:
  // The default constructor.
  // The object should be filled by the init method.
  PatchComposer();

  virtual ~PatchComposer();

  virtual TypeId objectType() const
  { return TpMeqPatchComposer; }

  // Get the requested result of the Node.
  virtual int getResult (Result::Ref &resref, 
                         const std::vector<Result::Ref> &childres,
                         const Request &req,bool newreq);

  
 protected:

  virtual void setStateImpl (DMI::Record::Ref &rec,bool initializing);

 private:

  double _max_baseline;
  double _uvppw;
   
};


} // namespace Meq

#endif
