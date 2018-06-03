# A highly useful rsync wrapper that does the heavy lifting to support humans in detecting dangerous changes to a folder structure synchronization.
# The script highlights the main changes and detects potential unwanted file deletions, while hinting to moved files that might correspond to a folder rename or move

# RSYNC status output explanation:
#   Source: https://stackoverflow.com/questions/4493525/rsync-what-means-the-f-on-rsync-logs
#   1: > received,  . unchanged or modified (cf. below), c local change, * message, e.g. deleted, h hardlink, * = message following (no path)
#   2: f file, d directory, L symlink, D device, S special
#   3: c checksum of orther change
#   4: s size change
#   5: t time change
#   6: p permission
#   7: o owner
#   8: g group
#   9: u future
#   10: a ACL (not available on all systems)
#   11: x extended attributes (as above)

# rsync options:
#   -r  --recursive  recursive
#   -R  --relative   preserves full path
#   -u  --update     skip files newer in target (to avoid unnecessary write operations)
#   -i  --itemize-changes  Show results (itemize - necessary to allow parsing)
#   -t  --times            keep timestamps
#   -S  --sparse           sparse files handling
#   -b  --backup           make backups using the "~~" suffix (into folder hierarchy), use --backup-dir and --suffix to modify base backup dir and backup suffix. A second sync will remove backups as well!
#   -h  --human-readable   ...
#   -c  --checksum         compute checksum, don't use name, time and size
#   --stats                show traffic stats
#   --existing             only update files already there
#   --ignore-existing      stronger than -u: don't copy existing files, even if older than in source
#   --prune-empty-dirs     on target, if updating
#   -z, --compress --compress-level=9


# Standard modules
import collections
import os
import subprocess
import sys


# Constants
MAX_MOVE_DIRS = 2  # don't show more than this number of potential directory moves
MAX_EDIT_DISTANCE = 5  # insertions/deletions/replacements(/moves for damerau-levenshtein)

# Rsync output classification helpers
State = {".": "unchanged", ">": "store", "c": "changed", "<": "restored", "*": "message"}
Entry = {"f": "file", "d": "dir", "u": "unknown"}
Change = {".": False, "+": True, "s": True, "t": True}  # size/time have [.+st] in their position
FileState = collections.namedtuple("FileState", ["state", "type", "change", "path", "newdir"])  # 9 characters and one space before relative path


# Utility functions
def xany(pred, lizt): return reduce(lambda a, b: a or pred(b), lizt if hasattr(lizt, '__iter__') else list(lizt), False)
def xall(pred, lizt): return reduce(lambda a, b: a and pred(b), lizt if hasattr(lizt, '__iter__') else list(lizt), True)

# Conditional function definition for cygwin under Windows
if sys.platform == 'win32':  # this assumes that the rsync for windows build is using cygwin internals
  def cygwinify(path):
    p = path.replace("\\", "/")
    if ":" in p:  # cannot use os.path.splitdrive on linux/cygwin
      x = p.split(":")
      p = "/cygdrive/" + x[0].lower() + x[1]
    return p[:-1] if p[-1] == "/" else p
else:
  def cygwinify(path): return path[:-1] if path[-1] == "/" else path

def parseLine(line):
  ''' Parse one rsync item. '''
  atts = line.split(" ")[0]  # until space between itemization info and path
  path = line[line.index(" ") + 1:]

  state = State.get(atts[0])
  if state != "message":
    entry = Entry.get(atts[1])
    change = xany(lambda _: _ in "cstpoguax", atts[2:])  # check attributes
  else:
    entry = Entry["u"]
    change = True
  while path.startswith(" "): path = path[1:]
  path = cygwinify(os.path.abspath(path))
  newdir = atts[:2] == "cd" and xall(lambda _: _ == "+", atts[2:])
  if state == "message" and atts[1:] == "deleting": state = "deleted"
  try: assert path.startswith(cwdParent + "/")
  except: raise Exception("Wrong path prefix: %s vs %s " % (path, cwdParent))
  return FileState(state, entry, change, path[len(cwdParent):], newdir)

def getCommand(simulate):  # -m prune empty dir chains from file list  -I copy even if size/mtime match
  ''' Warning: Consults global variables. '''
  return '"%s"' % rsyncPath + " %s%s%s%s%s--exclude=.redundir/ --exclude=$RECYCLE.BIN/ --exclude='System Volume Information' --filter='P .redundir' --filter='P $RECYCLE.BIN' --filter='P System Volume Information' -i -t %s'%s' '%s'" % (  # -t keep times, -i itemize
      "-n " if simulate else "",
      "-r " if not flat else "",
      "--ignore-existing " if add else "-u ",  # -u only copy if younger, --ignore-existing only copy additional files (vs. --existing: don't add new files)
      "--delete --prune-empty-dirs --delete-excluded " if sync else "",
      "-S -z --compress-level=9 " if compress else "",
      "" if simulate or not backup else "-b --suffix='~~' --human-readable --stats ",
      source,
      target
    )


# Main script code
if __name__ == '__main__':
  if len(sys.argv) < 2 or '--help' in sys.argv or '-' in sys.argv: print("""rsyncr  (C) Arne Bachmann 2017-2018
    This rsync-wrapper simplifies backing up the current directory tree.

    Syntax:  rsyncr <target-path> [options]

    Copy mode options (default: update):
      --add                -a  Copy only additional files (otherwise updating only younger files)
      --sync               -s  Remove files in target if removed in source, including empty folders
      --simulate           -n  Don't actually sync, stop after simulation
      --force-foldername   -f  Sync even if target folder name differs
      --force              -y  Sync even if deletions or moved files have been detected
      --ask                -i  In case of dangerous operation, ask user interactively
      --file <file path>       Transfer a single local file instead of synchronizing a folder
      --user <user name>   -u  Manual remote user name specification, unless using user@host notation

    Generic options:
      --flat       -1  Don't recurse into sub folders, only copy current folder
      --compress   -c  Compress data during transport, handle many files better
      --verbose    -v  Show more output
      --help       -h  Show this information
  """); sys.exit(0)


  # Parse program options
  add = '--add' in sys.argv or '-a' in sys.argv
  sync = '--sync' in sys.argv or '-s' in sys.argv
  simulate = '--simulate' in sys.argv or '-n' in sys.argv
  force_foldername = '--force-foldername' in sys.argv or '-f' in sys.argv
  force = '--force' in sys.argv or '-y' in sys.argv
  ask = '--ask' in sys.argv or '-i' in sys.argv
  flat = '--flat' in sys.argv or '-1' in sys.argv
  compress = '--compress' in sys.argv or '-c' in sys.argv
  verbose = '--verbose' in sys.argv or '-v' in sys.argv
  backup = '--backup' in sys.argv

  # Source handling
  file = sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else None
  if file: del sys.argv[sys.argv.index('--file'):sys.argv.index('--file') + 2]; print("Running in single file transfer mode for %r" % file)
  while len(file) > 0 and file[0] in '/\\': file = file[1:]
  while len(file) > 0 and file[-1] in '/\\': file = file[:-1]

  # Target handling
  user = sys.argv[sys.argv.index('--user') + 1] if '--user' in sys.argv else None
  if user: del sys.argv[sys.argv.index('--user'):sys.argv.index('--user') + 2]
  if '@' in sys.argv[1]:  # must be a remote URL with user name specified
    user = sys.argv[1].split("@")[0]
    target = sys.argv[1].split("@")[1]
    remote = True
    assert ':' in target
  else: remote = None
  if user: print("Using remote account %r for login" % user)
  remote = remote or ':' in sys.argv[1]
  if remote:  # TODO use getpass lib
    remote = sys.argv[1].split(':')[0]  # host name
    target = sys.argv[1].split(':')[1]  # remote path
    assert user
  else:  # local mode
    target = cygwinify(os.path.abspath(sys.argv[1]))

  if verbose:
    import time
    time_start = time.time()


  # External modules - down here as we need parsed options
  try:
    from textdistance import distance as _distance  # https://github.com/orsinium/textdistance, now for Python 2 as well
    def distance(a, b): return _distance('l', a, b)  # h = hamming, l = levenshtein, dl = damerau-levenshtein
    assert distance("abc", "cbe") == 2  # until bug has been fixed
    if verbose: print("Using textdistance library")
  except:
    try:
      from stringdist import levenshtein as distance  # https://pypi.python.org/pypi/StringDist/1.0.9
      assert distance("abc", "cbe") == 2
      if verbose: print("Using StringDist library")
    except:
      try:
        from brew_distance import distance as _distance  # https://github.com/dhgutteridge/brew-distance  slow implementation
        def distance(a, b): return _distance(a, b)[0]  # [1] contains operations
        assert distance("abc", "cbe") == 2  # until bug has been fixed
        if verbose: print("Using brew_distance library")
      except:
        try:
          from edit_distance import SequenceMatcher as _distance # https://github.com/belambert/edit-distance  slow implementation
          def distance(a, b): return _distance(a, b).distance()
          assert distance("abc", "cbe") == 2
          if verbose: print("Using edit_distance library")
        except:
          try:
            from editdistance import eval as distance  # https://pypi.python.org/pypi/editdistance/0.2
            assert distance("abc", "cbe") == 2
            if verbose: print("Using editdistance library")
          except:
            def distance(a, b): return 0 if a == b else 1  # simple distance measure fallback
            assert distance("abc", "cbe") == 1
            if verbose: print("Using simple comparison")


  # Preprocess source and target folders
  rsyncPath = os.getenv("RSYNC", "rsync")  # allows definition if custom executable
  cwdParent = cygwinify(os.path.dirname(os.getcwd()))  # because current directory's name may not exist in target, we need to track its contents as its own folder
  if target[-1] != "/": target += "/"
  source = cygwinify(os.getcwd()); source += "/"
  if not remote:
    diff = os.path.relpath(target, source)
    if diff != "" and not diff.startswith(".."):
      raise Exception("Cannot copy to parent folder of source! Relative path: .%s%s" % (os.sep, diff))
  if not force_foldername and os.path.basename(source[:-1]) != os.path.basename(target[:-1]):
    raise Exception("Are you sure you want to synchronize from %r to %r? Use --force-foldername or -f if yes" % (os.path.basename(source[:-1]), os.path.basename(target[:-1])))  # TODO D: to E: raises warning as well
  if file: source += file  # combine source folder
  if remote: target = remote + ":" + target
  if verbose: print("Operation: %s%s from %s to %s" % ("SIMULATE " if simulate else "", "ADD" if add else ("UPDATE" if not sync else "SYNC"), source, target))


  # Simulation rsync run
  command = getCommand(simulate = True)
  if verbose: print("\nSimulating: %s" % command)
  so = subprocess.Popen(command, shell = False, bufsize = 1, stdout = subprocess.PIPE, stderr = sys.stderr).communicate()[0]
  lines = so.replace("\r", "").split("\n")
  entries = [parseLine(line) for line in lines if line != ""]  # parse itemized information
  entries = [entry for entry in entries if entry.path != "" and not entry.path.endswith(".corrupdetect")]  # throw out all parent folders (TODO might require makedirs())

  # Detect files belonging to newly create directories - can be ignored regarding removal or moving
  newdirs = {entry.path: [e.path for e in entries if e.path.startswith(entry.path) and e.type == "file"] for entry in entries if entry.newdir}  # associate dirs with contained files
  entries = [entry for entry in entries if entry.path not in newdirs and not xany(lambda files: entry.path in files, newdirs.values())]

  # Main logic: Detect files and relationships
  def new(entry): return [e.path for e in addNames if e != entry and os.path.basename(entry.path) == os.path.basename(e.path)]  # all entries not being the first one (which they shouldn't be anyway)
  addNames = [f for f in entries if f.state == "store"]
  potentialMoves = {old.path: new(old) for old in entries if old.type == "unknown" and old.state == "deleted"}  # what about modified?
  removes = [rem for rem, froms in potentialMoves.items() if froms == []]
  potentialMoves = {k: v for k, v in potentialMoves.items() if k not in removes}
  modified = [entry.path for entry in entries if entry.type == "file" and entry.change and entry.path not in removes and entry.path not in potentialMoves]
  added = [entry.path for entry in entries if entry.type == "file" and entry.state in ("store", "changed") and entry.path and not xany(lambda a: entry.path in a, potentialMoves.values())]  # latter is a weak check
  modified = [name for name in modified if name not in added]
  potentialMoveDirs = {}
  if '--skip-move' not in sys.argv:
    if verbose: print("Computing potential directory moves")  # HINT: a check if all removed files can be found in a new directory cannot be done, as we only that that a directory has been deleted, but nothing about its files
    potentialMoveDirs = {delname: ", ".join(["%s:%d" % (_[1], _[0]) for _ in sorted([(distance(os.path.basename(addname), os.path.basename(delname)), addname) for addname in newdirs.keys()]) if _[0] < MAX_EDIT_DISTANCE][:MAX_MOVE_DIRS]) for delname in potentialMoves.keys() + removes}
    potentialMoveDirs = {k: v for k, v in potentialMoveDirs.items() if v != ""}


  # User output
  if len(added) > 0:
    print("%-5s added files" % len(added))
    if verbose: print("\n".join("  " + add for add in added))
  if len(newdirs) > 0:
    print("%-5s added dirs  (including %d files)" % (len(newdirs), sum([len(files) for files in newdirs.values()])))
    if verbose: print("\n".join("DIR " + folder + " (%d files)" % len(files) + ("\n    " + "\n    ".join(files) if len(files) > 0 else "") for folder, files in sorted(newdirs.items())))
  if len(modified) > 0:
    print("%-5s mod'd files" % len(modified))
    if verbose: print("\n".join("  > " + mod for mod in sorted(modified)))
  if len(removes) > 0:
    print("%-5s rem'd entries" % len(removes))
    print("\n".join("  " + rem for rem in sorted(removes)))
  if len(potentialMoves) > 0:
    print("%-5s moved files (maybe)" % len(potentialMoves))
    print("\n".join("  %s -> %s" % (_from, _tos) for _from, _tos in sorted(potentialMoves.items())))
  if len(potentialMoveDirs) > 0:
    print("%-5s moved dirs  (maybe) " % len(potentialMoveDirs))
    print("\n".join("  %s -> %s" % (_from, _tos) for _from, _tos in sorted(potentialMoveDirs.items())))
  if not (added or newdirs or modified or removes):
    print("Nothing to do.")


  # Breaking point before real execution
  if ask:
    if sys.platform == 'win32':
      print("Cannot get interactive user input from wrapper batch file")
    else:
      force = raw_input("Continue? [y/N] ").strip().lower().startswith('y')  # TODO or input() for Python 3
  elif simulate:
    print("Aborting before execution by user request.")  # never continue beyond this point
    if verbose: print("Finished after %.1f minutes." % ((time.time() - time_start) / 60.))
    sys.exit(0)
  if len(removes) + len(potentialMoves) + len(potentialMoveDirs) > 0 and not force:
    print("\nPotentially harmful changes detected. Use --force or -y to run rsync anyway.")
    sys.exit(0)


  # Main rsync execution with some stats output
  command = getCommand(simulate = False)
  if verbose: print("\nExecuting: " + command)
  subprocess.Popen(command, shell = False, bufsize = 1, stdout = sys.stdout, stderr = sys.stderr).wait()

  # Quit
  if verbose: print("Finished after %.1f minutes." % ((time.time() - time_start) / 60.))
