#ifndef MEQSERVER_SRC_PYNODE_H
#define MEQSERVER_SRC_PYNODE_H
    
#include <MEQ/Node.h>
#include <MeqServer/MeqPython.h>
#include <MeqServer/AID-MeqServer.h>
#include <MeqServer/TID-MeqServer.h>
#include <OCTOPython/OctoPython.h>

#pragma types #Meq::PyNode
#pragma aid Class Module Name

// handy macro to fail on a condition, checking for a python error,
// printing & clearing it if necessary, and raising an exception
#define PyFailWhen(condition,message) \
  if( condition ) \
  { \
    if( PyErr_Occurred() )\
    { \
      LOFAR::Exception exc = getPyException(); \
      ThrowMore(exc,message); \
    } \
    else \
      Throw(message); \
  }

// if the Python error indicator is raised, prints & clears it,
// and throws an exception
#define PyCheckError(message)  \
  if( PyErr_Occurred() ) \
  { \
    LOFAR::Exception exc = getPyException(); \
    ThrowMore(exc,message); \
  }

namespace Meq {

LOFAR::Exception getPyException ();
  
class PyNodeImpl 
{
  public:

  // NB: how do we access a node from MeqPython, and still allow multiple classes?
      
    PyNodeImpl (Node *node);
      
    //##ModelId=3F9FF6AA0300
    int getResult (Result::Ref &resref, 
                   const std::vector<Result::Ref> &childres,
                   const Request &req,bool newreq);
    
    int discoverSpids (Result::Ref &resref, 
                       const std::vector<Result::Ref> &childres,
                       const Request &req);

    int processCommand (Result::Ref &resref,
                        const HIID &command,
                        DMI::Record::Ref &args,
                        const RequestId &rqid = RequestId(),
                        int verbosity=0);
      
    //##ModelId=3F9FF6AA03D2
    void setStateImpl (DMI::Record::Ref &rec,bool initializing);
    
    //##ModelId=3F9FF6AA016C
    LocalDebugContext;
    
    string sdebug(int detail = 0, const string &prefix = "", const char *name = 0) const;

    OctoPython::PyObjectRef pynode_obj_;
    OctoPython::PyObjectRef pynode_setstate_;
    OctoPython::PyObjectRef pynode_getresult_;
    OctoPython::PyObjectRef pynode_discoverspids_;
    OctoPython::PyObjectRef pynode_processcommand_;
    
  protected:
    // converts request to python (with caching), returns 
    // NEW REFERENCE
    PyObject * convertRequest (const Request &req);
      
    // cached request object
    OctoPython::PyObjectRef py_prev_request_;
    Request::Ref prev_request_;
    
    Node *pnode_;
};


class PyNode : public Node
{
  public:
    PyNode ();
  
    virtual ~PyNode ();
    
    virtual TypeId objectType() const
    { return TpMeqPyNode; }
    
    ImportDebugContext(PyNodeImpl);

  protected:
    virtual int getResult (Result::Ref &resref, 
                           const std::vector<Result::Ref> &childres,
                           const Request &req,bool newreq);
  
    virtual int discoverSpids (Result::Ref &resref, 
                               const std::vector<Result::Ref> &childres,
                               const Request &req);
    
    virtual int processCommand (Result::Ref &resref,
                                const HIID &command,
                                DMI::Record::Ref &args,
                                const RequestId &rqid = RequestId(),
                                int verbosity=0);
    
    virtual void setStateImpl (DMI::Record::Ref &rec,bool initializing);
    
    PyNodeImpl impl_;
};

}

#endif
