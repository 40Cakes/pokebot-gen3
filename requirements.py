import sys
import subprocess

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "./requirements.txt"])
except Exception as e:
    print(str(e))

input("Press enter to continue...")