# Configuration of calculations
## General concepts
* **project** - a series of calculations based on a given set of routines where each calculation is defined by a configuration
* **configuration** - dictionary of parameters describing the whole process 
  of calculation, including parameters of specific routines
* **sequence** - as a part of configuration, the plan of calculation composed of steps
	* includes the information about dependencies between steps, where output of **parent** step(s) is/are input(s) of **child** step 
	* in general, can be represented as an oriented graph without cycles, where nodes are steps and edges are dependencies between steps
* routine - a method / variant of implementation for a specific step
	* different routines implementing a same step should have the same interface ensuring interchangeability
	* a good practice is to fix the sequence and only change routines for specific steps if needed
  
### Configurations
Configurations are `dict`s stored in JSON files. 
* Each key (parameter's name) and each sub-key (if any) is `str`. 

There are following kinds of configuration.
* *Master* - defining the whole process of calculation
* *Step's* - defining calculation up to the given step, i.e. step and its parents.
	* Contains only parameters influencing the result of this step
	* Is stored in the folder where step's results are cached.
* *Hashing* - for a given step, configuration which defines the location of the cache folder through hashing of the step\s configuration
	* Is obtained by removing irrelevant parameters from step's configuration, e.g. ones listed in *_invariant*
	* Is not stored explicitly, but is used for defining the cache folder name    
### Parameters
There are two kinds of parameters in a configuration
* *Routines' parameters* - influencing calculation in specific routines.
	* Can have any names, which should not start with _ or $
* *System parameters* - related to organizing the process of calculation
	* Have predefined names, which start with _ or $

## System parameters
* **_sequence** - the calculation sequence. 
	*Format*: list of two types of elements:
	* `str` – name of the step to execute
	* { `str`: [list of `str`] } – name of the step to execute and list of its parent steps
		* the order of parent steps defines the order of arguments in routine(s) implementing the child step 
	* A child step always goes in the list after its parent steps 

	*Is optional*. If `_sequence` missing, then the step sequence is assumed to be [`dflt_step_name`], where `dflt_step_name`="Main"
	
	

* **_invariant** the list of parameters, whose values are ignored when identifying the cached folder.
	*Format*: list of `str` (parameter names)
	*Usage*: save time by making the caching process invariant to certain parameters, i.e. the results are not recalculated if only those parameters change 

* **$step_name** for each step "*step_name*", defines the name of the routine to be called for executing the step. format: `str`

|               | Required      | In step's config | In hash   |
| :-------------| :------------:|------------------|:----------:|
| **_sequence** | no     		| Subsequence      |yes			|
| **_invariant**| no		    | Step's + system  |no			|
| **$step_name**| yes (for each)| For all parents  |yes			|

# Routines
For short, in the context of a given sequence, a *parent*/*child* routine of a given routine is a routine implementing a parent/child step of the corresponding step.

Routines' names cannot start with _ or $

## Expected behavior
* Routine can raise any exceptions - then calculations stop, but the results from previous steps are stored.
* Artificially raising an exception can be used by a routine to send a signal to stop subsequent calculations, e.g. if the results of step's calculations make no sense for proceeding to next steps, 

## Cached and non-cached routines
Cached routines are ones that save the results of calculations to a folder; non-cached return the results explicitly.

## Routine's API

### Routine's arguments
`( p_1, ..., p_k, folder_name, config )`
* `p_i` for each *i* = 1,...,*k* – output of the corresponding parent routine
	* *k* is the number of parent routines, which can be 0 (then arguments `p_1`,...,`p_k` are missing)
	* if the *i*-th parent routine is cached, then `p_i` is the name of the corresponding cache folder (otherwise is the value returned by the parent)
* `folder_name` – the folder name to save output to, if the routine is cached (otherwise, the argument `folder_name` is missing)  
* `config` – the corresponding step's configuration (`dict`)

So, if the routine is not cached and has no parents, it has `config` as the only argument. Moreover, if the routine does not have parameters, then it has no arguments at all.

### Routine's returned value

Besides *the result of calculation*, a routine may produce some information as `dict`, called *summary statistics*. The purpose of the latter: display useful information such as the accuracy or calculation time. Summary statistics from all routines is collected in each calculation, and can be used to create a table summarizing the results of experiments.  

#### Cached routine's returned value
There are following options:
1. `None`
2. `dict` – summary statistics

#### Non-cached routine's returned value
There are following options:
1. `dict` containing key `return_stats_key`:="*_stats*" and optionally, `return_res_key`:="*_result*" – then *_result* is the routine's output, *_stats* is `dict` containing summary statistics
2. any other value – the routine's output
 
## Initialization of the project
Initialization of the project means the definition of all routines that can be used in calculations. The definition is given as a `dict` or *.json* file containing the following:
* "routine_name": [list of names of configuration parameters the routine depends on]
* "_cached": [list of names of cached routines] *or*
* "_non_cached": [list of names of non-cached routines]

"_cached" and "_non_cached" keys are optional:
* if none of them presents, all the routines are considered as cached;
* if "_cached" is given, then only the listed routines are cached, and "_non_cached" is ignored (if present)
* if only "_non_cached" key is given, then all the routines except listed ones are considered cached
