
import string
import os

### Force determinism on sets etc.
PYTHONHASHSEED=0

### Logging
from loguru import logger
from loginfer import Loginfer

#
# Global "constants", may be overwritten by command line options
#

# Alphabets
CHAR_SET = set(string.printable)    # character set for edit operations
ALPHABET = set()                    # character set used in training examples, set by lexemize_JSON

# Tokenization control
### TODO: allow multiple escape lengths (e.g., 2 for standard escapes, 6 for UTF-8 escapes)
ESC_LENGTH = 2          # length of character escape sequences

# Directories
TMP_DIR  = '/tmp/lexinfer/'         # tmp dir for intermediate files; trailing / required
OUT_DIR  = './outputs/'             # output dir for json files; trailing / required

# Resource control
NUM_THREADS = os.cpu_count()+4      # max workers for ThreadPoolExecutor
NUM_ROUNDS  = 20                    # max number of token post-procssing rounds


