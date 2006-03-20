#include "OctoPython.h"
#include <OCTOPUSSY/Message.h>
#include <DMI/Record.h>
#include <DMI/Vec.h>
#include <DMI/NumArray.h>
#include <DMI/List.h>
#include <DMI/DynamicTypeManager.h>
#define Bool NumarrayBool
#include <numarray/libnumarray.h>
#undef Bool

using Debug::ssprintf;
using std::endl;
using namespace DMI;
        
namespace OctoPython {    
    
DMISymbols py_dmisyms;

// -----------------------------------------------------------------------
// convertSeqToHIID
// converts sequence of ints (or any other object supporting iterators)
// to HIID
// -----------------------------------------------------------------------
int convertSeqToHIID (HIID &id,PyObject *list)
{
  PyObjectRef iter = PyObject_GetIter(list); // new ref
  if( !iter )
    throwError(Type,"can't convert non-iterable object to HIID");
  // check that this is a sequence
  id.clear();
  PyObjectRef item;
  while( ( item = PyIter_Next(*iter) ) != 0 && !PyErr_Occurred() ) // new ref
  {
    int aid = int( PyInt_AsLong(*item) );
    if( !PyErr_Occurred() )
      id.add(AtomicID(aid));
  }
  if( PyErr_Occurred() )
    throwErrorOpt(Type,"error converting to hiid"); 
  return 1;
}

// -----------------------------------------------------------------------
// convertHIIDToSeq
// Converts HIID to Python-compatible sequence of ints
// Returns NEW REF
// -----------------------------------------------------------------------
PyObject * convertHIIDToSeq (const HIID &id)
{
  // build up tuple
  PyObjectRef list = PyTuple_New(id.size()); // new ref
  for( uint i=0; i<id.size(); i++ )
    PyTuple_SET_ITEM(*list,i,PyInt_FromLong(id[i].id())); // steals ref to item, new ref returned, so ok
  return ~list; // returns new ref
}

// -----------------------------------------------------------------------
// pyFromHIID
// -----------------------------------------------------------------------
PyObject * pyFromHIID (const HIID &id)
{
  // put hiid-sequence into tuple of args
  PyObjectRef args = Py_BuildValue("(N)",convertHIIDToSeq(id));  // new ref
  // call hiid constructor
  return PyObject_CallObject(*py_dmisyms.hiid,*args);
}

// -----------------------------------------------------------------------
// pyToMessage
// 
// -----------------------------------------------------------------------
int pyToMessage (Message::Ref &msg,PyObject *pyobj)
{
//  PyObject_Print(pyobj,stdout,Py_PRINT_RAW);
  if( !PyObject_IsInstance(pyobj,*py_dmisyms.message) )
    throwError(Type,"object is not of type message");
  // get message ID
  PyObjectRef py_msgid = PyObject_GetAttrString(pyobj,"msgid"); // new ref
  if( !py_msgid )
    throwError(Attribute,"missing or bad msgid attribute");
  HIID msgid;
  pyToHIID(msgid,*py_msgid);
  // get message priority
  int priority = 0;
  PyObjectRef py_priority = PyObject_GetAttrString(pyobj,"priority"); // new ref
  if( py_priority )
    priority = PyInt_AsLong(*py_priority); 
  
  // create message object
  msg <<= new Message(msgid,Message::PRI_NORMAL + priority);
  
  // get message payload
  PyObjectRef py_payload = PyObject_GetAttrString(pyobj,"payload"); // new ref
  if( py_payload && *py_payload != Py_None )
  {
    ObjRef ref;
    pyToDMI(ref,*py_payload);
    msg() <<= ref;
  }
  // NB: Use PyBuffer objects for SmartBlock payloads
  
  // map additional attributes, if they exist
  HIID addr;
  PyObjectRef py_from  = PyObject_GetAttrString(pyobj,"from"); // new ref
  if( py_from && pyToHIID(addr,*py_from)>0 )
    msg().setFrom(addr);
  PyObjectRef py_to    = PyObject_GetAttrString(pyobj,"to"); // new ref
  if( py_to && pyToHIID(addr,*py_to)>0 )
    msg().setTo(addr);
  PyObjectRef py_state = PyObject_GetAttrString(pyobj,"state"); // new ref
  if( py_state )
    msg().setState(PyInt_AsLong(*py_state));
  PyObjectRef py_hops  = PyObject_GetAttrString(pyobj,"hops"); // new ref
  if( py_hops )
    msg().setHops(PyInt_AsLong(*py_hops));
  // clear errors at this point, since they only relate to optional attrs
  PyErr_Clear();
  return 1;
}

// helper method: returns string describing object
inline string ObjStr (const PyObject *obj) 
{
  return Debug::ssprintf("%s @%p",obj->ob_type->tp_name,(void*)obj);
}

// getDMIType:
// Helper templated function. Uses the dmi_typename() function to determine
// the type of an object, returns its TypeId if found.
// Otherwise returns 0.
static TypeId getDMIType (PyObject *pyobj)
{
  // create object according to its DMI typestring
  PyObjectRef args = Py_BuildValue("(Oi)",pyobj,1); // returns new ref, increments ref to pyobj
  if( !args )
    return 0;
  // returns new ref, does nothing to args
  PyObjectRef dmitypename = PyObject_CallObject(*py_dmisyms.dmi_typename,*args);
  if( !dmitypename )
    return 0;
  char *typestr = PyString_AsString(*dmitypename);
  if( !typestr )
    return 0;
  return TypeId(typestr);
}

// createSubclass:
// Helper templated function to create a DMI object. Uses getDMIType() 
// to determine DMI type of Python object pyobj. This must be a subclass of 
// Base, or Base itself, otherwise an exception is thrown.
// Creates new object and returns pointer.
template<class Base>
static Base * createSubclass (PyObject *pyobj)
{
  Base *pbase;
  // create object according to its DMI typestring
  TypeId tid = getDMIType(pyobj);
  if( tid == 0 )
    throwErrorOpt(Runtime,"Python object is not in dmi type map");
  dprintf(4)("real object type is %s\n",tid.toString().c_str());
  DMI::BObj * bo = DynamicTypeManager::construct(tid);
  pbase = dynamic_cast<Base *>(bo);
  if( !pbase )
  {
    delete bo;
    throwError(Type,tid.toString()+"is not a subclass of "+TpOfPtr(pbase).toString());
  }
  dprintf(5)("%s created at address %x\n",pbase->objectType().toString().c_str(),(int)pbase);
  return pbase;
}

// -----------------------------------------------------------------------
// pyToRecord
// -----------------------------------------------------------------------
int pyToRecord (DMI::Record::Ref &rec,PyObject *pyobj)
{
  string objstr = 
      Debug(3) ? "PyToRecord("+ObjStr(pyobj)+"): " : string();
  int num_original = PyMapping_Length(pyobj);
  int num_assigned = 0;
  cdebug(3)<<objstr<<"converting mapping of "<<num_original<<" items\n";
  PyObjectRef py_keylist = PyMapping_Keys(pyobj); // new ref
  if( !py_keylist )
    throwErrorOpt(Type,"no key list returned");
  rec <<= createSubclass<DMI::Record>(pyobj);
  int numkeys = PySequence_Length(*py_keylist);
  // loop over dict keys
  for( int ikey=0; ikey<numkeys; ikey++ )
  {
    PyErr_Clear();
    PyObjectRef py_key = PySequence_GetItem(*py_keylist,ikey); // new ref
    if( !py_key )
      throwErrorOpt(Key,ssprintf("can't get key #%s",ikey));
    // key must be a string, ensure this here
    char *key = PyString_AsString(*py_key);
    if( !key )
    {
      cdebug(4)<<objstr<<"skipping key "<<ikey<<": not a string"<<std::endl;
      continue;
    }
    string keystr(key);
    // convert string to HIID
    HIID id; 
    bool failed = false;
    try { id = HIID(keystr,true,"._"); } // allow literals
    catch (...) { failed=true; }
    if( failed )
    {
      cdebug(4)<<objstr<<"skipping key " <<keystr<<" ("<<ikey<<"): not a HIID"<<endl;
      continue;
    }
    // attempt to convert value to DMI object
    PyObjectRef pyval = PyMapping_GetItemString(pyobj,const_cast<char*>(keystr.c_str())); // new ref
    if( !pyval )
    {
      cdebug(4)<<objstr<<"skipping key " <<keystr<<" ("<<ikey<<"): failed to get value"<<endl;
      continue;
    }
    // try to convert the value and assign it to record field
    cdebug(4)<<objstr<<"converting key " <<keystr<<" ("<<ikey<<")\n";
    ObjRef ref;
    try 
    { 
      pyToDMI(ref,*pyval); 
      rec().add(id,ref,DMI::REPLACE);
      cdebug(4)<<objstr<<"assigned value for key " <<keystr<<" ("<<ikey<<")\n";
      num_assigned++;
    }
    // catch various failures and ignore them
    catch( std::exception &exc )
    { cdebug(4)<<objstr<<"skipping key " <<keystr<<" ("<<ikey<<"): failed to convert value: "<<
          exceptionToString(exc); }
    catch( ... )
    { cdebug(4)<<objstr<<"skipping key " <<keystr<<" ("<<ikey<<"): failed to convert value: unknown exception\n"; }
  }
  PyErr_Clear();
  cdebug(3)<<objstr<<"assigned "<<num_assigned<<" of "<<num_original<<" fields\n";
  rec().validateContent(true);
  return 1;
}

// Helper functions map NumarrayType enums to TypeIds
// Note that only a limited subset of element types is supported by DMI
static TypeId numarrayToTypeId (int num)
{
  switch( num )
  {
    case tBool:       return Tpbool;   
    case tUInt8:      return Tpuchar;
    case tInt16:      return Tpshort;
    case tInt32:      return Tpint;
    case tFloat32:    return Tpfloat;
    case tFloat64:    return Tpdouble;
    case tComplex32:  return Tpfcomplex;
    case tComplex64:  return Tpdcomplex;
    default:
      throwError(Type,ssprintf("numarray type %d not supported by dmi",num));
  }
}

static NumarrayType typeIdToNumarray (TypeId tid)
{
  switch( tid.id() )
  {
    case Tpbool_int:      return tBool;   
    case Tpuchar_int:     return tUInt8;
    case Tpshort_int:     return tInt16;
    case Tpint_int:       return tInt32;
    case Tpfloat_int:     return tFloat32;
    case Tpdouble_int:    return tFloat64;
    case Tpfcomplex_int:  return tComplex32;
    case Tpdcomplex_int:  return tComplex64;
    default:
      throwError(Type,"dmi type "+tid.toString()+" no supported by numarray");
  }
}

// -----------------------------------------------------------------------
// pyToArray
// -----------------------------------------------------------------------
int pyToArray (DMI::NumArray::Ref &arref,PyObject *pyobj)
{
  // create object
  DMI::NumArray &arr = arref <<= createSubclass<DMI::NumArray>(pyobj);
  // get input array object
  PyArrayObject *pyarr = NA_InputArray(pyobj,tAny,NUM_C_ARRAY); // new ref
  PyObjectRef pyarr_ref((PyObject*)pyarr); // attach here for auto-cleanup
  if( !pyarr ) 
    throwErrorOpt(Type,"NA_InputArray fails, perhaps object is not an array");
  // figure out array shape
  uint ndim = pyarr->nd;
  if( ndim>MaxLorrayRank )
    throwError(Type,ssprintf("array of rank %d, maximum supported is %d",ndim,MaxLorrayRank));
  // create shape of output array -- but do note that 0-dimensional 
  // numarrays (i.e. scalars) are represented by one-element 1D NumArrays
  LoShape shape((ndim?ndim:1)|LoShape::SETRANK);
  if( ndim )
    for( uint i=0; i<ndim; i++ )
      shape[i] = pyarr->dimensions[i];
  else
    shape[0] = 1;
  TypeId tid = numarrayToTypeId(pyarr->descr->type_num);
  ulong nb = ulong(pyarr->itemsize)*shape.product();
  // init DMI::NumArray
  cdebug(3)<<"pyToArray("<<ObjStr(pyobj)<<": type "<<tid<<", shape "<<shape<<", "<<nb<<" bytes\n";
  arr.init(tid,shape,DMI::NOZERO);
  
  memcpy(arr.getDataPtr(),NA_OFFSETDATA(pyarr),nb);
  arr.validateContent(true);

  // success
  return 1;
}

// returns DMI TypeId corresponding to python object
// TpDMIObjRef for None objects
// TpDMIList for sequence objects
// 0 if unmappable type
TypeId pyToDMI_Type (PyObject *obj)
{
  // first check for primitives
  if( obj == Py_None ) 
    return TpDMIObjRef;
  else if( PyInt_Check(obj) )
    return Tpint;
  else if( PyLong_Check(obj) )
    return Tplong;
  else if( PyFloat_Check(obj) )
    return Tpdouble;
  else if( PyComplex_Check(obj) )
    return Tpdcomplex;
  else if( PyString_Check(obj) )
    return Tpstring;
  else if( PyObject_IsInstance(obj,*py_dmisyms.hiid) )
    return TpDMIHIID;
  else if( PyObject_IsInstance(obj,*py_dmisyms.record) ) 
    return TpDMIRecord;
  else if( PyObject_IsInstance(obj,*py_dmisyms.array_class) )
    return TpDMINumArray;
  else if( PyObject_IsInstance(obj,*py_dmisyms.message) )
    return TpOctopussyMessage;
  else if( PySequence_Check(obj) )  // process a sequence
    return TpDMIList;
  else // non-supported type
    return 0;
}

// -----------------------------------------------------------------------
// pyToDMI
// converts a Python object to a DMI object reference
// May be called in two modes, depending on whether the object is
// part of a DMI::Vec or not:
// (a) pvec0=0: create new container to hold object if needed. 
//     Return via objref.
// (b) pvec0!=0: object is part of a vec. Insert into pvec0 at position
//     pvec_pos, and ignore objref. Throw exception on type mismatch.
// -----------------------------------------------------------------------
int pyToDMI (ObjRef &objref,PyObject *obj,TypeId objtype,DMI::Vec *pvec0,int pvec_pos)
{
  string objstr = 
      Debug(3) ? "PyToDMI("+ObjStr(obj)+"): " : string();
  cdebug(3)<<objstr<<"called for "<<bool(pvec0)<<"/"<<pvec_pos<<endl;
  // None is empty ObjRef
  if( obj == Py_None )
  {
    if( pvec0 )
      pvec0->put(pvec_pos,ObjRef());
    else
      objref.detach();
    return 1;
  }
  // dmi_supported_types =
  // (int,long,float,complex,str,hiid,array_class,record,message);
  // this is really a switch calling different kinds of object builders
  DMI::NumArray *parr;
  if( !objtype ) // determine type if not set
    objtype = pyToDMI_Type(obj);
  switch( objtype.id() )
  {
    case Tpint_int:
          if( pvec0 )
            (*pvec0)[pvec_pos] = int( PyInt_AS_LONG(obj) );
          else
          {
            objref <<= parr = new DMI::NumArray(Tpint,LoShape(1));
            *static_cast<int*>(parr->getDataPtr()) = int( PyInt_AS_LONG(obj) );
          }
          break;
    case Tplong_int:
          if( pvec0 )
            (*pvec0)[pvec_pos] = PyLong_AsLong(obj);
          else // single numeric scalar -- convert to DatArray
          {
            objref <<= parr = new DMI::NumArray(Tplong,LoShape(1));
            *static_cast<long*>(parr->getDataPtr()) = PyLong_AsLong(obj);
          }
          if( PyErr_Occurred() )
          {
            if( PyErr_ExceptionMatches(PyExc_OverflowError) )
              throwErrorOpt(Overflow,"overflow in long type");
            throwErrorOpt(Type,"unexpected error: "+string(PyErr_Occurred()->ob_type->tp_name));
          }
          break;
    case Tpdouble_int:
          if( pvec0 )
            (*pvec0)[pvec_pos] = PyFloat_AS_DOUBLE(obj);
          else
          {
            objref <<= parr = new DMI::NumArray(Tpdouble,LoShape(1));
            *static_cast<double*>(parr->getDataPtr()) = PyFloat_AS_DOUBLE(obj);
          }
          break;
    case Tpdcomplex_int:
          Py_complex pc = PyComplex_AsCComplex(obj);
          if( pvec0 )
            (*pvec0)[pvec_pos] = make_dcomplex(pc.real,pc.imag);
          else
          {
            objref <<= parr = new DMI::NumArray(Tpdcomplex,LoShape(1));
            *static_cast<dcomplex*>(parr->getDataPtr()) = make_dcomplex(pc.real,pc.imag);
          }
          break;
    case Tpstring_int:
          if( !pvec0 )
            objref <<= pvec0 = new DMI::Vec(Tpstring);
          (*pvec0)[pvec_pos] = PyString_AS_STRING(obj);
          break;
    case TpDMIHIID_int:
          { HIID id;
          pyToHIID(id,obj);
          if( !pvec0 )
            objref <<= pvec0 = new DMI::Vec(TpDMIHIID,-1,&id);
          else
            (*pvec0)[pvec_pos] = id;
          } break;
    case TpDMIObjRef_int:
          if( pvec0 )
            pvec0->put(pvec_pos,ObjRef());
          else
            objref.detach();
          break;
    case TpDMIRecord_int:
          { DMI::Record::Ref rec;
          pyToRecord(rec,obj);
          if( pvec0 )
            pvec0->put(pvec_pos,rec);
          else
            objref <<= rec;
          } break;
    case TpDMINumArray_int:
          { DMI::NumArray::Ref arr;
          pyToArray(arr,obj);
          if( pvec0 )
            pvec0->put(pvec_pos,arr);
          else
            objref <<= arr;
          } break;
    case TpOctopussyMessage_int:
          { Message::Ref msg;
          pyToMessage(msg,obj);
          if( pvec0 )
            pvec0->put(pvec_pos,msg);
          else
            objref <<= msg;
          } break;
    case TpDMIList_int:
        { int len = PySequence_Size(obj);
          // for sequences of the same non-dynamic type, use a DMI::Vec
          // for all other sequences use a DMI::List
          // scan through list to determine item type
          TypeId seqtype = 0, seqbasetype;
          bool use_list = false;
          for( int i=0; i<len; i++ )
          {
            PyObjectRef item = PySequence_ITEM(obj,i); // new ref
            // determine base content type based on Python type
            TypeId basetype = pyToDMI_Type(*item);
            if( !basetype )
            {
              string type = item->ob_type->tp_name;
              cdebug(3)<<objstr<<"type "<<type<<" not supported"<<endl;
              throwError(Type,"dmi: type "+type+" not supported");
            }
            // actual type may be a subclass of basetype (e.g.
            // base is DMI::Record, actual type is Meq::Result)
            TypeId type = getDMIType(*item);
            if( !type )
              type = basetype;
            // set sequence type if not set
            if( !seqtype )
            {
              seqtype = type;
              seqbasetype = basetype;
            }
            // dynamic types, or null objects (ObjRef), or mismatching types:
            // use a list instead
            // OMS 29/08/2005: removed the isDynamic() condition; objects
            // of the same type ought to go into a DMI::Vec. Not sure why it
            // was there in the first place
            if( type == TpDMIObjRef || type != seqtype )
//            if( TypeInfo::isDynamic(type) || type == TpDMIObjRef || type != seqtype )
            {
              use_list = true;
              break;
            }
          }
          // now, use list or vector as appropriate
          ObjRef seqref;
          if( use_list )
          {
            cdebug(3)<<"converting sequence to DMI::List"<<endl;
            DMI::List *plist = new DMI::List;
            seqref <<= plist;
            for( int i=0; i<len; i++ )
            {
              cdebug(4)<<objstr<<"converting seq element "<<i<<endl;
              PyObjectRef item = PySequence_ITEM(obj,i); // new ref
              ObjRef itemref; 
              pyToDMI(itemref,*item);
              plist->addBack(itemref);
            }
          }
          else // else using vector
          {
            cdebug(3)<<"converting sequence of type "<<seqtype.toString()<<" to DMI::Vec"<<endl;
            // type will have been set if we have at least one element
            if( len )
              Assert(seqtype);
            // else we'll just init an empty vector
            DMI::Vec *pvec = seqtype ? new DMI::Vec(seqtype,len) : new DMI::Vec;
            seqref <<= pvec;
            for( int i=0; i<len; i++ )
            {
              cdebug(4)<<objstr<<"converting seq element "<<i<<endl;
              PyObjectRef item = PySequence_ITEM(obj,i); // new ref
              ObjRef dum;
              pyToDMI(dum,*item,seqbasetype,pvec,i);  // this mode causes an insert into vector
            }
          }
          // check if we're actually an item in a DMI::Vec
          if( pvec0 )
            pvec0->put(pvec_pos,seqref);
          else
            objref <<= seqref;
          cdebug(3)<<objstr<<"successfully converted seq of "<<len<<" objects\n";
        }
        break;
    default:
        string type = obj->ob_type->tp_name;
        cdebug(3)<<objstr<<"type "<<type<<" not supported"<<endl;
        throwError(Type,"dmi: type "+type+" not supported");
  }
  // success
  return 1;
}


// Inline helper functions 
// Converts dcomplex into PyComplex, returns NEW REF
inline PyObject * PyComplex_FromDComplex (const dcomplex &x)
{
  return PyComplex_FromDoubles(creal(x),cimag(x));
}

// -----------------------------------------------------------------------
// PyFromObjRef
// Converts ObjRef into python object. Unattached refs converted to None,
// everything else passed to pyFromDMI().
// Returns NEW REF.
// Default error policy is to return a conversion error object.
// -----------------------------------------------------------------------
inline PyObject * pyFromObjRef (const ObjRef &ref,int err_policy=EP_CONV_ERROR)
{
  if( ref.valid() )
    return pyFromDMI(*ref,err_policy); // new ref
  else
    returnNone;  // increments ref count to None
}


// -----------------------------------------------------------------------
// createPyObject
// Creates PyObject from given dmiobj; uses basetype as the base type.
// Optional constructor arguments may be supplied.
// Returns NEW REF to python object.
// -----------------------------------------------------------------------
PyObject * createPyObject (PyObject *basetype,const BObj &dmiobj,PyObject *constructor_args=0)
{
  std::string objtype = dmiobj.objectType().toString();
  cdebug(3)<<"createPyObject for DMI type "<<objtype<<endl;
  PyObjectRef args = Py_BuildValue("(sO)",objtype.c_str(),basetype); // new ref
  if( !args )
    throwErrorOpt(Runtime,"failed to create dmi_type() args tuple for "+objtype);
  PyObjectRef constructor = PyObject_CallObject(*py_dmisyms.dmi_type,*args); // new ref
  if( !constructor )
    throwErrorOpt(Runtime,"failed to call dmi_type() for "+objtype);
  PyObjectRef pyobj = PyObject_CallObject(*constructor,constructor_args); // new ref
  if( !pyobj )
    throwErrorOpt(Runtime,"failed to create a python object for "+objtype);
  return ~pyobj;
}

// -----------------------------------------------------------------------
// pyFromVec
// converts a DMI::Vec to a Python scalar or tuple
// Returns NEW REF
// -----------------------------------------------------------------------
PyObject * pyFromVec (const DMI::Vec &dv)
{
  Thread::Mutex::Lock lock(dv.mutex());
  cdebug(3)<<"pyFromVec: creating\n";
  //  PyObjectRef tuple = createPyObject((PyObject*)&PyTuple_Type,dv);
  // subclasses of tuple not permitted
  PyObjectRef tuple;
  // empty/uninit Vec -- return empty tuple
  if( !dv.valid() )
  {
    cdebug(3)<<"pyFromVec: null DMI::Vec, returning empty tuple\n";
    return PyTuple_New(0); // new ref
  }
  TypeId type = dv.type();
  const TypeInfo &typeinfo = TypeInfo::find(type);
  int num = dv.size();
  if( dv.isScalar() ) // scalar field: will be returned directly
  {
    cdebug(3)<<"pyFromVec: will return scalar "<<type<<endl;
  }
  else   // non-scalar field: allocate a tuple
  {
    cdebug(3)<<"pyFromVec: creating tuple of size "<<num<<"\n";
    tuple = PyTuple_New(num);  // new ref, so assign
    if( !tuple )
      throwErrorOpt(Runtime,"failed to resize tuple");
  }
  // Define macro to extract field contents and assign to tuple, or else
  // return immediately.
  // Note that all the PyFuncs called here return a new reference,
  // while PyTuple_SET_ITEM  steals a reference, so we can pass in the
  // return value of any function ('pyfunc') returning a NEW REF.
  #define extractField(pyfunc,hookfunc) \
    { if( tuple ) { \
        cdebug(4)<<"using "<<num<<" " #pyfunc "(vec[i]." #hookfunc ")\n"; \
        for( int i=0; i<num; i++ ) \
          PyTuple_SET_ITEM(*tuple,i,pyfunc(dv[i].hookfunc)); \
      } else { \
        cdebug(4)<<"using scalar " #pyfunc "(vec." #hookfunc ")\n"; \
        return pyfunc(dv[HIID()].hookfunc); } }
  // now proceed depending on object type
  if( typeinfo.category == TypeCategories::NUMERIC )
  {
    if( type == Tpbool )
      extractField(PyBool_FromLong,as<long>())
    else if( type < Tpbool && type >= Tplong )
      extractField(PyInt_FromLong,as<long>())
    else if( type <= Tpulong && type >= Tplonglong )
      extractField(PyLong_FromLongLong,as<longlong>())
    else if( type == Tpulonglong )
      extractField(PyLong_FromLongLong,as<ulonglong>())
    else if( type <= Tpfloat && type >= Tpldouble )
      extractField(PyFloat_FromDouble,as<double>())
    else if( type <= Tpfcomplex && type >= Tpdcomplex )
      extractField(PyComplex_FromDComplex,as<dcomplex>())
    else
      throwError(Runtime,"unexpected numeric DMI type "+type.toString());
  }
  else if( type == Tpstring )
    extractField(pyFromString,as<string>())
  else if( type == TpDMIHIID )
    extractField(pyFromHIID,as<HIID>())
  else if( typeinfo.category == TypeCategories::DYNAMIC )
    extractField(pyFromObjRef,ref(true))
  else
    return pyConvError("dmi type "+type.toString()+" not supported under Python");
  // if we got here, we've formed a tuple
  // (scalars should have been returned directly from the if-else blocks above)
  Assert(tuple);
  return ~tuple; // return new ref, stealing from ours
}

// -----------------------------------------------------------------------
// pyFromList
// converts a DMI::List to a Python list
// -----------------------------------------------------------------------
PyObject * pyFromList (const DMI::List &dl)
{
  Thread::Mutex::Lock lock(dl.mutex());
  cdebug(3)<<"pyFromList: creating\n";
  PyObjectRef pylist = createPyObject((PyObject*)&PyList_Type,dl); // new ref
  for( DMI::List::const_iterator iter = dl.begin(); iter != dl.end(); iter++ )
  {
    PyObjectRef item = pyFromObjRef(*iter,EP_CONV_ERROR); // new ref
    PyList_Append(*pylist,*item); // list takes its own ref
  }
  cdebug(3)<<"pyFromList: converted "<<dl.size()<<" items\n";
  return ~pylist; // return new ref, stealing from ours
}

// -----------------------------------------------------------------------
// pyFromRecord
// converts a DMI::Record to a Python record instance
// -----------------------------------------------------------------------
PyObject * pyFromRecord (const DMI::Record &dr)
{
  Thread::Mutex::Lock lock(dr.mutex());
  cdebug(3)<<"pyFromRecord: creating"<<endl;
  PyObjectRef pyrec = createPyObject(*py_dmisyms.record,dr); // new ref
  for( DMI::Record::const_iterator iter = dr.begin(); iter != dr.end(); iter++ )
  {
    string idstr = strlowercase(iter.id().toString('_',false)); // false = do not mark literals with $
    PyObjectRef item = pyFromObjRef(iter.ref(),EP_CONV_ERROR); // new ref
    // Dict takes its own ref
    PyDict_SetItemString(*pyrec,const_cast<char*>(idstr.c_str()),*item);
  }
  cdebug(3)<<"pyFromRecord: converted "<<PyDict_Size(*pyrec)<<" fields\n";
  return ~pyrec; // return new ref, stealing from ours
}

// -----------------------------------------------------------------------
// pyFromArray
// converts a DMI::NumArray to a Numarray instance
// -----------------------------------------------------------------------
PyObject * pyFromArray (const DMI::NumArray &da)
{
  Thread::Mutex::Lock lock(da.mutex());
  // get rank & shape into terms that Numarray understands
   cdebug(3)<<"pyFromArray: creating array"<<endl;
  int rank = da.rank();
  TypeId objtype = da.objectType();
  // a [1] array is converted to a scalar, unless it's a subclass of NumArray
  // (in which case we'll need to subclass it, so we need to make it into
  // an array anyway)
  if( rank==1 && da.size() == 1 && objtype == TpDMINumArray )
  {
    TypeId type = da.elementType();
    DMI::NumArray::Hook hook(da,0);
    if( type == Tpbool )
      return PyBool_FromLong(hook.as<bool>());
    else if( type < Tpbool && type >= Tplong )
      return PyInt_FromLong(hook.as<long>());
    else if( type <= Tpulong && type >= Tplonglong )
      return PyLong_FromLongLong(hook.as<longlong>());
    else if( type == Tpulonglong )
      return PyLong_FromLongLong(hook.as<ulonglong>());
    else if( type <= Tpfloat && type >= Tpldouble )
      return PyFloat_FromDouble(hook.as<double>());
    else if( type <= Tpfcomplex && type >= Tpdcomplex )
      return PyComplex_FromDComplex(hook.as<dcomplex>());
    else
      throwError(Runtime,"unsupported array type "+type.toString());
  }
  else // else regular array
  {
    // do we need to reclassify later?
    PyObjectRef realclass;
    if( objtype != TpDMINumArray )
    {
      cdebug(3)<<"pyFromArray: real type is "<<objtype<<endl;
      PyObjectRef args = Py_BuildValue("(sO)",objtype.toString().c_str(),*py_dmisyms.array_class); // new ref
      if( !args )
        throwErrorOpt(Runtime,"failed to create dmi_type() args tuple for "+objtype.toString());
      realclass = PyObject_CallObject(*py_dmisyms.dmi_type,*args); // new ref
      if( !realclass )
        throwErrorOpt(Runtime,"failed to call dmi_type() for "+objtype.toString());
    }
    // create array
    NumarrayType typecode = typeIdToNumarray(da.elementType());
// 20/01/05: get rid of transpose here since NumArrays are in C order now
// this is the old version: column-major ordering
//     maybelong dims[rank];
//     maybelong strides[rank];
//     maybelong stride = da.elementSize();
//     for( int i=0; i<rank; i++ )
//     {
//       strides[i] = stride;
//       stride *= dims[i] = da.shape()[i];
//     }
//    PyObjectRef pyarr = (PyObject*)
//        NA_NewAllStrides(rank,dims,strides,typecode,
//                         const_cast<void*>(da.getConstDataPtr()),
//                         0,NUM_LITTLE_ENDIAN,0,1);

//  this is the new version: only specify shape (C order by default)
    maybelong dims[rank];
    for( int i=0; i<rank; i++ )
      dims[i] = da.shape()[i];
    PyObjectRef pyarr = (PyObject*)
      NA_vNewArray(const_cast<void*>(da.getConstDataPtr()),typecode,rank,dims); // new ref
    // reclassify
    if( objtype != TpDMINumArray )
    {
      cdebug(3)<<"pyFromArray: recasting array to "<<objtype<<endl;
      PyObjectRef args = Py_BuildValue("(OO)",*pyarr,*realclass); // new ref
      if( !args )
        throwErrorOpt(Runtime,"failed to create dmi_coerce() args tuple for "+objtype.toString());
      PyObjectRef result = PyObject_CallObject(*py_dmisyms.dmi_coerce,*args);
      if( !result )
        throwErrorOpt(Runtime,"failed to call dmi_coerce() for "+objtype.toString());
    }
    return ~pyarr; // steal our ref since we need to return a NEW REF
  }
}

// -----------------------------------------------------------------------
// pyFromMessage
// -----------------------------------------------------------------------
PyObject * pyFromMessage (const Message &msg)
{
  // get payload
  PyObjectRef py_payload = pyFromObjRef(msg.payload(),EP_CONV_ERROR);
  // create message object
  PyObjectRef args = Py_BuildValue("(NNN)",
      pyFromHIID(msg.id()),  // new ref
      ~py_payload,  // steal our ref since "N" is used
      PyInt_FromLong(msg.priority()-Message::PRI_NORMAL)); // new ref
  if( !args )
    throwErrorOpt(Runtime,"failed to build args tuple");
  
  PyObjectRef py_msg = PyObject_CallObject(*py_dmisyms.message,*args); // new ref
  if( !py_msg )
    throwErrorOpt(Runtime,"failed to create a message instance");
  
  // create additional attributes
  // we use PyObjectRefs here because the functions return new refs,
  // so ref counts do need to be decremented after calling SetAttrString.
  PyObject_SetAttrString(*py_msg,"from",PyObjectRef(pyFromHIID(msg.from())).obj());
  PyObject_SetAttrString(*py_msg,"to",PyObjectRef(pyFromHIID(msg.to())).obj());
  PyObject_SetAttrString(*py_msg,"state",PyObjectRef(PyInt_FromLong(msg.state())).obj());
  PyObject_SetAttrString(*py_msg,"hops",PyObjectRef(PyInt_FromLong(msg.hops())).obj());
  return ~py_msg;
}

// -----------------------------------------------------------------------
// pyFromDMI
// converts a DMI object (DMI::Vec, DMI::Record, DMI::NumArray, Message)
// into a Python object.
// May be called in two modes, depending on whether the object is
// part of a sequence or not:
// (a) seqlen=0: create new container to hold object, return via objref.
//     This is for objects not part of a sequence.
// (b) seqlen>0: object is part of a sequence; objref must already contain
//     a DMI::Vec.
//     If seqpos=0, init the DMI::Vec with the object type and store at #0
//     If seqpos>0, check for type consistency, and store at #seqpos.
// -----------------------------------------------------------------------
PyObject * pyFromDMI (const DMI::BObj &obj,int err_policy)
{
  Thread::Mutex::Lock lock(obj.crefMutex());
  try
  {
    TypeId objtype = obj.objectType();
    // all of the below return new refs
    PyObjectRef pyobj;
    if( dynamic_cast<const DMI::Record *>(&obj) )
      pyobj = pyFromRecord(dynamic_cast<const DMI::Record &>(obj));
    else if( dynamic_cast<const DMI::Vec *>(&obj) )
      pyobj = pyFromVec(dynamic_cast<const DMI::Vec &>(obj));
    else if( dynamic_cast<const DMI::NumArray *>(&obj) )
      pyobj = pyFromArray(dynamic_cast<const DMI::NumArray &>(obj));
    else if( dynamic_cast<const DMI::List *>(&obj) )
      pyobj = pyFromList(dynamic_cast<const DMI::List &>(obj));
    else if( dynamic_cast<const Message *>(&obj) )
      pyobj = pyFromMessage(dynamic_cast<const Message &>(obj));
    else
      pyobj = pyConvError("dmi type "+objtype.toString()+" not supported under Python");
    return ~pyobj;
  }
  catch( std::exception &exc )
  {
    if( err_policy == EP_RETNULL )
    {
      cdebug(2)<<"pyFromDMI: exception "<<exc.what()<<", returning NULL\n";
      if( !PyErr_Occurred() )
        returnError(NULL,DataConv,exc);
      return NULL;
    }
    else if( err_policy == EP_CONV_ERROR )
    {
      cdebug(2)<<"pyFromDMI: exception "<<exc.what()<<", returning conv_error\n";
      return pyConvError(exc.what());
    }
    else // re-throw
    {
      cdebug(2)<<"pyFromDMI: exception "<<exc.what()<<", re-throwing\n";
      throw;
    }
  }
}

// -----------------------------------------------------------------------
// pyConvError
// Create a conv_error description
// Returns NEW REFERENCE
// -----------------------------------------------------------------------
PyObject * pyConvError (const string &msg)
{
  // create message object (new ref returned)
  PyObjectRef args = Py_BuildValue("NO",
        pyFromString(msg), // new ref passed in
        PyErr_Occurred() ? PyErr_Occurred() : Py_None); // borrowed ref passed in
  if( !args )
    throwErrorOpt(Runtime,"failed to build args tuple");
  PyErr_Clear();
  PyObjectRef converr = PyObject_CallObject(*py_dmisyms.conv_error,*args); // new ref
  if( !converr )
    throwErrorOpt(Runtime,"failed to create a conv_error instance");
  // steal our ref so that new one is returned
  return ~converr;
}


// -----------------------------------------------------------------------
// initDataConv()
// -----------------------------------------------------------------------
void initDataConv ()
{
  if( sizeof(bool) != sizeof(NumarrayBool) )
  {
    Py_FatalError("C++ bool != numarray bool, conversion code must be implemented");
  }
  import_libnumarray();
}

}; // namespace OctoPython
