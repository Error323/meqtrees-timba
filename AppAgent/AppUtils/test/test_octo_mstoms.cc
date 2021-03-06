//  test_mstoms.cc: tests VisRepeater with two MS agents
//
//  Copyright (C) 2002-2007
//  ASTRON (Netherlands Foundation for Research in Astronomy)
//  and The MeqTree Foundation
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

#include <AppAgent/AppControlAgent.h>
#include <AppAgent/BOIOSink.h>
#include <AppAgent/InputAgent.h>
#include <AppAgent/OutputAgent.h>
#include <AppUtils/MSInputSink.h>
#include <AppUtils/MSOutputSink.h>
#include <AppAgent/OctoEventMultiplexer.h>
#include <OCTOPUSSY/Octopussy.h>
#include "../src/VisRepeater.h"

using namespace casa;

int main (int argc,const char *argv[])
{
  using namespace AppAgent;
  using namespace MSVisAgent;
  using namespace AppControlAgentVocabulary;
  using namespace VisRepeaterVocabulary;
  using namespace OctoAgent;
  
  try 
  {
    // this is needed to keep the ms from going crazy
    MeasurementSet ms1("test.ms",Table::Old);
    MeasurementSet ms2("test.ms",Table::Update);
    // comment the above two lines out, and MeasurementSet constructor
    // in MSVisOutputAgent will wind up the stack
  
    Debug::setLevel("VisRepeater",4);
    Debug::setLevel("MSVisAgent",4);
    Debug::setLevel("VisAgent",4);
    Debug::setLevel("OctoEventMux",4);
    Debug::setLevel("OctoEventSink",4);
    Debug::setLevel("BOIOSink",4);
    Debug::setLevel("AppControl",4);
    Debug::setLevel("Dsp",1);
    Debug::initLevels(argc,argv);
    
    cout<<"=================== starting OCTOPUSSY thread ==================\n";
    Octopussy::initThread(true);

    cout<<"=================== creating input repeater ====================\n";
      // initialize parameter record
    DMI::Record::Ref params1ref;
    DMI::Record & params1 = params1ref <<= new DMI::Record;
    {
      params1[FThrowError] = true;
      DMI::Record &args = params1[AidInput] <<= new DMI::Record;
        args[FMSName] = "test.ms";
        args[FDataColumnName] = "DATA";
        args[FTileSize] = 10;
        // setup selection
        DMI::Record &select = args[FSelection] <<= new DMI::Record;
          select[FDDID] = 0;
          select[FFieldIndex] = 0;
          select[FChannelStartIndex] = 10;
          select[FChannelEndIndex]   = 20;
          select[FSelectionString] = "ANTENNA1=1 && ANTENNA2=2";

      DMI::Record &outargs = params1[AidOutput] <<= new DMI::Record;
        outargs[FEventMapOut] <<= new DMI::Record;
          outargs[FEventMapOut][FDefaultPrefix] = HIID("A");

      DMI::Record &ctrlargs = params1[AidControl] <<= new DMI::Record;
        ctrlargs[FAutoExit] = true;
        ctrlargs[FEventMapIn] <<= new DMI::Record;
          ctrlargs[FEventMapIn][InitNotifyEvent] = HIID("Output.VisRepeater.Init");
        ctrlargs[FEventMapOut] <<= new DMI::Record;
          ctrlargs[FEventMapOut][StopNotifyEvent] = HIID("Input.VisRepeater.Stop");
    }
        
    OctoAgent::EventMultiplexer::Ref mux1(
        new OctoAgent::EventMultiplexer(AidVisRepeater),DMI::ANONWR);
    VisAgent::InputAgent::Ref inagent1(
        new VisAgent::InputAgent(new MSVisAgent::MSInputSink,AidInput),DMI::ANONWR);
    VisAgent::OutputAgent::Ref outagent1(
        new VisAgent::OutputAgent(mux1().newSink(),AidOutput),DMI::ANONWR);
    AppControlAgent::Ref controlagent1(
        new AppControlAgent(mux1().newSink(),AidControl),DMI::ANONWR);
    inagent1().attach(mux1().eventFlag());
//    controlagent1().attach(mux1().eventFlag());
    Octopussy::dispatcher().attach(mux1,DMI::WRITE);
    
    VisRepeater::Ref repeater1(DMI::ANONWR);
    repeater1()<<inagent1<<outagent1<<controlagent1;
    
    cout<<"=================== creating output repeater ===================\n";
      // initialize parameter record
    DMI::Record::Ref params2ref;
    DMI::Record & params2 = params2ref <<= new DMI::Record;
    {
      params2[FThrowError] = true;

      DMI::Record &args = params2[AidInput] <<= new DMI::Record;
        args[FEventMapIn] <<= new DMI::Record;
          args[FEventMapIn][FDefaultPrefix] = HIID("A");

      DMI::Record &outargs = params2[AidOutput] <<= new DMI::Record;
          outargs[AppEvent::FBOIOFile] = "test.boio";
          outargs[AppEvent::FBOIOMode] = "write";
//        outargs[FWriteFlags]  = true;
//        outargs[FFlagMask]    = 0xFF;
//        outargs[FDataColumn]      = "MODEL_DATA";

      DMI::Record &ctrlargs = params2[AidControl] <<= new DMI::Record;
        ctrlargs[FAutoExit] = true;
        ctrlargs[FEventMapIn] <<= new DMI::Record;
          ctrlargs[FEventMapIn][HaltEvent] = HIID("Input.VisRepeater.Stop");
        ctrlargs[FEventMapOut] <<= new DMI::Record;
          ctrlargs[FEventMapOut][InitNotifyEvent] = HIID("Output.VisRepeater.Init");
    }
        
    OctoAgent::EventMultiplexer::Ref mux2(
        new OctoAgent::EventMultiplexer(AidVisRepeater));
    VisAgent::InputAgent::Ref inagent2(
        new VisAgent::InputAgent(mux2().newSink(),AidInput));
//    MSVisAgent::MSOutputAgent outagent2(AidOutput);
    VisAgent::OutputAgent::Ref outagent2(
        new VisAgent::OutputAgent(new BOIOSink,AidOutput));
    AppControlAgent::Ref controlagent2(
        new AppControlAgent(mux2().newSink(),AidControl));
    outagent2().attach(mux2().eventFlag());
//    controlagent2().attach(mux2().eventFlag());
    
    Octopussy::dispatcher().attach(mux2,DMI::WRITE);
    
    VisRepeater::Ref repeater2(DMI::ANONWR);
    repeater2()<<inagent2<<outagent2<<controlagent2;
    
    cout<<"=================== launching output thread ================\n";
    controlagent1().preinit(params1ref);
    controlagent2().preinit(params2ref);
    
    Thread::ThrID id1,id2;
    
    id2 = repeater2().runThread(false);
    // wait for it to start
    cout<<"=================== waiting for output thread to start =====\n";
    repeater2().control().waitUntilLeavesState(AppState::INIT);
    
    cout<<"=================== launching input thread =================\n";
    // now run the input repeater
    id1 = repeater1().runThread(false),
    
    cout<<"=================== rejoining threads =========================\n";
    id1.join();
    id2.join();
    
    cout<<"=================== stopping OCTOPUSSY ========================\n";
    Octopussy::stopThread();
    
    cout<<"=================== end of run ================================\n";
  }
  catch ( std::exception &exc ) 
  {
    cout<<"Exiting with exception: "<<exc.what()<<endl;  
    return 1;
  }
  
  return 0;  
}
