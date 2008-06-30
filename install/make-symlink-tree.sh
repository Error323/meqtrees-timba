#!/bin/bash

makedir()
{
  if [ -d $1 ]; then
    echo "$1 exists"
  else
    echo -n "Creating $1... "
    if ! mkdir $1; then
      exit 1;
    fi
    echo "OK"
  fi
}

ln-s()
{
  if [ "$2" == "" ]; then
    fn=${1##*/}
  else
    fn=$2
  fi
  if [ -h $fn ]; then
    echo "$fn exists"
  else
    echo -n "Creating $fn... "
    if ! ln -s $1 $fn; then
      exit 1;
    fi
    echo "OK"
  fi
}


if [ "$1" == "" ]; then
  cat <<END
  $0: creates a tree of symlinks for Timba.
  Usage:
    $0 build_flavour
  will create a tree called symlinked-build_flavour.
END
  exit 1
fi

flavour=${1#symlinked-}

makedir symlinked-$flavour 
cd symlinked-$flavour
makedir bin
makedir lib
makedir libexec

cd bin
ln-s ../../../TimBase/src/gprof-run
ln-s ../../../PyApps/src/meqbrowser.py
ln-s ../../../MeqServer/build/$flavour/src/.libs/meqserver
ln-s ../../../PyApps/src/tdlrun.py
ln-s ../../../PyApps/src/trut
ln-s ../../../PyApps/src/trutify
ln-s ../../../PyApps/src/trut.py

if [ -f meqserver-mpi ]; then
  echo "meqserver-mpi exists";
else
  cat <<END >meqserver-mpi
#!/bin/bash
source \$HOME/Timba/install/timba-init.sh
_timba-setup symlinked-$flavour
meqserver \$*
END
  chmod 755 meqserver-mpi
fi

cd ../lib
for libname in `find ../../../ -name "*so" -o -name "*.so.*" | grep $flavour`; do
  ln-s $libname
done

cd ../libexec
ln-s ../../../TimBase/build/$flavour/src/gprof-helper.so
makedir python
cd python
ln-s ../../../../WH/contrib/OMS/Meow
ln-s ../../../../PyApps/src/meqbrowser.py
makedir Timba
cd Timba
ln-s ../../../../../PyApps/src/Apps
ln-s ../../../../../WH/contrib Contrib
ln-s ../../../../../OCTOPython/src/dmi.py
ln-s ../../../../../OCTOPython/src/dmi_repr.py
ln-s ../../../../../PyApps/src/Grid
ln-s ../../../../../PyApps/src/GUI
ln-s ../../../../../OCTOPython/src/__init__.py
ln-s ../../../../../LSM/src/LSM
ln-s ../../../../../PyApps/src/Meq
ln-s ../../../../../MeqServer/src/meqkernel.py
ln-s ../../../../../PyApps/build/$flavour/src/.libs/mequtils.so
ln-s ../../../../../PyApps/build/$flavour/src/.libs/mequtils.so.0
ln-s ../../../../../PyApps/build/$flavour/src/.libs/mequtils.so.0.0.0
ln-s ../../../../../OCTOPython/src/octopussy.py
ln-s ../../../../../OCTOPython/build/$flavour/src/.libs/liboctopython.so octopython.so
ln-s ../../../../../OCTOPython/build/$flavour/src/.libs/liboctopython.so.0 octopython.so.0
ln-s ../../../../../OCTOPython/build/$flavour/src/.libs/liboctopython.so.0.0.0 octopython.so.0.0.0
ln-s ../../../../../PyParmDB/src/ParmDB.py
ln-s ../../../../../PyApps/build/$flavour/src/.libs/parmtables.so
ln-s ../../../../../PyApps/build/$flavour/src/.libs/parmtables.so.0
ln-s ../../../../../PyApps/build/$flavour/src/.libs/parmtables.so.0.0.0
ln-s ../../../../../PyApps/src/Plugins
ln-s ../../../../../PyApps/src/pretty_print.py
ln-s ../../../../../MeqServer/src/pynode.py
ln-s ../../../../../PyParmDB/build/$flavour/src/.libs/pyparmdb.so
ln-s ../../../../../PyParmDB/build/$flavour/src/.libs/pyparmdb.so.0
ln-s ../../../../../PyParmDB/build/$flavour/src/.libs/pyparmdb.so.0.0.0
ln-s ../../../../../OCTOPython/src/qt_threading.py
ln-s ../../../../../PyApps/src/TDL
ln-s ../../../../../PyApps/src/Trees
ln-s ../../../../../PyApps/src/Trut
ln-s ../../../../../OCTOPython/src/utils.py