//## begin module%1.4%.codegen_version preserve=yes
//   Read the documentation to learn more about C++ code generator
//   versioning.
//## end module%1.4%.codegen_version

//## begin module%3C10CC81037C.cm preserve=no
//	  %X% %Q% %Z% %W%
//## end module%3C10CC81037C.cm

//## begin module%3C10CC81037C.cp preserve=no
//## end module%3C10CC81037C.cp

//## Module: CountedRefBase%3C10CC81037C; Package specification
//## Subsystem: DMI%3C10CC810155
//	f:\lofar\dvl\lofar\cep\cpa\pscf\src
//## Source file: F:\LOFAR\dvl\LOFAR\cep\cpa\pscf\src\CountedRefBase.h

#ifndef CountedRefBase_h
#define CountedRefBase_h 1

//## begin module%3C10CC81037C.additionalIncludes preserve=no
#include "Common.h"
#include "DMI.h"
//## end module%3C10CC81037C.additionalIncludes

//## begin module%3C10CC81037C.includes preserve=yes
//## end module%3C10CC81037C.includes

// CountedRefTarget
#include "CountedRefTarget.h"
// Debug
#include "Debug.h"
//## begin module%3C10CC81037C.declarations preserve=no
//## end module%3C10CC81037C.declarations

//## begin module%3C10CC81037C.additionalDeclarations preserve=yes
//## end module%3C10CC81037C.additionalDeclarations


//## begin CountedRefBase%3C0CDEE200FE.preface preserve=yes
//## end CountedRefBase%3C0CDEE200FE.preface

//## Class: CountedRefBase%3C0CDEE200FE
//	Implements a counted reference mechanism. See CountedRef<T> for a
//	type-specific interface. CountedRefs have destructive copy semantics.
//## Category: PSCF::DMI%3BEAB1F2006B; Global
//## Subsystem: DMI%3C10CC810155
//## Persistence: Transient
//## Cardinality/Multiplicity: n



//## Uses: <unnamed>%3C19B9380140;Debug::Error { -> }

class CountedRefBase 
{
  //## begin CountedRefBase%3C0CDEE200FE.initialDeclarations preserve=yes
  //## end CountedRefBase%3C0CDEE200FE.initialDeclarations

  public:
    //## Constructors (generated)
      CountedRefBase();

    //## Constructors (specified)
      //## Operation: CountedRefBase%3C0CE1C10277; C++
      //	Generic copy constructor. Default is destructive transfer (via xfer
      //	Other(). If  DMI::COPY is used, calls copyOther() to make a copy. If
      //	DMI::PRIVATIZE is used, calls privatizeOther(). See
      //	copy()/privatize() for other flags.
      //
      //	Flags with xfer: none
      //	Flags with DMI::PRIVATIZE: DMI::FORCE_CLONE to force target cloning,
      //	see attach() for all others.
      CountedRefBase (const CountedRefBase& other, int flags = 0);

    //## Destructor (generated)
      ~CountedRefBase();

    //## Assignment Operation (generated)
      CountedRefBase & operator=(const CountedRefBase &right);

    //## Equality Operations (generated)
      Bool operator==(const CountedRefBase &right) const;

      Bool operator!=(const CountedRefBase &right) const;


    //## Other Operations (specified)
      //## Operation: isValid%3C0CDEE2015A; C++
      //	Returns True if reference is valid (i.e. has a target).
      bool isValid () const;

      //## Operation: getTarget%3C0CDEE2015B; C++
      //	Dereferences, returns const reference to target.
      const CountedRefTarget* getTarget () const;

      //## Operation: getTargetWr%3C0CE2970094; C++
      //	Dereferences to writable target (exception if not writable).
      CountedRefTarget* getTargetWr ();

      //## Operation: copy%3C0CDEE20162; C++
      //	Makes and returns a second copy of  the reference. Flags are:
      //	DMI::LOCKED to lock the copy, DMI::WRITE for writable copy (defaults
      //	is READONLY).
      CountedRefBase copy (int flags = 0) const;

      //## Operation: copy%3C0CDEE2018A; C++
      //	Makes this a copy of the other reference. Flags are: DMI::LOCKED to
      //	lock the copy, DMI::WRITE for writable copy (defaults is READONLY).
      void copy (const CountedRefBase& other, int flags = 0);

      //## Operation: xfer%3C0CDEE20180; C++
      //	Destructive transfer of other ref
      void xfer (CountedRefBase& other);

      //## Operation: privatize%3C0CDEE20164; C++
      //	Creates a "private copy" of the target. Will clone() the target as
      //	necessary. Without DMI::WRITE, simply guarantees a non-volatile
      //	target (i.e. clones it in the presense of any writers). With WRITE,
      //	makes a writable clone of the target. Other flags: : DMI::FORCE_
      //	CLONE to force  cloning, DMI::LOCKED to lock the ref, DMI::EXCL_
      //	WRITE to make exclusive writer.
      //	.
      CountedRefBase& privatize (int flags = 0);

      //## Operation: lock%3C187D92023F; C++
      //	Locks the ref. Locked refs can't be detached or transferred.
      CountedRefBase& lock ();

      //## Operation: unlock%3C187D9A022C; C++
      //	Unlocks the ref.
      CountedRefBase& unlock ();

      //## Operation: change%3C18873600E9; C++
      //	Changes ref properties, if possible. Recognized flags:
      //	DMI::WRITE/READONLY, LOCKED/UNLOCKED, EXCL_WRITE/NONEXCL_WRITE.
      CountedRefBase& change (int flags);

      //## Operation: setExclusiveWrite%3C1888B001A1; C++
      //	Makes the ref an exclusive writer, if no other writers exist
      //	(exception otherwise)
      CountedRefBase& setExclusiveWrite ();

      //## Operation: attach%3C0CDEE20171; C++
      //	Attaches to target object. Flags:
      //	DMI::ANON for anonymous object (default EXTERNAL), WRITE for
      //	writable ref (default READONLY), LOCKED to lock the ref, EXCL_WRITE
      //	for exclusive write access.
      CountedRefBase& attach (CountedRefTarget* targ, int flags = 0);

      //## Operation: attach%3C0CDEE20178; C++
      //	Attaches to target, with READONLY forced.
      CountedRefBase& attach (const CountedRefTarget* targ, int flags = 0);

      //## Operation: detach%3C1612A60137; C++
      //	Detaches ref from its target. Can't be called if ref is locked.
      void detach ();

      //## Operation: isWrite%3C19F62B0137
      //	Alias for isWritable().
      bool isWrite () const;

    //## Get and Set Operations for Class Attributes (generated)

      //## Attribute: locked%3C15DF4D036D
      //	Flag: locked ref. Locked references can't be transferred, only
      //	copy()d. Also, they may not be detached.
      const bool isLocked () const;

      //## Attribute: writable%3C0CDEE20112
      //	True if reference target is writable.
      const bool isWritable () const;

      //## Attribute: exclusiveWrite%3C0CDEE20127
      //	True if this is an exclusive-write reference, i.e., other writable
      //	refs can't be created.
      const bool isExclusiveWrite () const;

      //## Attribute: anonObject%3C0CDEE20130
      //	True if target is an anonymous object (i.e. will be deleted when last
      //	reference to it is deleted.)
      const bool isAnonObject () const;

    //## Get and Set Operations for Associations (generated)

      //## Association: PSCF::DMI::<unnamed>%3C0CE0F60398
      //## Role: CountedRefBase::prev%3C0CE0FA0394
      //	prev ref in list (0 if first ref)
      const CountedRefBase * getPrev () const;

      //## Association: PSCF::DMI::<unnamed>%3C0CE0F60398
      //## Role: CountedRefBase::next%3C0CE0FB0010
      //	next ref in list (0 if last ref)
      const CountedRefBase * getNext () const;

    // Additional Public Declarations
      //## begin CountedRefBase%3C0CDEE200FE.public preserve=yes
      CountedRefBase * getNext ();
      CountedRefBase * getPrev ();

      // This is a typical debug() method setup. The sdebug()
      // method creates a debug info string at the given level of detail.
      // If detail<0, then partial info is returned: e.g., for detail==-2,
      // then only level 2 info is returned, without level 0 or 1.
      // Other conventions: no trailing \n; if newlines are embedded
      // inside the string, they are followed by prefix.
      // If class name is not specified, a default one is inserted.
      // It is sometimes useful to have a virtual sdebug(). 
      string sdebug ( int detail = 1,const string &prefix = "",
                      const char *name = 0 ) const;
      // The debug() method is an alternative interface to sdebug(),
      // which stores the info in a static data member, and returns a 
      // const char *. Thus debug()s can't be nested, while sdebug()s can.
      static string last_debug; 
      const char * debug ( int detail = 1,const string &prefix = "",
                           const char *name = 0 ) const
      {
        return (Debug::last_message = sdebug(detail,prefix,name) ).c_str();
      };
      //## end CountedRefBase%3C0CDEE200FE.public
  protected:

    //## Other Operations (specified)
      //## Operation: privatizeOther%3C1611C702DB; C++
      //	Privatizes a reference.
      void privatizeOther (const CountedRefBase& other, int flags);

      //## Operation: empty%3C161C330291; C++
      //	Nulls internals.
      void empty ();

    // Additional Protected Declarations
      //## begin CountedRefBase%3C0CDEE200FE.protected preserve=yes
      //## end CountedRefBase%3C0CDEE200FE.protected

  private:
    // Data Members for Associations

      //## Association: PSCF::DMI::<unnamed>%3C0CE0F60398
      //## begin CountedRefBase::prev%3C0CE0FA0394.role preserve=no  public: CountedRefBase {0..1 -> 0..1RHN}
      CountedRefBase *prev;
      //## end CountedRefBase::prev%3C0CE0FA0394.role

      //## Association: PSCF::DMI::<unnamed>%3C0CE0F60398
      //## begin CountedRefBase::next%3C0CE0FB0010.role preserve=no  public: CountedRefBase {0..1 -> 0..1RHN}
      CountedRefBase *next;
      //## end CountedRefBase::next%3C0CE0FB0010.role

      //## Association: PSCF::DMI::<unnamed>%3C0CDF6500AC
      //## Role: CountedRefBase::target%3C0CDF6503A5
      //	Reference target
      //## begin CountedRefBase::target%3C0CDF6503A5.role preserve=no  public: CountedRefTarget {0..1 -> 0..1RHN}
      CountedRefTarget *target;
      //## end CountedRefBase::target%3C0CDF6503A5.role

    // Additional Private Declarations
      //## begin CountedRefBase%3C0CDEE200FE.private preserve=yes
      //## end CountedRefBase%3C0CDEE200FE.private

  private: //## implementation
    // Data Members for Class Attributes

      //## begin CountedRefBase::locked%3C15DF4D036D.attr preserve=no  public: bool {U} 
      bool locked;
      //## end CountedRefBase::locked%3C15DF4D036D.attr

      //## begin CountedRefBase::writable%3C0CDEE20112.attr preserve=no  public: bool {U} 
      bool writable;
      //## end CountedRefBase::writable%3C0CDEE20112.attr

      //## begin CountedRefBase::exclusiveWrite%3C0CDEE20127.attr preserve=no  public: bool {U} 
      bool exclusiveWrite;
      //## end CountedRefBase::exclusiveWrite%3C0CDEE20127.attr

      //## begin CountedRefBase::anonObject%3C0CDEE20130.attr preserve=no  public: bool {U} 
      bool anonObject;
      //## end CountedRefBase::anonObject%3C0CDEE20130.attr

    // Additional Implementation Declarations
      //## begin CountedRefBase%3C0CDEE200FE.implementation preserve=yes
      //## end CountedRefBase%3C0CDEE200FE.implementation

  //## begin CountedRefBase%3C0CDEE200FE.friends preserve=no
    friend class CountedRefTarget;
  //## end CountedRefBase%3C0CDEE200FE.friends
};

//## begin CountedRefBase%3C0CDEE200FE.postscript preserve=yes
//## end CountedRefBase%3C0CDEE200FE.postscript

// Class CountedRefBase 

inline CountedRefBase::CountedRefBase()
  //## begin CountedRefBase::CountedRefBase%3C0CDEE200FE_const.hasinit preserve=no
  //## end CountedRefBase::CountedRefBase%3C0CDEE200FE_const.hasinit
  //## begin CountedRefBase::CountedRefBase%3C0CDEE200FE_const.initialization preserve=yes
  //## end CountedRefBase::CountedRefBase%3C0CDEE200FE_const.initialization
{
  //## begin CountedRefBase::CountedRefBase%3C0CDEE200FE_const.body preserve=yes
  dprintf(5)("      CountedRefBase/%08x default constructor\n",(int)this);
  empty();
  //## end CountedRefBase::CountedRefBase%3C0CDEE200FE_const.body
}

inline CountedRefBase::CountedRefBase (const CountedRefBase& other, int flags)
  //## begin CountedRefBase::CountedRefBase%3C0CE1C10277.hasinit preserve=no
  //## end CountedRefBase::CountedRefBase%3C0CE1C10277.hasinit
  //## begin CountedRefBase::CountedRefBase%3C0CE1C10277.initialization preserve=yes
  //## end CountedRefBase::CountedRefBase%3C0CE1C10277.initialization
{
  //## begin CountedRefBase::CountedRefBase%3C0CE1C10277.body preserve=yes
  empty();
  dprintf(5)("      CountedRefBase/%08x constructor: %08x,%d\n",(int)this,(int)&other,flags);
  if( !other.isValid() ) // construct empty ref
    return;
  else if( flags&DMI::PRIVATIZE ) // constructing ref to privatized target
    privatizeOther(other,flags);
  else if( flags&DMI::COPYREF ) // constructing true copy of reference
    copy(other,flags);
  else  // else do destructive copy
    xfer((CountedRefBase&)other);
  //## end CountedRefBase::CountedRefBase%3C0CE1C10277.body
}


inline CountedRefBase::~CountedRefBase()
{
  //## begin CountedRefBase::~CountedRefBase%3C0CDEE200FE_dest.body preserve=yes
  dprintf(5)("      CountedRefBase/%08x destructor\n",(int)this);
  if( isLocked() )
    unlock();
  detach();
  //## end CountedRefBase::~CountedRefBase%3C0CDEE200FE_dest.body
}


inline CountedRefBase & CountedRefBase::operator=(const CountedRefBase &right)
{
  //## begin CountedRefBase::operator=%3C0CDEE200FE_assign.body preserve=yes
  dprintf(5)("      CountedRefBase/%08x assignment: %08x\n",(int)this,(int)&right);
  xfer((CountedRefBase&)right);
  return *this;
  //## end CountedRefBase::operator=%3C0CDEE200FE_assign.body
}


inline Bool CountedRefBase::operator==(const CountedRefBase &right) const
{
  //## begin CountedRefBase::operator==%3C0CDEE200FE_eq.body preserve=yes
  return isValid() && target == right.target;
  //## end CountedRefBase::operator==%3C0CDEE200FE_eq.body
}

inline Bool CountedRefBase::operator!=(const CountedRefBase &right) const
{
  //## begin CountedRefBase::operator!=%3C0CDEE200FE_neq.body preserve=yes
  return !( (*this) == right );
  //## end CountedRefBase::operator!=%3C0CDEE200FE_neq.body
}



//## Other Operations (inline)
inline bool CountedRefBase::isValid () const
{
  //## begin CountedRefBase::isValid%3C0CDEE2015A.body preserve=yes
  return target != 0;
  //## end CountedRefBase::isValid%3C0CDEE2015A.body
}

inline const CountedRefTarget* CountedRefBase::getTarget () const
{
  //## begin CountedRefBase::getTarget%3C0CDEE2015B.body preserve=yes
  FailWhen( !isValid(),"dereferencing invalid ref");
  return target;
  //## end CountedRefBase::getTarget%3C0CDEE2015B.body
}

inline CountedRefTarget* CountedRefBase::getTargetWr ()
{
  //## begin CountedRefBase::getTargetWr%3C0CE2970094.body preserve=yes
  FailWhen( !isValid(),"dereferencing invalid ref");
  FailWhen( !isWritable(),"r/w access violation: non-const dereference");
  return target;
  //## end CountedRefBase::getTargetWr%3C0CE2970094.body
}

inline CountedRefBase CountedRefBase::copy (int flags) const
{
  //## begin CountedRefBase::copy%3C0CDEE20162.body preserve=yes
  return CountedRefBase(*this,flags|DMI::COPYREF);
  //## end CountedRefBase::copy%3C0CDEE20162.body
}

inline CountedRefBase& CountedRefBase::lock ()
{
  //## begin CountedRefBase::lock%3C187D92023F.body preserve=yes
  dprintf(3)("%s: locking\n",debug());
  locked=True;
  return *this;
  //## end CountedRefBase::lock%3C187D92023F.body
}

inline CountedRefBase& CountedRefBase::unlock ()
{
  //## begin CountedRefBase::unlock%3C187D9A022C.body preserve=yes
  dprintf(3)("%s: unlocking\n",debug());
  locked=False;
  return *this;
  //## end CountedRefBase::unlock%3C187D9A022C.body
}

inline CountedRefBase& CountedRefBase::attach (const CountedRefTarget* targ, int flags)
{
  //## begin CountedRefBase::attach%3C0CDEE20178.body preserve=yes
  // delegate to other version of attach, with READONLY flag set
  if( flags&DMI::READONLY )
    flags &= ~DMI::WRITE;
  else
    FailWhen(flags&DMI::WRITE,"can't attach writable ref to const object");
  return attach((CountedRefTarget*)targ,flags|DMI::READONLY);
  //## end CountedRefBase::attach%3C0CDEE20178.body
}

inline bool CountedRefBase::isWrite () const
{
  //## begin CountedRefBase::isWrite%3C19F62B0137.body preserve=yes
  return isWritable();
  //## end CountedRefBase::isWrite%3C19F62B0137.body
}

inline void CountedRefBase::empty ()
{
  //## begin CountedRefBase::empty%3C161C330291.body preserve=yes
  target=0; next=prev=0;
  locked=writable=exclusiveWrite=anonObject=False;
  //## end CountedRefBase::empty%3C161C330291.body
}

//## Get and Set Operations for Class Attributes (inline)

inline const bool CountedRefBase::isLocked () const
{
  //## begin CountedRefBase::isLocked%3C15DF4D036D.get preserve=no
  return locked;
  //## end CountedRefBase::isLocked%3C15DF4D036D.get
}

inline const bool CountedRefBase::isWritable () const
{
  //## begin CountedRefBase::isWritable%3C0CDEE20112.get preserve=no
  return writable;
  //## end CountedRefBase::isWritable%3C0CDEE20112.get
}

inline const bool CountedRefBase::isExclusiveWrite () const
{
  //## begin CountedRefBase::isExclusiveWrite%3C0CDEE20127.get preserve=no
  return exclusiveWrite;
  //## end CountedRefBase::isExclusiveWrite%3C0CDEE20127.get
}

inline const bool CountedRefBase::isAnonObject () const
{
  //## begin CountedRefBase::isAnonObject%3C0CDEE20130.get preserve=no
  return anonObject;
  //## end CountedRefBase::isAnonObject%3C0CDEE20130.get
}

//## Get and Set Operations for Associations (inline)

inline const CountedRefBase * CountedRefBase::getPrev () const
{
  //## begin CountedRefBase::getPrev%3C0CE0FA0394.get preserve=no
  return prev;
  //## end CountedRefBase::getPrev%3C0CE0FA0394.get
}

inline const CountedRefBase * CountedRefBase::getNext () const
{
  //## begin CountedRefBase::getNext%3C0CE0FB0010.get preserve=no
  return next;
  //## end CountedRefBase::getNext%3C0CE0FB0010.get
}

//## begin module%3C10CC81037C.epilog preserve=yes
inline CountedRefBase * CountedRefBase::getPrev ()
{
  return prev;
}
inline CountedRefBase * CountedRefBase::getNext ()
{
  return next;
}
//## end module%3C10CC81037C.epilog


#endif
