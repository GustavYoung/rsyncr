import os, subprocess, sys

command = '"' + sys.executable + '" "' + os.path.join(os.path.dirname(os.path.abspath(__file__)), "rsyncr.py") + '"' + ((' "' + '" "'.join(sys.argv[1:]) + '"') if len(sys.argv) > 1 else "")
subprocess.Popen(command, shell = True, bufsize = 1).wait()
