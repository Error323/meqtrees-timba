#include "EchoWP.h"
#include "OCTOPUSSY/Dispatcher.h"
#include "OCTOPUSSY/Gateways.h"
#include "OCTOPUSSY/GWClientWP.h"
#include "OCTOPUSSY/LoggerWP.h"
#include <sys/types.h>
#include <unistd.h>    

static int dum = aidRegistry_Testing();
    
int main (int argc,const char *argv[])
{
  Debug::initLevels(argc,argv);
  OctopussyConfig::initGlobal(argc,argv);
  
  try 
  {
    Dispatcher dsp;
    dsp.attach(new LoggerWP(10,Message::LOCAL),DMI::ANON);
    dsp.attach(new EchoWP(-1),DMI::ANON);
    initGateways(dsp);
    dsp.start();
    dsp.pollLoop();
    dsp.stop();
  }
  catch( Debug::Error err ) 
  {
    cerr<<"\nCaught exception:\n"<<err.what()<<endl;
    return 1;
  }
  cerr<<"Exiting normally\n";
  return 0;
}

