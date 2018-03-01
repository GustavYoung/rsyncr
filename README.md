# rsyncr #
![GPLv3 logo](http://www.gnu.org/graphics/gplv3-127x51.png)

Awesome useful `rsync` convenience wrapper for Python.
Does the heavy lifting of finding potential problems.

Might be slow on many renames/moves.


## Installation ##
```
pip[3] install rsyncr
```

## Usage ##
```
rsyncr <target-folder> [options]
```
with options:
```
Copy mode options (default: update):
    --add       -a  Add only new files (don't update older files in target)
    --sync      -s  Remove files in target if removed in source
    --simulate  -n  Don't actually sync, stop after simulation
    --force     -y  Sync even if deletions or moved files have been detected
    --ask       -i  In case of dangerous operation, ask user interactively

  Generic options:
    --flat      -1  Don't recurse into sub folders, only copy current folder
    --compress  -c  Compress data during transport, handle many files better
    --verbose   -v  Show more output
    --help      -h  Show this information
```
