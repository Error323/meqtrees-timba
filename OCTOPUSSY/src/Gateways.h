//
//% $Id$ 
//
//
// Copyright (C) 2002-2007
// The MeqTree Foundation & 
// ASTRON (Netherlands Foundation for Research in Astronomy)
// P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, see <http://www.gnu.org/licenses/>,
// or write to the Free Software Foundation, Inc., 
// 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//

#ifndef OCTOPUSSY_Gateways_h
#define OCTOPUSSY_Gateways_h 1
    
#include <DMI/HIID.h>
#include <DMI/Record.h>
#include <OCTOPUSSY/AID-OCTOPUSSY.h>

namespace Octopussy
{

// this includes declarations common to all gateways
class Dispatcher;
    
// Use checksum in gateway transmissions? This increases CPU usage
// during local transfers by a factor of 2
#define GATEWAY_CHECKSUM 0
    
// Re-advertise servers. If set, all open GWServers will publish
// a GW.Server.Bound message at regular intervals. This should re-enable
// any connections that have dropped out. Quite a paranoid feature
#define ADVERTISE_SERVERS 0

#pragma aid ConnectionMgrWP GWServerWP GWClientWP GatewayWP Timestamp
#pragma aid GW Client Server Bind Error Fatal Bound Remote Up Down Network Type
#pragma aid Duplicate Host Port Peers Connected Connection Add Network Local Open
    
// gateway-related messages
const DMI::HIID 
  // Messages published by server
  // common prefix
  MsgGWServer(AidGW|AidServer),      
  // This is used to advertise when a server socket has been bound...
  MsgGWServerOpen(AidGW|AidServer|AidOpen),                     
  // ...for local unix sockets
  // Payload: [AidHost] = hostname (string), [AidPort] = port.
  MsgGWServerOpenLocal(MsgGWServerOpen|AidLocal),           
  // ...for network tcp sockets. Payload is the same, where
  // "host" is the base path, and port is a socket number (i.e. the
  // actual socket is available as host:port)
  MsgGWServerOpenNetwork(MsgGWServerOpen|AidNetwork),
  // common prefix for error messages
  MsgGWServerError(MsgGWServer|AidError),           
  // bind() failed. Payload as above
  MsgGWServerBindError(MsgGWServerError|AidBind),
  // other (fatal) error. Payload as above, plus [AidEerror] = error string
  MsgGWServerFatalError(MsgGWServerError|AidFatal),

  // Messages generated by GatewayWPs
  // Common prefix
  MsgGWRemote(AidGW|AidRemote),
  // Error: duplicate connection to remote peer. Payload: [AidHost], [AidPort],
  // if this was a client connection
  MsgGWRemoteDuplicate(MsgGWRemote|AidDuplicate),
  // Connected to remote peer (GW.Remote.Up.process.host)
  MsgGWRemoteUp(MsgGWRemote|AidUp),
  // Disconnected from remote peer (GW.Remote.Down.process.host)
  MsgGWRemoteDown(MsgGWRemote|AidDown),

  // Local data fieldnames
  // list of connections
  GWPeerList(AidGW|AidPeers),
  // local server port (-1 when no server yet)
  GWNetworkServer(AidGW|AidNetwork|AidPort),
  GWLocalServer(AidGW|AidLocal|AidPort),

// dummy const  
  GWNull();
  
extern DMI::Record gatewayPeerList;

// Opens standard set of client/server gateways
// If tcp_port is 0, opens a GWServer on standard TCP port (as defined by config or args),
//    else opens server on a specific port.
// If !sock, opens GWServer on standard local socket (or as defined by config or args),
//    else opens server on a specific socket.
void initGateways (Dispatcher &dsp,int tcp_port=0,const std::string &sock="");
  
};
#endif
