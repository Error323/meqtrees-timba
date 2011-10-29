#!/usr/bin/python
# -*- coding: utf-8 -*-

import traceback

if __name__ == '__main__':

  import Timba
  import Timba.utils
  import sys

  #
  # setup some standard command-line option parsing
  #
  from optparse import OptionParser
  parser = OptionParser(usage="""%prog: [options] <commands> ...

Runs TDL scripts in batch mode. <commands> are interpreted as follows:

    "[section]" or "@section"   load options from given section of config file

    "option=value"              set value of given option

    "scriptname.py"             compile TDL script. Config section [scriptname] will be loaded, unless
                                a [section] command has already been given.

    "scriptname.py[section]"    compile given TDL script (specified config section will be (re)loaded)
    or "scriptname.py@section"

    "=job":                   run specified TDL job (by name or job_id or method name)
""");
  parser.add_option("-c","--config",dest="config",type="string",
                    help="configuration file to use (default batch.tdlconf)");
  parser.add_option("--mt",dest="mt",type="int",
                    help="number of threads to run in meqserver (default 1)");
  parser.add_option("-d", "--debug",dest="debug",type="string",action="append",metavar="Context=Level",
                    help="(for debugging C++ code) sets debug level of the named C++ context. May be used multiple times.");
  parser.add_option("-v", "--verbose",dest="verbose",type="string",action="append",metavar="Context=Level",
                    help="(for debugging Python code) sets verbosity level of the named Python context. May be used multiple times.");
  parser.add_option("-t", "--trace",dest="trace",action="store_true",
                    help="(for debugging Python code) enables line tracing of Python statements");
  parser.set_defaults(mt=1,config="batch.tdlconf");

  (options, rem_args) = parser.parse_args();

  if not rem_args:
    parser.print_help();
    sys.exit(2);

  if options.trace:
    sys.settrace(trace_lines);

  for optstr in (options.debug or []):
    opt = optstr.split("=") + ['1'];
    context,level = opt[:2];
    debuglevels[context] = int(level);

  # tell verbosity class to not parse argv -- we do it ourselves here
  Timba.utils.verbosity.disable_argv();
  for optstr in (options.verbose or []):
    opt = optstr.split("=") + ['1'];
    context,level = opt[:2];
    Timba.utils.verbosity.set_verbosity_level(context,int(level));


  # start meqserver
  from Timba.Apps import meqserver
  from Timba.TDL import Compile
  from Timba.TDL import TDLOptions
  TDLOptions.enable_save_config(False);
  print "### Starting meqserver";
  mqs = meqserver.default_mqs(wait_init=10,extra=["-mt",str(options.mt)]);

  # use a try...finally block to exit meqserver cleanly at the end
  try:
    print "### Attaching to configuration file",options.config;
    TDLOptions.config.read(options.config);
    # disable the writing-out of configuration
    TDLOptions.config.set_save_filename(None);

    import re
    re_load_config    	= re.compile("^\[(.+)\]$");
    re_load_config1   	= re.compile("^@(.+)$");
    re_set_config     	= re.compile("^([^=]+)=(.*)$");
    re_compile_script 	= re.compile("^(.*\.py)(\[(.*)\])?$");
    re_compile_script1  = re.compile("^(.*\.py)(@(.*))?$");
    re_run_job        	= re.compile("^=(.*)$");

    loaded_options = False;
    module = None;

    # now parse commands
    for cmd in rem_args:

      load_match = re_load_config.match(cmd) or re_load_config1.match(cmd);
      set_match  = re_set_config.match(cmd);
      compile_match = re_compile_script.match(cmd) or re_compile_script1.match(cmd);
      job_match = re_run_job.match(cmd);

      if load_match:
        section = load_match.group(1);
        print "### Loading config section",section;
        TDLOptions.init_options(section,save=False);
        loaded_options = True;

      elif set_match:
        if not loaded_options:
          raise RuntimeError,"Config section not yet specified";
        name,value = set_match.groups();
        print "### Setting option %s=%s"%(name,value);
        TDLOptions.set_option(name,value,save=False,from_str=True);

      elif compile_match:
        script,dum,section = compile_match.groups(None);
        print "### Compiling",script;
        if not loaded_options and not section:
          # this mode reloads default config section
          print "### (using options from default section)";
          module,ns,msg = Compile.compile_file(mqs,script);
        else:
          # this mode uses explicit section, or None if section is not specified
          if section:
            print """### (using options from config section "%s")"""%section;
          else:
            section = None;
            print "### (using previously set options)";
          module,ns,msg = Compile.compile_file(mqs,script,config=section);
        print "### ",msg;

      elif job_match:
        if not module:
          print "### Error: please specify a script before any TDL jobs";
          raise RuntimeError,"TDL job specified before script";
        job = job_match.group(1);
        print "### Running TDL job \"%s\""%job;
        try:
          func = TDLOptions.get_job_func(job);
        except NameError:
          func = getattr(module,job,None);
          if not func:
            print "### Error: no job such job found. Perhaps it is not available with this option set?"
            print "### Currently available jobs are:""";
            for name,job_id in TDLOptions.get_all_jobs():
              print "### '%s' (id: %s)"%(name,job_id);
            raise NameError,"No such TDL job: '%s'"%job;
	try:
	  res = func(mqs,None,wait=True);
	  print "### Job result:",res;
	except:
	  print "### Job terminated with exception:"
	  traceback.print_exc();

    print "### No more commands";

  ### Cleanup time
  finally:
    if not mqs.current_server:
      print "### The meqserver appears to have died on us :( Please check for core files and such.";
    else:
      print "### Stopping the meqserver";
    # this halts the meqserver
    try:
      meqserver.stop_default_mqs();
    except:
      traceback.print_exc();
      print "### There was an error stopping the meqserver cleanly. Exiting anyway.";
      sys.exit(1);
    # now we can exit
    print "### All your batch are belong to us. Bye!";