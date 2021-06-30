#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALculations CONtrol
====================
"""
import sys
import os
import json
from importlib import import_module
from numpy import base_repr # for compacting hash string
import hashlib
from shutil import rmtree

# Constants
temp_step_fname = "_temp_step"
"""Folder name where step results are stored before renaming to hash folder"""
step_config_fname = "_config"
"""file name where step's config is stored"""
dfl_r_init_fname = "_init_routines"
"""Default name of `.json` file listing routines` parameters"""
dfl_step_name = "Main"
"""Default step name if the sequence consists of a single step"""
step_prefix = "$"
"""Prepended to a step name when it serves as a config. parameter name"""
step_prefix_len = len(step_prefix)
pname_seq = "_sequence"
"""Name of the parameter defining the calculations sequence"""
pname_invar = "_invariant"
"""Name of parameter defining invariant-caching parameters"""
iname_cached = "_cached"
"""Name of init. parameter defining which routines are cached"""
iname_non_cached = "_noncached"
"""Name of init. parameter defining which routines are NOT cached"""
sys_params_set = {pname_seq,pname_invar}
"""Set of system parameter names"""
sys_params_hashed_set = {pname_seq}
"""Set of system parameter names which are included in hash"""
return_stats_key = "_stats"
"""Key name containing summary stats returned by routines"""
return_res_key = "_result"
"""Key name containing output returned by routines"""

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
    return next(iter(arg.values()))

def _remove_ls_prefix(l,pref="_"):
    """
    Given a list-like of strings, returns the list without strings 
    starting with "_"
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
        routines_package = None,
        routines_module = "__main__",
        configs_subfolder = ""
            ):
        # Setting folders
        self._calc_folder = calc_folder
        self._config_folder = os.path.join(
            self._calc_folder,configs_subfolder
            )
        self._temp_folder = os.path.join(calc_folder,temp_step_fname)
        # Reading routines parameters if needed
        if isinstance(routines_params,str):
            routines_params = self._read_json(routines_params)
        # Dictionary of sets of routines' parameters
        self._r_params = {
            ki: set(_force_list(vi)) 
                for ki,vi in routines_params.items() if
                    not(ki.startswith("_"))
            }
        # Set of routines names
        self._r_names = set( self._r_params.keys() )
        # Set information about routines caching
        self._set_r_caching_info(
            *[
                routines_params.get(ki,None) 
                    for ki in [iname_cached,iname_non_cached]
                ]
            )
        # Creating hooks for routines
        if routines_package is not None:
            self._r_modules_hooks(routines_package)
        else:
            self._r_objects_hooks(routines_module)

    # Saving information about if routines are cached
    def _set_r_caching_info(self,l_cached,l_non_cached):
        if l_cached is not None:
            self._r_caching = {ki:False for ki in self._r_names}
            self._r_caching.update( {ki: True for ki in l_cached} )
        else:
            self._r_caching = {ki:True for ki in self._r_names}
            if l_non_cached is not None:
                self._r_caching.update( {ki: False for ki in l_non_cached} )
    # Creating hooks for routines as modules (import if needed)
    def _r_modules_hooks(self,package_name):
        pkg_prefix = package_name+"." if package_name else ""
        self._routines = {
            ri: sys.modules.get(
                    pkg_prefix+ri,
                    import_module(pkg_prefix+ri)
                    ) 
                for ri in self._r_names
            }
    # Creating hooks for routines as module's objects (import if needed)
    def _r_objects_hooks(self,module_name):
        r_module = sys.module.get(
            module_name,
            import_module(module_name)
            )
        self._routines = {
            ri: getattr(r_module,ri)()
                for ri in self._r_names
            }

    def _read_json(self, fname, subfolder=""):
        """
        Reads a json file and returns it as object (dict/list/etc). 
        `fname` can be just a name or a full file name.
        By default, it is a `.json` file in `config_folder/subfolder`.
        """
        fname = _fn_normalize(
            fname,
            os.path.join(self.calc_folder,subfolder),
            ".json"
            )
        with open(fname) as f:
            return json.load(f)
    
    def _inclusion_list(self,step_name,lst):
        """
        Recursively updates boolean list (which steps from self._seq should be
        included, keeping all dependencies starting from the given step)
        """
        lst[self._s_nrs[step_name]] = True
        for si in self._s_parent[step_name]:
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
            self._r_params, self._s_routine[step], set()
            )
    def load_config(self,config):
        """
        Given master configuration as `dict` or `str` (config. file name),
        checks its consistency and prepares calculations plan.
        """
        if isinstance(config,str):
            config = self._read_json(config)
        invar_set = set(config.get(pname_invar,[]))
        # The calculations plan (by default, has one step "Main")
        self._seq = config.get(pname_seq, [dfl_step_name])
        # Dictionaries containing various information for each step
        self._s_config = {} # Step's full configuration
        self._s_params = {} # Step's param. names including dependencies
        self._s_hash_params = {} # Param. names used in step's hashing
        self._s_nrs = {} # Nr of step in master sequence
        self._s_parent = {} # List of steps the step depends on
        self._s_seq = {} # Step's subsequence
        self._s_routine = {} # Step's routine name
        self._s_if_cached = {} # If step is cached (boolean)
        self._s_cached_folder = {} # Cached folder name if exists
        for i,ist in enumerate(self._seq): # ist is calculations step (#i)
            step_name = _str_key(ist)
            self._s_nrs[step_name] = i
            self._s_parent[step_name] = s_parent = _list_val(ist)
            self._s_seq[step_name] = subseq = self._subsequence(i)
            self._s_routine[step_name] = config[step_prefix+step_name]
            self._s_params[step_name] = s_params = set.union(
                set([step_prefix+step_name]),
                    *[self._get_params(_str_key(si)) for si in s_parent]
                )
            self._s_invar = s_invar = invar_set.intersect(
                s_params,sys_params_hashed_set
                )
            self._s_hash_params[step_name] = s_params.union(
                sys_params_hashed_set
                    ).difference(invar_set)
            self._s_config[step_name] = s_config = {
                config[ki] for ki in s_params
                }
            self._s_config[step_name][pname_seq] = subseq
            if len(s_invar) > 0:
                self._s_config[step_name][pname_invar] = sorted(list(s_invar))
            self._s_cached_folder[step_name] = _dict2hash(s_config)
    # Prepares a new temp folder for step calculation with step's config file
    def _make_step_folder(self,s_name):
        if os.path.exists(self._temp_folder):
            rmtree(self._temp_folder)
        os.mkdir(self._temp_folder)
        with open(
            _fn_normalize(step_config_fname,self._temp_folder,"json"),"w"
                ) as f:
            json.dump(self.s_config[s_name],f)
    # After step's calculation ends successfuly, renames the temp folder to
    # its intended name
    def _checkin_step_folder(self,s_name):
        cached = os.path.join(self._calc_folder,self._s_cached_folder[s_name])
        if os.path.exists(cached):
            rmtree(cached)
        os.path.rename(self._temp_folder,cached)
        
    def run_step(self,s_name):
        """
        Perform calculation of the given step. 
        Returns False if calculation was successful, 
        otherwise returns error information (yielding True)
        """
        q_cached = self._s_if_cached[s_name]
        args = [self._s_res[si] for si in self._s_parent]
        if q_cached:
            self._make_temp_folder(s_name)
            args.append(self._temp_folder)
        args.append(self._s_sonfig[s_name])
        try:
            val = self._routine(*args)
        except:
            return True
        if q_cached:
            self._stats[s_name] = val
            self._res[s_name] = os.path.join(
                self._calc_folder,self._s_cached_folder[s_name]
                )
        else:
            if isinstance(val,dict) and return_stats_key in val:
                self._stats[s_name] = val[return_stats_key]
                self._res[s_name] = val.get(return_res_key,None)
            else:
                self._stats[s_name] = None
                self._res[s_name] = val
        return False
    
    def run_calcs(self):
        """
        Runs the calculations, provided that configuration was already loaded
        """
        # Initialize the collections of results and summary statistics
        self._res = {}
        self._stats = {}
        for si in self._seq:
            err = self.run_step(_str_key(si))
            if err:
                print("Error in step",si)
                break

        