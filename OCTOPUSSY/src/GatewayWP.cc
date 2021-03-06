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

#include "Gateways.h"
#include "GatewayWP.h"
#include <DMI/Exception.h>

namespace Octopussy
{
    
static const char PacketSignature[] = "oMs";

// use large timeouts because we're not multithreaded anymore
const Timeval to_init(30.0),
              to_write(30.0),
              to_heartbeat(5.0);
    

GatewayWP::GatewayWP (Socket* sk)
  : WorkProcess(AidGatewayWP),sock(sk)
{
  memcpy(wr_header.signature,PacketSignature,sizeof(wr_header.signature));
  setState(0);
  setPeerState(INITIALIZING);
  rprocess = rhost = 0;
}


GatewayWP::~GatewayWP()
{
  if( sock )
    delete sock;
}



void GatewayWP::init ()
{
   // subscribe to local subscribe notifications and Bye messages
  // (they will be forwarded to peer as-is)
  subscribe(MsgSubscribe|AidWildcard,Message::LOCAL);
  subscribe(MsgBye|AidWildcard,Message::LOCAL);
}

bool GatewayWP::start ()
{
  WorkProcess::start();
  // handle & ignore SIGURG -- out-of-band data on socket. 
  // addInput() will catch an exception on the fd anyway
  addSignal(SIGURG,EV_IGNORE);
  // ignore SIGPIPE, 
  addSignal(SIGPIPE,EV_IGNORE);
  
  // collect local subscriptions data and send it to peer
  // iterate over all WPs to find total size of all subscriptions
  size_t nwp = 0, datasize = 0;
  Dispatcher::WPIter iter = dsp()->initWPIter();
  WPID id;
  const WPInterface *pwp;
  
  while( dsp()->getWPIter(iter,id,pwp) )
  {
    if( id.wpclass() != AidGatewayWP ) // ignore gateway WPs
    {
      nwp++;
      datasize += pwp->getSubscriptions().packSize() + pwp->address().packSize();
    }
  }
  size_t hdrsize = (1+2*nwp)*sizeof(size_t);
  // form block containing addresses and subscriptions
  SmartBlock *block = new SmartBlock(hdrsize+datasize);
  BlockRef blockref(block,DMI::ANON);
  size_t *hdr = static_cast<size_t*>(block->data());
  char *data  = static_cast<char*>(block->data()) + hdrsize;
  *(hdr++) = nwp;
  iter = dsp()->initWPIter();
  while( dsp()->getWPIter(iter,id,pwp) )
    if( id.wpclass() != AidGatewayWP ) // ignore gateway WPs
    {
      data += *(hdr++) = pwp->address().pack(data,datasize);
      data += *(hdr++) = pwp->getSubscriptions().pack(data,datasize);
    }
  Assert( !datasize );
  dprintf(1)("generating init message for %d subscriptions, block size %d\n",
      nwp,hdrsize+datasize);
  // put this block into a message and send it to peer
  Message::Ref msg(new Message(AidSubscriptions,blockref),DMI::ANON|DMI::WRITE);
  msg().setFrom(address());
  msg()[AidPeers] = gatewayPeerList;
  prepareMessage(msg);
  
  // init timeouts
  addTimeout(to_init,AidInit,EV_ONESHOT);
  addTimeout(to_heartbeat,AidHeartbeat,EV_CONT);
  
  // start watching the socket fd
  addInput(sock->getSid(),EV_FDREAD|EV_FDWRITE|EV_FDEXCEPTION);
  write_seq = 0;
  read_junk = 0;
  readyForHeader();
  
  // init the status counters
  statmon.counter = 0;
  statmon.read = statmon.written = 0;
  statmon.ts = Timestamp::now();
  return false;
}

void GatewayWP::stop ()
{
  if( sock )
    delete sock;
  sock = 0;
  read_bset.clear();
  write_queue.clear();
}

bool GatewayWP::willForward (const Message &msg) const
{
  if( peerState() != CONNECTED )
    return false;
  // We're doing a simple everybody-connects-to-everybody topology.
  // This determines the logic below:
  dprintf(3)("willForward(%s)",msg.sdebug(1).c_str());
  // Normally, messages will only be forwarded once (i.e, only
  // when hopcount=0).
  // GwServerBound are the exception: they're forwarded up to three times.
  // This insures that when, e.g, the following link ("=") is established:
  //    A1\       /B1
  //       A0 = B0
  //    A2/       \B2
  // ... A1/A2/B1/B2 can quickly learn about each other's server ports.
  if( msg.id().matches(MsgGWServerOpen|AidWildcard) )
  {
    if( msg.forwarder() == address() )
    {
      dprintf(3)("no, we were the forwarder\n");
      return false;
    }
    if( msg.hops() > 3 )
    {
      dprintf(3)("no, hopcount = %d\n",msg.hops() );
      return false;
    }
  }
  else if( msg.hops() > 0 )
  {
    dprintf(3)("no, non-local origin, hopcount = %d\n",msg.hops() );
    return false;
  }
  // Check that to-scope of message matches remote 
  if( !rprocess.matches( msg.to().process() ) ||
      !rhost.matches( msg.to().host() ) )
  {
    dprintf(3)("no, `to' does not match remote %s.%s\n",
               rprocess.toString().c_str(),rhost.toString().c_str());
    return false;
  }
  // if message is published, search thru remote subscriptions
  if( msg.to().wpclass() == AidPublish )
  {
    for( CRSI iter = remote_subs.begin(); iter != remote_subs.end(); iter++ )
      if( iter->second.matches(msg) )
      {
        dprintf(3)("yes, subscribed to by remote %s\n",iter->first.toString().c_str());
        return true;
      }
    dprintf(3)("no, no remote subscribers\n");
  }
  else // else check for match with a remote address
  {
    for( CRSI iter = remote_subs.begin(); iter != remote_subs.end(); iter++ )
      if( iter->first.matches(msg.to()) )
      {
        dprintf(3)("yes, `to' address matches remote %s\n",
            iter->first.toString().c_str());
        return true;
      }
    dprintf(3)("no, no matching remote WPs\n");
  }
  return false;
}

int GatewayWP::receive (Message::Ref& mref)
{
  // ignore any messages out of the remote's scope
  if( !rprocess.matches(mref->to().process()) ||
      !rhost.matches(mref->to().host()) )
  {
    dprintf(3)("ignoring [%s]: does not match remote process/host\n",mref->sdebug(1).c_str());
    return Message::ACCEPT;
  }
  // ignore any messages from GatewayWPs, with the exception of Remote.Up
  if( mref->from().wpclass() == AidGatewayWP &&
      !mref->id().matches(MsgGWRemoteUp) )
  {
    dprintf(3)("ignoring [%s]: from a gateway\n",mref->sdebug(1).c_str());
    return Message::ACCEPT;
  }
  // hold off while still initializing the connection
  if( peerState() == INITIALIZING )
    return Message::HOLD;
  // else ignore if not connected
  else if( peerState() != CONNECTED )
    return Message::ACCEPT;
  
  if( writeState() != IDLE )   // writing something? 
  {
    // hold off we already have a pending message
    if( pending_msg.valid() )  
      return Message::HOLD; 
    pending_msg.xfer(mref);
  }
  else // no, write state is idle, so start sending
  {
    prepareMessage(mref);
    dprintf(5)("enabling write input on socket\n");
    addInput(sock->getSid(),EV_FDWRITE);  // enable write input
    Timestamp::now(&last_write_to);
  }
  return Message::ACCEPT;
}

int GatewayWP::timeout (const HIID &id)
{
  if( id == AidInit )  // connection timeout
  { 
    if( peerState() == INITIALIZING )
    {
      lprintf(1,"error: timed out waiting for init message from peer\n");
      shutdown();
    }
    return Message::CANCEL;
  }
  else if( id == AidHeartbeat )  // heartbeat 
  {
    // check that write is not blocked
    if( writeState() != IDLE && Timestamp::now() - last_write_to >= to_write )
    {
      lprintf(1,"error: timed out waiting for write()\n");
      shutdown();
    }
    // report on write queue status
    if( (statmon.counter++)%4 == 0 )
    {
      double now = Timestamp::now(), d = now - statmon.ts;
      lprintf(3,"%.2f seconds elapsed since last stats report\n"
                 "read %llu bytes (%.3f MB/s)\n"
                 "wrote %llu bytes (%.3f MB/s)\n",
                 d,statmon.read,statmon.read/(1024*1024*d),
                 statmon.written,statmon.written/(1024*1024*d));
      statmon.ts = now;
      statmon.read = statmon.written = 0;
    }
  }
  return Message::ACCEPT;
}

int GatewayWP::input (int fd, int flags)
{
  // in case we're shutting down, ignore the whole shebang
  if( !sock )
    return Message::CANCEL;
  // first handle out-of-band messages
  if( flags&EV_FDEXCEPTION ) 
  {
    flags &= ~EV_FDEXCEPTION;
    // to be implemented
    
  }
  // then handle writing
  while( flags&EV_FDWRITE )
  {
    // write is idle? disable the write input
    if( writeState() == IDLE )
    {
      dprintf(5)("write state is IDLE, removing input\n");
      removeInput(fd,EV_FDWRITE);
      flags &= ~EV_FDWRITE;    
      continue;   // call us again
    }
    // write data from current block
    while( nwritten < write_buf_size )
    {
      int n = sock->write(write_buf + nwritten,write_buf_size - nwritten);
      dprintf(5)("write(buf+%d,%d)=%d\n",nwritten,write_buf_size-nwritten,n);
      if( n < 0 )
      {
        // on write error, just commit harakiri. GWClient/ServerWP will
        // take care of reopening a connection, eventually
        lprintf(1,"error: socket write(): %s. Aborting.\n",sock->errstr().c_str());
        shutdown();
        return Message::CANCEL; 
      }
      else if( n == 0 ) // nothing written at all, so clear the write bit
      {
        flags &= ~EV_FDWRITE;
        break;
      }
      else 
      {
        statmon.written += n;
        last_write_to = Timestamp::now(&last_write);
        // update checksum and advance the nread pointer
        #if GATEWAY_CHECKSUM
        for( ; n>0; n--,nwritten++ )
          write_checksum += write_buf[nwritten];
        #else
        nwritten += n;
        #endif
      }
    }
    // in case we broke out of the loop
    if( nwritten < write_buf_size )
      break;
    // chunk written, advance to next one?
    if( writeState() == HEADER ) 
    {
      if( !write_queue.size() ) // were sending header but queue is empty
      {
        // if GW is being closed, detach now
        if( peerState() == CLOSING )
        {
          lprintf(2,AidLogError,"write finished, shutting down");
          detachMyself();
          return Message::ACCEPT;
        }
        // make sure we haven't been sending a data header
        FailWhen(wr_header.type == MT_DATA,"write queue empty after data header");
        dprintf(5)("wrote lone header, now IDLE\n");
        setWriteState( IDLE );
      }
      else // were sending header and queue is not empty, must be data header then
      {
        FailWhen(wr_header.type != MT_DATA,"write queue unexpectedly not empty");
        prepareData(); 
      }
    }
    else if( writeState() == BLOCK ) 
    {
      prepareTrailer();        // after block, send trailer
    }
    else if( writeState() == TRAILER ) 
    {
      // if GW is being closed, detach now
      if( peerState() == CLOSING )
      {
        lprintf(2,AidLogError,"write finished, shutting down");
        detachMyself();
        return Message::ACCEPT;
      }
      // something else in queue? send next header
      if( write_queue.size() ) 
        prepareHeader();
      else
      {
        dprintf(5)("nothing else in write queue, now IDLE\n");
        setWriteState( IDLE );
      }
    }
    // have we changed state to IDLE? 
    if( writeState() == IDLE )
    {
      if( pending_msg.valid() )        // send pending message, if any
        prepareMessage(pending_msg);
    }
  }
  // now handle reading
  while( flags&EV_FDREAD )
  {
    // read up to full buffer
    while( nread < read_buf_size )
    {
      int n = sock->read(read_buf + nread,read_buf_size - nread);
      dprintf(5)("read(buf+%d,%d)=%d\n",nread,read_buf_size-nread,n);
      if( n < 0 )
      {
        // on read error, just commit harakiri. GWClient/ServerWP will
        // take care of reopening a connection, eventually
        lprintf(1,"error: socket read(): %s. Aborting.\n",sock->errstr().c_str());
        shutdown();
        return Message::CANCEL; 
      }
      else if( n == 0 ) // nothing read at all, so clear the read bit
      {
        flags &= ~EV_FDREAD;
        break;
      }
      else // read something
      {
        statmon.read += n;
        Timestamp::now(&last_read);
        // update checksum and advance the nread pointer
        #if GATEWAY_CHECKSUM
        for( ; n>0; n--,nread++ )
          read_checksum += read_buf[nread];
        #else
        nread += n;
        #endif
      }
    }
    // in case we broke out of the loop
    if( nread < read_buf_size )
      break;
    // since we got here, we have a complete buffer, so dispose of it according to mode
    if( readState() == HEADER ) // got a packet header?
    {
      if( memcmp(header.signature,PacketSignature,sizeof(header.signature)) ||
          header.type > MT_MAXTYPE )
      {
        dprintf(5)("header does not start with signature\n");
        // invalid header -- flush it
        if( !read_junk )
        {
          dprintf(2)("error: junk data before header\n");
          requestResync();  // request resync if this is first instance
        }
        // look for first byte of signature in this header
        void *pos = memchr(&header,PacketSignature[0],sizeof(header));
        if( !pos ) // not found? flush everything
        {
          dprintf(5)("no signature found, flushing everything\n");
          nread = 0;
          read_junk += sizeof(header);
        }
        else
        { // else flush everything up to matching byte
          int njunk = static_cast<char*>(pos) - reinterpret_cast<char*>(&header);
          nread = sizeof(header) - njunk;
          read_junk += njunk;
          memmove(&header,pos,nread);
          dprintf(5)("signature found, flushing %d junk bytes\n",njunk);
        }
        // retry
        return input(fd,flags);
      }
      // else header is valid
      if( read_junk )
      { // got any junk before it? report it
        lprintf(2,"warning: %d junk bytes before header were discarded\n",read_junk);
        read_junk = 0;
      }
      Timestamp::now(&last_read);
      switch( header.type )
      {
        case MT_PING: 
            dprintf(5)("PING packet, ignoring\n");
            break; // ignore ping message

        case MT_DATA:       // data block coming up
            readyForData(header); // sets buffers and read states accordingly
            break;

        case MT_ACK:         // acknowledgement of data message
            dprintf(5)("ACK packet, ignoring\n");
            // to do later
        case MT_RETRY:       // retry data message
            dprintf(5)("RETRY packet, ignoring\n");
            // to do later
            break;
        default:
          lprintf(2,"warning: unknown packet type %d, ignoring\n",header.type);
      }
    } // end if( readState() == HEADER )
    else if( readState() == BLOCK )
    {
      incoming_checksum = read_checksum;
      readyForTrailer(); // sets buffers and read states accordingly
    }
    else if( readState() == TRAILER )
    {
      // to do: check sequence number
      // verify checksum
      #if GATEWAY_CHECKSUM
      if( incoming_checksum == trailer.checksum )
      #endif
      {
        dprintf(4)("received block #%d of size %d, checksum OK\n",
            trailer.seq,read_bset.back()->size());
//        acknowledge(true);    // reply with acknowledgment
        if( trailer.msgsize ) // accumulated a complete message?
        {
          if( read_bset.size() != trailer.msgsize )
          { // major oops
            lprintf(1,"error: block count mismatch, expected %d got %d\n",
                trailer.msgsize,read_bset.size());
            // NB: DO SOMETHING VIOLENT HERE!!
            read_bset.clear();
          }
          else
          {
            processIncoming();     // process the incoming message
            // if peer is being closed, return immediately
            if( peerState() == CLOSING )
              return Message::CANCEL;
          }
        }
        // expect header next
        readyForHeader(); // sets buffers and read states accordingly
      }
      #if GATEWAY_CHECKSUM
      else
      {
        dprintf(2)("block #%d: bad checksum\n",trailer.seq);
        requestRetry();  // ask for retry, clear buffer
      }
      #endif
    }
    else
      Throw("unexpected read state");
  }
  return Message::ACCEPT;
}

// Additional Declarations
int GatewayWP::requestResync ()
{
  // Should eventually send an OOB message for a resync.
  // For now, just start looking for a header
  return readyForHeader();
}

int GatewayWP::requestRetry ()
{
  // Should eventually send an OOB message for a retransmit.
  // For now, just fllush incoming blocks and start looking for a header.
  read_bset.clear();
  return readyForHeader();
}

int GatewayWP::readyForHeader ()
{
  read_buf_size = sizeof(header);
  read_buf = reinterpret_cast<char*>(&header);
  nread = 0;
  setReadState( HEADER );
  dprintf(5)("read state is now HEADER\n");
  return 0;
}

int GatewayWP::readyForTrailer ()
{
  read_buf_size = sizeof(trailer);
  read_buf = reinterpret_cast<char*>(&trailer);
  nread = 0;
  setReadState( TRAILER );
  dprintf(5)("read state is now TRAILER\n");
  return 0;
}

int GatewayWP::readyForData ( const PacketHeader &hdr )
{
  read_buf_size = hdr.content;
  if( read_buf_size > MaxBlockSize )
  {
    lprintf(1,"error: block size too big (%d), aborting\n",read_buf_size);
    return requestResync();
  }
  nread = 0;
  SmartBlock * bl = new SmartBlock(read_buf_size);
  read_bset.pushNew().attach(bl,DMI::ANON|DMI::WRITE);
  read_buf = static_cast<char*>(bl->data());
  setReadState( BLOCK );
  dprintf(5)("read state is now BLOCK\n");
  read_checksum = 0;
  return 0;
}

void GatewayWP::prepareMessage (Message::Ref &mref)
{
  FailWhen(write_queue.size(),"write queue is not empty??");
  dprintf(5)("write-queueing [%s]\n",mref->sdebug(1).c_str());
  // convert the message to blocks, placing them into the write queue
  write_msgsize = mref->toBlock(write_queue);
  // release ref, so as to minimize the blocks' ref counts
  mref.detach();
  // start sending
  prepareHeader();
}


void GatewayWP::prepareHeader ()
{
  if( !write_queue.size() )
  {
    wr_header.type = MT_PING;
    wr_header.content = 0;
  }
  else
  {
    wr_header.type = MT_DATA;
    wr_header.content = write_queue.front()->size();
  }
  write_buf = reinterpret_cast<char*>(&wr_header);
  write_buf_size = sizeof(wr_header);
  write_checksum = 0;
  nwritten = 0;
  setWriteState( HEADER );
  dprintf(5)("write state is now HEADER\n");
}

void GatewayWP::prepareData ()
{
  const BlockRef & ref = write_queue.front();
  write_buf = static_cast<const char *>(ref->data());
  write_buf_size = ref->size();
  FailWhen(write_buf_size>MaxBlockSize,"block size too large");
  write_checksum = 0;
  nwritten = 0;
  setWriteState( BLOCK );
  dprintf(5)("write state is now BLOCK\n");
}

void GatewayWP::prepareTrailer ()
{
  write_queue.pop();
  wr_trailer.seq = write_seq++;
  wr_trailer.checksum = write_checksum;
  if( write_queue.size() )  // something left in queue?
    wr_trailer.msgsize = 0;
  else
    wr_trailer.msgsize = write_msgsize;
  write_buf = reinterpret_cast<char*>(&wr_trailer);
  write_buf_size = sizeof(wr_trailer);
  write_checksum = 0;
  nwritten = 0;
  setWriteState( TRAILER );
  dprintf(5)("write state is now TRAILER\n");
}

void GatewayWP::processIncoming()
{
  Message::Ref ref = Message::Ref(new Message,DMI::ANON|DMI::WRITE);
  ref().fromBlock(read_bset);
  Message &msg = ref;
  msg.setForwarder(address());
  msg.addHop(); // increment message hop-count
  dprintf(5)("received from remote [%s]\n",msg.sdebug(1).c_str());
  if( read_bset.size() )
  {
    lprintf(2,"warning: %d unclaimed incoming blocks were discarded\n",read_bset.size());
    read_bset.clear();
  }
// if connected, it is a true remote message, so send it off
  if( peerState() == CONNECTED )
  {
    // Bye message from remote: drop WP from routing table
    if( msg.id().prefixedBy(MsgBye) )
    {
      RSI iter = remote_subs.find(msg.from());
      if( iter == remote_subs.end() )
        lprintf(1,"warning: got Bye [%s] from unknown remote WP\n",msg.sdebug(1).c_str());
      else
      {
        dprintf(2)("got Bye [%s], deleting routing entry\n",msg.sdebug(1).c_str());
        remote_subs.erase(iter);
      }
    } 
    // Subscribe message from remote: update table
    else if( msg.id().prefixedBy(MsgSubscribe) )
    {
      // unpack subscriptions block, catching any exceptions
      Subscriptions subs;
      bool success = false;
      if( msg.data() )
      {
        try {
          subs.unpack(msg.data(),msg.datasize());
          success = true;
        } catch( std::exception &exc ) {
          lprintf(2,"warning: failed to unpack Subscribe message: %s\n",
              exceptionToString(exc).c_str());
        }
      }
      if( success )
      {
        dprintf(2)("got Subscriptions [%s]: %d subscriptions\n",
                    msg.sdebug(1).c_str(),subs.size());
        RSI iter = remote_subs.find(msg.from());
        if( iter == remote_subs.end() )
        {
          dprintf(2)("inserting new entry into routing table\n");
          remote_subs[msg.from()] = subs;
        }
        else
        {
          dprintf(2)("updating entry in routing table\n");
          iter->second = subs;
        }
      }
      else
      {
        lprintf(2,"warning: ignoring bad Subscriptions message [%s]\n",msg.sdebug(1).c_str());
      }
    }
    // send the message on, regardless of the above
    // (call Dispatcher directly in order to bypass WPInterface::send,
    // thus retaining the original from address and hopcount)
    dsp()->send(ref,msg.to());
  }
// if initializing, then it must be a Subscriptions message from peer
// (see start(), above)
  else if( peerState() == INITIALIZING ) 
  {
    dprintf(1)("received init message from peer: %s\n",msg.sdebug(1).c_str());
    if( msg.id() != HIID(AidSubscriptions) )
    {
      lprintf(1,"error: unexpected init message\n");
      shutdown();
      return;
    }
    // catch all exceptions during processing of init message
    try 
    {
      // remote peer process/host id
      rprocess = msg.from().process();
      rhost = msg.from().host();
      HIID peerid(rprocess|rhost);
      // paranoid case: if we already have a connection to the peer, shutdown
      // (this really ought not to happen)
      if( gatewayPeerList[peerid].exists() )
      {
        lprintf(1,AidLogError,"already connected to %s (%s:%d %s), closing gateway",
              peerid.toString().c_str(),
             gatewayPeerList[peerid][AidHost].as<string>().c_str(),
             gatewayPeerList[peerid][AidPort].as<int>(),
             gatewayPeerList[peerid][AidTimestamp].as<Timestamp>().toString("%T").c_str());
        Message *msg1 = new Message(MsgGWRemoteDuplicate|peerid);
        Message::Ref mref1; mref1 <<= msg1;
        (*msg1)[AidHost] = sock->host();
        (*msg1)[AidPort] = atoi(sock->port().c_str());
        publish(mref1,0,Message::LOCAL);
        setPeerState(CLOSING);
        // if not writing anything, detach ourselves immediately
        if( writeState() == IDLE )
        {
          lprintf(2,AidLogError,"shutting down immediately");
          detachMyself();
        }
        else
        {
          // else stop reading, and allow the writing to finish
          lprintf(2,AidLogError,"will shut down once write is complete");
          removeInput(sock->getSid(),EV_FDREAD);
        }
        return;
      }
      // add this connection to the local peerlist
      DMI::Record & rec = gatewayPeerList[peerid] <<= new DMI::Record;
      rec[AidTimestamp] = Timestamp::now();
      rec[AidHost] = sock->host();
      rec[AidPort] = atoi(sock->port().c_str());
      // process remote subscriptions data
      processInitMessage(msg.data(),msg.datasize());
      // set states
      setPeerState(CONNECTED);
      lprintf(2,("connected to remote peer " + msg.from().toString() +
                "; initialized routing for %d remote WPs\n").c_str(),
                 remote_subs.size());
      // re-publish the init message as Remote.Up 
      msg.setId(MsgGWRemoteUp|peerid);
      msg[AidHost] = sock->host();
      msg[AidPort] = atoi(sock->port().c_str());
      publish(ref,Message::GLOBAL);
    }
    catch( std::exception &exc ) 
    {
      lprintf(1,"error: processing init message: %s\n",
          exceptionToString(exc).c_str());
      shutdown();
      return;
    }
    // publish (locally only) fake Hello messages on behalf of remote WPs
    for( CRSI iter = remote_subs.begin(); iter != remote_subs.end(); iter++ )
    {
      Message::Ref mref;
      mref.attach(new Message(MsgHello|iter->first),DMI::ANON|DMI::WRITE );
      mref().setFrom(iter->first);
      dsp()->send(mref,MsgAddress(AidPublish,AidPublish,
                                address().process(),address().host()));
    }
    // tell dispatcher that we can forward messages now
    // (note that doing it here ensures that the GWRemoteUp message is
    // only published to peers on "this" side of the connection)
    dsp()->declareForwarder(this);
  }
  else
  {
    lprintf(1,"error: received remote message while in unexpected peer-state\n");
    shutdown();
  }
}

// processes subscriptions contained in peer's init-message
// (the message block is formed in start(), above)
void GatewayWP::processInitMessage( const void *block,size_t blocksize )
{
  FailWhen( !block,"no block" );
  size_t hdrsize;
  const size_t *hdr = static_cast<const size_t *>(block);
  int nwp;
  // big enough for header? 
  FailWhen( blocksize < sizeof(size_t) || 
            blocksize < ( hdrsize = (1 + 2*( nwp = *(hdr++) ))*sizeof(size_t) ),
            "corrupt block");
  // scan addresses and subscription blocks
  const char *data = static_cast<const char *>(block) + hdrsize,
             *enddata = static_cast<const char *>(block) + blocksize;
  for( int i=0; i<nwp; i++ )
  {
    size_t asz = *(hdr++), ssz = *(hdr++);
    // check block size again
    FailWhen( data+asz+ssz > enddata,"corrupt block" ); 
    // unpack address 
    MsgAddress addr; 
    addr.unpack(data,asz); data += asz;
    // unpack subscriptions
    Subscriptions &subs(remote_subs[addr]);
    subs.unpack(data,ssz);
    data += ssz;
  }
  FailWhen(data != enddata,"corrupt block");
}

void GatewayWP::shutdown () 
{
  if( peerState() == CONNECTED )     // publish a Remote.Down message
  {
    HIID peerid = rprocess|rhost;
    lprintf(1,"shutting down connection to %s",(rprocess|rhost).toString().c_str());
    Message::Ref mref(new Message(MsgGWRemoteDown|peerid),DMI::ANON);
    gatewayPeerList[peerid].remove();
    publish(mref,0,Message::LOCAL);
  }
  else
    lprintf(1,"shutting down");
  setPeerState(CLOSING); 
  detachMyself();
}

};
