import os, subprocess, sys

def main():  # wrapping the script call from the console_script
  subprocess.Popen(sys.executable + " " + os.path.join(os.path.dirname(os.path.abspath(__file__)), "rsyncr.py") + " " + " ".join(sys.argv[1:]), shell = True, bufsize = 1).wait()
