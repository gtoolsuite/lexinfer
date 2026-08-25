#############################################################################
#
# Generally useful methods
#
#############################################################################

#
# Imports and configuration
#

### General utilities

### Logging
from loguru import logger
from loginfer import Loginfer

### Token constructors
from tokens import LToken, Keyword, OperatorSymbol, Monoid, FreeMonoid, LeftPointedMonoid, GuardedMagma, IllegalCharacter


#############################################################################
#
# Auxiliary 
#
#############################################################################

#####
#
# Check whether the lexeme list starts with a given guard string. Split monoid
# lexemes if necessary. Return remaining lexemes or None if prefix is not
# found. 
#
#####
def split_prefix(guard, lexemes):

    if guard == "":
        return lexemes

    if lexemes == [] or guard == None:
        return None

    fst = lexemes[0]
    
    if guard.startswith(fst.lexeme):
        return split_prefix(guard[len(fst.lexeme):], lexemes[1:])

    # Try to split next character off a monoid
    hd, tl = fst.split_monoid(set(guard[0]))
    if hd == None:
        return None
    elif tl == None:
        return split_prefix(guard[1:], lexemes[1:])
    else:
        return split_prefix(guard[1:], [tl] + lexemes[1:])

