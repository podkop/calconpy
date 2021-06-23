#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALculations CONtrol
====================
"""
import sys
import os
import json

# Constants
dflt_r_params_fname = "_init_routines"
"""Default name of `.json` file listing routines` parameters"""
dflt_step_name = "Main"
"""Default step name if the sequence consists of a single step"""
step_prefix = "$"
"""Prepended to a step name when it serves as a config. parameter name"""
pname_seq = "_sequence"
"""Name of the parameter defining the calculations sequence"""
pname_invar = "_invariant"
"""Name of parameter defining invariant-caching parameters"""
iname_cached = "_cached"
"""Name of init. parameter defining which routines are cached"""
iname_not_cached = "_noncached"
"""Name of init. parameter defining which routines are NOT cached"""

def _str_key(arg):
    """
    Given arg as `str` or `dict`, returns arg or its 1st key 
    """
    if isinstance(arg,str):
        return arg
    return next(iter(arg))

def _list_val(arg):
    """
    Given arg as `str` or `dict`, returns [] or the value for the 1st key 
    """
    if isinstance(arg,str):
        return []
    return next(iter(arg.values()))

# def _remove_ls_pref(l,pref="_"):
#     """
#     Given a list of strings, returns the list without strings starting with "_"
#     """
#     return [si for si in l if not si.startswith(pref)]
    
def _fn_normalize(fname,folder,ext):
    """
    Given file name, folder and extension, 
    makes file name relative to the folder if possible, and
    adds the extension if there is no one
    """
    if os.path.splitext(fname)[1]:
        ext = ""
    elif ext and ext[0]!=".":
        ext = "."+ext
    return os.path.join(folder,fname)+ext

def force_list(arg):
    """
    If the argument is not a list, wraps it in the list.
    """
    if isinstance(arg,list):
        return arg
    return [arg]

class calcon:
    """
    The main object controlling all calculations for a project.
    The routines that can be used for calculations are set at
    the initiaization. After that the object enables repeating
    calculations with different configurations of routines.
    Args:
    -----
        calc_folder: str
            Name of the folder for storing [intermediate] results and 
            configuration file[s] for the project
        routines_params: dict or str, optional
            * dict: for each routine that can be used in calculations, 
              <routine name>: list of parameters names influencing the routine
              "_cached": list of cached routines or 
              "_noncached": list of non-cached routines (by default, all are cached)
            * str: name of `json` file containing the above dict, optionally
              containing path relative to `calc_folder` or absolute
                  * if the extension is missing, it is set to `.json`
                  * by default, `routines_params` are taken from 
                    `<calc_folder>/<dflt_r_params_fname>`
            * list of str: list of routines' names            
        routines_package: str, optional
            Provide <package> name, if each <routine> is implemented as the
            <package>.<routine> module, i.e. routine's methods are 
            module's functions with standard names
                * if `routines_package`="", then routines modules are plain
                * all used modules should be imported beforehand
        routines_module: str, optional
            Provide <module> name, if each <routine> is implemented as
            <routine> class of the <module>, i.e. routine's methods
            are methods of that class with standard names
                * the module should be imported beforehand
        configs_subfolder: str, optional
            Subfolder of `calc_folder` where master configuration files are stored
    Notes:
    ------
        * if neither `routines_package` nor `routines_module` are given,
          each routine is assumed to be <routine> object of "__main__" module
        * `routines_params` provides the list of routines which can be used,
          and the corresponding modules are imported on `__init__` 
    """
    
    def __init__(self,
        calc_folder,
        routines_params = dflt_r_params_fname,
        routines_package = None,
        routines_module = "__main__",
        configs_subfolder = ""
            ):
        # Setting folders
        self._calc_folder = calc_folder
        self._config_folder = os.path.join(
            self._calc_folder,configs_subfolder
            )
        # Reading routines parameters/list if needed
        if isinstance(routines_params,str):
            routines_params = self._read_json(routines_params)
        # Creating hooks for routines, initializing objects if needed
        if routines_package is not None:
            # Each routine is a module's function
            pkg_prefix = routines_package+"." if routines_package else ""
            self._routines = {
                ri: sys.modules[pkg_prefix+ri] for ri in routines_params
                }
        else:
            self._routines = {
                ri: getattr(sys.module[routines_module],ri)()
                    for ri in routines_params
                }
        # Saving information about sets of routines' parameters
        if isinstance(routines_params,dict):
            self._r_params = {
                ki: set(_remove_ls_pref(force_list(vi))) 
                    for ki,vi in routines_params.items()
                }
        else:
            self._r_params = {ki: None for ki in routines_params}
    def _read_json(self,fname):
        """
        Reads a json file and returns it as object (dict/list/etc). 
        `fname` can be just a name or a full file name.
        By default, it is a `.json` file in `config_folder`.
        """
        fname = _fn_normalize(fname,self.calc_folder,".json")
        with open(fname) as f:
            return json.load(f)
    def _inclusion_list(self,step_name,lst):
        """
        Recursively updates boolean list (which steps from self._seq should be
        included, keeping all dependencies starting from the given step)
        """
        lst[self._steps_nrs[step_name]] = True
        for si in self._steps_depend[step_name]:
            self._inclusion_list(si,lst)
    def _subsequence(self,nr):
        """
        Given step nr in `self._seq`, returns subsequence of 
        `self._seq` up to the nr, including only the step and all its 
        dependencies at all levels, keeping the original order 
        """
        incl_list = [False for _ in range(nr+1)]
        self._inclusion_list(_str_key(self._seq[nr]),incl_list)
        return [di for di,qi in zip(self._seq,incl_list) if qi]
    def _get_step_params(self,step):
        """
        Given step name, returns the set of its routine's parameters
        """
        return getattr(
            self._r_params, self._steps_routine[step], set()
            )
    def _load_config(self,config):
        """
        Given master configuration as `dict` or `str` (config. file name),
        checks its consistency and prepares calculations plan.
        """
        if isinstance(config,str):
            config = self._read_json(config)
        #? self._config = config
        # The calculations plan (by default, has one step "Main")
        self._seq = config.get(pname_seq, [dflt_step_name])
        # Dictionaries containing various information for each step
        self._steps_config = {} # Step's full configuration
        self._steps_params = {} # Step's param. names including dependencies
        self._steps_invar = {} # Param. names step's caching is invariant to
        self._steps_nrs = {} # Nr of step in master sequence
        self._steps_depend = {} # List of steps the step depends on
        self._steps_seq = {} # Step's subsequence
        self._steps_routine = {} # Step's routine name
        self._steps_cached = {} # If step is cached (boolean)
        self._steps_cached = {} # Cached folder name if exists
        for i,ist in enumerate(self._seq): # ist is calculations step (#i)
            step_name = _str_key(ist)
            self._steps_nrs[step_name] = i
            self._steps_depend[step_name] = _list_val(ist)
            self._steps_seq[step_name] = subseq = self._subsequence(i)
            self._steps_routine[step_name] = config[step_prefix+step_name]
            self._steps_params[step_name] = set.union(
                set([step_prefix+step_name]),
                    *[self._get_params(_str_key(si)) for si in subseq]
                )
            self._steps_invar = 
            self._steps_config[step_name] = cfg =