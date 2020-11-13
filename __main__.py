import sys

v = sys.version_info
if v.major < 3 or v.minor < 8:
    print('Error: Please use Python3.8 or above',file=sys.stderr)
    sys.exit(1)

if sys.platform=='win32':
    print('Error: Windows is not supported. Please use MacOS or Linux instead',file=sys.stderr)
    sys.exit(1)
    
from ui import main
main()
