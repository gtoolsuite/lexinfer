#############################################################################
#
# Tokenization of one or more given JSON file(s)
#
#############################################################################

#
# Imports and configuration
#

PYTHONHASHSEED = 0

### General utilities
import argparse
from collections import Counter
import copy
import glob
import json
import os
import sys

### Logging
from loguru import logger
from loginfer import Loginfer

### Token constructors
from tokens import LToken, TokenT, IllegalCharacter, Keyphrase, Keyword, FixedLengthSequence, Operator, OperatorSymbol, Magma, Monoid, FreeMonoid, LeftPointedMonoid, GuardedMagma, SplitMagma

### Maximum munch
from muncher import lexemize_json

### Reducers
from comments import Comment, strict_comment, relaxed_comment, line_comment, nested_comment, comment_instances, comment_segments, basic_comment, gobble_comment_instances
from strings  import String, string_literal, string_instances, string_literal_with_escapes, string_literal_with_escaped_quotes, string_escape, string_gobble_escapes, string_unwrap_escapes, string_merge_escapes, string_gobble_empty_strings, string_merge_free_monoids, reclassify_comment_as_string, string_merge_escape_sequences, resolve_inconsistent_strings

### Conversion into ANTLR lexer
### TODO: refactor into common main
from lex import produce_lex

# Global "constants", may be overwritten by command line options
from config  import CHAR_SET, ALPHABET, NUM_ROUNDS
from cutoffs import set_cutoff
# from config import MAGMA_CUTOFF, MONOID_CUTOFF, LPM_CUTOFF, STRING_CUTOFF, COMMENT_CUTOFF, RCOMMENT_CUTOFF, GM_CUTOFF, SM_CUTOFF

### Increase default limit to process larger JSON files
sys.setrecursionlimit(100000)


#############################################################################
#
# Driver functions to post-process tokens and lexemes, fixing up decomposition shortcomings
#
#############################################################################

#
# Reduce a single list of lexemes 
#
# reduce applies a simple reducer functions to a single list of lexemes; each
# reducer takes the file path and json data of the file, the list of lexemes,
# and a global info, and returns a reduced list of lexemes
#
def reduce(reducer, fixpoint, fpath, json_data, lexemes, info=None):

    logger.debug(f"Token post-processing, running {reducer.__name__} on {fpath}")

    # Run reducer and collect results
    reduced_lexemes = reducer(json_data, lexemes, info)

    # General sanity checks, run after each reducer step to identify potential
    # problems early on
    segmentation_gap_check(fpath, reducer, reduced_lexemes)
    lexeme_check(reducer, reduced_lexemes)

    # Reduce to fixpoint, if necessary. Return a result triple
    if fixpoint and reduced_lexemes != lexemes:
        logger.debug(f"Recursing reducer {reducer.__name__}")
        return reduce(reducer, fixpoint, fpath, json_data, reduced_lexemes, info)
    else:
        return (fpath, json_data, reduced_lexemes)


#
# Globally reduce the list of results using all steps
#
def reduce_all(step, results):

    (collector, reducer, fixpoint) = step

    logger.log("DETAIL", f"Token post-processing, running {reducer.__name__}")

    # Collect info only ones for all files
    info = collector(results)
    logger.debug(f"Calling {reducer.__name__}")
    reduced_results = [reduce(reducer, fixpoint, fpath, json_data, lexemes, info) for (fpath, json_data, lexemes) in results]

    return reduced_results


#############################################################################
#
# Sanity checks
#
#############################################################################

#
# Check for gaps in segmentation
#
def segmentation_gap_check(fpath, reducer, lexemes):
    for i in range(len(lexemes)-1):
        r = lexemes[i].end         # end of first token (+1)
        l = lexemes[i+1].start     # start of second token
        if r != l:
            logger.debug(f"Found gap in {fpath} from {r-1} to {l} between {lexemes[i]!r} and {lexemes[i+1]!r} after running {reducer.__name__}")
            logger.warning(f"Found gap in {fpath} from {r-1} to {l} between {lexemes[i].token!r} and {lexemes[i+1].token!r} after running {reducer.__name__}")
            break


#
# Check that token and lexeme match
#
def lexeme_check(reducer, lexemes):

    rname = reducer.__name__

    for i in range(len(lexemes)):
        t, l, start, end = lexemes[i].token, lexemes[i].lexeme, lexemes[i].start, lexemes[i].end
        header = "Error after running {0}, lexeme {1!r}".format(rname, lexemes[i])
        ### General structure checks
        if t == None:
            logger.error(f"{header} has None token")
            continue
        if l == None:
            logger.error(f"{header} has None text")
            continue
        if l == "":
            logger.error(f"{header} has empty text")
            continue
        if len(l) != end - start:
            logger.error(f"{header} does not match given source positions ({start}:{end})")
        ### Operator symbol checks
        if isinstance(t, OperatorSymbol) and l not in t.subst:
            logger.error(f"{header} inconsistent - operator symbol {l} not in alternatives set {Monoid.implode(t.subst)!a}")
        ### Operator checks
        if isinstance(t, Operator) and t.alternatives == set():
            logger.error(f"{header} inconsistent - operator {t!r} has no alternatives for operator {l!a}")
        ### Monoid checks
        if isinstance(t, Monoid) and (d := set(l) - t.alphabet) and d != set():
            logger.error(f"{header} inconsistent - characters {Monoid.implode(d)!a} not in alphabet {Monoid.implode(t.alphabet)!a}")
        if isinstance(t, LeftPointedMonoid) and not(t.initials <= t.alphabet):
            logger.error(f"{header} inconsistent - initials are not a subset of alphabet")
        ### Guarded Magma checks
        if isinstance(t, GuardedMagma) and t.left != None and l[:len(t.left)] != t.left:
            logger.error(f"{header} inconsistent - {t.__class__.__name__} does not start with left guard {t.left!a}")
        if isinstance(t, GuardedMagma) and t.right != None and l[-len(t.right):] != t.right:
            logger.error(f"{header} inconsistent - {t.__class__.__name__} does not end with right guard {t.right!a}")
        ### String checks
        if isinstance(t, String) and t.left != None and t.right != None:
            if len(t.left) == 1 and None != next((i for i, x in enumerate(l[1:-(len(t.right))]) if x == t.left and l[i] != t.escape_chr), None):
                logger.error(f"{header} inconsistent - String contains un-escaped left guard {t.left!a}")
            if len(t.right) == 1 and None != next((i for i, x in enumerate(l[len(t.left):-1]) if x == t.right and l[i-len(t.left)+1] != t.escape_chr), None):
                logger.error(f"{header} inconsistent - String contains un-escaped right guard {t.right!a}")


#
# Warn about inconsistent string tokens
#
def warn_string_incompatible_tokens(stage, results):

    occs    = collect_lexemes(results)
    strings = [s for s in occs.keys() if isinstance(s, String)]

    for i in range(0, len(strings)):
        for j in range(i+1, len(strings)):
            s1 = strings[i]
            s2 = strings[j]
            if s1.left == s2.left and s1.right == s2.escape_chr and s1.escape_chr == s2.right:
                logger.warning(f"Found incompatible string tokens {s1!r} ({len(occs[s1])} occurrences) and {s2!r} ({len(occs[s2])} occurrences)")


#
# Check monoid alphabets, warn about keywords and operators as characters, and unused characters
#
# Should only be run at the end of the inference
#
def warn_monoid_alphabet(results):

    occs   = collect_lexemes(results)
    tokens = occs.keys()
    kw_chars, op_chars = single_char_symbols(tokens)

    for m in tokens:
        if isinstance(m, Monoid) and (common := m.alphabet & kw_chars) and common != set():
            os = [o for o in occs[m] if set(o) & kw_chars != set()]
            if os == []:
                logger.warning(f"Alphabet of monoid token {m!r} contains single-character keywords {common}, but training set has no actual instances")
            else:
                logger.warning(f"Alphabet of monoid token {m!r} contains single-character keywords {common}, instances are {occs[m]!r}")

    for m in tokens:
        if isinstance(m, Monoid) and (common := m.alphabet & op_chars) and common != set():
            os = [o for o in occs[m] if set(o) & op_chars != set()]
            if os == []:
                logger.warning(f"Alphabet of monoid token {m!r} contains single-character operators {common}, but training set has no actual instances")
            else:
                logger.warning(f"Alphabet of monoid token {m!r} contains single-character operators {common}, instances are {occs[m]!r}")

    for m in tokens:
        if isinstance(m, Monoid):
            occurring = set()
            for o in occs[m]:
                occurring.update(set(o))
            missing = m.alphabet - occurring
            if missing != set():
                logger.warning(f"Alphabet of monoid token {m!r} contains characters {Monoid.implode(missing)}, but training set has no actual instances")



#############################################################################
#
# Reducers for post-processing
#
#############################################################################


#####
#
# Dummy reducer
#
#####

def no_reduction(json_data, lexemes, info=None):
    return lexemes


#####
#
# Merge individual illegal characters (sequences) into larger keyphrases
#
#####

#
# Extend a keyword by incorporating a single preceeding / following unmatched character
#
def extend_keywords_single_char(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]
    fchar = fst.token.single_character()
    schar = snd.token.single_character()

    # Check whether extension yields a lexeme that was recognized as keyword
    # elsewhere, or whether all other character alternatives are recognized as
    # operator symbols and insertions are possible.
    if fchar != None and isinstance(snd.token, Keyword):
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        newkwd = Keyword(fchar + snd.token.lexeme)
        if newkwd in tokens or keyword_extensible(tokens, json_data[fst.start], fchar, "Right"):
            ltoken = LToken(newkwd, fst.start, snd.end, newkwd.lexeme)
            logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {newkwd!r}")
            return extend_keywords_single_char(json_data, [ltoken] + lexemes[2:], tokens)
    elif isinstance(fst.token, Keyword) and schar != None:
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        newkwd = Keyword(fst.token.lexeme + schar)
        if newkwd in tokens or keyword_extensible(tokens, json_data[snd.start], schar, "Left"):
            ltoken = LToken(newkwd, fst.start, snd.end, newkwd.lexeme)
            logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {newkwd!r}")
            return extend_keywords_single_char(json_data, [ltoken] + lexemes[2:], tokens)

    return [fst] + extend_keywords_single_char(json_data, lexemes[1:], tokens)


#
# Check whether the left/right extension by preceding/following character is possible
#
# json_entry is the json data entry for the preceding/following character char;
# an extension is possible if the character's alternatives acutally occurring in
# the training examples are defined as operators and if the extension is maximal.
#
def keyword_extensible(tokens, json_entry, char, direction):
    subst = Monoid.explode(json_entry["Substitution"])
    logger.debug(f"Checking characters {Monoid.implode(subst & ALPHABET - {char})}")
    ### TODO: this is trivially not None
    # opsym = next((o for o in tokens if isinstance(o, OperatorSymbol) and o.subst == subst), None)
    ### TODO: FIXME: hardcoded newline char
    # return (check_operator_symbols(tokens, subst & ALPHABET - {char, '\n'}) and 
    #       json_entry["Insertion"][direction] == "None")
    return (json_entry["Insertion"][direction] == "None")


#
# Extend a keyword by preceeding / following fixed-length sequence
#
def extend_fixed_length_sequences(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    ### TODO: check FLS/FLS combination
    ### TODO: check FLS/opsym combinations
    ### TODO: check multi-character keywords
    if isinstance(fst.token, FixedLengthSequence) and isinstance(snd.token, Keyword) and len(snd.lexeme) == 1:
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        if json_data[snd.start]["Insertion"]["Left"] == "None":
            newkwd = FixedLengthSequence(fst.token.charsets + [set(snd.lexeme)])
            ltoken = LToken(newkwd, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {newkwd!r}")
            return extend_fixed_length_sequences(json_data, [ltoken] + lexemes[2:], tokens)
    elif isinstance(fst.token, Keyword) and len(fst.lexeme) == 1 and isinstance(snd.token, FixedLengthSequence):
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        if json_data[snd.start]["Insertion"]["Left"] == "None":
            newkwd = FixedLengthSequence([fst(snd.lexeme)] + snd.token.charsets)
            ltoken = LToken(newkwd, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {newkwd!r}")
            return extend_fixed_length_sequences(json_data, [ltoken] + lexemes[2:], tokens)

    return [fst] + extend_fixed_length_sequences(json_data, lexemes[1:], tokens)

#
# Merge consecutive illegal characters into existing keyword
#
# This can happen if a keyword is only recognized as such in certain contexts,
# but not in others (e.g., due to weak syntax checking by the SUT). 
#
# Note that some languages consider some sequences only as keywords in some
# syntactic contexts (e.g., Javascript's unreserved or contextually reserved
# keywords), but these are then typically recognized as magmas, not sequences
# of individual characters.
#
def extend_keywords_multi_char(json_data, lexemes, tokens):

    if lexemes == []:
        return []

    # Find longest prefix of illegal characters
    # lstpos, lexeme = illegal_segment(lexemes, 0)
    lstpos, lexeme = fixed_segment(lexemes, 0)
    if lstpos < 2:
        return [lexemes[0]] + extend_keywords_multi_char(json_data, lexemes[1:], tokens)
    logger.debug(f"Trying to merge {[l.token for l in lexemes[0:lstpos]]!r} into keyword {lexeme!r}, lstpos is {lstpos}")

    # Find longest prefix that has been defined as keyword elsewhere
    while lstpos > 1:
        if (newlex := ''.join([l.lexeme for l in lexemes[0:lstpos]])) and (newkwd := Keyword(newlex)) and newkwd in tokens:
            ltoken = LToken(newkwd, lexemes[0].start, lexemes[lstpos-1].end, newlex)
            logger.log("DETAIL", f"Merging {[l.token for l in lexemes[0:lstpos]]!r} into keyword {newkwd!r}")
            return [ltoken] + extend_keywords_multi_char(json_data, lexemes[lstpos:], tokens)
        lstpos -= 1

    return [lexemes[0]] + extend_keywords_multi_char(json_data, lexemes[1:], tokens)

#
# Merge consecutive illegal characters into (potentially new) operator symbol
#
# An operator n-gram is a sequence of n characters, where not all combinations
# are necessarily legal.
#
def find_operator_ngrams(json_data, lexemes, info=None):

    if lexemes == []:
        return []

    fst     = json_data[lexemes[0].start]
    fst_pos = fst["Position"]
    fst_del = fst["Deletion"]["Right"]

    # Compute characters that could be consumed by the preceding token
    # (and can thus "bleed" into the operator from the left); if the first
    # character cannot be deleted or substituted, this is empty.
    left_chars = Monoid.explode(fst["Insertion"]["Left"]) & Monoid.explode(fst["Substitution"])

    # Find longest prefix segment of illegal characters
    endpos, lexeme = illegal_segment(lexemes, 0)

    while endpos > 1:
        logger.debug(f"Checking merge of {lexemes[0:endpos]!a} into operator")
        no_op = False
        lst     = json_data[lexemes[endpos-1].start]
        lst_pos = lst["Position"]
        lst_del = lst["Deletion"]["Left"]
        # Check that first and current last position are the operator ends
        if (fst_pos + fst_del > lst_pos) or (lst_pos - lst_del < fst_pos):
            logger.debug(f"Deletions from {fst_pos} ({fst_del}) or {lst_pos} ({lst_del}) possibly going too far, skipping")
            return [lexemes[0]] + find_operator_ngrams(json_data, lexemes[1:], info)
        # Check that no surrounding characters can bleed into the lexeme
        chars = left_chars | (Monoid.explode(lst["Insertion"]["Right"]) & Monoid.explode(lst["Substitution"]))
        i = endpos - 1
        while i > 0 and not no_op:
            bleed = chars & Monoid.explode(json_data[fst_pos+i]["Insertion"]["Left"])
            if bleed != set():
                logger.debug(f"Insertion of surrounding characters {Monoid.implode(bleed)} possible at position {fst_pos+i}, skipping")
                no_op = True
            if i < endpos - 1:
                bleed = chars & Monoid.explode(json_data[fst_pos+i]["Insertion"]["Left"])
                if bleed != set():
                    logger.debug(f"Substitution of surrounding characters {Monoid.implode(bleed)} possible at position {fst_pos+i}, skipping")
                    no_op = True
            i -= 1
        if not no_op:
            ### TODO: check whether we can find multiple instances via substitutions?
            ltoken = LToken(Operator(lexeme[0:endpos]), lexemes[0].start, lexemes[endpos-1].end, lexeme[0:endpos])
            logger.log("DETAIL", f"Merging {[l.token for l in lexemes[0:endpos]]!r} into operator {ltoken.token!r}")
            return [ltoken] + find_operator_ngrams(json_data, lexemes[endpos:], info)
        else:
            endpos -= 1

    return [lexemes[0]] + find_operator_ngrams(json_data, lexemes[1:], info)


#
# Replace a fixed-length sequence by a keyword if the lexeme is used as one elsewhere
#
def replace_fixed_length_by_keyword(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):
        if isinstance(l.token, FixedLengthSequence) and (newkey := Keyword(l.lexeme)) and newkey in tokens:
            logger.log("DETAIL", f"Replacing {l.token!r} by {newkey!r}")
            lexemes[i] = LToken(newkey, l.start, l.end, l.lexeme)

    return lexemes


#
# Replace a monoid by a keyword if the lexeme is used as one elsewhere
#
def replace_monoid_by_keyword(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):
        if isinstance(l.token, Monoid) and (newkey := Keyword(l.lexeme)) and newkey in tokens:
            logger.log("DETAIL", f"Replacing {l.token!r} by {newkey!r}")
            lexemes[i] = LToken(newkey, l.start, l.end, l.lexeme)

    return lexemes


#####
#
# Identify guarded and split magmas
#
#####

#
# Find split magmas
#
# TODO: check for right guard (e.g., to allow trailing sigils like bit-width
#       denotations on reals)
#
def find_split_magmas(json_data, lexemes, tokens):

    if len(lexemes) < 3:
        return lexemes

    fst, snd  = lexemes[0], lexemes[1]
    # start is first index position of split magma, curr points to a FreeMonoid (or anything that can stand in for it)
    # if isinstance(fst.token, IllegalCharacter):
    if isinstance(fst.token, IllegalCharacter) or (isinstance(fst.token, Keyphrase) and len(fst.lexeme) > 1):
        alphabet = __get_magma_alphabet(snd.token)
        if alphabet == None:
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        left, curr, mono = fst.lexeme, 1, snd
    else:
        alphabet = __get_magma_alphabet(fst.token)
        if alphabet == None:
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        left, curr, mono = None, 0, fst

    logger.debug(f"Checking for possible split magma with alphabet {Monoid.implode(alphabet)} and left guard {left!a}, first token {fst!r}, first segment {mono!r}")

    # Search for segments and splitters, and right guard
    splitters, positions = [], []
    while curr < len(lexemes):

        # curr points to monoid, so find next possible splitter
        splitter, ___segment_alphabet = __find_splitter(alphabet, json_data, lexemes, curr+1)
        if splitter == None or splitter == len(lexemes):
            # logger.debug(f"No splitter segment found")
            break
        # logger.debug(f"Found (next) possible splitter segment {(lexemes[curr+1:splitter])!r}")

        t = lexemes[splitter].token
        # if isinstance(t, FreeMonoid) and t.alphabet == alphabet:
        over_generalized = False
        segment_alphabet = __get_magma_alphabet(t)
        if segment_alphabet == alphabet:
            splitters = splitters + [[l.token for l in lexemes[curr+1:splitter]]]
            positions = positions + [(lexemes[curr+1].start, lexemes[splitter-1].end-1)]
            curr = splitter
            # Need to add splitter
        ### TODO: refactor
        elif segment_alphabet != None and segment_alphabet < alphabet:
            over_generalized = True
            splitters = splitters + [[l.token for l in lexemes[curr+1:splitter]]]
            positions = positions + [(lexemes[curr+1].start, lexemes[splitter-1].end-1)]
            curr = splitter
            # Need to add splitter
        else:
            logger.debug(f"Next token {t!r} not a monoid or has wrong alphabet")
            break

    logger.debug(f"Number of splitter segments found: {len(splitters)}")

    # logger.debug(f"first mono {mono!r}")
    # logger.debug(f"last  mono {lexemes[curr]!r}")
    if splitters == []:
        return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
    ### TODO: this may be subsumed by subsequent check
    if len(splitters) == 1:
        logger.debug(f"split position {positions[0]}")
        l_pos, r_pos  = positions[0]
        splitter      = splitters[0]
        splitterchars = __unfold_splitter(alphabet, splitter)
        if splitterchars == set():
            logger.debug(f"Splitter is stand-alone operator {splitters[0]!r}, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        ssss = Monoid.explode(json_data[l_pos]["Substitution"])
        logger.debug(f"Subst {ssss!a}")
        ### TODO: Not sure the deletion condition is still relevant...
        logger.debug(f"splitter: {splitter}")
        l_del = json_data[(mono.end)-1]["Deletion"]["Left"] 
        r_del = json_data[lexemes[curr].end-1]["Deletion"]["Right"]
        l_lex_l = len(mono.lexeme)
        r_lex_l = len(lexemes[curr].lexeme)
        logger.debug(f"l_del: {l_del}, l_lex_l: {l_lex_l}, r_del: {r_del}, r_lex_l: {r_lex_l}")
        if l_pos != r_pos and json_data[(mono.end)-1]["Deletion"]["Left"] >= len(mono.lexeme) and json_data[lexemes[curr].end-1]["Deletion"]["Right"] >= len(lexemes[curr].lexeme):
            logger.debug(f"Splitter is stand-alone operator {splitters[0]!r}, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        if len(splitter) == 1 and not(alphabet <= Monoid.explode(json_data[l_pos]["Substitution"])):
            logger.debug(f"Splitter is stand-alone operator {splitters[0]!r}, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        l_insert = Monoid.explode(json_data[l_pos]["Insertion"]["Left"])
        r_insert = Monoid.explode(json_data[r_pos]["Insertion"]["Right"])
        l_extras = l_insert - alphabet - splitterchars
        r_extras = r_insert - alphabet - splitterchars
        logger.debug(f"left insertion {l_insert}, right insertion {r_insert}, splitterchars {splitterchars}, alphabet {alphabet}")
    ### TODO: not working, so simply protocol
    #     if not(l_insert < alphabet | splitterchars and r_insert <  alphabet | splitterchars):
    #         logger.warning(f"Splitter may be stand-alone operator {splitters[0]!r}")
    #         return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        if FreeMonoid(l_extras) in tokens:
            logger.debug(f"Splitter {splitter!r} is stand-alone operator, {l_extras=}, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        if FreeMonoid(r_extras) in tokens:
            if r_lex_l == json_data[r_pos+1]["Deletion"]["Right"]:
                logger.debug(f"Second segment {lexemes[curr]!r} could be optional")
            logger.debug(f"Splitter {splitter!r} is stand-alone operator, {l_extras=}, {r_extras=}, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
        found = False
        ### Check that the magma on either of the two sides is adjacent to the (single) splitter, if it is a (single) keyword
        if len(splitter) == 1 and isinstance(splitter[0], Keyword) and l_insert != alphabet and r_insert != alphabet:
            logger.debug(f"Splitter {splitter!r} is not adjacent to magma, magma dropped")
            return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
    else:
        for s in splitters:
            for t in s:
                if isinstance(t, Keyword):
                    logger.debug(f"Keywords not allowed as compound splitters, magma dropped")
                    return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)

    logger.debug(f"Splitter segments found: {splitters!r}")
    logger.debug(f"Splitter positions {positions}")
    if over_generalized == True:
        logger.warning(f"Constructing split magma over alphabet {Monoid.implode(alphabet)} with smaller segment alphabet(s), over-generalizing")
    splitter_segments = [_unfold_splitter(json_data, alphabet, s, p) for (s, p) in zip(splitters, positions)]
    if set() in splitter_segments:
        logger.debug(f"Splitter segment(s) empty, magma dropped")
        return [lexemes[0]] + find_split_magmas(json_data, lexemes[1:], tokens)
    newtok = SplitMagma(alphabet, left, None, splitter_segments)
    newlex = ''.join([l.lexeme for l in lexemes[0:curr+1]])
    ltoken = LToken(newtok, lexemes[0].start, lexemes[curr].end, newlex)
    logger.debug(f"Merged {lexemes[0:curr+1]!r} into {ltoken!r}")
    logger.log("DETAIL", f"Merged {lexemes[0:curr+1]!r} into split magma {newtok!r}")
    # return lexemes[0:curr+1] + find_split_magmas(json_data, lexemes[curr+1:], tokens)
    return [ltoken] + find_split_magmas(json_data, lexemes[curr+1:], tokens)


# Get the magma's alphabet from the first suitable token; return None if token isn't suitable
def __get_magma_alphabet(token):
    if isinstance(token, Monoid):
        ### TODO: this is too general, should perhaps refactor SplitMagma to allow left-pointed monoids?
        return(token.alphabet)
    elif isinstance(token, OperatorSymbol):
        return(token.subst)
    elif isinstance(token, Operator):
        return(token.alternatives)
    else:
        return None

# Find the longest initial sequence that serves as splitter (must be fixed-length elements, with suitable insertions)
def __find_splitter(alphabet, json_data, lexemes, start):
    end = start
    segment_alphabet = alphabet
    while end < len(lexemes):
        t = lexemes[end].token
        # Should not capture keywords
        ### TODO: allowing keywords merges too much stuff together
        ### if not(isinstance(t, Operator) or isinstance(t, IllegalCharacter) or (isinstance(t, Keyword) and len(lexemes[end].lexeme)==1)):
        if __get_magma_alphabet(t) == alphabet or not(isinstance(t, Operator) or isinstance(t, IllegalCharacter) or (isinstance(t, Keyword) and len(lexemes[end].lexeme)==1)):
            break
        end += 1

    # No splitter segment found
    if end == start:
        return None, None

    logger.debug(f"Found possible splitter segment {lexemes[start:end]}")

    # Splitter is full alphabet, so abort
    if end == start+1 and Monoid.explode(json_data[lexemes[start].start]["Substitution"]) == CHAR_SET:
        logger.warning(f"Single-character splitter with full char set, ignoring")
        return None, None

    # Check that splitter elements not part of the alphabet
    for i in range(start, end):
        if set(lexemes[i].lexeme) <= alphabet:
            logger.debug(f"Splitter element {lexemes[i]!r} is in alphabet")
            return None, None

    # Check that start must immediately follow the monoid
    left = Monoid.explode(json_data[lexemes[start].start]["Insertion"]["Left"])
    if not(left >= alphabet):
        logger.debug(f"No (further) splitter segment found - initial token {lexemes[start].token!r} has wrong left insertion {Monoid.implode(left)}")
        return None, None

    # Check that end can only be followed the monoid characters
    right = Monoid.explode(json_data[lexemes[end-1].end-1]["Insertion"]["Right"])
    if not(right >= alphabet):
        ### Can't make this work quickly, so disable...
        ### segment_alphabet &= right
        ### if True or segment_alphabet == set():
        logger.debug(f"No splitter segment found - final token {lexemes[end-1].token!r} has wrong right insertion {Monoid.implode(right)}")
        return None, None

    # Check that nothing can be inserted between the splitter elements
    for i in range(start, end-1):
        right = Monoid.explode(json_data[lexemes[i].end-1]["Insertion"]["Right"])
        if isinstance(lexemes[i].token, IllegalCharacter) and right != set() and right != alphabet:
            logger.debug(f"No splitter segment found - intermediate token {lexemes[i].token!r} has illegal right insertion {Monoid.implode(right)}")
            return None, None
        elif not isinstance(lexemes[i].token, IllegalCharacter) and right != set():
            logger.debug(f"No splitter segment found - intermediate token {lexemes[i].token!r} has illegal right insertion {Monoid.implode(right)}")
            return None, None

    return end, segment_alphabet

#
#
#
### TODO: this doesn't work
def _unfold_splitter(json_data, alphabet, splitter, positions):
    l_pos, r_pos = positions
    # Need to copy, otherwise we impact the original lexemes
    splitter_copy = copy.deepcopy(splitter)
    bases = [__alternatives(alphabet, s) for s in splitter_copy]
    # Remove elements from the fringes
    bases[0]               -= Monoid.explode(json_data[l_pos]["Insertion"]["Left"])
    bases[len(splitter)-1] -= Monoid.explode(json_data[r_pos]["Insertion"]["Right"])
    return __unfold_bases(bases) 

def __unfold_bases(bases):
    if len(bases) == 1:
        return bases[0]
    else:
        return {x + y for x in bases[0] for y in __unfold_bases(bases[1:])}

def __unfold_splitter(alphabet, s):
    if len(s) == 1:
        return __alternatives(alphabet, s[0])
    else:
        return {x + y for x in __alternatives(alphabet, s[0]) for y in __unfold_splitter(alphabet, s[1:])}

def __alternatives(alphabet, token):
    if isinstance(token, IllegalCharacter):
        return token.subst - alphabet
    elif isinstance(token, Operator):
        return token.alternatives
    elif isinstance(token, Keyword):
        return {token.lexeme}
    else:
        raise IncompleteImplementation

#
# Find guarded magmas
#

### TODO: GuardedMagmas should allow lpms, not just free monoids

def find_left_guarded_magmas(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    # Find longest prefix segment of illegal characters 
    ### TODO: this breaks the magma -digits+ in gson and json-antlr
    endpos, lexeme = illegal_or_op_segment(lexemes, 0)
    # endpos, lexeme = illegal_segment(lexemes, 0)
    if endpos > 0:
        logger.debug(f"Checking merge of {lexemes[0:endpos]!a} into left guard")
    ### Don't check insertions
    # for i in range(endpos):
    #     if json_data[lexemes[i].end-1]["Insertion"]["Right"] != "None":
    #         return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)

    if endpos >= len(lexemes):
        return lexemes

    if endpos > 1:
        l_guard_r, body = endpos-1, endpos
        fst, snd  = lexemes[0], lexemes[endpos]
    else:
        l_guard_r, body = 0, 1
        fst, snd  = lexemes[0], lexemes[1]

    alphabet = __get_magma_alphabet(snd.token)

    # Check whether left-guard is too long
    while alphabet == None and endpos > 1:
        endpos -= 1
        l_guard_r, body, snd = endpos-1, endpos, lexemes[endpos]
        alphabet = __get_magma_alphabet(snd.token)

    # if isinstance(fst.token, Magma) or isinstance(fst.token, Keyword) or alphabet == None:
    ### TODO: the length-check on keywords is a hack...
    if isinstance(fst.token, Magma) or (isinstance(fst.token, Keyword) and len(fst.lexeme) ==1) or alphabet == None:
        return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
    if len(lexemes) > body+1 and (trd := lexemes[body+1]) and not isinstance(trd.token, Magma):
        right, end = trd.lexeme, l_guard_r + body + 2
    else:
        right, end = None, l_guard_r + body + 1

    # Construct left guard lexeme
    left = ''.join([l.lexeme for l in lexemes[0:l_guard_r+1]])
    logger.debug(f"Checking for guarded magma with left guard {left!r} and right guard {right!a} over alphabet {Monoid.implode(alphabet)}, first token {fst!r}")

    # Check that nothing else can come between guards and monoid
    l_follow  = Monoid.explode(json_data[lexemes[l_guard_r].end-1]["Insertion"]["Right"])
    l_precede = Monoid.explode(json_data[lexemes[0].start]["Insertion"]["Left"])
    if not(l_follow <= alphabet):
        # follow can be subset because mono-like structure can be left-pointed
        if not(isinstance(snd.token, FreeMonoid) and len(snd.lexeme) == 1 and alphabet < l_follow and LeftPointedMonoid(alphabet, l_follow) in tokens):
            logger.debug(f"Left guard {lexemes[0:l_guard_r+1]!r} with follow set {Monoid.implode(l_follow)} not immediately joined to monoid {snd!r}")
            return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
    ### TODO: Why is this equality?
    if l_precede == l_follow:
        logger.debug(f"Left guard {lexemes[0:l_guard_r+1]!r} with precede set {Monoid.implode(l_precede)} and follow set {Monoid.implode(l_follow)} is stand-alone operator")
        return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
    if alphabet <= l_precede:
        logger.debug(f"Alphabet {Monoid.implode(alphabet)} can precede left guard {lexemes[0:l_guard_r+1]!r} with precede set {Monoid.implode(l_precede)}, left guard is stand-alone operator")
        return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
    if right != None:
        if len(right) == 1 and right[0] in alphabet:
            logger.debug(f"Right guard {right!a} in alhpabet {Monoid.implode(alphabet)}")
            return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
        r_precede = Monoid.explode(json_data[trd.start]["Insertion"]["Left"])
        if r_precede != alphabet:
            logger.debug(f"Right guard {trd!r} with precede {Monoid.implode(r_precede)} not immediately joined to monoid {snd!r}, dropping guard")
            right, end = None, l_guard_r + body + 1
    else:
        if body+1 >= len(lexemes):
            logger.debug(f"Body {body+1} reached end of input {len(lexemes)}")
            return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)
        nxt_chr = lexemes[body+1].lexeme[0]
        if nxt_chr in alphabet:
            logger.debug(f"Subsequent character {nxt_chr!a} in alphabet {Monoid.implode(alphabet)}")
            return [lexemes[0]] + find_left_guarded_magmas(json_data, lexemes[1:], tokens)

    logger.debug(f"{endpos=}, {end=}, {right=}")

    ### Some sanity checks
    if l_guard_r == 0 and set(fst.lexeme) <= alphabet:
        ### Simply warn and continue, otherwise we may get weird monos; --lex can deal with this
        logger.warning(f"Left guard {fst!r} in alphabet {Monoid.implode(alphabet)}")
    if isinstance(snd.token, LeftPointedMonoid):
        logger.warning(f"Constructing guarded magma over left-pointed monoid {snd.token!r}, over-generalizing")

    # Construct token; (do not) fall back to monoid if necessary
    newlex = ''.join([l.lexeme for l in lexemes[0:end]])
    newtok = GuardedMagma(alphabet, left, right)
    ltoken = LToken(newtok, lexemes[0].start, lexemes[end].start, newlex)
    logger.debug(f"Merged {lexemes[0:end]!r} into {ltoken!r}")
    logger.log("DETAIL", f"Merged {lexemes[0:end]!r} into {newtok!r}")
    return [ltoken] + find_left_guarded_magmas(json_data, lexemes[end:], tokens)

### old version
def ___find_guarded_magmas___(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd  = lexemes[0], lexemes[1]
    left, right, start, end = None, None, 0, 1
    alphabet = __get_magma_alphabet(snd.token)
    if isinstance(fst.token, IllegalCharacter) and alphabet != None:
        left, mono = fst, snd
        if len(lexemes) > 2 and (trd := lexemes[2]) and isinstance(trd.token, IllegalCharacter):
            right, start, end = trd, 0, 2

    # Check whether there are actually guards
    if left == None and right == None:
        return [lexemes[0]] + find_guarded_magmas(json_data, lexemes[1:], tokens)

    # Check that nothing else can come between guards and monoid
    left_guard, right_guard = None, None
    if left != None:
        follow = Monoid.explode(json_data[left.end-1]["Insertion"]["Right"])
        ### TODO: not clear this is the right condition
        if not(follow >= alphabet):
            logger.debug(f"Left guard {left!r} not joined to monoid {mono!r}")
            return [lexemes[0]] + find_guarded_magmas(json_data, lexemes[1:], tokens)
        left_guard = left.lexeme
    if right != None:
        precede = Monoid.explode(json_data[right.start]["Insertion"]["Left"])
        if not(precede == alphabet):
            logger.debug(f"Right guard {right!r} not joined to monoid {mono!r}")
            return [lexemes[0]] + find_guarded_magmas(json_data, lexemes[1:], tokens)
        right_guard = right.lexeme

    newtok = GuardedMagma(alphabet, left_guard, right_guard)
    newlex = ''.join([l.lexeme for l in lexemes[start:end+1]])
    ltoken = LToken(newtok, lexemes[start].start, lexemes[end].end, newlex)
    logger.debug(f"Merged {lexemes[start:end+1]!r} into {ltoken!r}")
    logger.log("DETAIL", f"Merged {lexemes[start:end+1]!r} into guarded magma {newtok!r}")
    if start == 1:
        return [fst, ltoken] + find_guarded_magmas(json_data, lexemes[end+1:], tokens)
    else:
        return [ltoken] + find_guarded_magmas(json_data, lexemes[end+1:], tokens)


#
# Version for missing left guard
#
def find_right_guarded_magmas(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    ### TODO: currently limited to a single-character guard, no operators or keywords allowed
    fst, snd  = lexemes[0], lexemes[1]
    if not(isinstance(fst.token, FreeMonoid) and isinstance(snd.token, IllegalCharacter)):
        return [lexemes[0]] + find_right_guarded_magmas(json_data, lexemes[1:], tokens)

    # Check that nothing else can come between guards and monoid; note that the
    # guard may shrink the allowable alphabet of the original monoid
    alpha  = Monoid.explode(json_data[snd.start]["Insertion"]["Left"]) & snd.token.subst
    follow = Monoid.explode(json_data[snd.start]["Insertion"]["Right"])
    if not(alpha <= fst.token.alphabet):
        logger.debug(f"Right guard {snd!r} not joined to monoid {fst!r}")
        return [lexemes[0]] + find_right_guarded_magmas(json_data, lexemes[1:], tokens)
    if not(Monoid.explode(fst.lexeme) <= alpha):
        logger.debug(f"Monoid instance {fst.lexeme!a} cannot be joined to right guard {snd!r}")
        return [lexemes[0]] + find_right_guarded_magmas(json_data, lexemes[1:], tokens)
    if alpha <= follow:
        logger.debug(f"Right guard {snd!r} can be followed by monoid alphabet {Monoid.implode(alpha)}")
        return [lexemes[0]] + find_right_guarded_magmas(json_data, lexemes[1:], tokens)
    
    newtok = GuardedMagma(alpha, None, snd.lexeme)
    ltoken = LToken(newtok, fst.start, snd.end, fst.lexeme + snd.lexeme)
    logger.debug(f"Merged {[fst, snd]!r} into {ltoken!r}")
    logger.log("DETAIL", f"Merged {fst.lexeme!a} and {snd.lexeme!a} into guarded magma {newtok!r}")
    return [ltoken] + find_right_guarded_magmas(json_data, lexemes[2:], tokens)


#####
#
# Re-adjust magmas
#
#####

#
# Merge illegal character into preceding / following monoid 
#
def extend_monoids_single_char(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    ### Don't merge single-character keywords
    if isinstance(fst.token, IllegalCharacter) and not(Keyword(fst.lexeme) in tokens) and isinstance(snd.token, Monoid):
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        chars    = fst.token.subst # Monoid.explode(json_data[fst.start]["Substitution"])
        initials = snd.token.initials
        alphabet = snd.token.alphabet
        if fst.token.char in initials:
            if initials <= chars:
                ltoken = LToken(snd.token, fst.start, snd.end, fst.lexeme + snd.lexeme)
                logger.debug(f"Merging {fst!r} into {snd!r}, new token {ltoken!r}")
                logger.log("DETAIL", f"Merging {fst.token!r} into {snd.token!r}, new lexeme {ltoken.lexeme!a}")
                return extend_monoids_single_char(json_data, [ltoken] + lexemes[2:], tokens)
            elif chars & alphabet != set():
                ltoken = LToken(LeftPointedMonoid(chars & alphabet, alphabet), fst.start, snd.end, fst.lexeme + snd.lexeme)
                logger.debug(f"Merging {fst!r} into {snd!r}, new token {ltoken!r}")
                logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {ltoken.token!r}, new lexeme {ltoken.lexeme!a}")
                return extend_monoids_single_char(json_data, [ltoken] + lexemes[2:], tokens)
    elif isinstance(fst.token, Monoid) and isinstance(snd.token, IllegalCharacter) and not (Keyword(snd.lexeme) in tokens):
        logger.debug(f"Checking merge of {fst!r} and {snd!r}")
        chars    = snd.token.subst # Monoid.explode(json_data[snd.start]["Substitution"])
        alphabet = fst.token.alphabet
        if snd.token.char in alphabet:
            tighten = True
            common = chars & alphabet 
            for c in fst.lexeme + snd.lexeme:
                if c not in common:
                    logger.debug(f"Combined lexeme character {c!a} not in common alphabet {Monoid.implode(common)}, not tightening")
                    tighten = False
                    break
            if tighten:
                if fst.token.initials & common != common and isinstance(fst.token, LeftPointedMonoid):
                    ltoken = LToken(LeftPointedMonoid(fst.token.initials & common, common), fst.start, snd.end, fst.lexeme + snd.lexeme)
                else:
                    ltoken = LToken(FreeMonoid(common), fst.start, snd.end, fst.lexeme + snd.lexeme)
            else:
                ltoken = LToken(fst.token, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Merging {fst!r} into {snd!r}, new token {ltoken!r}")
            logger.log("DETAIL", f"Merging {fst.token!r} and {snd.token!r} into {ltoken.token!r}, new lexeme {ltoken.lexeme!a}")
            return extend_monoids_single_char(json_data, [ltoken] + lexemes[2:], tokens)
        ### This doesn't really work
        # elif isinstance(fst.token, FreeMonoid):
        #     # Check whether free monoid can be turned into a left-pointed monoid; 
        #     mono = next((m for m in monos if isinstance(m, LeftPointedMonoid) and m.initials == fst.token.alphabet and snd.lexeme in m.alphabet), None)
        #     if mono != None:
        #         ltoken = LToken(mono, fst.start, snd.end, fst.lexeme + snd.lexeme)
        #         logger.debug(f"Extending free monoid {fst!r} by {snd!r} to left-pointed monoid {ltoken!r}")
        #         logger.log("DETAIL", f"Extending free monoid {fst.token!r} by {snd.token!r} to left-pointed monoid {ltoken!r}, new lexeme {ltoken.lexeme!a}")
        #         return extend_monoids_single_char(json_data, [ltoken] + lexemes[2:], monos)

    return [fst] + extend_monoids_single_char(json_data, lexemes[1:], tokens)


#
# Merge two adjacent monoid tokens with identical alphabets into a single token
#
def merge_adjacent_identical_monoids(json_data, lexemes, info=None):

    if len(lexemes) <= 1:
        return lexemes

    fst,  snd  = lexemes[0], lexemes[1]
    fstt, sndt = fst.token, snd.token

    if isinstance(fstt, Monoid) and isinstance(sndt, Monoid):
        monoid = None
        if fstt == sndt:
            monoid = fstt
        elif isinstance(fstt, LeftPointedMonoid) and isinstance(sndt, FreeMonoid):
            if fstt.alphabet == sndt.alphabet:
                monoid = fstt
        elif isinstance(fst, FreeMonoid) and isinstance(snd, LeftPointedMonoid):
            if fstt.alphabet == sndt.initial:
                monoid = sndt
        if monoid != None:
            ltoken = LToken(monoid, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Merging monoids {fst!r} and {snd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Merging monoids {fst.token!r} and {snd.token!r} into {monoid!r}, new lexeme {ltoken.lexeme!a}")
            return merge_adjacent_identical_monoids(json_data, [ltoken] + lexemes[2:], info)

    return [fst] + merge_adjacent_identical_monoids(json_data, lexemes[1:], info)


#
# Merge two adjacent monoid tokens with compatible alphabets into a single token
#
def merge_adjacent_monoids(json_data, lexemes, tokens):

    if len(lexemes) <= 1:
        return lexemes

    fst,  snd  = lexemes[0], lexemes[1]
    fstt, sndt = fst.token, snd.token

    if isinstance(fstt, Monoid) and isinstance(sndt, Monoid):
        fsta, snda, monoid = fstt.alphabet, sndt.alphabet, None
        # Check that we are not merging over keyword characters
        # if (c := next((c for c in snda if Keyword(c) in tokens), None)) and c != None:
        #     logger.debug(f"Second token {snd!r} contains keyword character {c!a}, not merging")
        if Keyword(snd.lexeme[0]) in tokens:
            logger.debug(f"Second token {snd!r} starts with keyword character {snd.lexeme[0]!a}, not merging")
            return [fst] + merge_adjacent_monoids(json_data, lexemes[1:], tokens)
        if fstt == sndt:
            monoid = fstt
        elif isinstance(fstt, FreeMonoid) and isinstance(sndt, FreeMonoid) and fsta < snda:
            monoid = LeftPointedMonoid(fsta, snda)
        elif isinstance(fstt, FreeMonoid) and isinstance(sndt, LeftPointedMonoid) and fsta <= sndt.initials:
            monoid = LeftPointedMonoid(fsta, snda)
        elif isinstance(fstt, LeftPointedMonoid) and isinstance(sndt, FreeMonoid) and fsta <= snda and set(snd.lexeme) <= fsta:
            monoid = fstt
        if monoid != None:
            ltoken = LToken(monoid, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Merging monoids {fst!r} and {snd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Merging monoids {fst.token!r} and {snd.token!r} into {monoid!r}, new lexeme {ltoken.lexeme!a}")
            return merge_adjacent_monoids(json_data, [ltoken] + lexemes[2:], tokens)

    return [fst] + merge_adjacent_monoids(json_data, lexemes[1:], tokens)


#
# Unify two adjacent monoid tokens with different alphabets into a single monoid token over the common alphabet
#
def unify_adjacent_monoids(json_data, lexemes, info=None):

    if len(lexemes) <= 1:
        return lexemes

    fst,  snd  = lexemes[0], lexemes[1]
    fstt, sndt = fst.token, snd.token

    if isinstance(fstt, Monoid) and isinstance(sndt, Monoid):
        fsta, snda, monoid = fstt.alphabet, sndt.alphabet, None

        if isinstance(fstt, FreeMonoid) and isinstance(sndt, FreeMonoid):
            if set(fst.lexeme) & snd.token.alphabet == set() or set(snd.lexeme) & fst.token.alphabet == set():
                logger.debug(f"Adjacent monoids {fst!r} and {snd!r} have well-separated lexemes, not joining")
            # logger.debug(f"fst {Monoid.implode(set(fst.lexeme))}, snd {Monoid.implode(set(snd.lexeme))}")
            ### if set(fst.lexeme) <= snda and set(snd.lexeme) <= fsta:
            ### TODO: maybe construct a new free mono with the union alphabet?
            elif set(snd.lexeme) <= fsta:
                monoid = fstt
        elif isinstance(fstt, FreeMonoid) and isinstance(sndt, LeftPointedMonoid):
            pass
        elif isinstance(fstt, LeftPointedMonoid) and isinstance(sndt, FreeMonoid):
            ### Well-separation test 
            if len(fst.lexeme) == 1 and len(snd.lexeme) > 1 and fstt.initials & sndt.alphabet == set():
                logger.debug(f"Adjacent monoids {fst!r} and {snd!r} have well-separated lexemes, not joining")
            elif set(fst.lexeme) <= fstt.initials and fstt.alphabet - fstt.initials == sndt.alphabet:
                ltoken = LToken(FreeMonoid(fstt.initials), fst.start, fst.end, fst.lexeme)
                logger.debug(f"Adjacent monoids {fst!r} and {snd!r} have well-separated lexemes, rebalancing {fst!r} to {ltoken!r}")
                logger.log("DETAIL", f"Adjacent monoids {fstt!r} and {sndt!r} have well-separated lexemes, rebalancing {fstt!r} to {ltoken.token!r}")
                return [ltoken] + unify_adjacent_monoids(json_data, lexemes[1:], info)
            else:
                new_initials = fstt.initials & snda
                new_alphabet = fsta & snda
                ### Try to shrink the common alphabet
                if fst.lexeme[0] in new_initials and set(fst.lexeme + snd.lexeme) <= new_alphabet:
                    if new_initials == new_alphabet:
                        monoid = FreeMonoid(new_alphabet)
                    else:
                        monoid = LeftPointedMonoid(new_initials, new_alphabet)
                ### See whether the left-pointed monoid is already big enough
                else: 
                    if snda < fsta:
                        monoid = fstt
        elif isinstance(fstt, LeftPointedMonoid) and isinstance(sndt, LeftPointedMonoid):
            if fstt.initials < sndt.initials:
                new_alphabet = sndt.initials & fsta & snda
                if fstt.initials < new_alphabet and set(fst.lexeme + snd.lexeme) <= new_alphabet:
                    monoid = LeftPointedMonoid(fstt.initials, new_alphabet)

        if monoid != None:
            ltoken = LToken(monoid, fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}") 
            return unify_adjacent_monoids(json_data, [ltoken] + lexemes[2:], info)

    return [fst] + unify_adjacent_monoids(json_data, lexemes[1:], info)


#
# Unify two adjacent free monoid tokens with different alphabets into a single monoid token over the common alphabet
#
# TODO: Does this ever happen??? Is it even a good thing?
#
def _unify_adjacent_monoids(json_data, lexemes, info=None):

    if len(lexemes) <= 1:
        return lexemes

    fst,  snd  = lexemes[0], lexemes[1]
    fstt, sndt = fst.token, snd.token

    if isinstance(fstt, FreeMonoid) and isinstance(sndt, FreeMonoid):
        if  fstt.alphabet <= sndt.alphabet:
            if  fstt.alphabet == sndt.alphabet:
                ltoken = LToken(FreeMonoid(fstt.alphabet), fst.start, snd.end, fst.lexeme + snd.lexeme)
            else:
                ltoken = LToken(LeftPointedMonoid(fstt.alphabet, sndt.alphabet), fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}")
            return _unify_adjacent_monoids(json_data, [ltoken] + lexemes[2:], info)
        alphabet = fstt.alphabet & sndt.alphabet
        if all(c in alphabet for c in fst.lexeme + snd.lexeme):
            ltoken = LToken(FreeMonoid(alphabet), fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Joining adjacent monoids {fst!r} and {snd!r} into {ltoken!r}") 
            return _unify_adjacent_monoids(json_data, [ltoken] + lexemes[2:], info)

    return [fst] + _unify_adjacent_monoids(json_data, lexemes[1:], info)


#
# Subsume a monoid by a more common one that also matches the entire set of
# occurring lexemes 
#
# TODO: Does this ever happen???
# TODO: Should probably sort by number of occurrences first
# TODO: Should also work for LeftPointedMonoids
#
def subsume_monoids(json_data, lexemes, occurrences):

    for (i, l) in enumerate(lexemes):
        if isinstance(l.token, FreeMonoid):
            l_occs = occurrences[l.token]
            # m = next((m for (m, m_occs) in occurrences.items() if isinstance(m, FreeMonoid) and l_occs < m_occs), None)
            m = next((m for (m, m_occs) in occurrences.items() if isinstance(m, FreeMonoid) and m != l.token and l_occs <= m_occs), None)
            if m != None:
                logger.log("DETAIL", f"Replacing {l.token!r} by {m!r} capturing all instances")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)

    return lexemes


#
# Subsume a monoid instance by a more common one that also matches the entire
# set of occurring lexemes; replace free monoids by either free or left-pointed
# monoids, but try to replace left-pointed ones like for like first.
#
# TODO: Does this ever happen??? --> yes, for GCC
# TODO: Should probably sort by number of occurrences first
# TODO: Should be refactored
#
def subsume_monoid_instances(json_data, lexemes, occurrences):

    for (i, l) in enumerate(lexemes):
        l_occs = occurrences[l.token]
        if isinstance(l.token, FreeMonoid):
            m = next((m for (m, m_occs) in occurrences.items() if isinstance(m, Monoid) and len(l_occs) < len(m_occs) and l.lexeme in m_occs), None)
            if m != None:
                logger.log("DETAIL", f"Replacing instance {l.lexeme!a} of {l.token!r} by more common {m!r} with same instance")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)
        elif isinstance(l.token, LeftPointedMonoid):
            m = next((m for (m, m_occs) in occurrences.items() if isinstance(m, LeftPointedMonoid) and len(l_occs) < len(m_occs) and l.lexeme in m_occs), None)
            if m == None:
                m = next((m for (m, m_occs) in occurrences.items() if isinstance(m, Monoid) and len(l_occs) < len(m_occs) and l.lexeme in m_occs), None)
            if m != None:
                logger.log("DETAIL", f"Replacing instance {l.lexeme!a} of {l.token!r} by more common {m!r} with same instance")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)

    return lexemes


#
# Split left-pointed monoids that start with a single-character keyphrase only
#
def split_left_pointed_monoid(json_data, lexemes, tokens):

    replaced = []

    for l in lexemes:
        if isinstance(l.token, LeftPointedMonoid) and len(l.token.initials) == 1:
            [c] = l.token.initials
            if Keyword(c) in tokens:
                keyw = LToken(Keyword(c), l.start, l.start+1, c)
                ### TODO: go back to singleton
                mono = LToken(FreeMonoid(l.token.alphabet - set([c])), l.start+1, l.end, l.lexeme[1:])
                replaced.append(keyw)
                replaced.append(mono)
                logger.debug(f"Splitting left-pointed mono {l.token!r} starting with keyword {c} into keyword {keyw!r} and free mono {mono!r}")
                logger.log("DETAIL", f"Splitting left-pointed mono {l.token!r} starting with keyword {c} into keyword and free mono {mono.token!r}")
            else:
                replaced.append(l)
        else:
            replaced.append(l)

    return replaced


#
# Smash leftoover monoids into illegal characters
#
def smash_monoids(json_data, lexemes, occurrences):
    replaced = []
    for l in lexemes:
        num_occs = len(occurrences[l.token])
        if isinstance(l.token, FreeMonoid) and num_occs <= MONOID_CUTOFF:
        # if isinstance(l.token, FreeMonoid) and num_occs <= MONOID_CUTOFF and len(l.lexeme) > 1:
            # Don't smash if monoid has been introduced by generalizing illegal character
            logger.log("DETAIL", f"Smashing rare free monoid {l!r} into characters ({num_occs} different lexemes, less than cutoff {MONOID_CUTOFF})")
            __smash_lexeme(replaced, l.lexeme, l.start, l.token.alphabet)
        elif isinstance(l.token, FreeMonoid) and l.token.alphabet == Monoid.explode(CHAR_SET):
            ### TODO: Hack. Need to remove \r from CHAR_SET which is kicked out by explode
            logger.warning(f"Smashing monoid {l!r} over full character set into characters")
            __smash_lexeme(replaced, l.lexeme, l.start, l.token.alphabet)
        elif isinstance(l.token, LeftPointedMonoid) and num_occs <= LPM_CUTOFF:
            logger.warning(f"Smashing rare left-pointed monoid{l!r} ({num_occs} different lexemes, less than cutoff {LPM_CUTOFF})")
            __smash_lexeme(replaced, [l.lexeme[0]], l.start,   l.token.initials)
            __smash_lexeme(replaced, l.lexeme[1:],  l.start+1, l.token.alphabet)
        elif isinstance(l.token, Comment):
            if l.token.recursive:
                if num_occs <= RCOMMENT_CUTOFF:
                    logger.warning(f"Found rare nested comment {l!r}, not smashing ")
                    replaced.append(l)
                else:
                    replaced.append(l)
            else:
                if num_occs <= COMMENT_CUTOFF:
                    logger.warning(f"Smashing rare comment {l!r} ({num_occs} different lexemes, less than cutoff {COMMENT_CUTOFF})")
                    __smash_comment(replaced, l)
                else:
                    replaced.append(l)
        elif isinstance(l.token, String):
            if num_occs <= STRING_CUTOFF and l.token.escape_seq == set():
                logger.warning(f"Smashing rare string {l!r} ({num_occs} different lexemes, less than cutoff {STRING_CUTOFF})")
                ### can reuse smashing comments
                __smash_comment(replaced, l)
            else:
                # logger.warning(f"Found rare string {l!r} with escapes, not smashing ")
                replaced.append(l)
        elif isinstance(l.token, GuardedMagma) and num_occs <= GM_CUTOFF:
            logger.warning(f"Smasing rare guarded magma {l!r} ({num_occs} different lexemes, less than cutoff {GM_CUTOFF})")
            __smash_lexeme(replaced, l.lexeme, l.start, None)
        elif isinstance(l.token, SplitMagma) and num_occs <= SM_CUTOFF:
            logger.warning(f"Smashing rare split magma {l!r} ({num_occs} different lexemes, less than cutoff {SM_CUTOFF})")
            # ignore alphabet, may cause trouble...
            __smash_lexeme(replaced, l.lexeme, l.start, None)
        else:
            # Default, shouldn't apply
            replaced.append(l)
    return replaced

def __smash_lexeme(target, lexeme, start, alphabet):
    for (i, c) in enumerate(lexeme):
        if alphabet == None:
            target.append(LToken(IllegalCharacter(c, set([c])), start+i, start+i+1, c))
        else:
            target.append(LToken(IllegalCharacter(c, alphabet), start+i, start+i+1, c))

def __smash_comment(target, l):
    left, right = l.token.left, l.token.right
    l_start = l.start
    r_start = l.start + len(l.lexeme) - len(right)
    body = l.lexeme.removeprefix(left).removesuffix(right)
    b_start = l.start + len(left)
    __smash_lexeme(target, left,  l_start, None)
    __smash_lexeme(target, body,  b_start, l.token.alphabet)
    __smash_lexeme(target, right, r_start, None)


#
# Rebalance two adjacent monoid tokens
#
def rebalance_adjacent_monoids(json_data, lexemes, info=None):

    if len(lexemes) <= 1:
        return lexemes

    fst,  snd  = lexemes[0], lexemes[1]
    fstt, sndt = fst.token, snd.token
    start_pos  = lexemes[0].start

    if isinstance(fstt, Monoid) and isinstance(sndt, Monoid):
        alpha = fstt.alphabet - sndt.alphabet
        beta  = fstt.alphabet & sndt.alphabet
        logger.debug(f"Trying to rebalance {(fst, snd)!r}, new alphabets {Monoid.implode(alpha)}, {Monoid.implode(beta)}")

        split_pos = next((i for i, x in enumerate(fst.lexeme) if x in beta), None)
        if split_pos == 0 or split_pos == None: # beta matches all or nothing of fst.lexeme, so no split possible
            logger.debug(f"Cannot rebalance {fst.lexeme!a} into {Monoid.implode(alpha)}, {Monoid.implode(beta)}, skipping")
        else:
            if next((_ for x in fst.lexeme[split_pos:] if x in alpha), None) != None: # more than one split possible
                logger.debug(f"Cannot rebalance {fst.lexeme!a} into {Monoid.implode(alpha)}, {Monoid.implode(beta)}, skipping")
            else:
                if beta == sndt.initials and not isinstance(sndt, LeftPointedMonoid):
                    monoid = FreeMonoid(beta)
                else:
                    assert beta <= sndt.alphabet, f"Internal error: alphabet mismatch - {Monoid.implode(beta)} not a subset of {Monoid.implode(sndt.alphabet)}"
                    monoid = LeftPointedMonoid(beta, sndt.alphabet)
                ### TODO: should not split into chars if more than one but keep mono with smaller alphabet
                ### (chars are probably be merged again later)
                chars  = [LToken(IllegalCharacter(c), start_pos+i, start_pos+i+1, c) for (i, c) in enumerate(fst.lexeme[0:split_pos])]
                ltoken = LToken(monoid, start_pos+split_pos, snd.end, fst.lexeme[split_pos:] + snd.lexeme)
                logger.debug(f"Splitting monoid {fst!r}, keeping left half as {chars!r},  merging right half {fst.lexeme[split_pos:]!a} into {ltoken!r}")
                logger.log("DETAIL", f"Splitting monoid {fstt!r} and merging right half {fst.lexeme[split_pos:]!a} into {monoid!r}")
                return chars + rebalance_adjacent_monoids(json_data, [ltoken] + lexemes[2:], info)

    return [fst] + rebalance_adjacent_monoids(json_data, lexemes[1:], info)


#
# Remove unused single-character keyword and operator symbols from alphabets and alternatives
#
### TODO: parameterize for:
###       - remove from IllegalCharacter as well or not
###       - remove op_chars as well or not
def _remove_unused_symbols(remove_op_symbols, mono_only, json_data, lexemes, tokens):

    base, op_chars = single_char_symbols(tokens)
    symbol_class   = "keyword"
    if remove_op_symbols:
        base |= op_chars
        symbol_class += " and operator"

    for (i, l) in enumerate(lexemes):
        occ, tok = l.lexeme, l.token
        unused   = base - set(l.lexeme)
        if not(isinstance(tok, Keyword)) and not(isinstance(tok, Operator)) and not(isinstance(tok, Comment)) and not(isinstance(tok, String)) and unused != set():
            if isinstance(tok, FreeMonoid):
                removed = tok.alphabet & unused
                newtok  = FreeMonoid(tok.alphabet - unused)
            elif isinstance(tok, LeftPointedMonoid):
                removed = tok.alphabet & unused
                newinitials, newalphabet = tok.initials - unused, tok.alphabet - unused
                if newinitials == newalphabet:
                    newtok = FreeMonoid(newalphabet)
                else:
                    newtok = LeftPointedMonoid(newinitials, newalphabet)
            elif not(mono_only) and isinstance(tok, IllegalCharacter):
                removed = tok.subst & unused
                newtok = IllegalCharacter(occ, tok.subst - unused)
            elif not(mono_only) and isinstance(tok, OperatorSymbol):
                removed = tok.subst & unused
                newtok = OperatorSymbol(occ, tok.subst - unused)
            elif not(mono_only) and isinstance(tok, FixedLengthSequence):
                removed = unused
                newchars = [s - unused for s in tok.charsets]
                if all([len(s) == 1 for s in newchars]):
                    newtok = Keyword(occ)
                else:
                    newtok = FixedLengthSequence([s - unused for s in tok.charsets])
            else:
                logger.debug(f"Ignoring {tok!r} for now ({mono_only=})")
                newtok = tok

            if tok != newtok:
                logger.debug(f"Removing unused single-character {symbol_class} symbols {Monoid.implode(removed)} from {l!r} to get {newtok!r}")
                logger.log("DETAIL", f"Removing unused single-character {symbol_class} symbols {Monoid.implode(removed)} from {tok!r} to get {newtok!r}")
                lexemes[i] = LToken(newtok, l.start, l.end, l.lexeme)

    return lexemes

### Wrappers
def remove_unused_keyword_symbols(json_data, lexemes, tokens):
    return _remove_unused_symbols(False, False, json_data, lexemes, tokens)
def remove_unused_symbols_from_monoids(json_data, lexemes, tokens):
    return _remove_unused_symbols(True, True, json_data, lexemes, tokens)

#
# Remove unused single-character keyword symbols from monoid alphabet
#
def ___remove_unused_symbols_from_monoids(json_data, lexemes, tokens):

    kw_chars, op_chars = single_char_symbols(tokens)

    for (i, l) in enumerate(lexemes):
        occ, tok = l.lexeme, l.token
        if isinstance(tok, Monoid) and (unused := (kw_chars & tok.alphabet) - set(occ)) and unused != set():
            if isinstance(tok, FreeMonoid):
                newtok = FreeMonoid(tok.alphabet - unused)
            elif isinstance(tok, LeftPointedMonoid):
                if tok.initials - unused == set() or tok.initials - unused == tok.alphabet - unused:
                    newtok = FreeMonoid(tok.alphabet - unused)
                else:
                    newtok = LeftPointedMonoid(tok.initials - unused, tok.alphabet - unused)
            else:
                logger.warning(f"Unexpected Monoid-type {tok!r}")
                continue
            logger.debug(f"Removing unused single-character keywords {Monoid.implode(unused)} from monoid {l!r} to get {newtok!r}")
            logger.log("DETAIL", f"Removing unused single-character keywords {Monoid.implode(unused)} from monoid {tok!r} to get {newtok!r}")
            lexemes[i] = LToken(newtok, l.start, l.end, l.lexeme)

    return lexemes


#
# Replace monoid by one with larger alphabet matching the same lexeme elsewhere
#
def widen_monoids(json_data, lexemes, info):

    ### TODO: may not need occurrences
    (occurences, counters) = info
    monos = [m for (m, _) in counters.most_common() if isinstance(m, FreeMonoid)]
    lpms  = [m for (m, _) in counters.most_common() if isinstance(m, LeftPointedMonoid)]

    for (i, l) in enumerate(lexemes):
        occ = l.lexeme
        if isinstance(l.token, FreeMonoid):
            m = next((m for m in monos if counters[m] > counters[l.token] and m.alphabet > l.token.alphabet and occ in occurences[m]), None)
            if m != None:
                logger.debug(f"Widening monoid occurrence {occ!a} of {l.token!r} ({counters[l.token]} occurrences) to {m!r} ({counters[m]} occurrences)")
                logger.log("DETAIL", f"Widening monoid occurrence {occ!a} of {l.token!r} to {m!r}")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)
        elif isinstance(l.token, LeftPointedMonoid):
            m = next((m for m in lpms if counters[m] > counters[l.token] and m.initials > l.token.initials and m.alphabet > l.token.alphabet and occ in occurences[m]), None)
            if m != None:
                logger.debug(f"Widening monoid occurrence {occ!a} of {l.token!r} ({counters[l.token]} occurrences) to {m!r} ({counters[m]} occurrences)")
                logger.log("DETAIL", f"Widening monoid occurrence {occ!a} of {l.token!r} to {m!r}")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)

    return lexemes


#
# Replace monoid by one with smaller alphabet matching all the same lexemes elsewhere
#
def tighten_monoids(json_data, lexemes, info):

    (occurences, counters) = info
    monos = [m for (m, _) in counters.most_common() if isinstance(m, FreeMonoid)]
    lpms  = [m for (m, _) in counters.most_common() if isinstance(m, LeftPointedMonoid)]

    for (i, l) in enumerate(lexemes):
        assert l.lexeme != ""
        if isinstance(l.token, FreeMonoid):
            for occ in occurences[l.token]:
                m = next((m for m in monos if m.alphabet < l.token.alphabet and set(l.lexeme) <= m.alphabet and occ in occurences[m]), None)
                if m != None:
                    logger.log("DETAIL", f"Tightening occurrence {occ!a} of {l.token!r} to {m!r}")
                    lexemes[i] = LToken(m , l.start, l.end, l.lexeme)
        elif isinstance(l.token, LeftPointedMonoid):
            for occ in occurences[l.token]:
                m = next((m for m in lpms if m.initials < l.token.initials and m.alphabet < l.token.alphabet and l.lexeme[0] in m.initials and set(l.lexeme) <= m.alphabet and occ in occurences[m]), None)
                if m != None:
                    logger.log("DETAIL", f"Tightening occurrence {occ!a} of {l.token!r} to {m!r}")
                    lexemes[i] = LToken(m , l.start, l.end, l.lexeme)

    return lexemes


#
# Split monoids on single-character keywords and operators
#
# TODO: parameterize to split on both kw and op chars
# TODO: Perhaps restrict to keywords?
# TODO: inefficient, should pass symbol chars along, not tokens
#
def split_monoids_on_symbols(json_data, lexemes, counter):

    if lexemes == []:
        return lexemes

    fst = lexemes[0]
    occ, tok = fst.lexeme, fst.token

    if len(fst.lexeme) == 1 or not(isinstance(tok, Monoid)):
        return [fst] + split_monoids_on_symbols(json_data, lexemes[1:], counter)

    kw_chrs, op_chrs = single_char_symbols(counter.keys())
    # split_syms = tok.alphabet & kw_chrs
    split_syms = tok.alphabet & (kw_chrs | op_chrs)
    if split_syms == tok.alphabet:
        logger.debug(f"split symbols include full monoid alphabet, not splitting {fst!r}")
        return [fst] + split_monoids_on_symbols(json_data, lexemes[1:], counter)
    split_pos, split_chr  = next(((i, x) for i, x in enumerate(occ) if x in split_syms), (None, None))
    if split_pos == None:
        return [fst] + split_monoids_on_symbols(json_data, lexemes[1:], counter)

    logger.debug(f"Trying to split monoid {fst!r} on symbol character {split_chr!a} at position {split_pos}")

    # Split into two or three segments, depending on split_pos
    if split_pos > 0:
        ltoken1 = [LToken(tok, fst.start, fst.start+split_pos, occ[:split_pos])]
    else:
        ltoken1 = []

    if split_chr in kw_chrs:
        split_token = Keyword(split_chr)
    else:
        ### TODO: check that alternatives is subset of subst[split_pso]
        split_token = next(o for (o, _) in counter.most_common() if isinstance(o, Operator) and split_chr in o.alternatives)

    ltoken2 = LToken(split_token, fst.start+split_pos, fst.start+split_pos+1, split_chr)

    if split_pos < len(occ) - 1:
        if occ[split_pos+1] in tok.initials:
            newtok = tok
        else:
            newtok = FreeMonoid(tok.alphabet)
        ltoken3 = [LToken(newtok, fst.start+split_pos+1, fst.end, occ[split_pos+1:])]
    else:
        ltoken3 = []

    logger.debug(f"Splitting monoid {fst!r} on symbol {ltoken2.token!r} at position {split_pos}")
    logger.log("DETAIL", f"Splitting monoid {fst!r} on symbol character {split_chr!a} at position {split_pos}")
    return ltoken1 + [ltoken2] + split_monoids_on_symbols(json_data, ltoken3 + lexemes[1:], counter)

    #if isinstance(fst.token, FreeMonoid):
    #    kw_chars, op_chars = single_char_symbols(tokens)
    #    split_syms = fst.token.alphabet & (kw_chars | op_chars)
    #    split_pos  = next((i for i, x in enumerate(fst.lexeme) if x in split_syms), None)
    #    if split_pos != None:
    #        split_chr = fst.lexeme[split_pos]
    #        logger.debug(f"Trying to split monoid {fst!r} on symbol {split_chr!a}")
    #        newmon = next((m for m in tokens if isinstance(m, FreeMonoid) and m.alphabet == fst.token.alphabet - split_syms), None)
    #        if newmon != None:
    #            logger.debug(f"Found smaller monoid {newmon!r}")
    #            newsym = next((s for s in sorted(list(tokens)) if (isinstance(s, Keyword) and split_chr == s.lexeme) or (isinstance(s, Operator) and split_chr in s.alternatives)), None)
    #            if split_pos == 0:
    #                ltoken1 = LToken(newsym, fst.start, fst.start+1, fst.lexeme[0])
    #                ltoken2 = LToken(fst.token, fst.start+1, fst.end, fst.lexeme[1:])
    #                logger.debug(f"Splitting initial keyword symbol {ltoken1!r} off monoid, leaving {ltoken2!r}")
    #                logger.log("DETAIL", f"Splitting initial keyword symbol {ltoken1.token!r} off monoid {fst.token!r}")
    #                return [ltoken1] + split_monoids_on_symbols(json_data, [ltoken2] + lexemes[1:], tokens)
    #            else:
    #                ltoken1 = LToken(newmon, fst.start, fst.start+split_pos, fst.lexeme[:split_pos])
    #                ltoken2 = LToken(newsym, fst.start+split_pos, fst.start+split_pos+1, fst.lexeme[split_pos])
    #                ### Check whether there's anything left after the split position
    #                if fst.start+split_pos+1 < fst.end:
    #                    logger.debug(f"fst is {fst}, split_pos is {split_pos}")
    #                    tail = [LToken(fst.token, fst.start+split_pos+1, fst.end, fst.lexeme[split_pos+1:])]
    #                else:
    #                    tail = []
    #                logger.debug(f"Splitting monoid at keyword symbol {ltoken2!r}, position {split_pos}, leaving initial monoid {ltoken1!r}")
    #                logger.log("DETAIL", f"Splitting monoid {fst.token} at keyword symbol {ltoken2.lexeme!a}, position {split_pos}, leaving initial monoid {ltoken1.token!r}")
    #                return [ltoken1, ltoken2] + split_monoids_on_symbols(json_data, tail + lexemes[1:], tokens)
    #        else:
    #            logger.debug(f"Cannot find smaller monoid, skipping")

    ### TODO: clone of above, shoudl be unified
    #elif isinstance(fst.token, LeftPointedMonoid):
    #    kw_chars, op_chars = single_char_symbols(tokens)
    #    split_syms = fst.token.alphabet & (kw_chars | op_chars)
    #    split_pos  = next((i for i, x in enumerate(fst.lexeme) if x in split_syms), None)
    #    if split_pos != None:
    #        split_chr = fst.lexeme[split_pos]
    #        logger.debug(f"Trying to split monoid {fst!r} on symbol {split_chr!a}")
    #        newmon = next((m for m in tokens if isinstance(m, LeftPointedMonoid) and m.alphabet == fst.token.alphabet - split_syms), None)
    #        if newmon != None:
    #            logger.debug(f"Found smaller monoid {newmon!r}")
    #            newsym = next((s for s in sorted(list(tokens)) if (isinstance(s, Keyword) and split_chr == s.lexeme) or (isinstance(s, Operator) and split_chr in s.alternatives)), None)
    #            if split_pos == 0:
    #                ltoken1 = LToken(newsym, fst.start, fst.start+1, fst.lexeme[0])
    #                ltoken2 = LToken(fst.token, fst.start+1, fst.end, fst.lexeme[1:])
    #                logger.debug(f"Splitting initial keyword symbol {ltoken1!r} off monoid, leaving {ltoken2!r}")
    #                logger.log("DETAIL", f"Splitting initial keyword symbol {ltoken1.lexeme!a} off monoid {fst.token!r}")
    #                return [ltoken1] + split_monoids_on_symbols(json_data, [ltoken2] + lexemes[1:], tokens)
    #            else:
    #                ltoken1 = LToken(newmon, fst.start, fst.start+split_pos, fst.lexeme[:split_pos])
    #                ltoken2 = LToken(newsym, fst.start+split_pos, fst.start+split_pos+1, fst.lexeme[split_pos])
    #                ### Check whether there's anything left after the split position
    #                if fst.start+split_pos+1 < fst.end:
    #                    logger.debug(f"fst is {fst}, split_pos is {split_pos}")
    #                    tail = [LToken(fst.token, fst.start+split_pos+1, fst.end, fst.lexeme[split_pos+1:])]
    #                else:
    #                    tail = []
    #                logger.debug(f"Splitting monoid at keyword symbol {ltoken2!r}, position {split_pos}, leaving initial monoid {ltoken1!r}")
    #                logger.log("DETAIL", f"Splitting monoid {fst.token} at keyword symbol {ltoken2.lexeme!a}, position {split_pos}, leaving initial monoid {ltoken1.token!r}")
    #                return [ltoken1, ltoken2] + split_monoids_on_symbols(json_data, tail + lexemes[1:], tokens)
    #        else:
    #            logger.debug(f"Cannot find smaller monoid, skipping")

    return [fst] + split_monoids_on_symbols(json_data, lexemes[1:], tokens)


#####
#
# Replace operatar characters by other structures
#
#####

#
# Replace operator characters by single-character keywords 
#
def replace_opsym_by_keyword(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, OperatorSymbol) and (char := l.token.char):
            if Keyword(char) in tokens:
                kw = LToken(Keyword(char), l.start, l.end, l.lexeme)
                lexemes[i] = kw
                logger.log("DETAIL", f"Replacing {l!r} by keyword {kw!r}")

    return lexemes

#
# Remove single-character keywords from operator and illegal character alternatives 
#
### TODO: replace by remove_unused_keyword_symbols
def remove_keyword_alternatives(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):

        token = l.token
        if isinstance(token, OperatorSymbol) or isinstance(token, IllegalCharacter):
            kw_chars = set()
            for char in l.token.subst - {l.lexeme}:
                if Keyword(char) in tokens:
                    kw_chars.add(char)
            if kw_chars != set():
                if isinstance(token, OperatorSymbol):
                    ltoken = LToken(OperatorSymbol(l.lexeme, l.token.subst - kw_chars), l.start, l.end, l.lexeme)
                else:
                    ltoken = LToken(IllegalCharacter(l.lexeme, l.token.subst - kw_chars), l.start, l.end, l.lexeme)
                lexemes[i] = ltoken
                logger.log("DETAIL", f"Replacing {l!r} by {ltoken!r}")

    return lexemes


#
# Remove unused alternatives from operator character alternatives 
#
def remove_operator_alternatives(json_data, lexemes, info):

    (occurences, counters) = info

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, OperatorSymbol):
            m = next((m for (m, _) in counters.most_common() if isinstance(m, OperatorSymbol) and occurences[l.token] in m.subst and m.subst < l.token.subst and l.token != m), None)
            # logger.debug(f"checking OperatorSymbol {l!r} with {m}")
            if m != None:
                op = LToken(OperatorSymbol(l.lexeme, l.token.subst - m.subst), l.start, l.end, l.lexeme)
                lexemes[i] = op
                logger.log("DETAIL", f"Replacing {l!r} by operator symbol {op!r}")

        if isinstance(l.token, Operator):
            m = next((m for (m, _) in counters.most_common() if isinstance(m, Operator) and occurences[l.token] in m.alternatives and m.alternatives < l.token.subst and l.token != m), None)
            # logger.debug(f"checking Operator {l!r} with {m}")
            if m != None:
                op = LToken(Operator(l.token.subst - m.alternatives), l.start, l.end, l.lexeme)
                lexemes[i] = op
                logger.log("DETAIL", f"Replacing {l!r} by operator {op!r}")

    return lexemes

#
# Replace operator characters by operators (unless there's a monoid with the
# same alphabet)
#
def replace_opsym_by_op(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, OperatorSymbol) and None == next((m for m in tokens if isinstance(m, Monoid) and m.initials == l.token.subst), None):
            op = LToken(Operator(l.token.subst), l.start, l.end, l.lexeme)
            lexemes[i] = op
            logger.log("DETAIL", f"Replacing {l!r} by operator {op!r}")

    return lexemes

#
# Replace operators by minimized versions with fewer alternatives
#
def replace_op_by_smaller(json_data, lexemes, sorted_tokens):

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, Operator):
            smaller = next((o for o in sorted_tokens if isinstance(o, Operator) and o != l.token and l.lexeme in o.alternatives and o.alternatives < l.token.alternatives), None)
            if smaller != None:
                op = LToken(smaller, l.start, l.end, l.lexeme)
                lexemes[i] = op
                logger.log("DETAIL", f"Replacing {l!r} by operator {op!r}")

    return lexemes

#
# Merge adjacent operators and keywords
#
def extend_operators(json_data, lexemes, info=None):

    if len(lexemes) < 2:
        return lexemes

    fst, snd  = lexemes[0], lexemes[1]
    fst_tok, snd_tok = fst.token, snd.token

    if (isinstance(fst_tok, Operator) and isinstance(snd_tok, Keyword)) or (isinstance(fst_tok, Keyword) and isinstance(snd_tok, Operator)):
        if (Monoid.explode(json_data[fst.end]["Insertion"]["Left"]) == set()):
            newlex = LToken(Operator(__unfold_splitter(set(), [fst_tok, snd_tok])), fst.start, snd.end, fst.lexeme + snd.lexeme)
            logger.debug(f"Merging {[fst, snd]!r} into operator {newlex!r}")
            logger.log("DETAIL", f"Merging {[fst_tok, snd_tok]!r} into operator {newlex.token!r}")
            return extend_operators(json_data, [newlex] + lexemes[2:], tokens)

    return [fst] + extend_operators(json_data, lexemes[1:], tokens)


#####
#
# Replace isolated individual illegal characters by other structures
#
#####

#
# Replace illegal characters by single-character keywords or operators
#
def replace_illegal_by_keyphrase(json_data, lexemes, tokens):

    keywords   = {k for k in tokens if isinstance(k, Keyphrase)}
    operators  = sorted(list({o for o in tokens if isinstance(o, Operator)}))
    op_symbols = sorted(list({o for o in tokens if isinstance(o, OperatorSymbol)}))

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, IllegalCharacter) and (char := l.token.char):
            logger.debug(f"Trying to replace illagel character {l!r} by keyphrase")
            if Keyword(char) in keywords:
                kw = LToken(Keyword(char), l.start, l.end, l.lexeme)
                lexemes[i] = kw
                logger.log("DETAIL", f"Replacing {l!r} by keyword {kw!r}")
            else:
                # op = next((o for o in operators if char in o.alternatives), None)
                op = next((o for o in operators if char in o.alternatives and o.alternatives <= l.token.subst), None)
                if op != None:
                    o = LToken(op, l.start, l.end, l.lexeme)
                    lexemes[i] = o
                    logger.log("DETAIL", f"Replacing {l!r} by operator {o!r}")
                else:
                    op = next((o for o in op_symbols if char == o.char and l.token.subst == o.subst), None)
                    if op != None:
                        o = LToken(op, l.start, l.end, l.lexeme)
                        lexemes[i] = o
                        logger.log("DETAIL", f"Replacing {l!r} by existing operator symbol {o!r}")
                    else:
                        op_sets = sorted([o.subst & l.token.subst for o in op_symbols], key=len)
                        op_set  = next((o for o in op_sets if char in o), None)
                        ### TODO: should only be done if the illegal cannot be replaced by natural
                        if False and op_set != None:
                            op = LToken(OperatorSymbol(char, op_set), l.start, l.end, l.lexeme)
                            lexemes[i] = op
                            logger.log("DETAIL", f"Replacing {l!r} by new operator symbol {op!r}")
                        else:
                            logger.debug(f"Could not find or construct suitable keyphrase")

    return lexemes


#
# Replace illegal characters by single-character keywords or operators
#
def replace_illegal_by_exact_keyphrase(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, IllegalCharacter) and (char := l.token.char):
            if Keyword(char) in tokens:
                kw = LToken(Keyword(char), l.start, l.end, l.lexeme)
                lexemes[i] = kw
                logger.log("DETAIL", f"Replacing {l!r} by keyword {kw!r}")
            else:
                op = next((o for o in sorted(list(tokens)) if isinstance(o, Operator) and l.token.subst == o.alternatives), None)
                if op != None:
                    o = LToken(op, l.start, l.end, l.lexeme)
                    lexemes[i] = o
                    logger.log("DETAIL", f"Replacing {l!r} by operator {o!r}")
                else:
                    op = next((o for o in sorted(list(tokens)) if isinstance(o, OperatorSymbol) and l.token.subst == o.subst), None)
                    if op != None:
                        o = LToken(op, l.start, l.end, l.lexeme)
                        lexemes[i] = o
                        logger.log("DETAIL", f"Replacing {l!r} by operator symbol {o!r}")

    return lexemes


#
# Replace illegal characters by free monoids with identical alphabet 
#
def replace_illegal_by_exact_monoid(json_data, lexemes, tokens):

    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, IllegalCharacter):
            mono = next((m for m in tokens if isinstance(m, FreeMonoid) and l.token.subst == m.alphabet), None)
            if mono != None:
                m = LToken(mono, l.start, l.end, l.lexeme)
                lexemes[i] = m
                logger.log("DETAIL", f"Replacing {l!r} by free monoid {m!r}")

    return lexemes

#
# Replace illegal characters by new free monoids with identical alphabet 
#
# We do this only if the illegal character is wedged between two keywords, so
# its (hypothetical) extension cannot be tacked on to either the preceding or
# subsequent token; this assumes that keywords have been extended already.
#
def replace_illegal_by_new_monoid(json_data, lexemes, monos):

    for i in range(1, len(lexemes)-2):

        k, l, m = lexemes[i-1], lexemes[i], lexemes[i+1] 
        if (isinstance(k.token, Keyword) and isinstance(l.token, IllegalCharacter) and isinstance(m.token, Keyword)
                and next((m for m in monos if m.alphabet & l.token.subst != set()), None) == None):
            mono = LToken(FreeMonoid(l.token.subst), l.start, l.end, l.lexeme)
            lexemes[i] = mono
            logger.log("DETAIL", f"Replacing {l!r} by free monoid {mono!r}")

    return lexemes


#
# Replace illegal characters by most common enclosing monoids
#
# counter is global token occurrence counter. This should be called last.
#
def _replace_illegal_by_natural_monoid(json_data, lexemes, counter, exact=True):

    tokens = counter.keys()
    monos   = [m for (m, _) in counter.most_common() if isinstance(m, Monoid)]
    op_syms = [o for (o, _) in counter.most_common() if isinstance(o, OperatorSymbol)]

    # replaced = []

    # for l in lexemes:
    for (i, l) in enumerate(lexemes):

        if isinstance(l.token, IllegalCharacter) and (char := l.token.char) and not Keyword(char) in tokens and not OperatorSymbol(char) in tokens:
            subst = Monoid.explode(json_data[l.start]["Substitution"])
            left  = Monoid.explode(json_data[l.start]["Insertion"]["Left"])
            right = Monoid.explode(json_data[l.start]["Insertion"]["Right"])
            follow  = subst & right
            natural = left & subst & right
            logger.debug(f"Checking replacement of {l!r} by monoid, natural alphabet {Monoid.implode(natural)}")

            ### Check for suitable left-pointed monoid before trying free monoid
            if (mono := next((m for m in monos if m.initials == natural and m.alphabet == follow), None)) and mono == None:
                mono = next((m for m in monos if m.alphabet == natural), None)
            if l.token.char in natural and mono != None:
                ltoken = LToken(mono, l.start, l.end, l.lexeme)
                logger.log("DETAIL", f"Replacing {l.token!r} by monoid {ltoken.token!r}")
                lexemes[i] = ltoken
                # replaced.append(ltoken)
                continue
            else:
                logger.debug(f"Exact natural monoid does not exist")
                if exact:
                    continue


            ### Try to replace by an operator symbol first
            op_set  = next((os for os in sorted([o.subst & l.token.subst for o in op_syms], key=len, reverse=True) if char in os and os < natural), None)
            if op_set != None:
                if next((m for m in monos if m.alphabet == op_set), None) == None:
                    op = LToken(OperatorSymbol(char, op_set), l.start, l.end, l.lexeme)
                    # op = LToken(OperatorSymbol(char, {char}), l.start, l.end, l.lexeme)
                    lexemes[i] = op
                    logger.log("DETAIL", f"Replacing {l!r} by new operator symbol {op!r}")
                    continue
                else:
                    logger.debug(f"Not replacing {l!r} by operator with monoid alphabet {Monoid.implode(op_set)}")
            else:
                logger.debug(f"No suitable operator found")
 
            found = False
            for m in monos:
                m_init  = m.initials  ### relies on FreeMonoid to provide initials
                m_right = m.alphabet
                if char in m_init and subst >= m_init and right >= m_right:
                    ltoken = LToken(m, l.start, l.end, l.lexeme)
                    logger.log("DETAIL", f"Replacing {l.token!r} by monoid {ltoken.token!r}")
                    lexemes[i] = ltoken
                    # replaced.append(ltoken)
                    ### only pick most common matching mono
                    found = True
                    break
 
            if not found:
                # None of the monos works
                logger.debug(f"Could not find matching monoid to replace {l!r}")
                # replaced.append(l)

        # else:
        #     replaced.append(l)
 
    # return replaced
    return lexemes

### Wrappers
def replace_illegal_by_natural_monoid(json_data, lexemes, counter):
    return _replace_illegal_by_natural_monoid(json_data, lexemes, counter)
def replace_illegal_by_new_natural_monoid(json_data, lexemes, counter):
    return _replace_illegal_by_natural_monoid(json_data, lexemes, counter, exact=False)

#####
#
# Replace monoids below cut-off by wider monoids
#
#####

def widen_monoids2(json_data, lexemes, info):

    (occs, counters) = info
    monos = [m for (m, _) in counters.most_common() if isinstance(m, FreeMonoid)]

    for (i, l) in enumerate(lexemes):
        if isinstance(l.token, FreeMonoid) and len(occs[l.token]) <= MAGMA_CUTOFF:
            logger.debug(f"Number of occurrences {len(occs[l.token])} of monoid at {l!r} at or below cutoff {MAGMA_CUTOFF}, trying to widen")
            m = next((m for m in monos if m.alphabet > l.token.alphabet and len(m.alphabet - l.token.alphabet) == 1), None)
            if m != None:
                logger.log("DETAIL", f"Number of monoid occurrences of {l.token!r} at or below cutoff {MAGMA_CUTOFF}, widened minimally to {m!r}")
                lexemes[i] = LToken(m , l.start, l.end, l.lexeme)

    return lexemes


#############################################################################
#
# Collectors for global post-processing
#
#############################################################################


#
# Collect token segments of length N
#
def __collect_segments(collector, results, counting=False):
    segments = []
    for (_, _, lexemes) in results:
        collector(segments, lexemes)
    segments.sort()
    runs = [(1, s) for s in segments]
    runs = __run_compression_(runs)
    if counting:
        runs.sort(reverse=True)
    logger.debug("Segments:")
    for r in runs:
        logger.debug(f"  {r!a}")
    if counting:
        return runs
    else:
        return [s for (_, s) in runs]

def __run_compression_(runs):
    if runs == []:
        return runs
    else:
        (count, elem) = runs[0]
        # Need to add 2 to the result of next because we start at 1 and need to get the following index
        run_end = 2 + next((i for i, (_, x) in enumerate(runs[1:]) if x != elem), len(runs))
        run_len = sum(c for (c, _) in runs[1:run_end])
        if run_end == len(runs):
            return [(count + run_len, elem)]
        else:
            return [(count + run_len, elem)] + __run_compression_(runs[run_end:])

def __collect_segments_n(n, tuples, lexemes):
    if len(lexemes) < n:
        return tuples
    else:
        tuples.append([l.token for l in lexemes[0:n]])
        return __collect_segments_n(n, tuples, lexemes[1:])

### wrappers for constant N
def collect_triples(results):
    return __collect_segments(__collect_triples, results, False)
def collect_triples(results):
    return __collect_segments(__collect_triples, results, True)
def __collect_triples(triples, lexemes):
    return __collect_segments_n(3, triples, lexemes)


#
# Collect set of all occurring tokens
#
def collect_tokens(results):
    tokens = set()
    for (_, _, lexemes) in results:
        tokens.update(token_set(lexemes))
    return tokens

def sorted_tokens(results):
    return sorted(list(collect_tokens(results)))

### Monoid tokens
def collect_monos(results):
    return [m for m in collect_tokens(results) if isinstance(m, FreeMonoid) or isinstance(m, LeftPointedMonoid)]

### String-style tokens
def sorted_strings(results):
    return sorted([m for m in collect_tokens(results) if isinstance(m, String)])


#
# Collect the list of lexemes matched against each token
#
def collect_lexemes(results):
    d = {}
    for (_, _, lexemes) in results:
        for l in lexemes:
            s = d.get(l.token, None)
            if s == None:
                d[l.token] = set([l.lexeme])
            else:
                try:
                    s.add(l.lexeme)
                except TypeError:
                    logger.error(f"Something went wrong with {l.lexeme}")
                    raise TypeError
    return d

#
# Count how many occurrences each token has, given the list of results
#
def count_occurrences(results):
    counter = Counter()
    for (_, _, lexemes) in results:
        for l in lexemes:
            counter[l.token] += 1
    return counter

#
# Return list of monoids, ordered by number of occurences
#
def ordered_monoids(results):
    counters = count_occurrences(results)
    return [m for (m, _) in counters.most_common() if isinstance(m, Monoid)]

#
# Collect information for monoid widening
#
def collect_widening(results):
    return (collect_lexemes(results), count_occurrences(results))

#
# Dummy, use if no global information is required
#
def no_collection(results):
    return None


#############################################################################
#
# Auxiliary 
#
#############################################################################

### Extract set of occurring tokens from lexeme list
def token_set(lexemes):
    tokens = set()
    for l in lexemes:
        tokens.add(l.token)
    return tokens

### Extract set of occurring characters from lexeme list
def char_set(lexemes):
    chars = set()
    for l in lexemes:
        chars.update(set(l.lexeme))
    return chars

### Extract sets of single-character keywords and operators from token list
### NOTE: Does not check for OperatorSymbol, only for Operator
def single_char_symbols(tokens):
    kw_chars = set([c for k in tokens if isinstance(k, Keyword) and (c := k.single_character()) and c != None])
    op_chars = set()
    for o in tokens:
        if isinstance(o, Operator):
            for a in o.alternatives:
                if len(a) == 1:
                    op_chars.add(a)
    return kw_chars, op_chars

### Check whether all characters in a set have been defined as a single-character token
def check_operator_symbols(tokens, chars):
    for char in chars:
        if next((t for t in tokens if ((isinstance(t, OperatorSymbol) or isinstance(t, Keyword)) and t.single_character() == char)), None) == None:
        # if OperatorSymbol(char) not in tokens and Keyword(char) not in tokens:
            logger.debug(f"Character {char!a} not defined as single-character symbol")
            return False
    return True

### Find the longest segment of illegal characters lexemes[startpos:endpos]; returns end and character string
def illegal_segment(lexemes, startpos=0):
    endpos, lexeme = startpos, ""
    while (endpos + 1 < len(lexemes)) and isinstance(lexemes[endpos].token, IllegalCharacter):
        lexeme += lexemes[endpos].lexeme
        endpos += 1
    return endpos, lexeme

### Find the longest segment of single characters lexemes[startpos:endpos]; returns end and character string; must start with an IllegalCharacter
def illegal_or_op_segment(lexemes, startpos=0):
    endpos, lexeme = startpos, ""
    if isinstance(lexemes[startpos].token, IllegalCharacter):
        while (endpos + 1 < len(lexemes)) and (tok := lexemes[endpos].token) and (isinstance(tok, IllegalCharacter) or isinstance(tok, OperatorSymbol) or isinstance(tok, Operator)):
            lexeme += lexemes[endpos].lexeme
            endpos += 1
    return endpos, lexeme

### Find the longest segment of fixed-length lexemes[startpos:endpos]; returns end and character string
def fixed_segment(lexemes, startpos=0):
    endpos, lexeme = startpos, ""
    while (endpos + 1 < len(lexemes)) and (isinstance(lexemes[endpos].token, Keyphrase) or isinstance(lexemes[endpos].token, IllegalCharacter)):
        lexeme += lexemes[endpos].lexeme
        endpos += 1
    return endpos, lexeme

### safe call; return None for None
def safe(f, args):
    if args == None:
        return None
    else:
        return f(args)

######
#
# Printing routines
#
######

### Print segmentation of all results (token types and lexeme strings)
def print_lexemization(args, printer, results):
    if args["print_lexemization"]:
        for (fpath,  _, lexemes) in results:
            printer(f"Lexemization of {fpath}:")
            for l in lexemes:
                printer(f"  {l!s}")

### Print segmentation of all results (lexeme strings only)
def print_segmentation(args, printer, results):
    if args["print_segmentation"]:
        for (fpath,  _, lexemes) in results:
            printer(f"Segmentation of {fpath}:")
            for l in lexemes:
                printer(f"  {l.lexeme!s}")

def print_tokens(args, header, printer, tokens):
    if args["print_tokens"]:
        printer(header)
        for token in sorted(tokens):
            printer(f"  {token!s}")

def print_token_counts(args, header, printer, counts, lexemes):
    if args["print_token_counts"]:
        printer(header)
        for token, count in sorted(counts.items()):
            printer(f"  {token!s}")
            printer(f"    --> {count} occurrences with {len(lexemes[token])} different lexemes: {sorted(lexemes[token])!s}")


#############################################################################
#
# Parse command line arguments
#
#############################################################################

def parse_cmdline():
    
    class RequireLexAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if not getattr(namespace, "lex", False):
                parser.error(f"{option_string} requires --lex to be enabled.")
            setattr(namespace, self.dest, values)

    parser = argparse.ArgumentParser()
    Loginfer.set_cmdline_arguments(parser)
    parser.add_argument("--extension",                type=str, default="*")
    # control token learning process
    parser.add_argument("--segmentation-only",        action="store_true")    # runs muncher only
    parser.add_argument("--magma-cutoff",             type=int, default=0)    # cutoff is min(magma, specific value)
    parser.add_argument("--monoid-cutoff",            type=int, default=0)
    parser.add_argument("--lpm-cutoff",               type=int, default=0)
    parser.add_argument("--string-cutoff",            type=int, default=0)
    parser.add_argument("--comment-cutoff",           type=int, default=0)
    parser.add_argument("--recursive-comment-cutoff", type=int, default=0)
    parser.add_argument("--guarded-magma-cutoff",     type=int, default=0)
    parser.add_argument("--split-magma-cutoff",       type=int, default=0)
    parser.add_argument("--roundnum",                 type=int, default=NUM_ROUNDS)
    # print full lexical token sequence
    parser.add_argument("--print-lexemization",     dest="print_lexemization", action="store_true", default=False)
    parser.add_argument("--no-print-lexemization",  dest="print_lexemization", action="store_false")
    # print tokens and meta-information about tokens
    parser.add_argument("--print-tokens",           dest="print_tokens",       action="store_true", default=True)
    parser.add_argument("--no-print-tokens",        dest="print_tokens",       action="store_false")
    parser.add_argument("--print-token-counts",     dest="print_token_counts", action="store_true", default=False)
    # print lexeme sequence in compact form
    parser.add_argument("--print-segmentation",     dest="print_segmentation", action="store_true", default=False)
    parser.add_argument("--no-print-segmentation",  dest="print_segmentation", action="store_false")

    ## spit out some lex file
    parser.add_argument("--lex", type=str, default="")
    ## grammar name for the output antlr lexer
    parser.add_argument("--grammar_name", type=str, help="Requires --lex", action=RequireLexAction)

    parser.add_argument("json_paths",  type=str, nargs='+')

    return vars(parser.parse_args())


#############################################################################
#
# Main entry point
#
#############################################################################

if __name__ == "__main__":

    # Collect and store command line arguments
    args = parse_cmdline()
    NUM_ROUNDS      = args["roundnum"]
    MAGMA_CUTOFF    = args["magma_cutoff"]
    if MAGMA_CUTOFF == 0:
        MONOID_CUTOFF   = args["monoid_cutoff"]            
        LPM_CUTOFF      = args["lpm_cutoff"]               
        STRING_CUTOFF   = args["string_cutoff"]            
        COMMENT_CUTOFF  = args["comment_cutoff"]           
        RCOMMENT_CUTOFF = args["recursive_comment_cutoff"] 
        GM_CUTOFF       = args["guarded_magma_cutoff"]     
        SM_CUTOFF       = args["split_magma_cutoff"]       
    else:
        MONOID_CUTOFF   = min(MAGMA_CUTOFF, args["monoid_cutoff"])
        LPM_CUTOFF      = min(MAGMA_CUTOFF, args["lpm_cutoff"])
        STRING_CUTOFF   = min(MAGMA_CUTOFF, args["string_cutoff"])
        COMMENT_CUTOFF  = min(MAGMA_CUTOFF, args["comment_cutoff"])
        RCOMMENT_CUTOFF = min(MAGMA_CUTOFF, args["recursive_comment_cutoff"])
        GM_CUTOFF       = min(MAGMA_CUTOFF, args["guarded_magma_cutoff"])
        SM_CUTOFF       = min(MAGMA_CUTOFF, args["split_magma_cutoff"])
    json_paths      = args["json_paths"]

    ### Write back values of config constants
    set_cutoff('MONOID',   MONOID_CUTOFF)
    set_cutoff('LPM',      LPM_CUTOFF)
    set_cutoff('STRING',   STRING_CUTOFF)
    set_cutoff('COMMENT',  COMMENT_CUTOFF)
    set_cutoff('RCOMMENT', RCOMMENT_CUTOFF)
    set_cutoff('GM',       GM_CUTOFF)
    set_cutoff('SM',       SM_CUTOFF)

    # logger.warning(f"{MONOID_CUTOFF=}, {LPM_CUTOFF=}")

    # Customized logging
    Loginfer.process_cmdline_arguments(args)

    logger.info("Token analysis started")

    results = []
    for json_path in json_paths:
        if os.path.isfile(json_path):
            results.append(lexemize_json(json_path))
        else:
            for json_file in sorted(glob.glob(f'{json_path}/**/*.json', recursive=True)):
                results.append(lexemize_json(json_file))

    # Collect in ALPHABET charactars used in training set
    ALPHABET = set()
    for (_, _, lexemes) in results:
        ALPHABET.update(char_set(lexemes))
    logger.debug(f"Characters used: {Monoid.implode(ALPHABET)}")

    ### TODO: run sanity checks on munch

    tokens  = collect_tokens(results)
    header  = "Token list after initial munch ({} tokens):".format(len(tokens))
    print_tokens(args, header, logger.debug, tokens)
    print_lexemization(args, logger.debug, results) 
    print_segmentation(args, logger.debug, results)

    if args["segmentation_only"] != True:   ### argparse changes '-' to '_'

        #
        # Apply a sequence of reduction stages, each consisting of several
        # steps to the basic munched lexemization; each stage is run until an
        # individual fixpoint is reached.
        #
        # Each step collects global information using the collector component,
        # and then applies the reducer component over each lexeme list; if the
        # flag is set, the reducer is run on each lexeme list until a (local)
        # fixpoint is reached.
        #
        # Note that 
        # - comments need to precede strings, because of nesting
        # - strings need to precede comments, because of escaping
        # We fix this by running reclassify_comment_as_string as part of the 
        # string identification.
        #

        # TODO: check which reducers should really be run recursively

        # Find various forms of comments
        comment_id = [
                 (no_collection,     strict_comment,                   False)
                ,(collect_tokens,    nested_comment,                   True)
                ,(no_collection,     relaxed_comment,                  False)
                ,(no_collection,     line_comment,                     False)
                ,(collect_tokens,    comment_instances,                False)
                ,(collect_tokens,    comment_segments,                 False)
                ,(collect_tokens,    basic_comment,                    False)
                ]
        comment_cleanup = [
                 # Cannot be folded into above because of nested comments, also causes other problems
                 (collect_tokens,    gobble_comment_instances,         False)
                ]
        # Find various forms of strings, including comment reclassification
        string_id = [
                 (no_collection,     string_literal,                   False)
                ,(sorted_tokens,     reclassify_comment_as_string,     False)
                ,(count_occurrences, resolve_inconsistent_strings,     False)
                ,(sorted_strings,    string_instances,                 False)
                ### TODO: called with sorted tokens, do not recurse
                ,(sorted_tokens,     string_literal_with_escapes,      False)
                ,(sorted_tokens,     string_literal_with_escaped_quotes, False)
                ,(no_collection,     string_escape,                    True)
                ,(collect_tokens,    string_gobble_empty_strings,      True)
                ### These are for the old escape handling and no longer required
                #,(collect_tokens,    string_gobble_escapes,            False)
                #,(collect_tokens,    string_unwrap_escapes,            False)
                #,(collect_tokens,    string_merge_escapes,             True)
                #,(collect_tokens,    string_merge_free_monoids,        False)
                ,(count_occurrences, string_merge_escape_sequences,    False)
                ]
        # Find (more instances of) longer keyphrases 
        keyphrase_extension = [
                 (collect_tokens,    extend_keywords_single_char,      True)
                ,(collect_tokens,    extend_keywords_multi_char,       True)
                ,(collect_tokens,    extend_fixed_length_sequences,    True)
                ,(no_collection,     find_operator_ngrams,             True)
                ,(collect_tokens,    replace_fixed_length_by_keyword,  False)
                ### Not helpful for inference, could be used for stand-alone lexing
                ### ,(collect_tokens,    replace_monoid_by_keyword,        False)
                ]
        # Remove unused keyword characters from other tokens
        keyword_symbol_cleanup = [
                 (collect_tokens,    remove_unused_keyword_symbols,    False)
                ]
        # Find "better" monoids: longer lexemes, more frequent monos, smaller alphabets
        mono_restructuring = [
                 (collect_tokens,    extend_monoids_single_char,       True)
                ,(collect_tokens,     merge_adjacent_monoids,           False)
                #,(collect_tokens,    split_monoids_on_symbols,         False)
                ,(count_occurrences,  split_monoids_on_symbols,         False)
                ,(collect_tokens,    remove_unused_symbols_from_monoids, False)
                ,(collect_widening,  widen_monoids,                    False)
                ,(collect_widening,  tighten_monoids,                  False)
                ,(no_collection,     unify_adjacent_monoids,           False)
                ,(collect_tokens,    rebalance_adjacent_monoids,       False)
                ,(collect_lexemes,   subsume_monoids,         False)
                ### Not helpful for inference, could be used for stand-alone lexing
                ### ,(collect_tokens,    replace_monoid_by_keyword,        False)
                ]
        # Clean-up mono structure
        mono_cleanups = [
                ### ,(collect_widening,  widen_monoids2,                   False)
                ### should probably not smash here yet
                #  (collect_lexemes,   smash_monoids,                    False)
                 (collect_tokens,    split_left_pointed_monoid,        False)
                ### These are counter-productive
                # ,(collect_tokens,    replace_illegal_by_exact_keyphrase, False)
                # ,(collect_tokens,    replace_illegal_by_exact_monoid,    False)
                ,(collect_tokens,    replace_illegal_by_keyphrase,     False)
                ,(no_collection,     extend_operators,                 False)
                ,(count_occurrences, replace_illegal_by_natural_monoid, False)
                ,(count_occurrences, replace_illegal_by_new_natural_monoid, False)
                ,(collect_monos,     replace_illegal_by_new_monoid,    False)
                #,(collect_tokens,    split_monoids_on_symbols,         False)
                ,(count_occurrences,  split_monoids_on_symbols,         False)
                ### Run again, we may have constructed new mono lexemes that can be merged
                ,(collect_tokens,     merge_adjacent_monoids,           False)
                ,(no_collection,     unify_adjacent_monoids,           False)
                ### Run again, we may have constructed new mono lexemes that match keywords
                # ,(collect_tokens,    replace_monoid_by_keyword,        False)
                ]
        # Clean-up operator structure; must follow mono restructuring and cleanup
        op_cleanups = [
                 (collect_tokens,    remove_keyword_alternatives,      False)
                ,(collect_widening,  remove_operator_alternatives,     False)
                ,(collect_tokens,    replace_opsym_by_keyword,         False)
                ,(collect_tokens,    replace_opsym_by_op,              False)
                ,(sorted_tokens,     replace_op_by_smaller,            False)
        ]
        # Identify split and guarded magmas
        magma_id = [
                 (collect_tokens,    find_split_magmas,                False)
                ,(collect_tokens,    find_left_guarded_magmas,         False)
                ### Old version
                ### ,(collect_tokens,    find_guarded_magmas,              False)
                ,(collect_tokens,    find_right_guarded_magmas,        False)
        ]
        # Clean-up token structure
        final_cleanups = [
                 (collect_widening,  widen_monoids2,                   False)
                ,(collect_lexemes,   subsume_monoid_instances,         False)
                # ,(collect_lexemes,   smash_monoids,                    False)
                ,(collect_tokens,    split_left_pointed_monoid,        False)
                ### These are counter-productive
                # ,(collect_tokens,    replace_illegal_by_exact_keyphrase, False)
                # ,(collect_tokens,    replace_illegal_by_exact_monoid,    False)
                ,(collect_tokens,    replace_illegal_by_keyphrase,     False)
                ,(no_collection,     extend_operators,                 False)
                ,(count_occurrences, replace_illegal_by_new_natural_monoid, False)
                ,(collect_monos,     replace_illegal_by_new_monoid,    False)
                #,(collect_tokens,    split_monoids_on_symbols,         False)
                ,(count_occurrences,  split_monoids_on_symbols,         False)
                ### cannot remove all symbols, because some grammars have letters or digits as operators
                # ,(collect_tokens,    remove_unused_symbols_from_monoids,    False)
                ,(collect_tokens,    remove_unused_keyword_symbols,    False)
                ### Run again, we may have constructed new mono lexemes that can be merged
                ,(collect_tokens,     merge_adjacent_monoids,           False)
                ,(no_collection,     unify_adjacent_monoids,           False)
                ### Run again, we may have constructed new mono lexemes that match keywords
                # ,(collect_tokens,    replace_monoid_by_keyword,        False)
                ]

        # Glue stages together
        stages = [('comment identification',  comment_id), 
                  ('comment cleanup',         comment_cleanup),
                  ('string identification',   string_id), 
                  ('keyphrase extension',     keyphrase_extension), 
                  ('keyword symbol clean-up', keyword_symbol_cleanup),
                  ('monoid restructuring',    mono_restructuring), 
                  ('monoid clean-up',         mono_cleanups),
                  ('operator clean-up',       op_cleanups), 
                  ('magma identification',    magma_id),
                  ('final clean-up',          final_cleanups)
                 ]

        round_nr = 1
        last_results = results
        for (stage_name, stage) in stages:

            logger.info(f"Token post-processing, {stage_name} stage")

            while round_nr < NUM_ROUNDS:

                logger.info(f"Token post-processing, {stage_name} round {round_nr}")
                names = ["(" + c.__name__ + ", " + r.__name__ + ")" for (c, r, _) in stage]
                logger.log("DETAIL", f"Token post-processing, {stage_name} with {names!a}")

                prev_results = last_results
                for step in stage:

                    results = reduce_all(step, results)
                    tokens  = collect_tokens(results)
                    (_, reducer, _) = step

                    if prev_results == results:
                        logger.debug(f"Token list after {stage_name} round {round_nr}, {reducer.__name__} ({len(tokens)} tokens) identical, no change in lexemization")
                    else:
                        header  = "Token list after {} round {}, {} ({} tokens):".format(stage_name, round_nr, reducer.__name__, len(tokens))
                        print_tokens(args, header, logger.debug, tokens)
                        print_lexemization(args, logger.debug, results) 
                        print_segmentation(args, logger.debug, results)

                    prev_results = results

                logger.info(f"Found {len(tokens)} token candidates after {stage_name} round {round_nr}")

                # Stage-level sanity checks
                warn_string_incompatible_tokens(stage_name, results)

                if results == last_results:
                    break

                last_results = results
                round_nr += 1

            # Given another try to the next stage
            round_nr = 1

    # Smash magmas with too few occurrences
    # (need to run outside loop, because it can run only once)
    logger.info(f"Token post-processing, magma smashing stage")
    results = reduce_all((collect_lexemes, smash_monoids, False), results)
    tokens  = collect_tokens(results)

    # Final sanity checks
    warn_monoid_alphabet(results)

    header = "Final token list ({} tokens):".format(len(tokens))
    lexemes = collect_lexemes(results) ### Need this for lexer anyway
    if args["print_token_counts"]:
        counts  = count_occurrences(results)
        print_token_counts(args, header, print, counts, lexemes)
    else:
        print_tokens(args, header, print, tokens)

    logger.success(f"Found {len(tokens)} tokens in total")

    print_lexemization(args, print, results)
    print_segmentation(args, print, results)

    ## write some lex file if option is enabled
    if len(args["lex"]) > 0:
        grammar_name = args['lex']
        produce_lex(lexemes, grammar_name)

    logger.success("Token analysis")

