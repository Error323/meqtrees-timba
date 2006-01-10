# JEN_inargGui.py:
#
# Author: J.E.Noordam
#
# Short description:
#    Gui for records of input arguments (see JEN_inarg.py)
#
# History:
#    - 05 jan 2006: creation (from MXM ArgBrowser.py)
#
# Full description:

#================================================================================
# Preamble
#================================================================================

import sys
from qt import *
from copy import deepcopy

from Timba.TDL import *

# The name of the control-record
CTRL_record = '_JEN_inarg_CTRL_record:'

# The name of an (optional) option field (e.g. see .modify())
option_field = '_JEN_inarg_option'



#================================================================================
#================================================================================

        

class ArgBrowser(QMainWindow):
    
    def __init__(self, *args):

        # NB: What is the usage of args (list): better to have **args?

        # We inherit from QMainWindow:
        apply(QMainWindow.__init__, (self,) + args)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        vbox = QVBoxLayout(self)
        combo = QComboBox(self)
        combo.setEditText('editText')
        vbox.addWidget(combo)

        # The listview displays the inarg record:
        self.__listview = QListView(self)
        # self.setCentralWidget(self.__listview)
        vbox.addWidget(self.__listview)
        self.__listview.addColumn("name")
        self.__listview.addColumn("value")
        self.__listview.addColumn("help")
        self.__listview.addColumn("ident")
        self.__listview.setRootIsDecorated(1)


        # Buttons to be added at the bottom:
        hbox = QHBoxLayout(self)
        vbox.addLayout(hbox)
        b_exec = QPushButton('Execute', self)
        hbox.addWidget(b_exec)
        b_cancel = QPushButton('Cancel', self)
        hbox.addWidget(b_cancel)
        QObject.connect(b_exec, SIGNAL("pressed ()"), self.exec_with_inarg)
        QObject.connect(b_cancel, SIGNAL("pressed ()"), self.cancel_exec)


        # Menus:
        # - save as (saves the edited inarg script)
        # - restore (load another inarg script)
        # - revert (revert to the input values, in self.__inarg)
        # - unhide (toggle, default=False, yellow if True)
        menubar = self.menuBar()
        filemenu = QPopupMenu(self)
        # filemenu.insertItem('save',,self,,SLOT(self.save))
        filemenu.insertItem('save', self.save_inarg)
        filemenu.insertItem('saveAs', self.saveAs_inarg)
        filemenu.insertItem('restore', self.restore_inarg)
        filemenu.insertItem('print', self.print_inarg)
        filemenu.insertItem('close', self.closeGui)
        menubar.insertItem('File', filemenu)
        editmenu = QPopupMenu(self)
        editmenu.insertItem('revert', self.revert_inarg)
        menubar.insertItem('Edit', editmenu)
        viewmenu = QPopupMenu(self)
        viewmenu.insertItem('unhide', self.unhide)
        menubar.insertItem('View', viewmenu)

        # Initialise:
        self.__inarg = None                        # edited copy
        self.__inarg_input = None                  # input copy
        self.__popup = None
        self.clearGui()
        return None

    def closeGui (self):
        """Close the gui"""
        self.clearGui()
        self.__listview.close()                    #............?
        if self.__popup: self.__popup.close()
        self.close()                             #............?
        # clean up any signal connections?
        return True


    def clearGui (self):
        """Clear the gui"""
        self.__listview.clear()
        if self.__popup: self.__popup.close()
        self.__itemdict = []                       # list of itd records
        self.__unhide = False                    # if True, hide nothing
        return True


#---------------------------------------------------------------------------

    def revert_inarg(self):
        """Revert to the original (input) inarg values"""
        self.__inarg = self.__inarg_input
        self.refresh()
        return True

    def unhide(self):
        """Hide the less important fields"""
        unhide = self.__unhide
        self.clearGui()
        self.__unhide = not unhide
        print '** unhide ->',self.__unhide
        self.refresh(clear=False)    
        return True

    def print_inarg(self):
        """Print the current inarg record"""
        print '** not yet implemented: self.print_inarg()'
        return True

    def saveAs_inarg(self):
        """Save the (edited) inarg record for later use"""
        print '** not yet implemented: self.saveAs()'
        return True

    def save_inarg(self):
        """Save the (edited) inarg record for later use"""
        print '** not yet implemented: self.save()'
        return True

    def restore_inarg(self):
        """Read in a stored inarg record"""
        print '** not yet implemented: self.restore()'
        # self.refresh()    
        return True

    #-------------------------------------------------------------------------------

    def cancel_exec(self):
        """Do nothing"""
        print '** not yet implemented: self.cancel()'
        self.closeGui()
        return False

    def exec_with_inarg(self):
        """Execute the relevant function"""
        print '** not yet implemented: self.execute()'
        return True


    #-------------------------------------------------------------------------------

    def input (self, inarg=None, name=None):
        """Input of a new (inarg) record in the gui"""
        if not isinstance(inarg, dict): return False
        self.clearGui()
        self.__inarg = deepcopy(inarg)                          # to be edited
        self.__inarg_input = deepcopy(self.__inarg)             # unchanged copy

        # Modify the name (of its main window):
        if not name:
            if self.__inarg.has_key('script_name'):             # MG_JEN script
                name = self.__inarg['script_name']
            else:
                name = self.__inarg.keys()[0]
        self.setCaption(name)

        # Transfer the inarg fields recursively:
        self.recurse (self.__inarg, listview=self.__listview)

        # Connect signals and slots, once a signal is detected the according slot is executed
        # QObject.connect(self.__listview, SIGNAL("doubleClicked (QListViewItem * )"), self.itemSelected)
        QObject.connect(self.__listview, SIGNAL("clicked (QListViewItem * )"), self.itemSelected)

        self.show()
        return True


    def refresh (self, clear=True):
        """Refresh the listview widget from self.__inarg"""
        print 'refresh()'
        if clear: self.clearGui()
        print 'refresh() after clearGui()'
        self.recurse (self.__inarg, listview=self.__listview)
        print 'refresh() after recurse()'
        return True

    def recurse (self, rr=None, listview=None, level=0, module='<module>'):
        """Recursive input of a hierarchical inarg record"""
        if not isinstance(rr, dict): return False

        # Every level of a hierarchical inarg record may have a CTRL_record:
        ctrl = None
        if rr.has_key(CTRL_record):                            # has a CTRL record
            ctrl = rr[CTRL_record]                             # use it

        for key in rr.keys():
            if isinstance(rr[key], dict):   
                if key==CTRL_record:                           # is a CTRL record         
                    itd = self.make_itd(key, rr[key], hide=True, module=module)    
                    if not itd['hide']:
                        item = QListViewItem(listview, key, 'CTRL_record')
                        self.recurse (rr[key], listview=item, level=level+1)
                else:
                    itd = self.make_itd(key, rr[key], ctrl=ctrl, module=key)    
                    if not itd['hide']:
                        item = QListViewItem(listview, key)
                        if level==0:
                            item.setOpen(True)                 # show its children
                        # item.setColor(itd['color'])          # <-----??            
                        self.recurse (rr[key], listview=item, level=level+1, module=key)

            else:                                              # rr[key] is a value
                itd = self.make_itd(key, rr[key], ctrl=ctrl, module=module)
                if not itd['hide']:
                    # value = QString(str(rr[key]))
                    value = str(itd['value'])                  # current value
                    ident = str(itd['ident'])                  # used by selectedItem()
                    help = ' '                                 # short explanation
                    if itd['help']:
                        help = str(itd['help'])
                        hh = help.split('\n')
                        if len(hh)>1: help = hh[0]+'...'       # first line only
                        hcmax = 40                             # max nr of chars
                        if len(help)>hcmax:
                            help = help[:hcmax]+'...'
                    item = QListViewItem(listview, key, value, help, ident)
                    # item.setColor(itd['color'])              # <-----??            

        return True


    #-------------------------------------------------------------------------------

    def make_itd(self, key, value, ctrl=None,
                 color='black', hide=False,
                 module='<module>',
                 save=True, level=0, trace=True):

        """Make an itd record from the given value and ctrl-record"""
        rr = dict(key=str(key),
                  value=value,                
                  type=None,                 # mandatory item type ...?
                  color=color,               # Display color  
                  hide=hide,                 # If True, hide this item
                  help=None,                 # help string
                  # help='help-string',
                  choice=None,               # list of choices
                  # choice=range(4),           # Choose from these values
                  range=None,                # list [min,max]
                  # range=[-1,1],              # Allowed range
                  min=None,                  # Allowed min value
                  max=None,                  # Allowed max value
                  tf=None,                   # If True, only True or False allowed 
                  editable=True,             # If True, the value may be edited
                  module=module,             # name of the relevant function module
                  level=level,               # inarg hierarchy level
                  ident=-1)                  # internal identifier

        # If ctrl is a record, use its information:
        if isinstance(ctrl, dict):
            # First some overall fields:
            overall = ['color']
            for field in overall:
                if ctrl.has_key(field):
                    rr[field] = ctrl[field]
            # Then the key-specific keys (see JEN_inarg.define()):
            key_specific = ['choice','tf',
                            'editable','hide','color',
                            'range','min','max','help']
            for field in key_specific:
                if ctrl.has_key(field):
                    if ctrl[field].has_key(key):
                        rr[field] = ctrl[field][key]

        # Override some fields, if required:
        if self.__unhide:                            # see self.unhide()
            rr['hide'] = False
        if rr['range']:
            if not isinstance(rr['range'], (tuple,list)):
                rr['range'] = 'error: '+str(type(rr['range']))
            elif not len(rr['range'])==2:
                rr['range'] = 'error: len ='+str(len(rr['range']))
            else:
                rr['min'] = rr['range'][0]
                rr['max'] = rr['range'][1]
        if not rr['choice']==None:
            if not isinstance(rr['choice'], (tuple,list)):
                rr['choice'] = [rr['choice']]
        if not rr['tf']==None:
            rr['choice'] = [True,False]
            rr['editable'] = False
            if not isinstance(rr['value'], bool):
                rr['value'] = rr['tf']                # ....!?
        if rr['help']:
            indent = (level*'.')
            rr['help'] = indent+str(rr['help'])

        # Keep the itemdict for later reference:
        if save:
            rr['ident'] = len(self.__itemdict)
            self.__itemdict.append(rr)
        if trace:
            print rr
        return rr

    #-------------------------------------------------------------------------------

    def itemSelected(self, item):
        """Deal with a selected listview item"""

        # If +/- clicked, the item is None:
        if not item: return False
        
        # Read the (string) values from the columns:
        key = item.text(0)            
        vstring = item.text(1)           
        help = item.text(2)              
        ident = item.text(3)          
        if self.__popup:
            self.__popup.close()

        # Use the ident string to get the relevant itemdict record:
        ident = str(ident)
        if ident==' ': ident = '0'
        try:
            ident = int(ident)
        except:
            # print sys.exc_info()
            return False
        if ident>0:
            itd = self.__itemdict[ident]
            self.__current_ident = ident
            # Make the popup object:
            self.__popup = Popup(self, name=itd['key'], itd=itd)
            QObject.connect(self.__popup, PYSIGNAL("valueChanged()"), self.valueChanged)
            # self.emit(PYSIGNAL("valueChanged()"),(v2,))
        return True


    def valueChanged(self, new):
        """Deal with a changed value from self.__popup"""
        ident = self.__current_ident
        print '\n** valueChanged() ->',type(new),'=',new,' (ident=',ident,')'
        # ...........
        return True


#----------------------------------------------------------------------------
# Popup for interaction with an argument value:
#----------------------------------------------------------------------------
        
class Popup(QDialog):
    def __init__(self, parent=None, name='popup_name', itd=None):
        QDialog.__init__(self, parent, "Test", 0, 0)

        # Keep the itemdict (itd) for use in self.textChanged():
        self.__itemdict = itd

        vbox = QVBoxLayout(self,10,5)           # ....?

        # The name (key) of the variable:
        label = QLabel(self)
        label.setText(str(itd['key']))
        vbox.addWidget(label)

        # Use a combobox for editing the vaue:
        self.combo = QComboBox(self)
        value = QString(str(itd['value']))
        self.combo.insertItem(value)            # current value
        self.combo_input_value = value          # see self.modified()
        self.combo.setEditable(itd['editable'])
        if itd['choice']:
            vv = itd['choice']
            for i in range(len(vv)):
                value = QString(str(vv[i]))
                self.combo.insertItem(value, i+1)
        vbox.addWidget(self.combo)
        QObject.connect(self.combo, SIGNAL("textChanged(const QString &)"), self.modified)
        QObject.connect(self.combo, SIGNAL("activated(const QString &)"), self.modified)

        # The value type is updated during editing:
        self.type = QLabel(self)
        self.type.setText('type'+':  '+str(type(itd['value'])))
        vbox.addWidget(self.type)

        # Other information (labels):
        keys = ['help']
        if itd['range']:
            keys.append('range')
        else:
            if itd['min']: keys.append('min')
            if itd['max']: keys.append('max')
        keys.append('module')
        for key in keys:
            if itd.has_key(key) and itd[key]:
                label = QLabel(self)
                label.setText(key+':  '+str(itd[key]))
                vbox.addWidget(label)

        # Status label:
        self.status = QLabel(self)
        self.status.setText(' ')
        vbox.addWidget(self.status)

        # Message label:
        self.message = QLabel(self)
        self.message.setText(' ')
        vbox.addWidget(self.message)

        # The close button:
        button = QPushButton('close',self)
        vbox.addWidget(button)
        QObject.connect(button, SIGNAL("pressed ()"), self.close)

        # Display the popup:
        self.show()
        return None

    #-------------------------------------------------------------------------

    def modified (self, value):
        """Deal with combo-box signals"""
        # print '\n** .modified(',value,'):',type(value)

        # Do nothing if the value has not changed:
        if value==self.combo_input_value:
            self.status.setText('...not modified...')
            return True

        # Deal with the modified value:
        self.status.setText('...modified...')
        v1 = str(value)                           # value is a QString object
        try:
            v2 = eval(v1)                         # covers most things
        except:
            v2 = v1                               # assume string
            # print sys.exc_info();
            # return;

        # print 'eval(',v1,') ->',type(v2),'=',v2
        self.type.setText('type'+':  '+str(type(v2)))

        # Update the itemdict(itd) from the ArgBrowser:
        itd = self.__itemdict
        itd['value'] = v2

        # Check the new value (range, min, max, type):
        ok = True
        if not ok:                                # problem....
            self.message.setText('...ERROR: ...')
            # Revert to the original value:
            self.combo.setCurrentText(self.combo_input_value)
            self.status.setText('...reverted...')
            return False

        # Return the modified itemdict(itd) to the ArgBrowser:
        self.emit(PYSIGNAL("valueChanged()"),(itd,))

        return True



#============================================================================
# Testing routine:
#============================================================================


if __name__=="__main__":
    from Timba.Trees import JEN_inarg
    # from Timba.Trees import JEN_record

    app = QApplication(sys.argv)
    igui = ArgBrowser()

    if 0:
        igui.test()

    if 1:
        qual = '<qual>'
        qual = None
        inarg = JEN_inarg.test1(_getdefaults=True, _qual=qual, trace=False)
        igui.input(inarg)
        # JEN_inarg.display(inarg, 'defaults', full=True)

    if 0:
        # Make a separate gui for the result:
        result = JEN_inarg.test1(_inarg=inarg, _qual=qual, bb='override', qq='ignored', nested=False)
        rgui = ArgBrowser()
        rgui.input(result)
        rgui.show()

    igui.show()
    app.connect(app, SIGNAL("lastWindowClosed()"),
                app, SLOT("quit()"))
    app.exec_loop()

