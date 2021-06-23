# Configuration of calculations
## General concepts
* sequence - the plan of calculations composed of steps
* step - atomic part of calculations taking as input / producing as output
  intermediate results
* routine - a method / variant of implementation for a specific step; different
  routines for a given step can be used interchangeably
* configuration - dictionary of parameters controlling the whole process 
  of calculations, including parameters of specific routines
  
### Configurations
Configurations are `dict`s stored in JSON files. 
* Each key (parameter's name) is str. 

There are following kinds of configurations.
* *Master* - defining the whole process of calculations
* *Step's* - defining calculations up to the given step, i.e. step and its parents.
	* Contains only parameters influencing the result of this step
	* Is stored in the folder where step's results are cached.
* *Caching* - for a given step, configuration which defines the location of the cache folder
	* Is obtained from step's configuration by removing irrelevant parameters, e.g. ones listed in *_invariant*
	* Is not stored explicitly, but is used for defining the cache folder name    
### Parameters
There are two kinds of parameters
* *Routines' parameters* - influencing calculations in specific routines.
	* Can have any names, but should not start with _ and $
* *System parameters* - related to organizing the process of calculations
	* Have predefined names, start with _ or $

## System parameters
* **_sequence** the calculation sequence. 
	*Format*: list of two types of elements:
	* `str` – name of the step to execute
	* { `str`: [list of `str`] } – name of the step to execute and list of previous steps whose outputs are its inputs
	*Is optional*. If missing, then the step sequence is assumed to be [`dflt_step_name`], `dflt_step_name`="Main"
	
	

* **_invariant** the list of parameters, whose values are ignored when identifying the cached folder.
	*Format*: list of `str` (parameter names)

* **$step_name** for each step "*step_name*", defines the name of the routine to execute the step. format: `str`

|               | Required      | In step's config | Cache ID   |
| :-------------| :------------:|------------------|:----------:|
| **_sequence** | no     		| Subsequence      |yes			|
| **_invariant**| no		    | Step's + system  |no			|
| **$step_name**| yes (for each)| For all parents  |yes			|

# Routines
For short, by a parent routine of the given routine we call the routine executing the parent step of the step executed by the given routine.

Routines' names cannot start with _

## Expected behavior
* Routine can raise any exceptions – then calculations stop, but the results from previous steps are stored.
* Artificially raising an exception can be used by a routine to send a signal to stop subsequent calculations, e.g. if the results of step's calculations make no sense for proceeding to next steps, 

## Cached and non-cached routines
Cached routines are ones that save the results of calculations to a folder; non-cached return the results explicitly.

## Routine's API

### Routine's arguments
`( p_1, ..., p_k, folder_name, config )`
* `p_i` for each *i* = 1,...,*k* – output of the corresponding parent routine
	* *k* is the number of parent routines, which can be 0 (then arguments `p_1`,...,`p_k` are missing)
	* if the *i*-th parent routine is cached, then `p_i` is the name of the corresponding cache folder (otherwise is the returned value)
* `folder_name` – the folder name to save output to if the routine is cached (otherwise, the argument `folder_name` is missing)  
* `config` – the corresponding step's configuration (`dict`)

So, if the routine is not cached and has no parents, it has `config` as the only argument.

### Routine's returned value

#### For a cached routine
There are following options:
1. `None`
2. `dict` – summary statistics

#### For a non-cached routine
There are following options:
1. `dict` containing keys "*_result*" and "*_stats*" – then *_result* is the routine's output, *_stats* is `dict` containing summary statistics
2. any other value – the routine's output
 

