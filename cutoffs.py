from tokens   import TokenT, FreeMonoid, LeftPointedMonoid, GuardedMagma, SplitMagma
from comments import Comment
from strings  import String

### Logging
from loguru import logger
from loginfer import Loginfer

#
# Cutoff values, may be overwritten by command line options
#

### Proper default values are set by argparse
CUTOFF = {}
CUTOFF['MAGMA']    = 0     # remove all magmas with as many or fewer occurrences (unless there's a specific smaller cutoff)
CUTOFF['MONOID']   = 0
CUTOFF['LPM']      = 0     # Left-pointed monoids
CUTOFF['STRING']   = 0
CUTOFF['COMMENT']  = 0
CUTOFF['RCOMMENT'] = 0     # Recursive comments; should really never be cutoff unless something goes wrong
CUTOFF['GM']       = 0     # Guarded Magmas
CUTOFF['SM']       = 0     # Split Magmas

def get_cutoff(key):
    #logger.warning(f"getting cutoff for {key}")
    _key = _get_cutoff_key(key)
    if isinstance(_key, str):
        #logger.warning(f"returning cutoff for {_key}={CUTOFF[_key]}")
        return CUTOFF[_key]
    else:
        #logger.warning(f"returning default cutoff for {_key}")
        return 0
def set_cutoff(key, value):
    #logger.warning(f"setting cutoff for {key} to {value}")
    _key = _get_cutoff_key(key)
    if isinstance(_key, str):
        #logger.warning(f"set cutoff for {_key} to {value}")
        CUTOFF[_key] = value

def _get_cutoff_key(token):
    if isinstance(token, FreeMonoid):
        return 'MONOID'
    elif isinstance(token, LeftPointedMonoid):
        return 'LPM'
    elif isinstance(token, String):
        return 'STRING'
    elif isinstance(token, Comment) and not token.recursive:
        return 'COMMENT'
    elif isinstance(token, Comment) and token.recursive:
        return 'RCOMMENT'
    elif isinstance(token, GuardedMagma):
        return 'GM'
    elif isinstance(token, SplitMagma):
        return 'SM'
    else:
        return token
