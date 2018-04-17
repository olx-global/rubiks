# Rubiks repositories and the .rubiks file

## Rubiks repositories

The rubiks tool is designed to be used on a "Rubiks repository," ie. a
repository with [.kube and .gkube files](Kube%20files%20and%20the%20DSL.md#file-properties).

These repositories have a set of sources to compile, a place to store the output,
and normally a '.rubiks' file at their root.

## The .rubiks file

A .rubiks file is a .ini file with several sections and options

### `[layout]` section

- `sources` _(default `sources`)_ repository-relative directory to find sources
  (.kube/.gkube/.ekube files)
- `outputs` _(default `generated`)_ repository-relative directory to write outputs
- `pythonpath` _(optional)_ repository-relative comma-separated list of directories
  which to allow pure-python imports
- `confidentiality_mode` _(default `none`)_ what to do when files have confidential
  markers in them
  - `none` do nothing
  - `hidden` replace confidential values with "\*\*\* HIDDEN \*\*\*"
  - `gitignore` add output filename to a `.gitignore` in the same output directory
    as the file
  - `git-crypt` add output filename to a `.gitattributes` file in the same output
    directory as the file, with the git-crypt filters
  - `gitignore-single` add output filename to a single `.gitignore` file at the
    top-level of the output directory
  - `git-crypt-single` add output filename to a single `.gitattributes` file at
    the top-level of the output directory, with the git-crypt filters

### `[global]` section

- `is_openshift` _(default `false`)_ see per-cluster version but overrides per-cluster
  setting if true and used in clusterless mode

### `[cluster_<clustername>]` sections

If none of these are present, rubiks will operate in clusterless mode, but the
sections define what clusters are available, even if empty

- `prod_state` _(default `production`)_ state of this cluster - allows `.is_prod`
  attribute to be read on the ClusterInfo object
- `is_openshift` _(default `false`)_ if this cluster is openshift then generate
  project and standard RoleBindings instead of Namespace
