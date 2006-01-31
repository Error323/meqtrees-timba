//  MSVisOutputAgent.h: agent for writing an AIPS++ MS
//
//  Copyright (C) 2002
//  ASTRON (Netherlands Foundation for Research in Astronomy)
//  P.O.Box 2, 7990 AA Dwingeloo, The Netherlands, seg@astron.nl
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation; either version 2 of the License, or
//  (at your option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with this program; if not, write to the Free Software
//  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//
//  $Id$

#include "MSOutputChannel.h"

#include <TimBase/BlitzToAips.h>
#include <DMI/Exception.h>
#include <AppAgent/VisDataVocabulary.h>
#include <TimBase/AipsppMutex.h>

#include <tables/Tables/ArrColDesc.h>
#include <tables/Tables/ArrayColumn.h>
#include <tables/Tables/ScalarColumn.h>
#include <casa/Arrays/Matrix.h>

using namespace casa;

namespace AppAgent
{

using namespace LOFAR;
using namespace LOFAR::Thread;
using AipsppMutex::aipspp_mutex;

using namespace AppEvent;
using namespace VisData;
using namespace MSChannel;

//##ModelId=3E2831C7010D
MSOutputChannel::MSOutputChannel ()
    : FileChannel(),msname_("(none)")
{
  setState(CLOSED);
}


//##ModelId=3E28315F0001
int MSOutputChannel::init (const DMI::Record &params)
{
  if( FileChannel::init(params) < 0 )
    return state();
  
  Mutex::Lock lock(aipspp_mutex);
  params_ = params;
  ms_ = MeasurementSet();
  msname_ = "(none)";
  
  cdebug(1)<<"initialized with "<<params_.sdebug(3)<<endl;
  
  return state();
}

void MSOutputChannel::close (const string &msg)
{
  FileChannel::close(msg);
  Mutex::Lock lock(aipspp_mutex);
  ms_ = MeasurementSet();
  msname_ = "(none)";
  cdebug(1)<<"closed\n";
}

//##ModelId=3EC25BF002D4
void MSOutputChannel::postEvent (const HIID &id, const ObjRef &data,AtomicID cat,const HIID &src)
{
  recordOutputEvent(id,data,cat,src);
  Mutex::Lock lock(aipspp_mutex);
  try
  {
    int code = VisEventType(id);
    if( code == HEADER )
    {
      DMI::Record::Ref ref = data;
      doPutHeader(*ref);
      setState(DATA);
    }
    else if( code == DATA )
    {
      if( state() != DATA )
      {
        cdebug(3)<<"got tile but state is not DATA, ignoring\n";
      }
      else
      {
        VTile::Ref ref = data;
        doPutTile(*ref);
      }
    }
    else if( code == FOOTER )
    {
      if( state() == DATA )
      {
        cdebug(2)<<"got footer event, flushing & closing ms\n";
        setState(CLOSED);
        ms_.unlock();
        ms_.flush();
        ms_ = MeasurementSet();
      }
      else
      {
        cdebug(2)<<"got footer but state is not DATA, ignoring\n";
      }
    }
  }
  catch( std::exception &exc )
  {
    cdebug(1)<<"error handling event ["<<id<<"]: "<<exceptionToString(exc);
  }
  catch( ... )
  {
    cdebug(1)<<"unknown exception handling event ["<<id<<"]\n";
  }
}

//##ModelId=3EC25BF002E4
bool MSOutputChannel::isEventBound (const HIID &id,AtomicID)
{
  return id.matches(VisEventMask());
}

bool MSOutputChannel::setupDataColumn (Column &col)
{
  // if name is not set, then column is ignored
  if( !col.name.length() )
    return col.valid = false;
  // add column to MS, if it doesn't exist
  if( !ms_.tableDesc().isColumn(col.name) ) 
  {
    cdebug(2)<<"creating new column "<<col.name<<", shape "<<null_cell_.shape()<<endl;
    ArrayColumnDesc<Complex> coldesc(col.name,"added by MSOutputAgent",null_cell_.shape(),ColumnDesc::Direct);
    ms_.addColumn(coldesc);
  }
  // init the column
  cdebug(2)<<"attaching to column "<<col.name<<endl;
  col.col.attach(ms_,col.name);
  return col.valid = true;
}

//##ModelId=3EC25F74033F
int MSOutputChannel::refillStream() 
{
  return AppEvent::WAIT; // no input events
}

//##ModelId=3E28316403E4
void MSOutputChannel::doPutHeader (const DMI::Record &header)
{
  // open the MS named in the header (incidentally, this will also
  // flush & close any previously named MS)
  msname_ = header[FMSName].as<string>();
  ms_ = MeasurementSet(msname_,TableLock(TableLock::AutoNoReadLocking),Table::Update);
  // get range of channels from header and setup slicer
  int chan0 = header[FChannelStartIndex].as<int>(),
      chan1 = header[FChannelEndIndex].as<int>(),
      chan_incr_ = header[FChannelIncrement].as<int>(1);
  int ncorr = header[FCorr].size(Tpstring);
  flip_freq_ = header[FFlipFreq].as<bool>(false);
  column_slicer_ = Slicer(IPosition(2,0,chan0),
                          IPosition(2,ncorr-1,chan1),
                          IPosition(2,1,chan_incr_),
                          Slicer::endIsLast);
  IPosition origshape = LoShape(header[FOriginalDataShape].as_vector<int>());
  null_cell_.resize(origshape);
  null_cell_.set(0);
  // setup parameters from default record
  write_flags_       = params_[FWriteFlags].as<bool>(false);
  flagmask_          = params_[FFlagMask].as<int>(0xFFFFFFFF);
  datacol_.name      = params_[FDataColumn].as<string>("");
  predictcol_.name   = params_[FPredictColumn].as<string>("");
  rescol_.name       = params_[FResidualsColumn].as<string>("");
  // and override them from the header
  if( header[FOutputParams].exists() )
  {
    const DMI::Record &hparm = header[FOutputParams].as<DMI::Record>();
    write_flags_       = hparm[FWriteFlags].as<bool>(write_flags_);
    flagmask_          = hparm[FFlagMask].as<int>(flagmask_);
    datacol_.name      = hparm[FDataColumn].as<string>(datacol_.name);
    predictcol_.name   = hparm[FPredictColumn].as<string>(predictcol_.name);
    rescol_.name       = hparm[FResidualsColumn].as<string>(rescol_.name);
  }
  // setup columns
  setupDataColumn(datacol_);
  setupDataColumn(predictcol_);
  setupDataColumn(rescol_);
  if( write_flags_ )
  {
    rowFlagCol_.attach(ms_,"FLAG_ROW");
    flagCol_.attach(ms_,"FLAG");
  }

  cdebug(2)<<"got header for MS "<<msname_<<endl;
  cdebug(2)<<"  orig shape: "<<origshape<<endl;
  cdebug(2)<<"  channels: "<<chan0<<"-"<<chan1<<endl;
  cdebug(2)<<"  correlations: "<<ncorr<<endl;
  cdebug(2)<<"  write_flags: "<<write_flags_<<endl;
  cdebug(2)<<"  flagmask: "<<flagmask_<<endl;
  cdebug(2)<<"  colname_data: "<<datacol_.name<<endl;
  cdebug(2)<<"  colname_predict: "<<predictcol_.name<<endl;
  cdebug(2)<<"  colname_residuals: "<<rescol_.name<<endl;
  // set state to indicate success
  tilecount_ = rowcount_ = 0;
}

//##ModelId=3F5F436303AB
void MSOutputChannel::putColumn (Column &col,int irow,const LoMat_fcomplex &data)
{
  Matrix<Complex> aips_data;
  if( flip_freq_ )
  {
    LoMat_fcomplex revdata(data);
    revdata.reverseSelf(blitz::secondDim);
    B2A::copyArray(aips_data,revdata);
  }
  else
    B2A::copyArray(aips_data,data);
  cdebug(6)<<"writing "<<col.name<<": "<<aips_data<<endl;
  if( !col.col.isDefined(irow) )
    col.col.put(irow,null_cell_);
  col.col.putSlice(irow,column_slicer_,aips_data);
}

//##ModelId=3E28316B012D
void MSOutputChannel::doPutTile (const VTile &tile)
{
  tilecount_++;
  cdebug(3)<<"putting tile "<<tile.tileId()<<", "<<tile.nrow()<<" rows"<<endl;
  cdebug(4)<<"  into table rows: "<<tile.seqnr()<<endl;
  cdebug(4)<<"  rowflags are: "<<tile.rowflag()<<endl;
  // iterate over rows of the tile
  int count=0;
  for( VTile::const_iterator iter = tile.begin(); iter != tile.end(); iter++ )
  {
    int rowflag = iter.rowflag();
    if( rowflag == int(VTile::MissingData) )
    {
      cdebug(5)<<"  tile row flagged as missing, skipping\n";
      continue;
    }
    count++;
    rowcount_++;
    int irow = iter.seqnr();
    cdebug(5)<<"  writing to table row "<<irow<<endl;
    // write flags if required
    if( write_flags_ )
    {
      rowFlagCol_.put(irow,rowflag&flagmask_ != 0);
      LoMat_bool flags( iter.flags().shape() );
      flags = blitz::cast<bool>(iter.flags() & flagmask_ );
      if( flip_freq_ )
        flags.reverseSelf(blitz::secondDim);
      Matrix<Bool> aflags;
      B2A::copyArray(aflags,flags);
      cdebug(6)<<"writing to FLAG column: "<<aflags<<endl;
      flagCol_.putSlice(irow,column_slicer_,aflags);
    }
    if( tile.defined(VTile::DATA) && datacol_.valid )
      putColumn(datacol_,irow,iter.data());
    if( tile.defined(VTile::PREDICT) && predictcol_.valid )
      putColumn(predictcol_,irow,iter.predict());
    if( tile.defined(VTile::RESIDUALS) && rescol_.valid )
      putColumn(rescol_,irow,iter.residuals());
  }
  cdebug(4)<<"  wrote "<<count<<"/"<<tile.nrow()<<" rows\n";
}

string MSOutputChannel::sdebug (int detail,const string &prefix,const char *name) const
{
  using Debug::append;
  using Debug::appendf;
  using Debug::ssprintf;
  
  string out;
  if( detail >= 0 ) // basic detail
  {
    appendf(out,"%s/%08x",name?name:"MSOutputChannel",(int)this);
  }
  if( detail >= 1 || detail == -1 )
  {
    appendf(out,"MS %s, state %s",msname_.c_str(),stateString().c_str());
  }
  if( detail >= 2 || detail <= -2 )
  {
    appendf(out,"wrote %d tiles/%d rows",tilecount_,rowcount_);
  }
  return out;
}

} // namespace AppAgent

