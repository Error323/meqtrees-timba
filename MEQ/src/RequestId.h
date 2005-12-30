#ifndef MeqSERVER_SRC_REQUESTID_H_HEADER_INCLUDED
#define MeqSERVER_SRC_REQUESTID_H_HEADER_INCLUDED
    
#include <DMI/HIID.h>
#include <MEQ/AID-Meq.h>
    
namespace Meq 
{ 
  
using namespace DMI;
  
// // -----------------------------------------------------------------------
// // dependency flags and symbolic dependencies
// // -----------------------------------------------------------------------
// 
////##Documentation
////## define a default set of dependency masks for nodes that generate
////## requests. These may be overridden via node state
typedef enum
{
//   RQIDM_VALUE       = 0x0001,
//   RQIDM_RESOLUTION  = 0x0002,
//   RQIDM_DOMAIN      = 0x0004,
//   RQIDM_DATASET     = 0x0008,
//   
  RQIDM_NBITS       = 16
} RequestIdMasks;
  
//##Documentation
//## The request ID is basically a HIID of length up to RQIDM_NBITS. Each 
//## index of an rqid maps onto one bit of the rqid mask, starting with 
//## the _first_ index. 
typedef HIID RequestId;
// 
// //=== Some standard symbolic deps
// const HIID FParmValue  = AidParm|AidValue;
// const HIID FResolution = AidResolution;
// // const HIID FDomain     = AidDomain; // already defined in MeqVocabulary
// const HIID FDataset    = AidDataset;
// 
// // -----------------------------------------------------------------------
// // defaultSymdepMasks()
// // returns set of default symdep masks corresponding to RQIDMs above
// // -----------------------------------------------------------------------
// const std::map<HIID,int> & defaultSymdepMasks ();

// utility functions reside in this namespace
namespace RqId
{

// -----------------------------------------------------------------------
// maskSubId()
// Sets to 0 all indices whose maskbit is 0. 
// This essentially returns the "sub-id" corresponding to mask.
// -----------------------------------------------------------------------
void maskSubId (RequestId &rqid,int mask);

inline RequestId maskSubId (const RequestId &rqid,int mask)
{ RequestId res = rqid; maskSubId(res,mask); return res; }

// -----------------------------------------------------------------------
// incrSubId()
// increments all indices whose maskbit is 1.
// -----------------------------------------------------------------------
void incrSubId (RequestId &rqid,int mask);

inline RequestId incrSubId (const RequestId &rqid,int mask)
{ RequestId res = rqid; incrSubId(res,mask); return res; }

// -----------------------------------------------------------------------
// setSubId()
// sets all indices whose maskbit is 1 to given value
// -----------------------------------------------------------------------
void setSubId (RequestId &rqid,int mask,int value);

inline RequestId setSubId (const RequestId &rqid,int mask,int value)
{ RequestId res = rqid; setSubId(res,mask,value); return res; }

// -----------------------------------------------------------------------
// maskedCompare()
// Compares two IDs using a mask -- i.e., only indices with a 1 maskbit
// are compared. Returns true if the IDs match
// -----------------------------------------------------------------------
bool maskedCompare (const RequestId &a,const RequestId &b,int mask);

// -----------------------------------------------------------------------
// diffMask()
// Compares two IDs and returns a bitmask with each bit set if IDs
// are different
// -----------------------------------------------------------------------
int diffMask (const RequestId &a,const RequestId &b);

}

};
#endif
