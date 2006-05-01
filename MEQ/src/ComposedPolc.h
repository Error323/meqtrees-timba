#ifndef MEQ_COMPOSEDPOLC_H
#define MEQ_COMPOSEDPOLC_H
//# Includes
#include <MEQ/Polc.h>
#include <DMI/List.h>
#include <TimBase/lofar_vector.h>

#pragma aidgroup Meq
#pragma type #Meq::ComposedPolc


//A Composed polc contains a list of polcs valid for subdomains of the domain of the composed polcs

namespace Meq 
{ 

  class ComposedPolc : public Polc
  {
    //reimplement axis function 
  public:
  typedef DMI::CountedRef<ComposedPolc> Ref;

  virtual DMI::TypeId objectType () const
  { return TpMeqComposedPolc; }

  // implement standard clone method via copy constructor
    //##ModelId=400E53550131
  virtual DMI::CountedRefTarget* clone (int flags, int depth) const
  { return new ComposedPolc(*this,flags,depth); }
  

  //constructors
  ComposedPolc (const ComposedPolc &other,int flags,int depth) ;
  ComposedPolc (const DMI::Record &other,int flags=0,int depth=0);
  
  ComposedPolc (double pert=defaultPolcPerturbation,double weight=defaultPolcWeight,DbId id=-1);
      
  ComposedPolc (vector<Funklet::Ref> & funklets,double pert=defaultPolcPerturbation,double weight=defaultPolcWeight,DbId id=-1);
  ~ComposedPolc(){}

  void initFunklets(vector<Funklet::Ref> & funklets);

  int makeSolvable(int spidIndex){
    Thread::Mutex::Lock lock(mutex());
    
    const Field * fld = Record::findField(FFunkletList);
    if(!fld ){
      cdebug(2)<<"no funklet list found in record"<<endl;
      return 0;
    }
    DMI::List & funklist =  (*this)[FFunkletList].as_wr<DMI::List>();

    int nr_funk = funklist.size();

    //Funklet::makeSolvable(spidIndex);
    Polc::makeSolvable(spidIndex);
    for(int funknr=0 ; funknr<nr_funk ; funknr++)
      {
	Funklet::Ref partfunk = funklist.get(funknr);

	partfunk().makeSolvable(spidIndex);
	
	funklist.replace(funknr,partfunk);
      }
    //    (*this)[FFunkletList].replace()=funklist;
    return getNrSpids();
  }

  int makeSolvable(int spidIndex,const std::vector<bool> &mask){
    Thread::Mutex::Lock lock(mutex());
    
    const Field * fld = Record::findField(FFunkletList);
    if(!fld ){
      cdebug(2)<<"no funklet list found in record"<<endl;
      return 0;
    }
    DMI::List & funklist = (*this)[FFunkletList].as_wr<DMI::List>();

    int nr_funk = funklist.size();

    Funklet::makeSolvable(spidIndex,mask);
    for(int funknr=0 ; funknr<nr_funk ; funknr++)
      {
	Funklet::Ref partfunk = funklist.get(funknr);

	partfunk().makeSolvable(spidIndex);
 	funklist.replace(funknr,partfunk);
     }
    //    (*this)[FFunkletList].replace()=funklist;
    return getNrSpids();
  }

  int nrFunklets(){
    return nr_funklets_;

  }

  virtual void changeSolveDomain(const Domain & solveDomain);
  virtual void changeSolveDomain(const std::vector<double> & solveDomain);
  virtual void setCoeffShape(const LoShape & shape);

  protected:
  //------------------ implement protected Funklet interface ---------------------------------
  

  virtual void do_evaluate (VellSet &vs,const Cells &cells,
                            const std::vector<double> &perts,
                            const std::vector<int>    &spidIndex,
                            int makePerturbed) const;

  virtual void do_update (const double values[],const std::vector<int> &spidIndex);
  virtual void do_update (const double values[],const std::vector<int> &spidIndex,const std::vector<double> &constraints);
    
  private:
  int nr_funklets_;
  int axisHasShape_[Axis::MaxAxis];
  };

  
  //define  compare functions, for sorting

  static bool compareDomain(const Polc::Ref & f1, const Polc::Ref & f2)
  {
    if(f1 == f2) return 0;
    
    //first sort on time
    if(f1->domain().start(0) != f2->domain().start(0)) return (f1->domain().start(0) < f2->domain().start(0));
    //then freq
    if(f1->domain().start(1) != f2->domain().start(1)) return (f1->domain().start(1) < f2->domain().start(1));
    //domains fully overlap now for sure
    //use the one with largest domain
    if(f1->domain().end(0) != f2->domain().end(0))  return (f1->domain().end(0) < f2->domain().end(0)) ;
    if(f1->domain().end(1) != f2->domain().end(1))  return (f1->domain().end(1) < f2->domain().end(1)) ;
  
    //all the same...hmmm, let's return somtehing for the moment
    return f1->ncoeff()<f2->ncoeff();
  
  }


}
 // namespace Meq

#endif
