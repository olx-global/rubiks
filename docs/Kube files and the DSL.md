# Kube files and the Rubiks DSL

There are several different types of files used by the rubiks DSL. These files are python and
all python is legitimate. The DSL gives you some utility functions and variable settings to
make it easier to generate the YAML needed by Openshift and Kubernetes.

## DSL description

### Basic functions and variables

Functions and variables that are available in the rubiks files

- `repobase`<br>
  variable containing the full path to the base of the repository where the processing
  is taking place

- `read_file(<relative path>[, cant_read_ok=False])`<br>
  function to read a file and make it available in a variable (eg. for a ConfigMap)
  - `cant_read_ok`: return None instead of raising an exception if the file is unreadable

- `run_command(<cmd>[, ...<args>][, cwd=<path>][, env={...}][, env_clear=False][, delay=True][, ignore_rc=True][, rstrip=True][, eol=False])`<br>
  run a command (with arguments) and capture the output
  - `rstrip`: run an "rstrip()" stripping trailing whitespace from the output
  - `env_clear`: run from a clean environment (not including PATH)
  - `env`: dict with which to update the environment under which this command is running
  - `cwd`: relative path to this file in which to run the command
  - `ignore_rc`: whether to give the output regardless of the returncode, or whether to raise an exception if rc != 0
  - `delay`: whether to delay running the command until YAML evaluation (potentially allowing it to be run multiple times)
  - `eol`: whether to enforce a newline termination (even after an rstrip)

- `import_python(<relative_path>[, ...<symbols>][, import_as=<name>][, <extra_options>])`<br>
  imports symbols from another kube file as the `import` keyword - but uses explicit
  pathnames (relative to this file). We can't use the `import` as it relies on `.py` files
  which we don't have. There are some extra options for, eg. ekube files to distinguish
  which symbol iteration.
  - `import_as=<name>`: the equivalent of "`import <origname> as <name>`"
  - `<symbols>`: a list of symbols to import<br>
    - `import_python(<path>, '*')` equivalent to `from <name> import *`
    - `import_python(<path>, <sym1>, <sym2>)` equivalent to `from <name> import <sym1>, <sym2>`
    - `import_python(<path>, (<sym1>, <name1>), (<sym2>, <name2>))` equivalent to
      `from <name> import <sym1> as <name1>, <sym2> as <name2>`
  - `no_import=<bool>`: If true (only valid with no symbols and without `import_as`), don't perform the import of the symbols, allowing use of the module as a return value. _Defaults False_.
  - `<extra_options>`: other options for the importer routines

- `yaml_dump(<obj>)`<br>
  generate a string dump of an object in yaml format

- `json_dump(<obj>[, expanded=True])`<br>
  generate a string dump of an object in json format (if `expanded` is not True, then this comes
  out as a compacted json string, otherwise it's in `indent=2` format)

- `yaml_load(<string>)`<br>
  generate an object from a string in yaml format

- `json_load(<string>)`<br>
  generate an object from a string in json format

- `fileinfo()`<br>
  returns a dictionary with information about full path and repository-relative information of
  the current file and the one being called outside
  - `{current|load}_file_{full|repo}_{path|dir}`
    - `current` current file
    - `load` base loaded file
    - `full` full path name
    - `repo` repository-based path name
    - `path` file path
    - `dir` path to containing directory

- `output(<obj>)`<br>
  used to explicitly output an object description to a YAML file in the output directory, if used
  will stop automatic output of other objects in this file, and will require all objects to be
  explicitly `output()`.

- `no_output()`<br>
  require all objects in this file to be explicitly `output()` if they would normally be
  automatically output

- `namespace(<ns_name>)`<br>
  setup a default namespace name for objects created in this context
  ```python
  with namespace(ns):
      ConfigMap(...)
      DeploymentConfig(...)
  ```

- `clusters` _(only if clusters are configured)_<br>
  contains a tuple with the names of clusters

- `cluster_info(<cluster>)` _(only if clusters are configured)_<br>
  return a ClusterInfo object for the cluster named `<cluster>`

- `cluster_context(<cluster>)` _(only if clusters are configured, and not in .ekube files)_<br>
  similar to namespace but for clusters instead
  ```python
  with cluster_context(cluster):
      ConfigMap(...)
      DeploymentConfig(...)
  ```

- `current_cluster_name` _(only if clusters are configured and in .ekube files)_<br>
  the name of the current cluster in this ekube context

- `current_cluster` _(only if clusters are configured and in .ekube files)_<br>
  the ClusterInfo object for the current cluster in this ekube context

### Kubernetes Objects

These are objects representing things in Kubernetes or OpenShift, such as ConfigMap, Secret,
Deployment, DeploymentConfig, DaemonSet. These are available without import in all rubiks
file types. For the outputtable types, these have an identifier as the first argument, and
can have their other arguments specified - see the help.

In a cluster mode, outputtable types with no cluster automatically end up output for all
clusters.

### Lazy-evaluated types

These objects get evaluated right at the point of writing out the files, allowing them to be
varied in a sane way. They act like strings and can be concatenated with them and with each
other. To render the value, call str(...).

- `Confidential(<string>)`<br>
  Marks the current variable as confidential - the action taken for this is dependent on the
  repository configuration

- `Base64(<string>)`<br>
  generates base64 output of the string

- `JSON(<obj>)`<br>
  generates a JSON representation - better to use `json_dump()`

- `Command(<cmdargs>[, ...<options>])`<br>
  runs a command, better using `run_command()` with `delay=True`.

## File properties

### .kube files

.kube files are meant to be utility files included by others. Objects constructed in a .kube
file are not automatically output, but can be imported and cloned into other types of file.
.kube files are run once with no context.

### .gkube files

.gkube files are similar to .kube files, but they output objects automatically, except in the
case that the `output()` function is called. They are run once, with no cluster context. These
can also be imported and cloned into other file types, though this can be confusing. This kind
of file is loaded automatically by rubiks.

### .ekube files

.ekube files are run once per cluster with a cluster context. Objects created in each context
exist only in that cluster. Similar to the .gkube files, objects created will be output unless
the `output()` function is called. An .ekube can be imported into another .ekube file and the
cluster is implied in each case, however if trying to `import_python()` an .ekube into a .gkube
or .kube, a `cluster=<clustername>` option will need to be specified. This kind of file is also
loaded automatically by rubiks.

### .ckube files

Like .ekube files, but don't automatically output objects.
