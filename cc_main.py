#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALculations CONtrol
====================
"""
import sys
import os
import json
import math
import time
from importlib import import_module
from numpy import base_repr # for compacting hash string
import hashlib
from shutil import rmtree

# Constants
temp_step_folder = "_temp_step"
"""Folder name where step results are stored before renaming to permanent"""
step_config_fname = "_config"
"""File name where step's config is saved"""
step_stats_fname = "_stats"
"""File name where step's statistics is saved in the cached folder"""
main_scope = "__main__"
"""Default scope of routine functions"""
dfl_r_init_fname = "_init_routines"
"""Default name of `.json` file listing routines` parameters"""
dfl_step_name = "Main"
"""Default step name if the sequence consists of a single step"""
step_prefix = "$"
"""Prepended to a step name when it serves as a config. parameter name"""
step_prefix_len = len(step_prefix)
_system_prefix = "_"
"""Prefix for system parameter names"""
pname_seq = "_sequence"
"""Name of the parameter defining the calculations sequence"""
pname_invar = "_invariant"
"""Name of parameter defining invariant-caching parameters"""
pname_timed, pname_nontimed = ["_timed","_non_timed"]
"""Names of parameters controlling which steps should be timed"""
iname_cached = "_cached"
"""Name of init. parameter defining which routines are cached"""
iname_non_cached = "_noncached"
"""Name of init. parameter defining which routines are NOT cached"""

# sys_params_set = {pname_seq,pname_invar,pname_timed,pname_nontimed}
# """Set of system parameter names"""
sys_params_hashed_set = {pname_seq,pname_timed}
"""Set of system parameter names which are included in hash"""

return_stats_key = "_stats"
"""Key name containing summary statistics returned by routines"""
return_res_key = "_result"
"""Key name containing output returned by routines"""
stats_timing_key = "_time"


def _str_key(arg):
    """
    Given arg as `str` or `dict`, returns str := arg or its 1st key 
    """
    if isinstance(arg,str):
        return arg
    return next(iter(arg))

def _list_val(arg):
    """
    Given arg as `str` or `dict`, returns list := [] or value of the 1st key 
    """
    if isinstance(arg,str):
        return []
    return _force_list(next(iter(arg.values())))

def _list2tuple(arg):
    """
    If the arg is a list, converts it to tuple, otherwise returns arg
    """
    if isinstance(arg,list):
        return tuple(arg)
    return arg
def _remove_ls_prefix(l,pref=_system_prefix):
    """
    Given a list-like of strings, returns the list without strings 
    starting with the prefix, e.g. "_"
    """
    return [si for si in l if not si.startswith(pref)]
def _param2stepname(param):
    """Given parameter of step's routine, returns the step name"""
    return param[step_prefix_len:]
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

def _force_list(arg):
    """
    If the argument is not a list, wraps it in the list.
    """
    if isinstance(arg,list):
        return arg
    return [arg]

## Converts the given dictionary to string invariant to keys order
#   - the dictoinary can be nested and include lists
#   - all keys at any level should be string
def _dict2str(dct):
    return json.dumps(dct,sort_keys=True)

# Given dct as dict or None; add_dct as dict or None:
#    safely updates dct with add_dct
#    returns the resulted dict or None if the result is empty
def _nonempty_dict(dct,add_dct):
    dct = {} if dct is None else dct.copy()
    add_dct = {} if add_dct is None else add_dct.copy()
    dct.update(add_dct)
    return None if len(dct) == 0 else dct

# Given l as a list-like, l_yes and l_no as list-like containing l's elements
# or None, creates {e:bool for each e in l} according to the rules:
#   - if l_yes is not None, only elements from l_yes are True;
#   - if l_yes is None, l_no is not None, only elements from l_no are False
#   - if both l_yes and l_no are None, all the elements are True
def _yes_no_dict(l,l_yes,l_no):
    if l_yes is not None:
        dct = {ki:False for ki in l}
        dct.update({ki: True for ki in l_yes})
    else:
        dct = {ki:True for ki in l}
        if l_no is not None:
            dct.update({ki: False for ki in l_no})
    return dct

## Calculates unique hash for a string, returns str
def _str2hash(string):
    return base_repr(
        int(
            hashlib.shake_128(
                bytearray(string,"utf-8")
            ).hexdigest(10),
            16
        ),
        base=36
        )
## Calculates hash for a given dict
def _dict2hash(dct):
    return _str2hash(_dict2str(dct))

## Given "routine_name" or "module_name.routine_name", returns the function
def _hook(r_name):
    l = r_name.rsplit(".",1)
    func_name = l[-1]
    if len(l)==1:
        module = sys.modules[main_scope]
    else:
        module = sys.modules.get( l[0], import_module(l[0]) ) 
    return getattr(module, func_name)

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
              "_cached": list of cached routine names or 
              "_noncached": list of non-cached routine names
                  * "_noncached" works only if "_cached" is missing
                  * by default, all routines are cached
            * str: name of `json` file containing the above dict, optionally
              containing path relative to `calc_folder` or absolute path
                  * if the extension is missing, it is set to `.json`
                  * by default, the file is in 
                    `<calc_folder>/<dfl_r_init_fname>`
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
        routines_params = dfl_r_init_fname,
        configs_subfolder = ""
            ):
        # Setting folders
        self._calc_folder = calc_folder
        self._conf_subfolder = configs_subfolder
        self._temp_folder = os.path.join(calc_folder,temp_step_folder)
        # Reading routines parameters if needed
        if isinstance(routines_params,str):
            routines_params = self._read_json(routines_params)
        # Collecting dicts of sets of routines' parameters and cached info
        self._r_params = {}
        cached_info = {iname_cached:None,iname_non_cached:None}
        for li in routines_params:
            if isinstance(li,list):
                self._r_params[_list2tuple(li[0])] = set(li[1:])
                # _list2tuple is applied to routine names for non-implemented
                # functionality, when a routine name may be given as 
                # ["module.object_name","method_name"]
            else:
                cached_info.update(li)
        # Set of routines names
        self._r_names = set( self._r_params.keys() )
        # Information about routines caching
        self._r_caching = _yes_no_dict(
            self._r_names, 
            cached_info[iname_cached], cached_info[iname_non_cached]
            )
        # Creating hooks for routines
        self._routines = {
            ri: _hook(ri) for ri in self._r_names
            }

    def _read_json(self, fname, subfolder=""):
        """
        Reads a json file and returns it as object (dict/list/etc). 
        `fname` can be just a name or a full file name.
        By default, it is a `.json` file in `config_folder/subfolder`.
        """
        fname = _fn_normalize(
            fname,
            os.path.join(self._calc_folder,subfolder),
            ".json"
            )
        with open(fname) as f:
            return json.load(f)
    
    def _inclusion_list(self,step_nr,lst):
        """
        Recursively updates boolean list: True for given step and ancestors
        """
        lst[step_nr] = True
        for si in self._seq[step_nr]:
            self._inclusion_list(si,lst)
    def _subsequence(self,step_nr):
        """
        Given step nr in `self._seq`, returns subsequence of `self._seq` 
        up to the nr, including only the step and its ancestors,
        keeping the original order 
        """
        incl_list = [False for _ in range(step_nr+1)]
        self._inclusion_list(step_nr,incl_list)
        return [
            self._s_names[i] if len(di) == 0 else
            {self._s_names[i]: [self._s_names[j] for j in di]}
            for i, (di,qi) in enumerate(zip(self._seq,incl_list)) if qi
            ]
    def _get_step_params(self,step_nr):
        """
        Given step number, returns the set of its routine's parameters
        """
        return self._r_params[ self._s_routine[step_nr] ]
    
    def load_config(self,config):
        """
        Given master configuration as `dict` or `str` (config. file name),
        checks its consistency and prepares calculation plan.
        """
        if isinstance(config,str):
            config = self._read_json(config,self._conf_subfolder)
        ## The calculations plan and steps names 
        # (by default, has one step "Main")
        seq_str = config.get(pname_seq, [dfl_step_name])
        # List of step names in the order of the sequence
        self._s_names = [_str_key(si) for si in seq_str]
        # The number of steps
        self._n = n = len(seq_str)
        # Initialize the collections of results and summary statistics
        self._res = [None for _ in range(self._n)]
        self._stats = [None for _ in range(self._n)]
        # Consistency check: all steps names should be different
        if self._n > len(set(self._s_names)):
            raise Exception(
                "All steps in the sequence should have different names"
                )
        # Dict "step_name": step_nr
        self._s_nrs = {si:ni for ni,si in enumerate(self._s_names)}
        # The main sequence as a list, where #element = #step,
        #   element = list of parent #steps
        self._seq = [
            [ self._s_nrs[sj] for sj in _list_val(si) ]
                    for si in seq_str
            ]
        # Consistency check: each step should go after its ancestors
        for i, li in enumerate(self._seq):
            if len(li)>0 and max(li)>=i:
                raise Exception(
                "Each step should go after its ancestors, not like",
                    seq_str[i]
                )
        # Information which steps should be timed
        if_timed_dct = _yes_no_dict(
            self._s_names,
            config.get(pname_timed,None),
            config.get(pname_nontimed,None)
            )
        self._s_if_timed = [if_timed_dct[ki] for ki in self._s_names]
        ## Lists containing various information for each step
        # Step's full configuration
        self._s_config = [ {} for _ in range(n) ]
        # Step's and ancestors' routine param. names, including $-params
        self._s_params = [set() for _ in range(n)] 
        # Invariant parameters among step's and ancestors' routine params
        self._s_invar = [set() for _ in range(n)] 
        # Param. names used in step's hashing
        self._s_hash_params = [set() for _ in range(n)]
        # Step's subsequence in str form
        self._s_seq = [[] for _ in range(n)]
        # Step's routine name
        self._s_routine = ["" for _ in range(n)]
        # If step is cached (boolean)
        self._s_if_cached = [True for _ in range(n)]
        # Cached folder name / full path if exists
        self._s_cached_folder = [None for _ in range(n)]
        self._s_cached_path = [None for _ in range(n)]
        # Shortening for invariant set
        invar_set = set(_force_list(config.get(pname_invar,[])))
        for i,isp in enumerate(self._seq): # isp is parents of step (#i)
            step_name = self._s_names[i]
            # Creating supplementary step information
            self._s_seq[i] = subseq = self._subsequence(i)
            self._s_routine[i] = s_routine = _list2tuple(
                config[step_prefix+step_name]
                )
            self._s_if_cached[i] = s_if_cached = self._r_caching[s_routine]
            self._s_params[i] = s_params = set.union(
                set([step_prefix+step_name]),
                self._r_params[s_routine],
                *[self._s_params[j] for j in isp]
                )
            self._s_invar[i] = s_invar = invar_set & (
                s_params | sys_params_hashed_set
                )
            self._s_hash_params[i] = s_hash_params = (
                s_params | sys_params_hashed_set
                ) - invar_set
            # Creating step's configuration
            self._s_config[i] = s_config = {
                ki:config.get(ki,None) for ki in s_params
                }
            s_config[pname_seq] = subseq
            if len(s_invar) > 0:
                s_config[pname_invar] = sorted(list(s_invar))
            s_config[pname_timed] = self._s_if_timed[i]
            # Cached folder name
            if s_if_cached:
                self._s_cached_folder[i] = cached = _dict2hash(
                        {
                        ki:vi for ki,vi in s_config.items()
                            if ki in s_hash_params
                        }
                    )
                self._s_cached_path[i] = os.path.join(self._calc_folder,cached)
    # Prepares a new temp folder for step calculation with step's config file
    def _make_step_folder(self,s_nr):
        if os.path.exists(self._temp_folder):
            rmtree(self._temp_folder)
        os.mkdir(self._temp_folder)
        with open(
            _fn_normalize(step_config_fname,self._temp_folder,"json"),"w"
                ) as f:
            json.dump(self._s_config[s_nr],f)
    # After step's calculation ends successfuly, renames the temp folder to
    # its intended name
    def _checkin_step_folder(self,s_nr):
        if os.path.exists(self._s_cached_path[s_nr]):
            rmtree(self._s_cached_path[s_nr])
        os.rename(self._temp_folder,self._s_cached_path[s_nr])
    # Check if there is a cached folder for the given step nr.
    # If yes, collects the saved stats, sets rezult as folder name
    #   and returns True, otherwise False
    def _try_step_folder(self,s_nr):
        if os.path.exists(self._s_cached_path[s_nr]):
            self._stats[s_nr] = self._read_json(
                step_stats_fname,self._s_cached_folder[s_nr]
                )
            self._res[s_nr] = self._s_cached_path[s_nr]
            return True
        return False
    # Saves summary statistics of the given step to the cache folder
    def _save_stats_json(self,s_nr):
        with open(
                os.path.join(
                    self._s_cached_path[s_nr],
                    step_stats_fname
                    )+".json",
                "w"
                ) as f:
            json.dump(self._stats[s_nr],f)
            
    def run_step(self,s_nr):
        """
        Perform calculation of the given step. 
        Returns False if calculation was successful, 
        otherwise returns error information (yielding True)
        """
        q_cached = self._s_if_cached[s_nr]
        q_timed = self._s_if_timed[s_nr]
        stats_internal = {} # addition to statistics
        if q_cached and self._try_step_folder(s_nr):
            return False
        args = [self._res[si] for si in self._seq[s_nr]]
        if q_cached:
            self._make_step_folder(s_nr)
            args.append(self._temp_folder)
        args.append(self._s_config[s_nr])
        if q_timed:
            _time = time.process_time()
        try:
            val = self._routines[self._s_routine[s_nr]](*args)
        except Exception as exc:
            return exc
        if q_timed:
            _time = time.process_time() - _time
            stats_internal[stats_timing_key] = _time
        if q_cached:
            self._res[s_nr] = self._s_cached_path[s_nr]
            self._stats[s_nr] = _nonempty_dict(val,stats_internal)
            self._checkin_step_folder(s_nr)
            self._save_stats_json(s_nr)
        else:
            if isinstance(val,dict) and return_stats_key in val:
                self._res[s_nr] = val.get(return_res_key,None)
                self._stats[s_nr] = _nonempty_dict(
                    val[return_stats_key], stats_internal
                    )
            else:
                self._res[s_nr] = val
                self._stats[s_nr] = _nonempty_dict({},stats_internal)
        return False
    
    def run_calc(self):
        """
        Runs the calculations, provided that configuration was already loaded
        """
        for si in range(self._n):
            err = self.run_step(si)
            if err:
                print(f"Error in step {si} ({self._s_names[si]})")
                return [si,err]
                break
        return -1
    
    def get_stats(self,numbering=True):
        """
        Returns summary stats collected as a result of calculation as a dict
        where keys are step names.
        If numbering=True, steps' numbers are added in front of names.
        
        """
        n_digits = math.ceil(math.log(self._n+1,10))
        stats={}
        for i,si in enumerate(self._stats):
            if si is not None:
                s_name = self._s_names[i]
                if numbering:
                    s_name = f"({str(i).zfill(n_digits)}) {s_name}"
                stats[s_name] = si
        return stats
    
    def get_result(self):
        return self._res.copy()
