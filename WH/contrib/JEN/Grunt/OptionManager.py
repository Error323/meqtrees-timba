# file: ../Grunt/OptionManager.py

# History:
# - 24jul2007: creation

# Description:

"""The Grunt OptionManager class manages the options of a module,
i.e. the values of the parameters that rule its compile-time and
run-time behaviour. It makes use of Meow options (see ....), and
provides some extra functionality to make things easy for the user.
It also allows stand-alone use of the module, i.e. without creating
TDLOption objects. And finally, by storing the option variables in
a separate objects, name clashes with the module attributes are avoided. 

An empty OptionManager object is created and attached to a module by:
- self._OM = OptionManager(self.name, [namespace])

A named (key) option with some (default) value is then defined by
means of the function:
- self._OM.define(key1, value1)
- self._OM.define(key2, value2)
-   ...
The key defines the (sub)menu structure, e.g. 'compile.submenu.option',
or 'runtime.sub,subsub.opt' etc. If the first substring is neither
'compile' or 'runtime', 'compile' is assumed.
Is this way, the (sub)menu structure may be nested to any depth.

The attributes (value etc, see below) for an option are stored in a separate
'optrec' record in the OptionManager, and an internal variable with its default
value is created. The latter is identical to the 'working' value that
is created by an eventual TDLOption object. It is the one that should
be used by the module, which should ONLY(!) access it by:
- x = self._OM[key]

The retrieval key may be any (unique) substring of the full key above:
- x = self._OM['x'] will retrieve the value of the option that has been
defined with the full key 'compile.submenu.subsub.x' etc.

The attributes in the 'optrec' record(s) may be used to make a TDLMenu
of TDLOPtions in the meqbrowser by:
- self._OM.make_TDLCompileOptionMenu()
- self._OM.make_TDLRuntimeOptionMenu()

Each object that has an OptionManager, or has objects that have them,
should implement two functions with the above names, which call the
corresponding functions of their om objects to make suitable TDLMenus.
It should also implement its own .reset_options() callback function,
which calls the corresponding functions of all its om objects. In that
case, the lower TDLMenus should be generated with (reset=False).

It should be realised that, upon creation of the TDLOption objects, the
working values will be modified, from the default values specified by
.define() to the most recent values stored in the .tdlconf file (if any).
Of course they will also be modified whenever the user changes an option
value with its meqbrowser menu items. The OptionManager provides a way
to reset all working values (and thus the values in the .tdlconf file!)
into the original default values specified with .define(). This is done
with the function .reset_options(), which is called by an optional menu
item that is included in TDLMenu's generated by the OptionManager.

The attributes that may be defined with .define() are: 
  - prompt[=None]:       automatic if not supplied
  - opt[=None]:          list of alternative option values
  - more[=None]:         type of custom option allowed (float,int,str)
  - doc[=None]:          some extra explanations on this option 
  - callback[=None]:     function called whenever the option is changed


"""


#======================================================================================

#
#% $Id$ 
#
#
# Copyright (C) 2002-2007
# The MeqTree Foundation & 
# ASTRON (Netherlands Foundation for Research in Astronomy)
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>,
# or write to the Free Software Foundation, Inc., 
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from Timba.TDL import *
from Timba.Meq import meq

# from copy import deepcopy

#======================================================================================

class OptionManager (object):
    """The Grunt OptionManager class manages the options of a module"""

    def __init__(self, name='<parent>', namespace=None):

        self.name = name
        self.frameclass = 'Grunt.OptionManager'

        # This field is expected by OMS:
        self.tdloption_namespace = namespace

        # The hierarchical option tree:
        self.tree = dict()
        
        # Flat record with option definition records:
        self.optrec = dict()
        self.order = []

        # Flat record with TDLOption objects (if defined):
        self.option = dict()

        # Used to undo the last reset operation:
        self.undo_last_reset = dict()

        # Flat record with TDLMenu objects (if defined):
        self.menu = dict()
        self.menu_order = []
        self.menu_option_keys = dict()

        # Finished:
        return None


    #---------------------------------------------------------------

    def namespace(self, prepend=None, append=None):
        """Return the namespace string (used for TDL options etc).
        If either prepend or apendd strings are defined, attach them.
        NB: Move to the OptionManager class?
        """
        if prepend==None and append==None:
            return self.tdloption_namespace                    # just return the namespace
        # Include the namespace in a string:
        ss = ''
        if isinstance(prepend, str): ss = prepend+' '
        if self.tdloption_namespace:
            ss += '{'+str(self.tdloption_namespace)+'}'
        if isinstance(append, str): ss += ' '+append
        return ss
    

    #-----------------------------------------------------------------------------

    def __getitem__ (self, key):
        """Get the current 'working' value of the specified option (key).
        This should be the ONLY way in which an option value is obtained
        from the OptionManager. This makes sure that the module can also be
        used standalone, i.e. without any TDLOptions/menus.
        """
        fkey = self.findkey (key, keys=self.optrec.keys(), trace=False)
        ukey = self.internal_name(fkey)
        if True:
            # Make sure that the internal value is equal to the current value
            # of the TDLOption.value (if it exists).
            # For some reason, this does not happen automatically when the
            # option value is modified by the user (it used too...).
            if self.option[fkey]:
                setattr(self, ukey, self.option[fkey].value)
        return getattr(self, ukey)

    #-------------------------------------------------------------------------

    def internal_name (self, key):
        """Helper function to make the internal option name from the given key.
        The name of the internal variable is prepended with '_': self._<key>
        This is to avoid name clashes with any object attributes."""
        return '_'+key


    #===============================================================
    # Display of the contents of this object:
    #===============================================================

    def oneliner(self):
        """Return a one-line summary of this object"""
        ss = self.frameclass+':'
        ss += '  name='+str(self.name)
        ss += '  namespace='+str(self.tdloption_namespace)
        nc = len(self.findkey('compile.', self.order, one=False))
        nr = len(self.findkey('runtime.', self.order, one=False))
        ss += '  (nc='+str(nc)+', nr='+str(nr)+')'
        return ss


    def display(self, txt=None, full=False, level=0):
        """Print a summary of this object"""
        prefix = '  '+(level*'  ')+'OM'
        if level==0: print
        print prefix,' '
        print prefix,'** '+self.oneliner()
        if txt: print prefix,'  * (txt='+str(txt)+')'
        #...............................................................
        if full:
            print prefix,'  * option definition(s) ('+str(len(self.order))+'): '
            for key in self.order:
                print prefix,'    - '+key+': '+str(self.optrec[key])
        #...............................................................
        print prefix,'  * TDLMenu object(s) ('+str(len(self.menu_order))+'): '
        for key in self.menu_order:
            if full or self.menu[key]:
                print prefix,'    - '+key+': '+str(self.menu[key])
            print prefix,'    - '+key+': '+str(self.menu_option_keys[key])
        #...............................................................
        if full:
            keys = self.option.keys()
            print prefix,'  * TDLOption object(s) ('+str(len(keys))+'): '
            for key in keys:
                if full or self.option[key]:
                    print prefix,'    - '+key+': '+str(self.option[key])
        #...............................................................
        keys = self.undo_last_reset.keys()
        print prefix,'  * undo_last_reset ('+str(len(keys))+'): '
        #...............................................................
        print prefix,'  * option values ('+str(len(self.order))+'): '
        for key in self.order:
            rr = self.optrec[key]
            value = self[key]
            ss = '(-) '
            if self.option[key]:
                ss = '(+) '
            ss += key+' = '+str(value)
            if not value==rr['default']:
                ss += '     (default value = '+str(rr['default'])+')' 
            if self.option[key]:
                TDLvalue = self.option[key].value
                if not value==TDLvalue:
                    ss += '    (option.value='+str(TDLvalue)+'!)'
            if self.undo_last_reset.has_key(key):
                undo = self.undo_last_reset[key]
                if not value==undo:
                    ss += '    (undo_last_reset='+str(undo)+'!)'
            print prefix,'    - '+ss
        #...............................................................
        print prefix,'**'
        if level==0: print
        return True


    #-----------------------------------------------------------------------------

    def showtree (self, rr=None, key=None, full=False, level=0):
        """Show self.tree"""
        prefix = (level*'..')
        if rr==None:
            rr = self.tree
            print '\n** showtree(',key,'):'
        if isinstance(rr,dict):                  # a menu entry
            print prefix,key,': menukey =',rr['_menukey_']
            for key in rr['_order_']:
                self.showtree (rr[key], key=key, level=level+1)
        else:                                    # an option entry 
            print prefix,key,': ',rr
        if level==0:
            print '\n'
        return


    #-------------------------------------------------------------------------------    

    def define (self, key, value, order=None,
                prompt=None, opt=None, more=None, doc=None,
                callback=None, trace=False):
        """Helper function to define a named (key) option with its (default) value.
        The key defines the (sub)menu structure, e.g. 'compile.submenu.subsub.option'
        (if the first substring is not 'compile' or 'runtime', 'compile' is assumed).
        Som (optional) attributes may be defined that will be used for the creation
        of TDLMenus of TDLOpion objects in a later stage.
        """

        # Split the key string on submenu dots (if any):
        ss = key.split('.')
        if not ss[0] in ['compile','runtime']:
            key = 'compile.'+key
            ss = key.split('.')

        # A submenu of options may be specified by a dict:    
        if isinstance(value, dict):
            keys = value.keys()
            # It is recommended to impose an order on the submenu options:
            if isinstance(order,list): keys = order          # optional, but recommended
            for key1 in keys:
                self.define(key+'.'+key1, value[key1])
        
        else:
            ukey = self.internal_name(key)
            setattr (self, ukey, value)                      # working values
            if not isinstance(prompt,str):
                ss = key.split('.')
                prompt = ss[len(ss)-1]                       # the last substring
            optrec = dict(type='optrec', optobj=None,
                          key=key, ukey=ukey, 
                          default=value, doc=doc, prompt=prompt,
                          opt=opt, more=more, callback=callback)
            self.create(key, optrec, trace=True)
            if trace:
                print '  ** define(',key,ukey,value,submenu,cat,')'
        return True

    #-----------------------------------------------------------------------------

    def modify (self, key, **pp):
        """Helper function to modify field(s) of an existing (key) optrec,
        which has been defined earlier with .define(key, ...)."""

        fkey = self.findkey(key, self.order)
        optrec = self.optrec[fkey]
        if self.option[fkey]:
            s = '** .modify('+fkey+'): only possible BEFORE creating a TDLOption object'
            raise ValueError,s

        if not isinstance(pp, dict): pp = dict()
        pp.setdefault('trace',False)
        keys = ['value','opt','more','prompt','doc','callback']
        for key in keys:
            if pp.has_key(key):
                if key=='value':
                    optrec['default'] = pp[key]
                    ukey = self.internal_name(fkey)
                    setattr (self, ukey, pp[key])    # modify the working value too
                else:
                    optrec[key] = pp[key]
        return True

    #-----------------------------------------------------------------------------

    def create (self, key, optrec=None, rr=None,
                menukey=None, optkey=None, 
                level=0, trace=False):
        """Recursive helper function to create an entry in the hierarchical
        self.tree record, specified by the key-string (e.g. 'compile.sub1.xx').
        The optree entries (menus and options) point to fields in flat records
        like self.optrec (which contains the option definition records),
        self.menu and self.option. The latter will contain TDLMenu/TDLOption
        objects after they have been created (optionally).
        """
        trace = False
        if trace:
            prefix = '--'+(level*'..')
            if level==0: print '\n** create(',key,type(optrec),'):'
        if not isinstance(rr, dict):
            rr = self.tree
        ss = key.split('.')
        if level==0:
            menukey = ss[0]
            optkey = key
        if trace:
            print prefix,' ss =',ss

        if len(ss)>1:                                    # recursive
            remainder = key[1+key.index('.'):]           # key withoy ss[0]+'.'
            if level>0: menukey += '.'+ss[0]
            if not rr.has_key(ss[0]):
                # OK, create a new menu entry:
                if self.menu.has_key(menukey):
                    s = '** create('+str(menukey)+'): menu already exists'
                    raise ValueError,s
                self.menu[menukey] = None
                self.menu_order.append(menukey)
                self.menu_option_keys[menukey] = []
                rr.setdefault('_menukey_',None)          # just in case
                rr.setdefault('_order_',[])              # just in case
                rr['_order_'].append(ss[0])              # update the submenu order
                rr[ss[0]] = dict()
                rr[ss[0]]['_order_'] = []                # order of creation 
                rr[ss[0]]['_menukey_'] = menukey         # points into self.menu 
            return self.create(remainder, optrec=optrec, rr=rr[ss[0]], 
                               menukey=menukey, optkey=optkey,
                               level=level+1, trace=trace)

        elif rr.has_key(ss[0]):                          # problem
            s = '** create('+str(optkey)+'): entry already exists: '+str(rr.keys())
            raise ValueError,s

        # OK, create the new option entry:
        if self.option.has_key(optkey):
            s = '** create('+str(optkey)+'): option already exists'
            raise ValueError,s
        self.option[optkey] = None
        self.optrec[optkey] = optrec                     # flat record of optrecs
        self.order.append(optkey)                        # order of optrec entries
        self.menu_option_keys[menukey].append(optkey)
        rr[ss[0]] = optkey
        rr.setdefault('_order_',[])                      # just in case
        rr['_order_'].append(ss[0])                      # update the submenu order
        if trace:
            print prefix,' ->',rr[ss[0]]
        return rr[ss[0]]



    #===================================================================
    # Access to, and operations on, TDLMenu and TDLOption objects:
    #===================================================================


    def TDLMenu (self, key='compile', severe=False, trace=False):
        """Return the specified (key) TDL(sub)menu object (or None).
        If the specified menu is not found, return False.
        But if severe==True, raise an error and stop.
        """
        s = '** TDLMenu('+str(key)+'): '
        key = self.findkey(key, self.menu_order)
        menu = self.menu[key]
        if trace:
            print s,'->',str(menu)
        if menu:                        # TDLMenu object is defined
            return menu
        elif severe:                    # not defined, error if severe==True
            s += 'not defined'
            print s
            raise ValueError,s
        return menu                     # return menu=None


    #---------------------------------------------------------------------

    def TDLOption (self, key=None, severe=False, trace=False):
        """Return the specified (key) TDL option object if it exists,
        otherwise return None (if severe==False) or raise an error.
        """
        s = '** TDLOption('+str(key)+'):'
        key = self.findkey(key, self.order)
        option = self.option[key]
        if trace:
            print s,'->',str(option)
        if option:                       # TDLOption object is defined
            return option
        elif severe:                     # not defined, error if severe==True
            s += 'not defined'
            print s
            raise ValueError,s
        return option                    # return option=None

        
    #---------------------------------------------------------------------

    def TDLOption_objects(self, substring,
                          menus=True, options=True, trace=False):
        """Return a list of all (existing) TDLObjects (menus and options)
        whose keys contain the given substring
        """
        trace = True
        if trace:
            print '** TDLOption_objects(',substring,menus,options,'): ',
        oolist = []
        if menus:
            keys = self.findkey(substring, self.menu_order, one=False)
            for key in keys:
                if self.menu[key]:
                    oolist.append(self.menu[key])
        if options:
            keys = self.findkey(substring, self.order, one=False)
            for key in keys:
                if self.option[key]:
                    oolist.append(self.option[key])
        if trace:
            print '->',len(oolist),':',oolist
        return oolist

    #----------------------------------------------------------------------

    def show(self, key=None, show=True):
        """Show/hide the specified (key) menu/option."""
        return self.hide(key=key, hide=(not show))


    def hide(self, key=None, hide=True):
        """Hide/unhide the specified menu/option."""
        if isinstance(key,bool):
            hide = key
            key = None
        oolist = self.TDLOption_objects(key, menus=True,
                                        options=True, trace=False)
        for oo in oolist:
            oo.hide(hide)
        return True
        
    #---------------------------------------------------------------------

    def enable(self, key=None, enable=True):
        """Enable/disable the specified (key) menu/option."""
        return self.disable (key=key, disable=(not enable))

    def disable(self, key=None, disable=True):
        """Disable/enable the specified menu/option."""
        if isinstance(key,bool):
            disable = key
            key = None
        oolist = self.TDLOption_objects(key, menus=True,
                                        options=True, trace=False)
        for oo in oolist:
            oo.disable(disable)
        return True
        
    #---------------------------------------------------------------------

    def set_value (self, key, value, trace=False):
        """Helper function to change the value of the specified (key) option."""
        option = self.TDLOption(key, severe=True, trace=trace)
        if not option: return False
        option.set_value(value)
        return True

    #---------------------------------------------------------------------

    def set_option_list (self, key, olist,
                         select=None, conserve_selection=True,
                         trace=False):
        """Helper function to change the option list of the specified (key) option."""
        option = self.TDLOption(key, severe=True, trace=trace)
        if not option: return False
        option.set_option_list(olist, select=select,
                               conserve_selection=conserve_selection)
        return True




    #=================================================================
    # Make TDL menu(s):
    #=================================================================

    def make_TDLCompileOptionMenu (self, insert=None,
                                   include_reset_option=True,
                                   trace=False):
        """Return the TDLMenu of compile-time options. Create it if necessary.
        NB: Every module that has an OptionManager, or has objects that have one,
        should implement a function with this name.
        This function is usually called before _define_forest().
        """
        cat = 'compile'
        if not self.tree.has_key(cat):            # No options specified 
            return None                           # do nothing...?
        return self.make_TDLOptionMenu (self.tree[cat], insert=insert,
                                        include_reset_option=include_reset_option,
                                        cat=cat, trace=trace)

    #----------------------------------------------------------------------------

    def make_TDLRuntimeOptionMenu (self, insert=None, trace=False):
        """Return the TDLMenu of run-time options. Create it if necessary.
        NB: Every module that has an OptionManager, or has objects that have one,
        should implement a function with this name.
        This function is usually called at the end of _define_forest().
        """
        cat = 'runtime' 
        if not self.tree.has_key(cat):            # No options specified 
            return None                           # do nothing...?
        return self.make_TDLOptionMenu (self.tree[cat], insert=insert,
                                        cat=cat, trace=trace)


    #-----------------------------------------------------------------

    def make_TDLOptionMenu (self, rr, key=None, insert=None,
                            level=0, cat='compile',
                            include_reset_option=False,
                            trace=False):
        """Recursive function that does the work for .make_TDLCompile/RuntimeMenu().
        """

        # Avoid duplication:
        if self.menu[cat]:                        # The TDLMenu already exists
            return self.menu[cat]                 # just return it

        # An option entry is a string (key into self.optrec):
        if not isinstance(rr, dict):
            optkey = rr
            optrec = self.optrec[optkey]
            opt = [self[optkey]]                  # current working value
            if isinstance(optrec['opt'],list):
                opt.extend(optrec['opt'])
            oo = TDLOption(key, optrec['prompt'], opt,
                           more=optrec['more'],
                           doc=optrec['doc'],
                           namespace=self)
            oo.when_changed(self._callback_submenu)
            if optrec['callback']:
                oo.when_changed(optrec['callback'])
            self.option[optkey] = oo
            return oo


        # A (sub)menu definition is a record:
        else:
            oolist = []
            for key in rr['_order_']:
                # recursive
                oo = self.make_TDLOptionMenu (rr[key], key=key, cat=cat, level=level+1)
                oolist.append(oo)
                
            # Optional: insert a list of given TDLOption objects:
            if isinstance(insert, list):
                oolist.extend(insert)

            # Optional (but last): Include a 'reset' option (if required):
            # NB: This seems ONLY useful at compile-time. (But in its present
            #     implementation it ALSO resets the runtime option values.....)
            if cat=='compile':
                if include_reset_option:
                    oolist.append(self.make_reset_option())

            # OK, make the TDLMenu:
            menukey = rr['_menukey_']
            if level==0:
                prepend = ' options for: '
                prompt = self.namespace(prepend=prepend, append=self.name)
            else:
                ss = menukey.split('.')
                # prompt = 'submenu: '+ss[len(ss)-1]
                prompt = '... '+ss[len(ss)-1]
            if len(oolist)==0:
                return None
            elif cat=='runtime':
                om = TDLRuntimeMenu(prompt, *oolist)
            else:
                om = TDLCompileMenu(prompt, *oolist)

            # Update the entry in self.menu:
            self.menu[menukey] = om

            # Return the menu object to the user:
            return om


    #.....................................................................

    def _callback_submenu(self, dummy=None):
        """Function called whenever any TDLOption in a submenu changes.
        It just remakes the summary string of all submenu headers."""
        for menukey in self.menu_order:
            if self.menu[menukey] and not menukey in ['compile','runtime']:
                summ = '... ('
                first = True
                for key in self.menu_option_keys[menukey]:
                    if self.option[key]:
                        value = self.option[key].value
                        if True:
                            ukey = self.internal_name(key)
                            setattr(self, ukey, value)
                        if not first: summ += ','
                        first = False
                        if value==None:
                            summ += '-' 
                        elif isinstance(value,str):
                            if len(value)<5:
                                summ += value
                            else:
                                summ += 'str'
                        else:
                            summ += str(value)
                summ += ')'
                # if not first:                            # ignore if empty
                self.menu[menukey].set_summary(summ)
        return True


        
    #---------------------------------------------------------------------
    # Functions dealing with resetting the option values:
    #---------------------------------------------------------------------

    def make_reset_option (self, hide=False):
        """Make the 'reset' option, that allows reset of ALL options to the
        original values that were given by .define() or .modify()"""
        self.key_of_reset_option = '_reset_all_options'
        key = self.key_of_reset_option
        if not self.option.has_key(key):
            doc = """If True, reset all options to their original default values.
            (presumably these are sensible values, supplied by the module designer.)
            If undo, restore the option values BEFORE the last reset operation
            """
            prompt = self.name+':  reset to defaults (!)'
            oo = TDLOption(key, prompt, [False, True, 'undo'], doc=doc, namespace=self)
            oo.when_changed(self._callback_reset)
            if hide: oo.hide()
            self.option[key] = oo          # NB: Do NOT update order....
        return self.option[key]


    #.....................................................................

    def _callback_reset(self, reset):
        """Function called whenever the 'reset' menuitem changes."""
        if reset==True:
            self.reset_options(trace=True)
        elif reset=='undo':
            self.reset_options(undo=True, trace=True)
        else:
            return True
        key = self.key_of_reset_option     # defined in .make_reset_option()
        # Set the value of the 'reset' option back to False: 
        self.option[key].set_value(False, callback=False, save=True)
        return True


    #.....................................................................

    def reset_options(self, undo=False, trace=False):
        """Helper function to reset the TDLOptions and their local
        'working' counterparts to the original default values.
        If undo==True, undo the last reset operation.
        """
        if trace:
            print '\n** reset_options(undo=',undo,'): ',self.oneliner()

        # Reset all options that have a regular optrec
        # (i.e. NOT the 'reset' option itself (see .make_reset_option())
        for key in self.order:
            ss = key.split('.')
            if ss[0] in ['compile','runtime']:
            # if ss[0] in ['compile']:                 # .....?
                ukey = self.internal_name(key)
                was = getattr(self,ukey)
                if not undo:
                    new = self.optrec[key]['default']
                elif self.undo_last_reset.has_key(key):
                    new = self.undo_last_reset[key]
                else:
                    break                              # undo not possible
                setattr(self, ukey, new)
                if self.option.has_key(key):
                    self.option[key].set_value(new, save=True)
                    now = self.option[key].value
                    self.undo_last_reset[key] = was    # see .undo_reset()
                if trace:
                    print ' - () '+key+':  -> '+str(now),
                    if not new==was: print '     (changed: was ',was,')',
                    print
        if trace: print
        return True
        


    #-----------------------------------------------------------------------------
    # Helper functions:
    #-----------------------------------------------------------------------------

    def find_menu_key (self, substring, one=True, trace=False):
        """Convenience version of .findkey() for menus only"""
        return self.findkey (substring, keys=self.menu_order,
                             one=one, trace=trace)

    def find_option_key (self, substring, one=True, trace=False):
        """Convenience version of .findkey() for options only"""
        return self.findkey (substring, keys=self.order,
                             one=one, trace=trace)


    def findkey (self, substring, keys=[], one=True, trace=False):
        """Helper function to find the key(s) that contain the specified (sub)string
        in the given list. If one==True, insist on one hit, and return this key.
        If one==False, return a list of all the keys that contain the substring.
        """
        s1 = '** .findkey('+str(substring)+','+str(len(keys))+'): '
        if trace:
            print s1,
        found = []
        if substring in keys:  
            found = [substring]
            if trace:
                print 'found'
        else:
            for key in keys:
                if substring in key:
                    found.append(key)
            if trace:
                print 'found =',found

        # Deal with the result:
        if not one:
            return found
        elif len(found)==0:
            s = s1+'none found in:'
            print s,keys
            raise ValueError, s
        elif len(found)>1:
            s = s1+'found more than one: '+str(found)
            print s
            raise ValueError, s

        # len(found)==1: Return the one (string) key:
        return found[0]
    


    #=====================================================================
    # Test-routine(s)
    #=====================================================================

    def test(self):
        """..."""
        # Deal with the (TDL) options in an organised way:
        # The various solver constraint options are passed by dict():
        constraint = dict()
        order = []
        if True:
            # Make sure that some constraint options are always there:
            constraint.setdefault('min', None)
            constraint.setdefault('max', None)
            order = ['min','max']
        if True:
            # Temporary: add some constraint options for testing
            constraint.setdefault('sum', 0.1)
            constraint.setdefault('product', -1.1)
            constraint.setdefault('ignore', 0)
            order.extend(['sum','product','ignore'])
        self.define('compile.mode', 'solve',
                    opt=['nosolve','solve','simulate'], more=str,
                    doc='The rain in Spain....', callback=self._callback_mode)
        self.define('default', 12.9, more=float)
        self.define('simuldev', 'expr', more=str)
        self.define('compile.span.tiling', None, opt=[1,2,4,8], more=int)
        self.define('compile.span.time_deg', 1, more=int)
        self.define('compile.xxx.span.freq_deg', 2, more=int)
        self.define('compile.constraint', constraint, order=order)
        return True

        
    def _callback_mode (self, mode):
        print '** callback_mode(',mode,')'
        return True



#=============================================================================
#=============================================================================
#=============================================================================
# Test routine (with meqbrowser):
#=============================================================================

if 0:
    om = OptionManager()
    om.test()
    om.make_TDLCompileOptionMenu()


def _define_forest(ns):

    cc = []

    om.define('runtime.copy_of_default', om['default'])

    om.display('final', full=True)

    if len(cc)==0: cc.append(ns.dummy<<1.1)
    ns.result << Meq.Composer(children=cc)
    om.make_TDLRuntimeOptionMenu()
    return True



#---------------------------------------------------------------

def _tdl_job_2D_tf (mqs, parent):
    """Execute the forest with a 2D request (freq,time), starting at the named node"""
    domain = meq.domain(1.0e8,1.1e8,0,2000)                            # (f1,f2,t1,t2)
    cells = meq.cells(domain, num_freq=10, num_time=100)
    request = meq.request(cells, rqtype='ev')
    result = mqs.meq('Node.Execute',record(name='result', request=request))
    return result
       

def _tdl_job_display (mqs, parent):
    om.display('tdl_job', full=False)

def _tdl_job_display_full (mqs, parent):
    om.display('tdl_job', full=True)








#===============================================================
# Test routine:
#===============================================================

if __name__ == '__main__':
    ns = NodeScope()


    if 1:
        om = OptionManager(name='test')

    if 1:
        om.display('initial')
        om.test()
        om.showtree()
        # om.display('test', full=True)

    if 0:
        for key in ['compile.default']:
            print key,'=',om[key]
            print om.TDLOption(key, trace=True)
            print om.TDLMenu(key, trace=True)

    if 1:
        om.make_TDLCompileOptionMenu()

    if 1:
        om.display('final')

    #---------------------------------------------------------------

    if 0:
        # rr = dict(aa=dict(cc=dict(orig=True)), bb=dict())
        rr = dict()
        om.create('aa', 56, rr=rr, trace=True)
        om.create('aa.cc', rr=rr, trace=True)
        om.create('aa.cc.dd', rr=rr, trace=True)
        om.create('aa.gg.cc.ee', dict(new=True), rr=rr, trace=True)
        om.create('aa.cc.ee', rr=rr, trace=True)

    if 0:
        keys = ['aa.bb','aa.cc','bb.dd.ee']
        om.findkey ('aa.bb', keys=keys, trace=True)
        om.findkey ('.bb', keys=keys, trace=True)
        om.findkey ('bb', keys=keys, trace=True)



#===============================================================

