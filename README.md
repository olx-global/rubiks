# Rubiks - a kubernetes yaml file manager

Rubiks exists to help programmatically generate and maintain the yaml files associated
with kubernetes configuration.

The rubiks compiler provides a [DSL](Kube%20files%20and%20the%20DSL.md) (basically python) to help
make this happen.

## Installing Rubiks

Installing Rubiks is easy, you can just check out this repository to your working space
and then symlink the rubiks binary into somewhere (eg `~/bin`) that is on your executable
search path (`$PATH`). Then you should be able to do rubiks help to get a list of commands.

## Using Rubiks

Rubiks is designed to point at a [Rubiks Repository](docs/Rubiks%20repositories%20and%20the%20.rubiks%20file.md),
which is just a repository with some possible rubiks configuration (in the form of a .rubiks
file in the repository root), and some rubiks source files.

Running `rubiks generate` while in such a repository will generate you all the YAML files
which you can use to update your clusters. Right now, we can use git status / git diff and
knowing what was changed to update these clusters, but in future this will be resolvable
within rubiks itself.

See also `rubiks help` for more information on how to use it

## Full set of docs

- [Kube files and the DSL](docs/Kube%20files%20and%20the%20DSL.md)
- [Rubiks repositories and the .rubiks file](docs/Rubiks%20repositories%20and%20the%20.rubiks%20file.md)
