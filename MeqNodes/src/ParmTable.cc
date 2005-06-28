///# ParmTable.cc: Object to hold parameters in a table.
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

#include <MeqNodes/ParmTable.h>
#include <MEQ/Meq.h>
#include <MEQ/Domain.h>
#include <MEQ/Polc.h>
#include <MEQ/PolcLog.h>
#include <Common/Debug.h>
#include <tables/Tables/TableLocker.h>
#include <tables/Tables/TableDesc.h>
#include <tables/Tables/ScaColDesc.h>
#include <tables/Tables/ArrColDesc.h>
#include <tables/Tables/SetupNewTab.h>
#include <tables/Tables/ExprNode.h>
#include <tables/Tables/ExprNodeSet.h>
#include <tables/Tables/ScalarColumn.h>
#include <tables/Tables/ArrayColumn.h>
#include <tables/Tables/TableRecord.h>
#include <casa/Arrays/Matrix.h>
#include <casa/Arrays/Vector.h>
#include <casa/Arrays/ArrayUtil.h>
#include <casa/Arrays/Slice.h>
#include <casa/Utilities/Regex.h>
#include <casa/Utilities/GenSort.h>
#include <casa/BasicMath/Math.h>
#include <Common/BlitzToAips.h>

using namespace casa;
using namespace DebugMeq;

namespace Meq {

// define some column names
const String ColName          = "NAME";
const String ColStartFreq     = "STARTFREQ";
const String ColEndFreq       = "ENDFREQ";
const String ColStartTime     = "STARTTIME";
const String ColEndTime       = "ENDTIME";
const String ColValues        = "VALUES";
const String ColFreq0         = "FREQ0";
const String ColTime0         = "TIME0";
const String ColFreqScale     = "FREQSCALE";
const String ColTimeScale     = "TIMESCALE";
const String ColPerturbation  = "PERT";
const String ColWeight        = "WEIGHT";
const String ColLongPolcId    = "LONGPOLCID";
const String ColFunkletType   = "FUNKLETTYPE";
const String ColLScale        = "LSCALE";

const String KeywordDefValues = "DEFAULTVALUES";

//##ModelId=3F95060D031A
std::map<string, ParmTable*> ParmTable::theirTables;

Thread::Mutex ParmTable::theirMutex;


Matrix<double> toParmMatrix (const LoMat_double &values)
{


  Matrix<double> matrix(IPosition(2,values.extent(0),values.extent(1)));
  /*  return Matrix<double> (IPosition(2,values.extent(0),values.extent(1)),
                         const_cast<double*>(values.data()),
                         SHARE);
  */
  B2A::copyArray (matrix , values);
  return matrix;

}

LoMat_double fromParmMatrix (const Array<double>& values)
{
  Assert (values.ndim() == 2);
  LoMat_double mat(values.data(),
                   LoMatShape(values.shape()[0], values.shape()[1]),
                   blitz::duplicateData);
  return mat;
}

//##ModelId=3F86886F02B7
ParmTable::ParmTable (const string& tableName)
: constructor_lock(theirMutex),
  itsTable    (tableName, TableLock(TableLock::UserLocking)),
  itsIndex    (itsTable,ColName),
  itsIndexName(itsIndex.accessKey(),ColName),
  itsInitIndex(0)
{
  if(itsTable.keywordSet().isDefined (KeywordDefValues)) 
  {
    itsInitTable = itsTable.keywordSet().asTable (KeywordDefValues);
    itsInitIndex = new ColumnsIndex (itsInitTable, ColName);
    itsInitIndexName = RecordFieldPtr<String> (itsInitIndex->accessKey(),
                                               ColName);
  }
  constructor_lock.release();
}

//##ModelId=3F86886F02BC
ParmTable::~ParmTable()
{
  Thread::Mutex::Lock lock(theirMutex);
  delete itsInitIndex;
}

//##ModelId=3F86886F02BD
int ParmTable::getFunklets (vector<Funklet::Ref> &funklets,
			    const string& parmName,const Domain& domain, const bool auto_solve_ )
{

  //check if table is still existing, needed if table is deleted in between to tests..
  if(!(Table::isReadable(itsTable.tableName()))){
    cdebug(2)<<"Cannot read Funklet in Table, table not existing "<<endl;
    return 0;
  }

  Thread::Mutex::Lock lock(theirMutex);
  TableLocker locker(itsTable, FileLocker::Read);
  Table sel = find (parmName, domain);
  funklets.resize(sel.nrow());
  if( sel.nrow() > 0 ) 
  {
    ROScalarColumn<double> sfCol (sel, ColStartFreq);
    ROScalarColumn<double> efCol (sel, ColEndFreq);
    ROScalarColumn<double> stCol (sel, ColStartTime);
    ROScalarColumn<double> etCol (sel, ColEndTime);
    ROArrayColumn<double> valCol (sel, ColValues);
    ROScalarColumn<double> f0Col (sel, ColFreq0);
    ROScalarColumn<double> t0Col (sel, ColTime0);
    ROScalarColumn<double> fsCol (sel, ColFreqScale);
    ROScalarColumn<double> tsCol (sel, ColTimeScale);
    ROScalarColumn<double> diffCol (sel, ColPerturbation);
    ROScalarColumn<double> weightCol (sel, ColWeight);    
    ROScalarColumn<String> ftypeCol; 
    
    if(itsTable.actualTableDesc().isColumn(ColFunkletType))
      ftypeCol.attach(sel, ColFunkletType);    
    ROScalarColumn<double> lscaleCol;
    if(itsTable.actualTableDesc().isColumn(ColLScale))
      lscaleCol.attach(sel, ColLScale);    
    //    ROScalarColumn<int> longpolcidCol (sel, ColLongPolcId);
    Vector<uInt> rowNums = sel.rowNumbers(itsTable);
    for( uint i=0; i<sel.nrow(); i++ )
    {
      int axis[] = { Axis::TIME,Axis::FREQ };
      double offset[] = { t0Col(i),f0Col(i) };
      double scale[]  = { tsCol(i),fsCol(i) };
      // for now, only Polcs are supported
      
      Funklet *funklet;
      if (!ftypeCol.isNull() && ftypeCol(i)=="PolcLog"){
	double lscale=1.;
	if(!lscaleCol.isNull()) lscale=lscaleCol(i);
	funklet= new PolcLog(fromParmMatrix(valCol(i)),
			     axis,offset,scale,diffCol(i),weightCol(i),rowNums(i),lscale);
      }
      else
	funklet= new Polc(fromParmMatrix(valCol(i)),
			  axis,offset,scale,diffCol(i),weightCol(i),rowNums(i));
      funklet->setDomain(Domain(stCol(i), etCol(i), sfCol(i), efCol(i)));
      
      if(auto_solve_)
	//reset Dbid, to keep all information
	funklet->setDbId(-1);
      funklets[i] <<=funklet;
            
    }
  }
  return funklets.size();
}

//##ModelId=3F86886F02C3
int ParmTable::getInitCoeff (Funklet::Ref &funkletref,const string& parmName)
{
  Thread::Mutex::Lock lock(theirMutex);
  // Try to find the default initial values in the InitialValues subtable.
  // The parameter name consists of parts (separated by dots), so the
  // parameters are categorised in that way.
  // An initial value can be defined for the full name or for a higher
  // category.
  // So look up until found or until no more parts are left.
  if( itsInitIndex ) 
  {
    string name = parmName;
    while( true ) 
    {
      *itsInitIndexName   = name;
      Vector<uInt> rownrs = itsInitIndex->getRowNumbers();
      if (rownrs.nelements() > 0) 
      {
        Assert( rownrs.nelements() == 1 );
        int row = rownrs(0);
        TableLocker locker(itsInitTable, FileLocker::Read);
        ROArrayColumn<Double> valCol (itsInitTable, ColValues);
        ROScalarColumn<double> f0Col (itsInitTable, ColFreq0);
        ROScalarColumn<double> t0Col (itsInitTable, ColTime0);
        ROScalarColumn<double> fsCol (itsInitTable, ColFreqScale);
        ROScalarColumn<double> tsCol (itsInitTable, ColTimeScale);
        ROScalarColumn<double> diffCol (itsInitTable, ColPerturbation);
        int axis[] = { Axis::TIME,Axis::FREQ };
        double offset[] = { t0Col(row),f0Col(row) };
        double scale[]  = { tsCol(row),fsCol(row) };
        // for now, only Polcs are supported
	Polc polc(fromParmMatrix(valCol(row)),
                              axis,offset,scale,diffCol(row));
	funkletref <<= new Polc(fromParmMatrix(valCol(row)),
                              axis,offset,scale,diffCol(row));
        return polc.ncoeff();
      }
      string::size_type idx = name.rfind ('.');
      // Exit loop if no more name parts.
      if (idx == string::npos) 
        break;
      // Remove last part and try again.
      name = name.substr (0, idx);
    }
  }
  return 0;
}
                                    
void ParmTable::putCoeff1 (const string & parmName,Funklet &funklet, int LPId,
                           bool domain_is_key)
{
  funklet.setDbId(putCoeff(parmName,funklet,LPId,domain_is_key));
}
    
    
//##ModelId=3F86886F02C8
Funklet::DbId ParmTable::putCoeff (const string & parmName,const Funklet & funklet, int LPId,
                                bool domain_is_key)
{

  Thread::Mutex::Lock lock(theirMutex);
  // for now, only Polcs are supported
  FailWhen(funklet.objectType() != TpMeqPolc,"ParmTable currently only supports Meq::Polc funklets");  

  //check if table is still existing, needed if table is deleted in between to tests..
  if(!(Table::isReadable(itsTable.tableName()))){
    cdebug(2)<<"Cannot put Funklet in Table, table not existing "<<endl;
    return -1;
  }
  itsTable.reopenRW();
  TableLocker locker(itsTable, FileLocker::Write);
  ScalarColumn<String> namCol (itsTable, ColName);
  ArrayColumn<double> valCol (itsTable, ColValues);
  ScalarColumn<double> sfCol (itsTable, ColStartFreq);
  ScalarColumn<double> efCol (itsTable, ColEndFreq);
  ScalarColumn<double> stCol (itsTable, ColStartTime);
  ScalarColumn<double> etCol (itsTable, ColEndTime);
  ScalarColumn<double> f0Col (itsTable, ColFreq0);
  ScalarColumn<double> t0Col (itsTable, ColTime0);
  ScalarColumn<double> fsCol (itsTable, ColFreqScale);
  ScalarColumn<double> tsCol (itsTable, ColTimeScale);
  ScalarColumn<double> diffCol (itsTable, ColPerturbation);
  ScalarColumn<double> weightCol (itsTable, ColWeight);
  if(!itsTable.actualTableDesc().isColumn(ColLongPolcId)){
    cdebug(2)<<"longpolcid column not existing, creating"<<endl;
    ScalarColumnDesc<int> newlongpolcidCol(ColLongPolcId); 
    newlongpolcidCol.setDefault (-1);
    itsTable.addColumn(newlongpolcidCol);
    
  }
  ScalarColumn<int> longpolcidCol(itsTable, ColLongPolcId);
  const Domain& domain = funklet.domain();
  const Polc & polc = dynamic_cast<const Polc&>(funklet);
  // for the moment, only Time-Freq variable polcs are supported
  Assert(polc.rank()==2);
  Assert(polc.getAxis(0)==Axis::TIME);
  Assert(polc.getAxis(1)==Axis::FREQ);
  LoMat_double values;
  // polc coefficients may actually be an N-vector or a scalar,
  // so convert them to matrix anyway
  const LoShape & polcshape = polc.getCoeffShape();

  if( polcshape.size() == 2 )
  {
    values.resize(polcshape);
    values = polc.getCoeff2();
 
  }
  else if( polcshape.size() == 1 )
  {
    values.resize(polcshape[0],1);
    values(LoRange::all(),0) = polc.getCoeff1();
  }
  else if( polcshape.size() == 0 )
  {
    values.resize(1,1);
    values = polc.getCoeff0();
  }
  int rownr = polc.getDbId();
  // have a row number? check name, etc.
  if( rownr >= 0 )
  {
    String name;
    namCol.get(rownr,name);
    AssertMsg(string(name)==parmName,"Funklet for parameter "<<
              parmName<<" already has a DbId "<<" and belongs to parameter "<<name);
  }
  else // no assigned row number? Look for one
  {
    if( domain_is_key )
    {
      Table sel = find(parmName,domain);
      if( sel.nrow() > 0 )
      {
        AssertMsg(sel.nrow()==1, "Parameter " << parmName <<
                     " has multiple entries for freq "
                     << domain.start(Axis::FREQ) << ':' << domain.end(Axis::FREQ)
                     << " and time "
                     << domain.start(Axis::TIME) << ':' << domain.end(Axis::TIME));
        rownr = sel.rowNumbers(itsTable)(0);
        AssertMsg (near(domain.start(Axis::FREQ), sfCol(rownr)) &&
                   near(domain.end(Axis::FREQ), efCol(rownr)) &&
                   near(domain.start(Axis::TIME), stCol(rownr)) &&
                   near(domain.end(Axis::TIME), etCol(rownr)),
                   "Parameter " << parmName <<
                   " has a partially instead of fully matching entry for freq "
                     << domain.start(Axis::FREQ) << ':' << domain.end(Axis::FREQ)
                     << " and time "
                     << domain.start(Axis::TIME) << ':' << domain.end(Axis::TIME));
        ArrayColumn<double> valCol (sel, ColValues);
        valCol.put (0, toParmMatrix(values));
      }
    }
    // still unassigned? add to end of table then
    if( rownr < 0 ) 
    {
      rownr = itsTable.nrow();
      itsTable.addRow();
      namCol.put(rownr,parmName);
    }
  }
  // At this point, rownr corresponds to a valid row. Write the polc to 
  // that row
  valCol.put  (rownr, toParmMatrix(values));
  sfCol.put   (rownr, domain.start(Axis::FREQ));
  efCol.put   (rownr, domain.end(Axis::FREQ));
  stCol.put   (rownr, domain.start(Axis::TIME));
  etCol.put   (rownr, domain.end(Axis::TIME));
  f0Col.put   (rownr, polc.getOffset(Axis::FREQ));
  t0Col.put   (rownr, polc.getOffset(Axis::TIME));
  fsCol.put   (rownr, polc.getScale(Axis::FREQ));
  tsCol.put   (rownr, polc.getScale(Axis::TIME));
  diffCol.put (rownr, polc.getPerturbation());
  weightCol.put(rownr, polc.getWeight());
  longpolcidCol.put(rownr,LPId);
  return rownr;
}

//##ModelId=3F86886F02CE
Table ParmTable::find (const string& parmName,
                       const Domain& domain)
{
  // First see if the parameter name exists at all.
  Table result;
  *itsIndexName   = parmName;
  Vector<uInt> rownrs = itsIndex.getRowNumbers();
  if (rownrs.nelements() > 0) {
    Table sel = itsTable(rownrs);
    // Find all rows overlapping the requested domain.
    Table sel3 = sel(domain.start(Axis::FREQ) < sel.col(ColEndFreq)   &&
                     domain.end(Axis::FREQ)   > sel.col(ColStartFreq) &&
                     domain.start(Axis::TIME) < sel.col(ColEndTime)   &&
                     domain.end(Axis::TIME)   > sel.col(ColStartTime));
    result = sel3;

  }
  return result;
}

//##ModelId=3F95060D033E
ParmTable* ParmTable::openTable (const String& tableName)
{
  Thread::Mutex::Lock lock(theirMutex);
  std::map<string,ParmTable*>::const_iterator p = theirTables.find(tableName);
  if (p != theirTables.end()) {
    return p->second;
  }
  //check if table is existing otherwise create
  if(!(Table::isReadable(tableName)))
    ParmTable::createTable(tableName);
  
  ParmTable* tab = new ParmTable(tableName);
  theirTables[tableName] = tab;
  return tab;

}

//##ModelId=3F95060D0372
void ParmTable::closeTables()
{
  Thread::Mutex::Lock lock(theirMutex);
  for (std::map<string,ParmTable*>::const_iterator iter = theirTables.begin();
       iter != theirTables.end();
       ++iter) {
    delete iter->second;
  }
  theirTables.clear();
}

//##ModelId=400E535402E7
void ParmTable::createTable (const String& tableName)
{
  Thread::Mutex::Lock lock(theirMutex);
  TableDesc tdesc;
  tdesc.addColumn (ScalarColumnDesc<String>(ColName));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColEndTime));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColStartTime));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColEndFreq));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColStartFreq));
  tdesc.addColumn (ArrayColumnDesc<Double>(ColValues, 2));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColFreq0));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColTime0));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColFreqScale));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColTimeScale));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColPerturbation));
  tdesc.addColumn (ScalarColumnDesc<Double>(ColWeight));
  tdesc.addColumn (ScalarColumnDesc<Int>(ColLongPolcId));
  SetupNewTable newtab(tableName, tdesc, Table::New);
  Table tab(newtab);
}

void ParmTable::unlock()
{
  Thread::Mutex::Lock lock(theirMutex);
  itsTable.unlock();
  if (! itsInitTable.isNull()) {
    itsInitTable.unlock();
  }
}

void ParmTable::lock()
{
  Thread::Mutex::Lock lock(theirMutex);
  itsTable.lock();
}

void ParmTable::lockTables()
{
  Thread::Mutex::Lock lock(theirMutex);
  for (std::map<string,ParmTable*>::const_iterator iter = theirTables.begin();
       iter != theirTables.end();
       ++iter) {
    iter->second->lock();
  }
}

void ParmTable::unlockTables()
{
  Thread::Mutex::Lock lock(theirMutex);
  for (std::map<string,ParmTable*>::const_iterator iter = theirTables.begin();
       iter != theirTables.end();
       ++iter) {
    iter->second->unlock();
  }
}

} // namespace Meq
