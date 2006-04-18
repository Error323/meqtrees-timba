//# Parm.cc: Stored parameter with polynomial coefficients
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



#include <MeqNodes/Parm.h>
#include <MEQ/ComposedPolc.h>
#include <MEQ/Polc.h>
#include <MEQ/PolcLog.h>
#include <MEQ/Request.h>
#include <MEQ/VellSet.h>
#include <MEQ/Cells.h>
#include <MEQ/MeqVocabulary.h>
#include <MeqNodes/AID-MeqNodes.h>
#include <TimBase/Debug.h>
#include <TimBase/Lorrays.h>
#include <casa/BasicMath/Math.h>
#include <casa/Arrays/Matrix.h>
#include <casa/Arrays/Vector.h>
#include <DMI/List.h>
#include <DMI/Record.h>
#include <MEQ/Forest.h>




using namespace casa;

namespace Meq {

  InitDebugContext(Parm,"MeqParm");

  const HIID symdeps_all[]     = { FDataset,FDomain,FResolution,FState,FIteration };
  const HIID symdeps_domain[]  = { FDataset,FDomain,FResolution };
  const HIID symdeps_solve[]   = { FIteration,FState };
  const HIID symdeps_default[] = { FDataset,FDomain,FResolution };

  const HIID
  // Parm staterec fields
    FSolvable        = AidSolvable,
    FTableName       = AidTable|AidName,
    FParmName        = AidParm|AidName,
    FAutoSave        = AidAuto|AidSave,
    FDomainId        = AidDomain|AidId,
  // FDomain      defined previously
    FFunklet         = AidFunklet,
    FDefaultFunklet  = AidDefault|AidFunklet,
    FDefaultValue  = AidDefault|AidValue,
    FSolveDomain = AidSolve|AidDomain,
    FUsePrevious = AidUse|AidPrevious,
    FTileSize = AidTile|AidSize,
    FTiling = AidTiling,
    FInitFunklet  = AidInit|AidFunklet,
    FConverged  = AidConverged,
    FSaveAll  = AidSave|AidAll,
    FResetFunklet = AidReset|AidFunklet;
  
    


  Parm::Parm()
    : Node  (0), // no children allowed
      solvable_ (false),
      auto_save_(false),
      tiled_ (false),
      _use_previous(true),
      converged_(false),
      ignore_convergence_(false),
      reset_funklet_(false),
      parmtable_(0),
      default_(1.),
      force_shape_(false),
      domain_depend_mask_(0),
      solve_depend_mask_(0),
      domain_symdeps_(symdeps_domain,symdeps_domain+sizeof(symdeps_domain)/sizeof(symdeps_domain[0])),
      solve_symdeps_(symdeps_solve,symdeps_solve+sizeof(symdeps_solve)/sizeof(symdeps_solve[0])),
      solve_domain_(2),
      integrated_(false)
  {
    // The default depmask includes Domain. This is done in such that the fuklet gets reinitialized in case of a Fail
    //solve_depend_mask 
    // is added if the parm is solvable
    setActiveSymDeps(symdeps_default,3);
  }


  //##ModelId=3F86886F021E
  Parm::~Parm()
  {}


  Funklet * Parm::findRelevantFunklet (Funklet::Ref &funkletref,const Domain &domain)
  {
 

    cdebug(2)<<"looking for suitable funklets"<<endl;
    funkletref.detach();
    if( parmtable_ )
      {
	//reimplement different function for (non)solvable
	vector<Funklet::Ref> funklets;
#ifdef HAVE_PARMDB	    
	int n=0;
#else
	parmtable_ = ParmTable::openTable(parmtable_name_);
	int n = parmtable_->getFunklets(funklets,name_,domain);
#endif
	
	cdebug(3)<<n<<" funklets found in MEP table"<<endl;
	if( n>1 )
	  {
	    cdebug(3)<<"discarding multiple funklets as only one is currently suported, unless ? "<<(!isSolvable()||tiled_)<< "= true "<<endl;
	    if(!reset_funklet_ && (tiled_ || !isSolvable()) ){
	      funkletref <<=new ComposedPolc(funklets);
	      cdebug(3)<<"composed funklet found? "<<funkletref-> objectType()<<endl;
	      funkletref().setDomain(domain);
	      if(force_shape_)
		funkletref().setCoeffShape(shape_);

	      return funkletref.dewr_p();
	    }
	  }
	if( n )
	  {
	    //get the one with best fitting domain....
	    funkletref <<= funklets.front();
	    
	    //reset dbid if funklet domain not matching 
	    if(funkletref->domain().start(0)!=domain.start(0) || funkletref->domain().start(1)!=domain.start(1) ||
	       funkletref->domain().end(0)!=domain.end(0) || funkletref->domain().end(1)!=domain.end(1))
	      {
		cdebug(3)<<" resetting dbid" <<funkletref->domain().start(0)<<" == "<<domain.start(0)<<endl;
		cdebug(3)<<funkletref->domain().start(1)<<" == "<<domain.start(1)<<endl;
		cdebug(3)<<funkletref->domain().end(1)<<" == "<<domain.end(1)<<endl;
		cdebug(3)<<funkletref->domain().end(1)<<" == "<<domain.end(1)<<endl;
		funkletref(). setDbId (-1);
		funkletref().setDomain(domain);
	      }
	    if(force_shape_)
	      funkletref().setCoeffShape(shape_);
	    if (!reset_funklet_) return funkletref.dewr_p();
	  }
      }
    else
      {
	cdebug(3)<<"no MEP table assigned"<<endl;
      }
    // If we get here, there's no table or no funklet has been found -- try to get default
    int dbid=-1;
    if(funkletref.valid())
      dbid=funkletref().getDbId();
    funkletref.detach();
    if( !funkletref.valid())
      {
	if( parmtable_ )
	  {
	    //MMMM change for parmdb
#ifdef HAVE_PARMDB	    
	    int n=0;
#else
	    parmtable_ = ParmTable::openTable(parmtable_name_);
	    int n = parmtable_->getInitCoeff(funkletref,name_);
#endif
	    cdebug(3)<<"looking for funklets in defaults subtable: "<<n<<endl;
	  }
	if( !funkletref.valid())
	  {
	    
	    //use previous funklet, unless user really wants default??
	    if( _use_previous && converged_ && its_funklet_.valid())
	      {
		if(its_funklet_->objectType()!=TpMeqComposedPolc)
		  {
		    funkletref = its_funklet_;
		    //reset dbid
		  }
		else
		  {
		    const DMI::List *funklist = its_funklet_[FFunkletList].as_po<DMI::List>();
		    funkletref = funklist->get(0);  //better getlast
		  }
	      }
	    
	    else
	      {
		const Funklet *initfunklet = state()[FInitFunklet].as_po<Funklet>();
		if(!initfunklet){
		  DMI::NumArray::Ref arrayref;
		  arrayref<<=new DMI::NumArray(Tpdouble,LoShape(1,1));
		  arrayref()[0,0]=default_;
		  Funklet *deffunklet = new Polc(arrayref);
		  funkletref <<= deffunklet;
		  cdebug(3)<<"no funklets found, using default value from state record, type "<<funkletref().objectType()<<endl;
		}
		else
		  {
		    funkletref<<=initfunklet;
		    cdebug(3)<<"using init funklet from state record, type "<<funkletref().objectType()<<endl;
		  }
	      }
	  }
      }	
    funkletref().clearSolvable();
    funkletref().setDomain(domain);
    if(force_shape_)
      funkletref().setCoeffShape(shape_);
    funkletref(). setDbId (dbid);
    return funkletref.dewr_p();

    
    
  }


  int Parm::initSolvable (Funklet &funklet,const Request &request)
  {
    // copy current domain into solvable funklet
    // (once we start solving, it is only valid for the solve domain, even if it may
    // have been valid for a bigger/different domain before)
  
    cdebug(4)<<"init solvable "<<endl;

    //MMMMMcheck when and why we set domain
    funklet.setDomain(request.cells().domain());
    int nr = 0;
    funklet.clearSolvable();

    if( isSolvable() )
      {
	int spidIndex = 256*nodeIndex();
	nr += funklet.makeSolvable(spidIndex);
	if( funklet.getPerturbation() == 0 )
	  {
	    cdebug(3)<<"warning: null funklet perturbation, using default 1e-6"<<endl;
	    funklet.setPerturbation(1e-6);
	  }
      } 
    cdebug(4)<<"init solvable, nr:"<<nr<<endl;

    return nr;
  }

  void Parm::GetTiledDomains(Domain::Ref & domain, const Cells & cells,vector<Domain::Ref> & domainV){
    //   vector<Domain> domainV; //create vector of domains..1 per funklettile
    domainV.clear();
    domainV.push_back(domain);
    //calculate domains..
    for(int axis=0;axis<Axis::MaxAxis;axis++){
      cdebug(4)<<"tiling axis "<<axis<<", nr_tiles:"<<tiling_[axis]<<endl;

      if(tiling_[axis]<=0) continue; //not tiled in this direction
      int nr_cells=cells.ncells(axis);
      const LoVec_double & cellStart = cells.cellStart (axis);
      const LoVec_double & cellEnd = cells.cellEnd (axis);
      if(nr_cells<=0) continue;

      int nr_tiles=(nr_cells+tiling_[axis]-1)/tiling_[axis]; //round to higher value
      vector<Domain::Ref> helpV;
 
      for(vector<Domain::Ref>::iterator domIt=domainV.begin();domIt<domainV.end();domIt++)
	  {
	    
	    for(int i=0;i<nr_tiles;i++)
	      {
		(*domIt)().defineAxis(axis,cellStart(i*tiling_[axis]),cellEnd(std::min(nr_cells-1,(i+1)*tiling_[axis]-1)));
		helpV.push_back(*domIt);
	      }
	    
	    
	  }
      domainV.clear();

      for(vector<Domain::Ref>::iterator domIt2=helpV.begin();domIt2<helpV.end();domIt2++)
	{
	  domainV.push_back(*domIt2);
	  
	}
      helpV.clear();
      cdebug(2)<<" total nr domains : "<<domainV.size()<<endl;
      
    }
  }

  bool Parm::checkTiledFunklet(Funklet::Ref &funkletref,std::vector<Domain::Ref> domainV)
  {
    //cehcks for solvable parms if te funkeltlist exactly matches the required tiling, reset the funklet otherwise
    bool match =false;
    
    if (funkletref->objectType()==TpMeqComposedPolc)
	{
	  match=true;
	  const DMI::List *funklist = funkletref[FFunkletList].as_po<DMI::List>();
	  FailWhen(!funklist,"Composed Polc does not contain funklist");
	  const Funklet::Ref & firstfunk = funklist->get(0);
	  int ncoeff = firstfunk->ncoeff();
	  
	  if(!funklist  || (int(domainV.size())!=funklist->size())) match=false;
	  else
	    for(int axis=0;axis<Axis::MaxAxis;axis++){
	      //if(!tiling_[axis]) continue;
	      int funknr=0;
	      for(vector<Domain::Ref>::iterator domIt=domainV.begin();domIt<domainV.end();domIt++){
		const Funklet::Ref & partfunk = funklist->get(funknr++); 

		if(((*domIt)->start(axis)!= partfunk->domain().start(axis)) ||
		   ((*domIt)->end(axis)!= partfunk->domain().end(axis))||
		   (partfunk->ncoeff()!=ncoeff))
		  {
		    //maybe even better; only keep those funklets that do match in case nr_funklets>nr_domains
		    match=false;
		    break;
		  }

	      }
	      if(!match) break;

	    }
	  if(!match){
	    funkletref = firstfunk;
	  }
	}
    if(match)
      if(force_shape_)
	funkletref().setCoeffShape(shape_);


    return match;
	  
  }    

  Funklet * Parm::initTiledFunklet(Funklet::Ref &funkletref,const Domain & domain, const Cells & cells){

    //now if tiling change to ComposedPolc, all initialized with the same funklet....(should we check on solvability here?) 
    vector<Domain::Ref> domainV; //create vector of domains..1 per funklettile
    Domain::Ref domref;
    domref <<=new Domain(domain);


    GetTiledDomains(domref,cells,domainV);
    if(domainV.size()<=1)
      return funkletref.dewr_p();

    if(checkTiledFunklet(funkletref,domainV))     
      return funkletref.dewr_p();

      
    //now create funklet for every domain.
 
    vector<Funklet::Ref> funklets;
    funklets.resize(domainV.size());
    int n=0;
    for(vector<Domain::Ref>::iterator domIt=domainV.begin();domIt<domainV.end();domIt++){
      funkletref().setDomain(**domIt);
      funkletref().setDbId(-1);
      funklets[n++]=funkletref;
    }
    cdebug(2)<<"creating composed polc  "<<funklets.size()<<endl;
    //   funkletref.detach();
    ComposedPolc * cpolc =new ComposedPolc(funklets);
    funkletref<<=cpolc;
    return funkletref.dewr_p();
      
  }


  Funklet * Parm::initFunklet (const Request &request,bool solve)
  {
    const Domain &domain = request.cells().domain();
    const Cells &cells = request.cells();

    //    HIID rq_dom_id = RqId::maskSubId(request.id(),forest().getDependMask(FDomain));
    HIID rq_dom_id = RqId::maskSubId(request.id(),domain_depend_mask_);

    // NB: OMS 20/02/2006: I have removed the newrid variable, since
    // the domain_depend_mask now includes FDataset, so the rq_dom_id
    // is pretty much equivalent

    // do we have a current funklet set up?

    //parm should keep a reference to the funklet object, snce it doesnt have to be equal to the wstate...
    //    Funklet * pfunklet = wstate()[FFunklet].as_wpo<Funklet>();
    Funklet * pfunklet(0);
    cdebug(3)<<" getting old funklet"<<endl;
    if(its_funklet_.valid())
      pfunklet= its_funklet_.dewr_p();
    // see if this can be reused
    
    if( pfunklet )
      {
	// reuse the funklet if domain and dataset do not change
         if( !rq_dom_id.empty() && rq_dom_id == domain_id_ )
          {
            cdebug(3)<<"current funklet request ID matches, re-using"<<endl;
            return its_funklet_.dewr_p();
          }
 
        // (b) no domain in funklet (i.e. effectively infinite domain of applicability)
        if( ! tiled_ && (pfunklet->objectType()!=TpMeqComposedPolc) && !pfunklet->hasDomain() )
          {
            cdebug(3)<<"current funklet has infinite domain, re-using"<<endl;
            wstate()[FDomainId] = domain_id_ = rq_dom_id;
            wstate()[FDomain].replace() <<= &domain;

	    const LoShape shape=pfunklet->getCoeffShape();
	    if(force_shape_)
	      pfunklet->setCoeffShape(shape_);
	    
            return its_funklet_.dewr_p();
          }
        // (c) funklet domain is a superset of the requested domain
        if(!tiled_ && (pfunklet->objectType()!=TpMeqComposedPolc) &&  pfunklet->domain().supersetOfProj(domain) )
          {
            cdebug(3)<<"current funklet defined for superset of requested domain, re-using"<<pfunklet->getDbId()<<endl;
	    if(pfunklet->domain().start(0)!=domain.start(0) || pfunklet->domain().start(1)!=domain.start(1) ||
	       pfunklet->domain().end(0)!=domain.end(0) || pfunklet->domain().end(1)!=domain.end(1))
	      {
		cdebug(3)<<" resetting dbid" <<pfunklet->domain().start(0)<<" == "<<domain.start(0)<<endl;
		cdebug(3)<<pfunklet->domain().start(1)<<" == "<<domain.start(1)<<endl;
		cdebug(3)<<pfunklet->domain().end(1)<<" == "<<domain.end(1)<<endl;
		cdebug(3)<<pfunklet->domain().end(1)<<" == "<<domain.end(1)<<endl;
		pfunklet->setDbId(-1);
	      }
            wstate()[FDomainId] = domain_id_ = rq_dom_id;
            wstate()[FDomain].replace() <<= &domain;
	    const LoShape shape=pfunklet->getCoeffShape();
	    if(force_shape_)
	      pfunklet->setCoeffShape(shape_);
            return its_funklet_.dewr_p();
          }


      }
    // no funklet, or funklet not suitable -- get a new one
    Funklet::Ref funkref;
    pfunklet = findRelevantFunklet(funkref,domain);
    FailWhen(!pfunklet,"no funklets found for specified domain");
    cdebug(2)<<"found relevant funklet, type "<<pfunklet->objectType()<<endl;
    if(pfunklet->objectType()!=TpMeqCompiledFunklet && pfunklet->hasField(FFunction))
      {
        cdebug(4)<<"function found in state, creating new compiled funklet"<<endl;
        its_funklet_<<=new CompiledFunklet(*pfunklet);
        pfunklet = its_funklet_.dewr_p();
      }
    else
      {
	if(force_shape_)
	  pfunklet->setCoeffShape(shape_);
	its_funklet_<<=pfunklet;
      }
    
    if(tiled_ && isSolvable()){

        cdebug(4)<<"tiling funklet, "<<endl;
        Funklet *newfunklet = initTiledFunklet(funkref,domain,cells);
        funkref().setDomain(domain);
        its_funklet_=funkref;
        wstate()[FFunklet].replace() = its_funklet_().getState();
        wstate()[FDomainId] = domain_id_ = rq_dom_id;
        wstate()[FDomain].replace() <<= &domain;
        cdebug(2)<<"found relevant funklet,after tiling type "<<newfunklet->objectType()<<endl;
        return its_funklet_.dewr_p();
      }
    wstate()[FFunklet].replace() = its_funklet_().getState();
    wstate()[FDomainId] = domain_id_ = rq_dom_id;
    wstate()[FDomain].replace() <<= &domain;
    return its_funklet_.dewr_p();
    
   
    //MMMMreimplement
  }



  // creates spid map in output result
  int Parm::discoverSpids (Result::Ref &ref,
                           const std::vector<Result::Ref> &,
                           const Request &request)
  {
    if( !isSolvable() )
      return 0;
    domain_depend_mask_ = symdeps().getMask(domain_symdeps_);
    solve_depend_mask_ = symdeps().getMask(solve_symdeps_);
    // init solvable funklet for this request
    Funklet * pfunklet = initFunklet(request,True);
    cdebug(3)<<"init funklet "<<pfunklet->objectType()<<" "<<pfunklet->isSolvable()<<endl;
    if( !pfunklet->isSolvable() )
      {	
	initSolvable(*pfunklet,request);
	if(  isSolvable()){
	  //set solve domain, default [0,1]
	  pfunklet->changeSolveDomain(solve_domain_);
	}
      }
    const LoShape shape=pfunklet->getCoeffShape();
    if(force_shape_)
      pfunklet->setCoeffShape(shape_);


    wstate()[FFunklet].replace() = pfunklet->getState();

    // get spids from funklet
    const std::vector<int> & spids = pfunklet->getSpids();
    ref <<= new Result(0);
    // populate spid map with default spid description record containing
    // just our node name
    DMI::Record::Ref defrec(DMI::ANONWR);
    defrec[AidName] = name();
    defrec[FNodeIndex] = nodeIndex();
    //get tilesizes, 0 for no tiling

    if(tiled_ && isSolvable())
      {
	DMI::Vec & tiles  = defrec[FTileSize] <<=new DMI::Vec(Tpint,Axis::MaxAxis,tiling_);
      }
    DMI::Record &map = ref()[FSpidMap] <<= new DMI::Record; 
    for( uint i=0; i<spids.size(); i++ ){
      map[spids[i]] = defrec; 
      cdebug(2)<<"spid "<<i<<" = "<<spids[i]<<endl;
    }
    return domain_depend_mask_|solve_depend_mask_;
  }


  //##ModelId=3F86886F022E
  int Parm::getResult (Result::Ref &resref,
		       const std::vector<Result::Ref> & childres,
		       const Request &request,bool newreq)
  {
    cdebug(3)<<"evaluating parm for domain "<<request.cells().domain()<<endl;
    domain_depend_mask_ = symdeps().getMask(domain_symdeps_);
    solve_depend_mask_ = symdeps().getMask(solve_symdeps_);
    
    // is request for solvable parm values?
    bool solve = isSolvable() && request.evalMode() > 0;
    // find a funklet to use
    Funklet * pfunklet = initFunklet(request,solve);
    // if funklet not set to solvable, do some extra init
    if( solve && !pfunklet->isSolvable() )
      {
	cdebug(3)<<"new solve domain, initializing"<<endl;
	initSolvable(*pfunklet,request);
	pfunklet->changeSolveDomain(solve_domain_);
      }
    else if( !solve && pfunklet->isSolvable() )
      {
	pfunklet->clearSolvable();
      }
    wstate()[FFunklet].replace() = pfunklet->getState();

    // init depend mask
    // if we are solvable, then we always depend on solution progress
    int depend = isSolvable() ? (solve_depend_mask_|domain_depend_mask_): domain_depend_mask_;
    // Create result object and attach to the ref that was passed in
    //    Result &result = resref <<= new Result(1,request); // result has one vellset
    Result &result = resref <<= new Result(1); // result has one vellset
    VellSet & vs = result.setNewVellSet(0,0,request.evalMode());
    if(childres.empty())
      {
	//let funklet define the grid
	cdebug(3)<<"evaluating funklet"<<endl;
	pfunklet->evaluate(vs,request);
      }
    else
      {
	//grid was (partially) defined by children
	pfunklet->evaluate(vs,request,childres);

      }


    // If we have a single constant funklet, and are not integrated, then there's no 
    // dependency on domain. Otherwise, add domain mask
    //MM: Changed since even a constant MeqParm can depend on domain (eg. if its coeff in the meptable depend onthe domain)  
    // OMS: changed again: even without a parmtable as we iterate over successive
    // snippets, we don't want the previous solution to be cached anywhere
    //   if( !pfunklet->isConstant() || integrated_ )
    //    if( !pfunklet->isConstant() || integrated_ || parmtable_)
    //depend |= domain_depend_mask_;

    // set cells in result as needed
    result.setCells(request.cells());
 
    // integrate over cell if so specified
    if( integrated_ )
      result.integrate();
  
    return depend;
  }


  void Parm::save()
  {
#ifdef HAVE_PARMDB	    
    return;
#else
    if( !parmtable_ )
      return;

    if( !its_funklet_.valid() ) 
      return;
    parmtable_ = ParmTable::openTable(parmtable_name_);

    if(its_funklet_->objectType()==TpMeqComposedPolc){
      DMI::List *funklist = its_funklet_()[FFunkletList].as_wpo<DMI::List>();
      if(!funklist) return;
      int nr_funk=funklist->size();
      cdebug(2)<<"saving "<<nr_funk<<" funklets"<<endl;
      for (int ifunk=0;ifunk<nr_funk;ifunk++)
	{
	  Funklet::Ref partfunk = funklist->get(ifunk);
	  parmtable_->putCoeff1(name_,partfunk,false);
	  cdebug(4)<<" put in database "<<partfunk->getDbId()<<endl;
 	  funklist->replace(ifunk,partfunk);
	}
    }
    else
      parmtable_->putCoeff1(name_,its_funklet_,false);
#endif

  }

  void Parm::setStateImpl (DMI::Record::Ref& rec, bool initializing)
  {
    Node::setStateImpl(rec,initializing);
    // get parm name, or use node name by default
    if( initializing && name_.empty() )
      name_ = name();
    rec[FParmName].get(name_,initializing);
    rec[FAutoSave].get(auto_save_,initializing);
    rec[FUsePrevious].get(_use_previous,initializing);
    rec[FConverged].get(converged_,initializing);
    rec[FSaveAll].get(ignore_convergence_,initializing);
    rec[FSolvable].get(solvable_,initializing);
    rec[FIntegrated].get(integrated_,initializing);
    rec[FResetFunklet].get(reset_funklet_,initializing);

    //default
    solve_domain_[0]=0.;
    solve_domain_[1]=1.;
    

    rec[FSolveDomain].get_vector(solve_domain_,initializing);

    const DMI::Record *tiling = rec[FTiling].as_po<DMI::Record>();
    if(tiling){
      for(int i=0;i<Axis::MaxAxis;i++){
	tiling_[i]=0;
	(*tiling)[Axis::axisId(i)].get(tiling_[i],0);
      
	if(tiling_[i]) tiled_=true;
      }
    }

    // recompute depmasks if active sysdeps change
    if( rec[FDomainSymDeps].get_vector(domain_symdeps_,initializing) )
      {
	cdebug(2)<<"domain_symdeps set via state\n";
      }
    if( rec[FSolveSymDeps].get_vector(solve_symdeps_,initializing) )
      {
	cdebug(2)<<"solve_symdeps set via state\n";
      }
 
   
    // Is a funklet specified? 
    const Funklet * pfunklet = rec[FFunklet].as_po<Funklet>();
    if( pfunklet )
      {
	
	if(pfunklet->objectType()!=TpMeqCompiledFunklet  && pfunklet->hasField(FFunction))
	  {
	    cdebug(4)<<"function found in state, creating new compiled funklet"<<endl;
	    its_funklet_<<= new CompiledFunklet(*pfunklet);
	    
	  }
	else
	  if(pfunklet->hasField(FClass) && (*pfunklet)[FClass].as<string>()=="MeqPolcLog")
	    its_funklet_<<= new PolcLog(*pfunklet);
	  else
	    its_funklet_<<= new Polc(*pfunklet);
	

	cdebug(2)<<"new funklet set via state\n";
	// if a new funklet is set on the fly (i.e. not in node initialization),
	// then reset cached domain & domain ID. This will force an reinit
	// on the next getResult() call, thus either re-using or discarding the
	// funklet as appropriate.
	if( !initializing )
	  {
	    cdebug(2)<<"resetting domainID"<<endl;
	    wstate()[FDomain].remove(); 
	    wstate()[FDomainId] = domain_id_ = HIID();
	  }
      }
    // get domain IDs, if specified
    rec[FDomainId].get(domain_id_);
    // Get default value (to be used if no table exists)
    rec[FDefaultValue].get(default_,initializing);
    cdebug(3)<<"default value "<<default_;
    const Funklet *initfunklet = rec[FInitFunklet].as_po<Funklet>();
    if( initfunklet )
      {
	cdebug(2)<<"default funklet set via state\n type = "<<initfunklet->objectType()<< endl;;
      }


    if(rec->hasField(FShape)){
	 std::vector<int> shape;    
	 rec[FShape].get_vector(shape,initializing);
	 if(!(shape.size())) return;
	 if(shape.size()>1)
	   shape_=LoShape(shape[0],shape[1]);
	 else
	   shape_=LoShape(shape[0],1);
	 force_shape_=true;
	   
       }

    //MMMMshape

    // Get ParmTable name 
    HIID tableId;
    TypeId  TableType;
    if( rec->hasField(FTableName))
      {  TableType= rec[FTableName].type();   
	//check wether tablename is a string or a hiid in which case one should look in the forest state for the name
	if(TableType==Tpstring)
	  rec[FTableName].get(parmtable_name_);
	else if(TableType==TpDMIHIID)
	  {
	    //try to get the name from forest
	    rec[FTableName].get(tableId);
	    cdebug(3)<<"looking for tablename in forest state, field: "<<tableId<<endl;
	    const DMI::Record &Fstate=forest().state();
	    if(Fstate.hasField(tableId) && Fstate[tableId].type()==Tpstring) 
	      {
		Fstate[tableId].get(parmtable_name_);
	      }
	  }
	if (parmtable_name_.empty())
	  cdebug(2)<<"TableName doesnot have  correct type, or not found in forest state"<<endl; 
      
	if( parmtable_name_.empty() ) { // no table
	  parmtable_ = 0;
	}
	else    // else open a table
	  {
	    cdebug(2)<<"opening table: "<<parmtable_name_<<endl;
	    //check if table exists, otherwise create.
	    //MMMM: change to new tableinterface...wait fo rbetter defaults??
#ifdef HAVE_PARMDB	    
	    parmtable_ = new  LOFAR::ParmDB::ParmDB(LOFAR::ParmDB::ParmDBMeta("aips",parmtable_name_));
#else
	    parmtable_ = ParmTable::openTable(parmtable_name_);
#endif
	  }
      }//if rec[TableName]
    
  }
  
  void Parm::clearFunklets ()
  {
    // clear out relevant fields
    its_funklet_.detach();
    wstate()[FFunklet].remove();
    wstate()[FDomain].remove();
    wstate()[FDomainId].remove();
    domain_id_ = HIID();
  }

  int Parm::processCommand (Result::Ref &resref,const HIID &command,
                            DMI::Record::Ref &args,int verbosity)
  {
    // process parent class commands
    int retcode = Node::processCommand(resref,command,args,verbosity);
    
    if( command == FUpdateParm )
    {
      retcode |= RES_OK;
      // check if Converged flag is raised
      if( args[FConverged].as<bool>(false) )
	wstate()[FConverged] = converged_ = true;
      
      // Are updated Values specified? use it to update solve funklets
      bool saved = false;
      DMI::Record::Hook hset(*args,FIncrUpdate);
      if( hset.exists() )
      {
	if( isSolvable() )
	{
          // OMS 27/02/2006: we used to pass in the Request and make this sanity check.
          // Since we no longer pass in a request, I have commented out this 
          // check and the else clause below.
          // 	  HIID req_domain_id = RqId::maskSubId(req.id(),domain_depend_mask_);
          //           // check that the update refers to the same domain (if this is not true,
          //           // something is seriously wrong)
          //	  if( req_domain_id == domain_id_ )
	  cdebug(2)<<"got updated values"<<endl;
	  // Update the funklet coefficients with the new values.
	  LoVec_double values = hset.as<LoVec_double>();
	  FailWhen(!tiled_ && (values.size() != int(its_funklet_->getSpids().size())),
		   "size of "+FIncrUpdate.toString()+" field does not match size of funklets");
	  its_funklet_().update(values.data());
	  wstate()[FFunklet].replace()=its_funklet_().getState();
	  if( auto_save_ )
	  {
	    save();
	    saved = true;
	  }
	  // result depends on everything
	  retcode |= domain_depend_mask_|solve_depend_mask_;
          if( verbosity>0 )
            postMessage("applied incremental spid value update");
          // 	  else
          // 	  {
          //             Throw("received incremental update for an unexpected domain ID");
          //             // cdebug(2)<<"got incremental update, but request domain ID "<<req_domain_id<<
          //             //  " does not match current funklet domain ID "<<domain_id_<<endl;
          //             // cdebug(2)<<"ignoring the incremental update"<<endl;
          // 	  }
	}
	else // not solvable
	{
          Throw("received incremental update for a non-solvable parm");
          // cdebug(2)<<"got incremental update but parm is not solvable"<<endl;
          // cdebug(2)<<"ignoring the incremental update"<<endl;
	}
      }
      
      // if not already saved, then check for a Save.Funklets option
      cdebug(2)<<"saving funklets ? "<<args[FSaveFunklets].as<bool>(false)<<endl;
      if( !saved && args[FSaveFunklets].as<bool>(false) )
      {
	if(converged_||ignore_convergence_)
	  {
	    save();
	    saved = true;
	  }
      }
      if( saved && verbosity>0 )
        postMessage("funklets have been saved");
      
      // lastly, check for a Clear.Funklets option
      if( args[FClearFunklets].as<bool>(false) )
      {
        clearFunklets();
        if( verbosity>0 )
          postMessage("clearing funklets");
      }
    }
    else if( command == FSaveFunklets )
    {
      save();
      if( verbosity>0 )
        postMessage("saving funklets");
      retcode |= RES_OK;
    }
    else if( command == FClearFunklets )
    {
      clearFunklets();
      if( verbosity>0 )
        postMessage("clearing funklets");
      retcode |= RES_OK;
    }
    
    // accumulated return code
    return retcode;
  }

  //##ModelId=400E53520391
  string Parm::sdebug (int detail, const string &prefix,const char* nm) const
  {
    string out = Node::sdebug(detail,prefix,nm);
    if( detail>=2 || detail == -2) {
#ifdef HAVE_PARMDB
      Debug::appendf(out,"  parmtable=%s", parmtable_->getParmDBMeta().getTableName().c_str());
      
#else
      Debug::appendf(out,"  parmtable=%s", parmtable_->name().c_str());
#endif
    }
    return out;
  }



} // namespace Meq
