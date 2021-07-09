# Configuration of calculations

## General concepts

* **project** - a series of calculations based on a given set of routines, where each run of calculations (**calculation** for short) is defined by a configuration
* **configuration** - dictionary of parameters or a *.json* file defining a calculation in the framework of a project, including the selection of routines and the parameters of each routine
* **step** - atomic part of a calculation, which is implemented by one of the given routines
	* besides actual calculations, there may be other types of steps such as *data acquisition*, *data preparation*, *summarizing the results*, etc.  
* **sequence** - as a part of configuration, the plan of a calculation composed of steps
	* includes the information about dependencies between steps, where outputs of **parent** steps are inputs of the **child** step 
	* in general, can be represented as an oriented graph without cycles, where nodes are steps and edges are dependencies between steps
	* **subsequence** - for a given step, a part of the sequence including only this step and all its **ancestors** (parents, their parents. etc.)
* **routine** - a method / variant of implementation of a specific step
	* all routines are implemented outside of `calconpy` as functions, which are defined in the main script or specified modules
	* different routines implementing a same step should have the same API, ensuring the interchangeability in different configurations
	* a good practice (for conducting a series of experiments or configuring the calculation in production) is to fix the sequence of steps and only change routines for specific steps if needed
  
### Configuration
Configurations are `dict`s, optionally stored in JSON files 
* each key (parameter's name) and each sub-key (if any) is `str`. 

There are following kinds of configurations.
* *Master* configuration - defines the whole process of calculation
* *Step's* configuration - defines calculation up to the given step, i.e. for the step and its ancestors
	* contains only parameters influencing the result of this step;
	* is stored in the folder where step's results are cached;
	* allows the user to inspect, what results are stored in a given cache folder 
* *Hashing* configuration - for a given step, defines the name of the cache folder by means of hashing of the step's configuration
	* is obtained by removing irrelevant parameters from step's configuration, e.g. ones listed in *_invariant*;
	* is not stored explicitly, but only used for defining the folder name
	* is invariant to the order of keys/sub-keys in the dictionary
### Parameters
There are three kinds of parameters in a configuration
* *Routines' parameters* - influencing calculation in specific routines
	* can have any names, which should not start with _ or $
	* multiple routines may have common parameters
	* if there are many parameters specific to different routines, a good practice is to name them *"routine_name.parameter_name"* 
* *Routine selection parameters* - define for each step of the sequence, which routine implements it, in either of the following two formats:
	* *"$step_name": "routine_name"* - when "routine_name" is the name of the function defined in the main scope
	* *"$step_name": ["module_name", "routine_name"]* - when "routine_name" is the name of the function defined in the module "module_name"
* *System parameters* - related to organizing the process of calculation
	* Have predefined names, which start with _

## Configuring the calculation via system parameters
* **_sequence** - the calculation sequence. 
	*Format*: list of two types of elements:
	* `str` – name of the step to execute
	* { `str`: [list of `str`] } – name of the step to execute and list of its parent steps
		* the order of parent steps defines the order of arguments (parent steps' outputs) in the routine implementing the step 
A child step always goes in the list after its parent steps 

This parameter is optional. If `_sequence` is missing, then the sequence is assumed to be [`dflt_step_name`], where `dflt_step_name` = *"Main"*

* **_invariant** - the list of parameters, whose values are ignored when identifying the cached folder.

	*Format*: `str` or list of `str` (parameter names)

	*Usage*: to save time by making the caching process for certain steps invariant to certain parameters, i.e. the result of a step is not recalculated if only those parameters change
	
The following table summarizes some properties of system parameters and routine selection parameters: if they required to be in the master configuration; how are they modified in step's configuration; if they are present in the hashing configuration.

|               | Required      | In step's config | In hashing config   |
| :-------------| :------------:|------------------|:----------:|
| **_sequence** | no     		| Subsequence      |yes			|
| **_invariant**| no		    | Step's, ancestors' & system  |no			|
| **$step_name**| yes (for each step)| Step's and ancestors'  |yes			|

In step's configuration, there are following modifications:
* *_sequence* turns into step's subsequence
* *_invariant* only contains parameters which are relevant to the step and its ancestors, and system parameters (if any)
* *$step_name* - only present for the step and its ancestors

## Routines
For short, in the context of a given sequence, a *parent* / *child* routine of a given routine is a routine implementing a parent / child step of the corresponding step.

Routines' names cannot start with _ or $

### Cached and non-cached routines
Cached routines are ones that save the results of calculations to a folder; non-cached routines return the results explicitly.

### Expected behavior
* Routine can raise any exceptions - then calculations stop, but the results from previous steps are saved.
* Artificially raising an exception can be used by a routine to send a signal to stop subsequent calculations, e.g. in the case where the results of step's calculations make no sense for proceeding to next steps.
* The requirements to a routine's API are determined by the following information: whether the routine is cached or not; what are parent routines and the order of their outputs as arguments; which of parent steps are cached. For example, the argument corresponding to a cached parent routine is the name of the folder cached, where the child routine should read the input.
	* The usage of `calconpy` lacks flexibility in the sense that defining the order of steps in the sequence is interconnected with the implementation of corresponding routines' API.

### Routine's API

#### Routine's arguments
`( p_1, ..., p_k, folder_name, config )`
* `p_i` for each *i* = 1,...,*k* – output of the corresponding parent routine
	* *k* is the number of parent routines, which can be 0 (then arguments `p_1`,...,`p_k` are missing)
	* if the *i*-th parent routine is cached, then `p_i` is the name of the corresponding cache folder as `str` (otherwise `p_i` is the value returned by the parent routine)
* `folder_name` – the folder name to save output to, if the routine is cached (otherwise, the argument `folder_name` is missing)  
* `config` – the corresponding step's configuration (`dict`)

If the routine is not cached and has no parents, it has `config` as the only argument.

#### Routine's returned value

Besides **the result of calculation**, a routine may produce some information as `dict`, called **summary statistics**. The purpose of the latter: to display useful information such as the accuracy or calculation time. Summary statistics from all steps is collected in each calculation, and can be used to create a table summarizing the results of experiments.
* *"_time": process_time_in_seconds* is automatically added to summary statistics of each step
* all keys and sub-keys of summary statistics `dict` should be `str`

#### Cached routine's returned value
There are following options:
1. `None`
2. `dict` – summary statistics

#### Non-cached routine's returned value
There are following options:
1. `dict` containing key `return_stats_key`:="*_stats*" and optionally, `return_res_key`:="*_result*" – then *"_result"* contains the routine's output, *"_stats"* is `dict` containing summary statistics
2. any other value – the routine's output
 
## Initialization of the project
Initialization of the project means the definition of all routines which can be used in calculations. The definition includes the following information about each routine: name of the function (and optionally, the module) implementing it; list of names of all configuration parameters influencing the routine; whether the routine is cached. 

The initialization should be provided as a `list` or a *.json* file with elements of the following kinds:
* `list` where the first element indicates a routine and the rest of elements are names of its parameters (if any) 
	* the first element is either *"routine_name"* or *["module_name", "routine_name"]* where "routine_name" is the name of the function, and "module_name" is the name of the module if the function is defined in it
* *{"_cached": [list of cached routines]}*
* *{"_non_cached": [list of non-cached routines]}*

The *"_cached"* and *"_non_cached"* dictionaries are optional:
* if none of them presents, all the routines are considered as cached;
* if *"_cached"* is given, then only the listed routines are cached, and *"_non_cached"* is ignored (if present)
* if only *"_non_cached"* dictionary is given, then all the routines except the listed ones are considered cached

During the initialization, all the modules containing the routines are imported.
