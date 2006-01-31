#ifndef OCTOPUSSY_OCTOPUSSY_H 
#define OCTOPUSSY_OCTOPUSSY_H 1

#define MAKE_LOFAR_SYMBOLS_GLOBAL 1

#include <TimBase/Thread.h>
    
namespace Octopussy
{
  class Dispatcher;    

//  using namespace LOFAR;
  
  Dispatcher &  init     (bool start_gateways=true,bool start_logger=false);
  void          start    ();
  void          pollLoop ();
  void          stop     ();
  void          destroy  ();
  
  
  Thread::ThrID  initThread  (bool wait_for_start=false);
  void           stopThread  ();
  
  Thread::ThrID  threadId    ();
  
  Dispatcher &   dispatcher  ();
  
  bool           isRunning ();

};
#endif
