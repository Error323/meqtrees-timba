//  MSVisInputAgent.h: agent for reading an AIPS++ MS
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

#ifndef _MSVISAGENT_MSVISINPUTAGENT_H
#define _MSVISAGENT_MSVISINPUTAGENT_H 1
    
#include <AppUtils/MSChannelDebugContext.h>
#include <AppUtils/MSChannelVocabulary.h>
#include <VisCube/VisVocabulary.h>
#include <VisCube/VTile.h>

#include <ms/MeasurementSets/MeasurementSet.h>
#include <tables/Tables/TableIter.h>
#include <AppAgent/FileChannel.h>

namespace AppAgent
{
using namespace DMI;
  
using namespace VisCube;
using namespace VisVocabulary;

//##ModelId=3DF9FECD013C
//##Documentation
//## MSVisInputAgent is an input agent for reading data from an AIPS++
//## Measurement Set. It is initialized from a DMI::Record laid out as follows:
//## 
//## rec[MSVisInputAgentParams]  (record)    contains all parameters below
//##    +--[FMSName]             (string)    MS filename (must be present)
//##    +--[FDataColumnName]     (string)    column to read visibilities from
//##                                         (default is "DATA", but can use, 
//##                                           e.g., "MODEL_DATA")
//##    +--[FTileSize]           (int)       tile size (default: 1 timeslot)
//##    +--[FClearFlags]         (bool)      clear all input flags
//##    +--[FSelection]          (record)    determines MS selection:
//##       +--[FDDID]              (int)     selects data description ID 
//##       +--[FFieldIndex]        (int)     selects field  
//##       +--[FChannelStartIndex] (int)     starting channel (default: 0)
//##       +--[FChannelEndIndex]   (int)     ending channel (default: last chan.)
//##       +--[FChannelIncrement]  (int)     channel increment step (default: 1)
//##       +--[FSelectionString] (string)    additional TaQL selection applied 
//##                                           to MS
class MSInputChannel : public FileChannel
{
  public:
    //##ModelId=3DF9FECD0219
      MSInputChannel ();
      
    //##ModelId=3DF9FECD0235
      virtual int init (const DMI::Record &data);
      
    //##ModelId=3DF9FECD0244
      virtual void close (const string &str="");
      
    //##ModelId=3DFDFC060373
      string sdebug ( int detail = 1,const string &prefix = "",
                      const char *name = 0 ) const;
      
    //##ModelId=400E5B6C0098
      ImportDebugContext(MSChannelDebugContext);
      
  protected:
    //##ModelId=3EC252C1000E
    //##Documentation
    //## called to put more objects on the stream. Returns SUCCESS if something
    //## was put on, or <0 code (ERROR/CLOSED/whatever)
    virtual int refillStream();

  private:
      //##ModelId=3DF9FECD0142
      typedef vector<VTile::Ref> TileCache;

    //##ModelId=3DF9FECD0248
      MSInputChannel(const MSInputChannel &right);
    //##ModelId=3DF9FECD0253
      MSInputChannel& operator = (const MSInputChannel &right);
      
      // prepares MS for reading
    //##ModelId=3DF9FECD025E
      void openMS     (DMI::Record &hdr,const DMI::Record &selection);
      // fills headers from subtables
    //##ModelId=3DF9FECD0285
      void fillHeader (DMI::Record &hdr,const DMI::Record &selection);

  
    //##ModelId=3DFDFC06033A
      string msname_;  
    //##ModelId=3DF9FECD0199
      casa::MeasurementSet ms_;
    //##ModelId=3DF9FECD019A
      casa::MeasurementSet selms_;
      
      // VDS id
    //##ModelId=3E00AA5101A0
      VDSID vdsid_;
      // observation ID -- this is incremented by 1 for each MS
    //##ModelId=3DF9FECD01A9
      int obsid_; 
      
      // name of data column used
    //##ModelId=3DF9FECD01B0
      string dataColName_;
      
      // MS tiling specification
      //  * if tilesegs_>1, then each tile will be composed of the specified
      //    number of segments; tilesize_ must be 0.
      //  * if tilesegs_=1 and tilesize_=0, there will be one tile per 
      //    segment
      //  * if tilesegs_=1 and tilesize_>0, each segment will be broken up
      //    into tiles of the requested size
      //  * if tilesegs_=0 and tilesize_>0, no segmentation is done, and each
      //    tile will simply have the requsite number of timeslots
      //  * if both are 0, tilesize_=1 will be used.
    //##ModelId=3DF9FECD01C0
      int tilesize_;
      int tilesegs_; 
      
      // channel subset
    //##ModelId=3DF9FECD01C8
      int channels_[2];         // integer channel indices
      // channel increment
      int channel_incr_;
      // various counts
    //##ModelId=3DF9FECD01D0
      int num_channels_;
    //##ModelId=3DF9FECD01D7
      int num_corrs_;
    //##ModelId=3DF9FECD01DF
      int num_antennas_;
    //##ModelId=3DF9FECD01E6
      int num_ifrs_;
      
      //## flag: flip frequency axis. Output frequencies will always be
      //## in increasing order; if MS freqs are decreasing, then the freq axis
      //## must be flipped. This flag is set in fillHeader()
      bool flip_freq_;
      
      bool clear_flags_;
      
      //## true is MS has a valid WEIGHT_SPECTRUM column
      bool has_weights_;
      
      // count of timeslots already returned
    //##ModelId=3DFDFC060354
      int current_timeslot_;
      
      // current MS chunk number. A chunk contains N timeslots (i.e. all
      // the per-ifr tiles for a particular time tile)
      int chunk_num_;
      
      // this gives the size of each successive MS tile
      std::vector<int>  tile_sizes_;
      // this gives the current tile number
      int current_tile_;
      
      // range of times in current selection
      std::vector<double> time_range_;
      
      
      // iterator
    //##ModelId=3DF9FECD01EE
      casa::TableIterator tableiter_;
      
      // tile format
    //##ModelId=3DF9FECD01F6
      VTile::Format::Ref tileformat_;
      
      //##ModelId=3DF9FECD020D
      TileCache::iterator tileiter_;

      //##ModelId=3DF9FECD01FF
      TileCache tiles_;

};

};    
#endif
