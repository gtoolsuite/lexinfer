#############################################################################
#
# Maximum-munch style decomposition of json-file
#
#############################################################################

#
# Imports and configuration
#

### General utilities
import json

### Logging
from loguru import logger
from loginfer import Loginfer

### Token constructors
from tokens import LToken, Keyword, FixedLengthSequence, Operator, OperatorSymbol, Monoid, FreeMonoid, LeftPointedMonoid, IllegalCharacter


#############################################################################
#
# Basic munchers
#
# The following muncher functions check whether json_data[start:] starts 
# with an instance of a meta-token
#
#############################################################################

#####
#
# Keyword
#
#####

def keyword(json_data, start):
    chars  = []
    for i in range(start, len(json_data)):  
        cur   = json_data[i]
        cchar = cur["Value"]
        ### HACK: Explode gets rid of \n <-> \r equivalence
        subst = Monoid.explode(cur["Substitution"])
        ### TODO: relax to allow case-insensitive keywords
        ### TODO: --> this needs parameterization of the token constructor
        if chars == []:
            if {cchar} == subst and cur["Deletion"]["Right"] == 0:
                ### TODO: should probably explode
                right = cur["Insertion"]["Right"]
                if right == "None":
                    # At start of keyword lexeme
                    chars = [cchar]
                elif (i + 1 < len(json_data) and (nxt := json_data[i+1]) and (nchar := nxt["Value"]) and 
                      nxt["Deletion"]["Left"] == 0 and nxt["Substitution"] == nchar and (right == cchar or right == nchar)): 
                    # Found a two character key symbol where first or second character can be inserted after first (e.g., '/*' or '*/')
                    ### TODO: may allow single left deletion from nxt?
                    lexeme = cchar + nchar
                    return (LToken(Keyword(lexeme), start, start+2, lexeme), start+2)
                else:
                    # Found a single-character key symbol
                    return (LToken(Keyword(cchar), start, start+1, cchar), start+1)
            else:
                # Not starting a new keyword lexeme
                return (None, start+1)
        else:
            # Already in a keyword lexeme
            if {cchar} == subst and cur["Deletion"]["Left"] == 0 and cur["Insertion"]["Left"] == "None":
                chars.append(cchar)
            else:
                # text[start:i] is complete keyword
                lexeme = ''.join(chars)
                return ((LToken(Keyword(lexeme), start, i, lexeme)), i)

    return (None, start+1)

#####
#
# Fixed-length sequence
#
# A lexeme is a fixed-length sequence if:
# - no characters can be deleted,
# - substitution sets cannot be singletons,
# - except for the initial position, left-insertion and substitution must be
#   equal (i.e., the final character could be pushed into the subsequent 
#   lexeme).
#
#####

def fixed_length(json_data, start):

    chars, sets  = [], []

    for i in range(start, len(json_data)):  
        cur   = json_data[i]
        cchar = cur["Value"]
        subst = Monoid.explode(cur["Substitution"])
        if cur["Deletion"]["Right"] != 0 or len(subst) <= 1 or not(i == start or Monoid.explode(cur["Insertion"]["Left"]) <= subst) or i == len(json_data)-1:
            # At least one of the conditions is broken, so the current
            # character is no longer part of the fixed length sequence or (or
            # we readched the end of input)
            #
            # TODO: The condition should be  > 1, but that somehow captures wrong lexemes.
            #
            if len(chars) > 2:
                lexeme = ''.join(chars)
                return ((LToken(FixedLengthSequence(sets), start, i, lexeme)), i)
            else:
                return (None, start+1)
        else:
            chars.append(cchar)
            sets.append(subst)

    logger.error("unexpected end of input")


#####
#
# Single-character operator symbols
#
#####

def operator_symbol(json_data, start):
    cur   = json_data[start]
    char  = cur["Value"]
    subst = cur["Substitution"]
    if (cur["Deletion"]["Left"] == 0 and char not in Monoid.explode(cur["Insertion"]["Left"]) and char not in Monoid.explode(cur["Insertion"]["Right"])):
        ### TODO: tighten to check for disjointness between substitutions and insertions?
    # if cur["Deletion"]["Left"] == 0:
        return (LToken(OperatorSymbol(char, Monoid.explode(subst)), start, start+1, char), start+1)
    else:
        return (None, start+1)

### TODO: Doesn't work for AMPL (but works for Space)
def operator_symbol2(json_data, start):
    cur   = json_data[start]
    char  = cur["Value"]
    subst = Monoid.explode(cur["Substitution"])
    if (cur["Deletion"]["Left"] == 0 and Monoid.explode(cur["Insertion"]["Left"]) < subst and Monoid.explode(cur["Insertion"]["Right"]) < subst):
        ### TODO: tighten to check for disjointness between substitutions and insertions?
    # if cur["Deletion"]["Left"] == 0:
        return (LToken(OperatorSymbol(char, subst), start, start+1, char), start+1)
    else:
        return (None, start+1)

# TODO: Not used
def operator(json_data, start):
    cur   = json_data[start]
    char  = cur["Value"]
    subst = Monoid.explode(cur["Substitution"])
    left  = Monoid.explode(cur["Insertion"]["Left"])
    right = Monoid.explode(cur["Insertion"]["Right"])
    if cur["Deletion"]["Left"] == 0 and subst & right == set():
        return (LToken(Operator(subst), start, start+1, char), start+1)
    else:
        return (None, start+1)


#####
#
# Free monoids (e.g., white space); all characters are drawn from the same
# alphabet
#
# Note that if relaxed==False this fails if any substitution or insertion
# fails, or if ayn left/right deletion leaving a non-empty segment fails, for
# example if either of the two cases results in a keyword. For relaxed==False,
# this shrinks the alphabet until it becomes empty and stops when a previously
# seen character needs to be removed from the alphabet; this means it may split
# off prefixes that are keywords.
#
#####

def free_monoid(json_data, start, relaxed=False):

    # Find the alphabet allowing the longest match, and the corresponding match
    # if relaxed == False, all edit tests need to give the same results
    seen  = {json_data[start]["Value"]}
    subst = Monoid.explode(json_data[start]["Substitution"])
    left  = Monoid.explode(json_data[start]["Insertion"]["Left"])
    right = Monoid.explode(json_data[start]["Insertion"]["Right"])

    alphabet = subst & left & right

    ### TODO: need to stop shrinking the alphabet and terminate monoid when we need to exclude a character that has already occured
    j = start + 1
    while j < len(json_data):

        # Break and stop when alphabet has become too small to capture all seen characters
        seen |= {json_data[j]["Value"]}
        if not seen <= alphabet:
            break

        subst = Monoid.explode(json_data[j]["Substitution"])
        left  = Monoid.explode(json_data[j]["Insertion"]["Left"])
        right = Monoid.explode(json_data[j]["Insertion"]["Right"])

        next_chars = subst & left & right

        # Check whether character at next position can still be matched with alphabet collected so far
        if relaxed:
            # if relaxed == True, the alphabet isn't determined by the first character
            # but can shrink to a later value (but cannot become empty)
            next_alphabet = alphabet & next_chars 
            if next_alphabet == set():
                break
            else:
                alphabet = next_alphabet
        else:
            if alphabet != next_chars:  # implies current char also in alphabet
                break
        j = j + 1

    # Cannot conclude free monoidal structure if only a single character matched 
    if j == start + 1:
        # Generalization at munch time is not a Good Idea 
        # char  = json_data[start]["Value"]
        # subst = Monoid.explode(json_data[start]["Substitution"])
        # left  = Monoid.explode(json_data[start]["Insertion"]["Left"])
        # right = Monoid.explode(json_data[start]["Insertion"]["Right"])
        # if subst <= left & right:
        #     logger.debug(f"Generalizing singleton {char!a} to FreeMonoid({FreeMonoid.implode(subst)!a})")
        return (None, start+1)

    # Check that all elements can be deleted
    for i in range(start, j):
        rdel = int(json_data[i]["Deletion"]["Right"])
        ldel = int(json_data[i]["Deletion"]["Left"])
        if i + rdel + (1 if i == start else 0) < j:
            return (None, start+1)
        if i - ldel - (1 if i == j -1 else 0) >= start:
            return (None, start+1)

    # Check that nothing went wrong with relaxation
    lexeme = ''.join(json_data[i]["Value"] for i in range(start, j))
    if (c := next((c for c in lexeme if c not in alphabet), None)) and c != None:
        if relaxed:
            logger.debug(f"Monoid lexeme {lexeme!a} contains character {c!a} not in alphabet {Monoid.implode(alphabet)!a}, skipping")
        else:
            logger.warning(f"Monoid lexeme {lexeme!a} contains character {c!a} not in alphabet {Monoid.implode(alphabet)!a}, skipping")
        return (None, start+1)
    else:
        return (LToken(FreeMonoid(alphabet), start, j, lexeme), j)

### Wrapper function
def free_monoid_relaxed(json_data, start):
    return free_monoid(json_data, start, True)


#####
#
# Left pointed monoids (e.g., identifiers); first character is from a subset of the alphabet
#
#####

def left_pointed_monoid(json_data, start, relaxed=False):

    if start + 1 == len(json_data):
        return (None, start+1)

    item  = json_data[start]
    char  = item["Value"]
    subst = Monoid.explode(item["Substitution"])
    left  = Monoid.explode(item["Insertion"]["Left"])
    right = Monoid.explode(item["Insertion"]["Right"])

    alpha = subst & left & right
    if char not in alpha:
        return (None, start+1)

    # Take the alphabet from the second character position
    j = start + 1
    item  = json_data[j]
    subst = Monoid.explode(item["Substitution"])
    left  = Monoid.explode(item["Insertion"]["Left"])
    right = Monoid.explode(item["Insertion"]["Right"])
    alphabet = subst & left & right

    # nchar  = item["Value"]
    # logger.debug(f"({relaxed}) initials at position {start} ({char!a}): {Monoid.implode(alpha)}")
    # logger.debug(f"({relaxed}) alphabet at position {start+1} ({nchar!a}): {Monoid.implode(alphabet)}")

    if not (alpha <= alphabet):
        # logger.debug(f"initials not a subset of alphabet, extra characters: {Monoid.implode(alpha - alphabet)}")
        return (None, start+1)

    lexeme = [char]
    while j < len(json_data):
        # Search until the alphabet changes (materially)
        item  = json_data[j]
        char  = item["Value"]
        subst = Monoid.explode(item["Substitution"])
        left  = Monoid.explode(item["Insertion"]["Left"])
        right = Monoid.explode(item["Insertion"]["Right"])
        if relaxed:
            # Shrink alphabet, check that we are not "over-shrinking"
            beta = subst & left & right
            ### TODO: this may be wrong...
            ### if (set(lexeme) | {char}) <= alphabet & beta and alpha <= alphabet & beta and beta <= alphabet:
            if (set(lexeme) | {char}) <= alphabet & beta and beta <= alphabet:
                alphabet &= beta
                lexeme.append(char)
                j = j + 1
            else:
                # logger.debug(f"breaking loop at {j}, matched {lexeme!a}, next char is {char!a}\nalpha:    {Monoid.implode(alpha)}, \nbeta:     {Monoid.implode(beta)}, \nalphabet: {Monoid.implode(alphabet)}")
                break
        else: 
            if char in alphabet and alphabet == subst & left & right:
                lexeme.append(char)
                j = j + 1
            else:
                # logger.debug(f"breaking loop at {j}, matched {lexeme!a}")
                break

    # First character set must be proper non-trivial subset; fail if equal or just single character
    if alpha & alphabet == alphabet or len(alpha) == 1:
        return (None, start+1)

    ldel=json_data[j-1]["Deletion"]["Left"]
    if j - ldel - 1 == start and ldel > 0:
        # do not extrapolate from single character lexeme 
        # return (LToken(LeftPointedMonoid(''.join(sorted(alpha)), ''.join(sorted(alphabet))), start, j, ''.join(lexeme)), j)
        return (LToken(LeftPointedMonoid(alpha & alphabet, alphabet), start, j, ''.join(lexeme)), j)
    else:
        return (None, start+1)

### Wrapper function
def left_pointed_monoid_relaxed(json_data, start):
    return left_pointed_monoid(json_data, start, True)


#####
#
# illegal character - to be used as default
#
#####

def illegal_character(json_data, start):
    char  = json_data[start]["Value"]
    subst = json_data[start]["Substitution"]
    return (LToken(IllegalCharacter(char, subst), start, start+1, char), start+1)
    # return (LToken(IllegalCharacter(char), start, start+1, char), start+1)


#############################################################################
#
# Muncher
#
#############################################################################


#
# Pick the maximum-length from a list of munches; for ties, pick the first munch
#
def maximum_munch(maximum, munches):
    if munches == []:
        return maximum
    munch_t, i = maximum
    _,       j = munches[0]
    if munch_t == None or j > i:
        return maximum_munch(munches[0], munches[1:])
    else:
        return maximum_munch(maximum, munches[1:])


#
# Maximum-munch split of the entries of a given JSON file using a list of munchers
#
def munch_json(fpath, entries, munchers):

    lexemes = []
    failed  = 0

    pos = 0
    while pos < len(entries):
        # Cannot use enumerate-loop because body updates pos and skips processed entries
        # let all munchers take a bite, then pick the maximum
        munches = [m(entries, pos) for m in munchers]
        logger.debug(f"Munches: {munches!r}")
        token, pos = maximum_munch((None, pos+1), munches)
        logger.debug(f"Munched: {token!r}")
        if token == None:
            logger.error(f"Could not match token at {fpath}:{pos}")
        elif isinstance(token.token, IllegalCharacter):
            logger.debug(f"Could not match character {token.token.char!a} at {fpath}:{pos-1}")
            failed = failed + 1
            lexemes.append(token)
        else:
            lexemes.append(token)

    return (lexemes, failed)


#############################################################################
#
# Main function
#
#############################################################################

### TODO: Check whether swapping free and left-pointed monoids is better
__munchers = [keyword, fixed_length, free_monoid, left_pointed_monoid, free_monoid_relaxed, left_pointed_monoid_relaxed, operator_symbol, illegal_character]

def lexemize_json(fpath):

    logger.info(f"Splitting file {fpath}")

    with open(fpath, 'r') as file:
        entries = json.load(file)

    lexemes, failed = munch_json(fpath, entries, __munchers)

    logger.log("DETAIL", f"Found {len(lexemes)} lexemes, could not match {failed}/{len(entries)} characters")
    logger.success(f"Splitting file {fpath}")

    return (fpath, entries, lexemes)

