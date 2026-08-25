#############################################################################
#
# A comment is a guarded magma where the magma's alphabet and the characters
# from the opening and closing guards together comprise the full character.
# Strict comments do not allow any of the guard's characters to occur in the
# magma, while relaxed comments allow this, under appropriate escaping to
# prevent nesting (if not allowed) or masking the right guard.
#
#############################################################################

#
# Imports and configuration
#

### Logging
from loguru import logger
from loginfer import Loginfer

### Token constructors
from tokens import LToken, Keyphrase, Keyword, OperatorSymbol, Monoid, FreeMonoid, LeftPointedMonoid, GuardedMagma, IllegalCharacter

# Global "constants", may be overwritten by command line options
from config import CHAR_SET, ALPHABET, ESC_LENGTH

### Auxiliary
from auxiliary import split_prefix

#############################################################################
#
# Token class
#
#############################################################################

class Comment(GuardedMagma):

    def __init__(self, alphabet, left, right, recursive=False):
        GuardedMagma.__init__(self, alphabet, left, right)
        self.recursive = recursive

    def __repr__(self):
        return f"Comment({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a}, {self.recursive})"


#####
#
# Basic comment
#
# A "basic" comment is a simple guarded magma, with the two guards enclosing a
# single monoid that allows (almost) the entire character set.  In the most
# basic form (strict==True, line==False), the monoid's guards are both
# keywords, the magma's alphabet doesn't contain any of the guard characters,
# and the alphabet and guard characters together form the full character set.
# If strict==False, the restriction on the monoid's alphabet is relaxed, and
# the guards' characters are allowed (note that the muncher does not identify a
# single monoid if either of the guards is made up from multiple characters,
# and the text between the guards contains more than one of them).  If
# line==True, the right guard does not have to be a keyword, but can be the
# single missing character (typically \n).
#
# TODO: Generalize line-style to multiple characters
#
#####

def _comment(strict, line, json_data, lexemes):

    if len(lexemes) < 3:
        return lexemes

    fst, snd, trd = lexemes[0], lexemes[1], lexemes[2]
    token = None

    if isinstance(fst.token, Keyword) and isinstance(snd.token, FreeMonoid):

        if (line and trd.token.single_character() == None) or (not line and not isinstance(trd.token, Keyword)):
            return [lexemes[0]] + _comment(strict, line, json_data, lexemes[1:])

        left, body, right =  fst.lexeme, snd.lexeme, trd.lexeme

        # Check that body allows all printable characters except guard characters
        alphabet = Monoid.explode(CHAR_SET) - (Monoid.explode(left) | Monoid.explode(right))
        if strict:
            if alphabet == snd.token.alphabet:
                token  = Comment(alphabet, left, right)
                action = "Identified strict basic comment,"
            if alphabet <= snd.token.alphabet and Monoid.explode(body) <= alphabet:
                token  = Comment(alphabet, left, right)
                action = "Identified strict basic comment, restricting alphabet and"
        else:
            if alphabet <= snd.token.alphabet:
                chars  = Monoid.explode(body) - alphabet
                token  = Comment(alphabet | chars, left, right)
                action = f"Identified relaxed basic comment, extending alphabet by {Monoid.implode(chars)!a} and"

        if token != None:
            ltoken = LToken(token, fst.start, trd.end, left + body + right)
            logger.debug(f"{action} merging {fst!r}, {snd!r}, and {trd!r} into {ltoken!r}")
            logger.log("DETAIL", f"Identified comment {ltoken!r}")
            return [ltoken] + _comment(strict, line, json_data, lexemes[3:])

    # Nothing found, try next position
    return [lexemes[0]] + _comment(strict, line, json_data, lexemes[1:])

### Wrappers
def strict_comment(json_data, lexemes, info=None):
    return _comment(True, False, json_data, lexemes)
def relaxed_comment(json_data, lexemes, info=None):
    return _comment(False, False, json_data, lexemes)
def line_comment(json_data, lexemes, info=None):
    return _comment(True, True, json_data, lexemes)


#####
#
# Nested comments
#
# For properly nested comments, the guards can occur in the magma.
#
#####

def nested_comment(json_data, lexemes, tokens):

    ### TODO: only works for ampl so far; need to check for multi-character guards a la Pascal etc.
    ### TODO: should iterate over magmas and use split prefix

    ### TODO: somehow this catches C-style single-character constants as nested comments... (see BasicGame.i)
    ###       funnily enough, this just makes them match correctly.

    if lexemes == []:
        return lexemes

    fst = lexemes[0]
    left  = fst.token.fixed_string()

    ### TODO: need to check occurrence of base case
    if left != None:
        magmas = [m for m in tokens if isinstance(m, Comment) and m.left == left]
        if magmas != []:
            logger.debug(f"Checking for recursive comment with left guard {fst!a}")
            for m in magmas:
                right    = m.right
                alphabet = m.alphabet
                # Find next occurence of right bracket, if any
                right_i  = next((i for (i, l) in enumerate(lexemes[1:]) if l.token.fixed_string() == right), None)
                if right_i != None:
                    segment = lexemes[1:right_i+1]
                    if check_segment(m, segment) and (m in [l.token for l in segment]):
                        newseq = Comment(alphabet, left, right, True)
                        newlex = "".join([l.lexeme for l in lexemes[0:right_i+2]])
                        ltoken = LToken(newseq, fst.start, lexemes[right_i+1].end, newlex)
                        logger.debug(f"Merging {lexemes[0:right_i+2]!r} into {ltoken!r}, using base magma {m!r}")
                        logger.log("DETAIL", f"Recursively merging lexemes into {newseq!r}")
                        return [ltoken] + nested_comment(json_data, lexemes[right_i+2:], tokens)

    # No nesting found, try next position
    return [lexemes[0]] + nested_comment(json_data, lexemes[1:], tokens)


#####
#
# Find additional instances
#
# Given a properly recognized Comment, we try to find additional instances
# that do not fit the definition of a basic comment (i.e., the guards are
# not keywords) but fit the lexical pattern.
#
#####

def _comment_instances(json_data, lexemes, tokens):

    if lexemes == []:
        return lexemes

    for m in tokens:
        if isinstance(m, Comment):
            # Check for left guard, try next guarded magma if not found
            tl0 = split_prefix(m.left, lexemes)
            if tl0 == None or tl0 == []:
                continue
            logger.debug(f"Found left guard {m.left}, checking comment {m!r}")
            # Merge split remainders into next monoid
            tl1  = merge_leading_monoids(m.alphabet, tl0[0], tl0[1:])
            body = tl1[0]
            # Check for monoid or illegal character, try next guarded magma if not found
            if isinstance(body.token, IllegalCharacter):
                if body.token.char in m.alphabet:
                    body_alphabet = m.alphabet
                else:
                    body_alphabet = body.token.subst
            elif isinstance(body.token, Monoid):
                body_alphabet = body.token.alphabet
            else:
                logger.debug(f"Next token {body!r} is not a suitable monoid, skipping comment {m!r}")
                continue
            # Check for alphabet compatibility and lexeme match
            if True or m.alphabet <= body_alphabet:
                if Monoid.explode(body.lexeme) <= m.alphabet:
                    logger.debug(f"Found monoid {body!r} with compatible alphabet {Monoid.implode(m.alphabet)}")
                    if tl1[1:] == []:
                        logger.debug(f"File ends before right guard {m.right!a} of comment {m!r} found, creating new comment token without right guard")
                        ltoken = LToken(Comment(m.alphabet, m.left, None, False), lexemes[0].start, lexemes[-1].end, m.left + body.lexeme)
                        logger.log("DETAIL", f"Identified new comment {ltoken!r} without right guard")
                        return [ltoken]
                    tl2 = split_prefix(m.right, tl1[1:])
                    if tl2 != None and tl2 != []:
                        ltoken = LToken(m, lexemes[0].start, tl2[0].start, m.left + body.lexeme + m.right)
                        logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                        return [ltoken] + _comment_instances(json_data, tl2, tokens)
                    elif tl2 == []:
                        ltoken = LToken(m, lexemes[0].start, tl1[-1].end, m.left + body.lexeme + m.right)
                        logger.log("DETAIL", f"Identified new instance of comment {ltoken!r} at end of file")
                        return [ltoken]
                    else:
                        logger.debug(f"Did not find right guard in mono, need to check next lexemes {tl1[1:]!r}")
                else:
                    lexeme_chars  = Monoid.explode(body.lexeme)
                    missing_chars = lexeme_chars - m.alphabet
                    logger.debug(f"Alphabet of {m!r} not big enough to capture lexeme {body.lexeme!a}, missing characters {Monoid.implode(missing_chars)}")
                    logger.log("DETAIL", f"Alphabet of {m!r} not big enough to capture lexeme {body.lexeme!a}")
                    tl3 = split_prefix(m.right, tl1[1:])
                    if tl3 != None:
                        # Right guard found following the body monoid,
                        # so need to check whether the alphabet can be extended
                        if tl3 == []:
                            logger.debug(f"Reached end of file before right guard found, implementation incomplete?")
                        else:
                            # logger.debug(f"Right guard found following the body monoid, next token is {tl3[0]!r}), implementation incomplete?")
                            ### TODO: refactore clone
                            # Need to extend alphabet without compromising guards
                            # logger.debug(f"{Monoid.explode(m.left) - lexeme_chars}") 
                            # logger.debug(f"{Monoid.explode(m.right) - lexeme_chars}") 
                            # logger.debug(f"{not(missing_chars <= Monoid.explode(m.left))}") 
                            # logger.debug(f"{not(missing_chars <= Monoid.explode(m.right))}")
                            if (Monoid.explode(m.left) - lexeme_chars != set() and Monoid.explode(m.right) - lexeme_chars != set()) or not(missing_chars <= Monoid.explode(m.left)) or not(missing_chars <= Monoid.explode(m.right)) :
                                logger.debug(f"Extended alphabet by {Monoid.implode(missing_chars)}")
                                token  = Comment(m.alphabet | lexeme_chars, m.left, m.right)
                                ltoken = LToken(token, lexemes[0].start, tl3[0].start, m.left + body.lexeme + m.right)
                                logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                                return [ltoken] + _comment_instances(json_data, tl3, tokens)
                            else:
                                logger.debug(f"Cannot extend alphabet")
                    else:
                        # Right is guard part of body monoid, and may spill into next lexemes
                        body1, tl4 = split_postfix(m.right, tl1)
                        if tl4 != None and tl4 != []:
                            # Found the right guard
                            lexeme_chars = Monoid.explode(body1.lexeme)
                            if lexeme_chars <= m.alphabet:
                                # Alphabet big enough after (partially) splitting off right guard
                                logger.debug(f"Alphabet big enough after (partially) splitting off right guard")
                                ltoken = LToken(m, lexemes[0].start, tl4[0].start, m.left + body1.lexeme + m.right)
                                logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                                return [ltoken] + _comment_instances(json_data, tl4, tokens)
                            else:
                                # Need to extend alphabet without compromising guards
                                ### TODO: why does this check for left twice??
                                if Monoid.explode(m.left) - lexeme_chars != set() and Monoid.explode(m.left) - lexeme_chars != set():
                                    logger.debug(f"Extended alphabet by {Monoid.implode(lexeme_chars - m.alphabet)}")
                                    token  = Comment(m.alphabet | lexeme_chars, m.left, m.right)
                                    ltoken = LToken(token, lexemes[0].start, tl4[0].start, m.left + body1.lexeme + m.right)
                                    logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                                    return [ltoken] + _comment_instances(json_data, tl4, tokens)
                                else:
                                    logger.debug(f"Cannot extend alphabet")
            else:
                logger.debug(f"Next token {body!r} is not a suitable monoid, skipping comment {m!r}")
                logger.debug(f"comment alphabet:\n{Monoid.implode(m.alphabet)}")
                logger.debug(f"body alphabet:\n{Monoid.implode(body.token.alphabet)}")

    # No comment instance found, try next position
    return [lexemes[0]] + _comment_instances(json_data, lexemes[1:], tokens)


def comment_instances(json_data, lexemes, tokens):

    if len(lexemes) < 3:
        return lexemes

    for m in tokens:
        if isinstance(m, Comment):

            # Check for mis-identified left guards
            # TODO: should be properly folded into code below
            fst, snd = lexemes[0], lexemes[1]
            if isinstance(snd.token, Comment) and fst.lexeme + snd.token.left == m.left and snd.token.right == m.right and snd.token.alphabet == m.alphabet:
                ltoken = LToken(m, fst.start, snd.end, fst.lexeme + snd.lexeme)
                logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                return [ltoken] + comment_instances(json_data, lexemes[2:], tokens)

            # Check for left guard, try next guarded magma if not found
            tail = split_prefix(m.left, lexemes)
            if tail == None or tail == []:
                continue
            logger.debug(f"Found left guard {m.left}, checking comment {m!r}")

            # Merge illegal characters and monoids into single token
            body, tail1 = find_body(m.alphabet, None, tail)

            # Check for body monoid
            if body == None:
                tl2 = split_prefix(m.right, tail1)
                if tl2 != None and tl2 != []:
                    ltoken = LToken(m, lexemes[0].start, tl2[0].start, m.left + m.right)
                    logger.log("DETAIL", f"Identified empyty comment {ltoken!r}")
                    return [ltoken] + comment_instances(json_data, tl2, tokens)
                elif tl2 == []:
                    ltoken = LToken(m, lexemes[0].start, tail1[-1].end, m.left + m.right)
                    logger.log("DETAIL", f"Identified empyty comment {ltoken!r} at end of file")
                    return [ltoken]
                else:
                    logger.debug(f"Next token {body!r} is not a suitable monoid, skipping comment {m!r}")
                    continue

            # Check for alphabet compatibility and lexeme match
            if Monoid.explode(body.lexeme) <= m.alphabet:
                logger.debug(f"Found body {body!r} with compatible alphabet {Monoid.implode(m.alphabet)}")
                if tail1 == []:
                    logger.debug(f"File ends before right guard {m.right!a} of comment {m!r} found, creating new comment token without right guard")
                    ltoken = LToken(Comment(m.alphabet, m.left, None, False), lexemes[0].start, lexemes[-1].end, m.left + body.lexeme)
                    logger.log("DETAIL", f"Identified new comment {ltoken!r} without right guard")
                    return [ltoken]
                tl2 = split_prefix(m.right, tail1)
                if tl2 != None and tl2 != []:
                    ltoken = LToken(m, lexemes[0].start, tl2[0].start, m.left + body.lexeme + m.right)
                    logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                    return [ltoken] + comment_instances(json_data, tl2, tokens)
                elif tl2 == []:
                    ltoken = LToken(m, lexemes[0].start, tail1[-1].end, m.left + body.lexeme + m.right)
                    logger.log("DETAIL", f"Identified new instance of comment {ltoken!r} at end of file")
                    return [ltoken]
                else:
                    logger.debug(f"Did not find right guard in mono, need to check next lexemes {tail1[1:]!r}")
            else:
                lexeme_chars  = Monoid.explode(body.lexeme)
                missing_chars = lexeme_chars - m.alphabet
                logger.debug(f"Alphabet of {m!r} not big enough to capture lexeme {body.lexeme!a}, missing characters {Monoid.implode(missing_chars)}")
                logger.log("DETAIL", f"Alphabet of {m!r} not big enough to capture lexeme {body.lexeme!a}")
                tl3 = split_prefix(m.right, tail1)
                if tl3 != None:
                    # Right guard found following the body monoid,
                    # so need to check whether the alphabet can be extended
                    if tl3 == []:
                        logger.debug(f"Reached end of file before right guard found, implementation incomplete?")
                    else:
                        # logger.debug(f"Right guard found following the body monoid, next token is {tl3[0]!r}), implementation incomplete?")
                        ### TODO: refactore clone
                        # Need to extend alphabet without compromising guards
                        # logger.debug(f"{Monoid.explode(m.left) - lexeme_chars}") 
                        # logger.debug(f"{Monoid.explode(m.right) - lexeme_chars}") 
                        # logger.debug(f"{not(missing_chars <= Monoid.explode(m.left))}") 
                        # logger.debug(f"{not(missing_chars <= Monoid.explode(m.right))}")
                        if (Monoid.explode(m.left) - lexeme_chars != set() and Monoid.explode(m.right) - lexeme_chars != set()) or not(missing_chars <= Monoid.explode(m.left)) or not(missing_chars <= Monoid.explode(m.right)) :
                            logger.debug(f"Extended alphabet by {Monoid.implode(missing_chars)}")
                            token  = Comment(m.alphabet | lexeme_chars, m.left, m.right)
                            ltoken = LToken(token, lexemes[0].start, tl3[0].start, m.left + body.lexeme + m.right)
                            logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                            return [ltoken] + comment_instances(json_data, tl3, tokens)
                        else:
                            logger.debug(f"Cannot extend alphabet")
                else:
                    # Right is guard part of body monoid, and may spill into next lexemes
                    body1, tl4 = split_postfix(m.right, [body] + tail1)
                    if tl4 != None and tl4 != []:
                        # Found the right guard
                        lexeme_chars = Monoid.explode(body1.lexeme)
                        if lexeme_chars <= m.alphabet:
                            # Alphabet big enough after (partially) splitting off right guard
                            logger.debug(f"Alphabet big enough after (partially) splitting off right guard")
                            ltoken = LToken(m, lexemes[0].start, tl4[0].start, m.left + body1.lexeme + m.right)
                            logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                            return [ltoken] + comment_instances(json_data, tl4, tokens)
                        else:
                            # Need to extend alphabet without compromising guards
                            ### TODO: why does this check for left twice??
                            if Monoid.explode(m.left) - lexeme_chars != set() and Monoid.explode(m.left) - lexeme_chars != set():
                                logger.debug(f"Extended alphabet by {Monoid.implode(lexeme_chars - m.alphabet)}")
                                token  = Comment(m.alphabet | lexeme_chars, m.left, m.right)
                                ltoken = LToken(token, lexemes[0].start, tl4[0].start, m.left + body1.lexeme + m.right)
                                logger.log("DETAIL", f"Identified new instance of comment {ltoken!r}")
                                return [ltoken] + comment_instances(json_data, tl4, tokens)
                            else:
                                logger.debug(f"Cannot extend alphabet")

    # No comment instance found, try next position
    return [lexemes[0]] + comment_instances(json_data, lexemes[1:], tokens)


#####
#
# Find comments that contain multiple text segments within the keywords
#
#####

def comment_segments(json_data, lexemes, tokens):

    if lexemes == []:
        return lexemes

    left = lexemes[0]

    for m in tokens:
        if isinstance(m, Comment) and isinstance(left.token, Keyword) and m.left == left.lexeme and not(isinstance(left.token, Comment)):
            logger.debug(f"Checking for comment with multiple segments and left guard {left!r}")
            right_i = next((i+1 for (i, l) in enumerate(lexemes[1:]) if isinstance(l.token, Keyword) and m.right == l.lexeme), None)
            if right_i != None and right_i > 2 and right_i < len(lexemes):
                lexeme = ''.join([l.lexeme for l in lexemes[1:right_i]])
                if Monoid.explode(lexeme) <= m.alphabet:
                    ltoken = LToken(m, left.start, lexemes[right_i].end, m.left + lexeme + m.right)
                    logger.debug(f"Merging multiple lexemes {lexemes[1:right_i]!r} into {ltoken!r}")
                    logger.log("DETAIL", f"Merged multiple lexemes into {ltoken!r}")
                    return [ltoken] + comment_segments(json_data, lexemes[right_i+1:], tokens)

    # Nothing found, try next position
    return [lexemes[0]] + comment_segments(json_data, lexemes[1:], tokens)


#####
#
# Gobble up token segments between identified comment brackets
#
#####

def gobble_comment_instances(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst = lexemes[0]

    #########
    for c in tokens:
        if isinstance(c, Comment) and len(c.left) > 1 and (c.right != None and len(c.right) > 1):
            if (i := find_existing_guard(lexemes, 0, c.left)) and i != None:
                logger.debug(f"Trying to gobble up lexemes into comment {c}, starting at {lexemes[i]!r}")
                end, level, recursive = 0, 0, False
                while i < len(lexemes):
                    if (j := find_existing_guard(lexemes, i, c.right)) and j != None:
                        logger.debug(f"Found closing bracket at {lexemes[i:j]!r}")
                        if level == 0:
                            end = j
                            break
                        else: 
                            level = level-1
                    if (j := find_existing_guard(lexemes, i, c.left)) and j != None:
                        logger.debug(f"Found another opening bracket at {lexemes[i:j]!r}")
                        level, recursive = level+1, True
                    ### TODO: need to check for comments
                    if lexemes[i].token == c:
                        logger.debug(f"Found recursive comment at {lexemes[i]!r}")
                        recursvie = True
                    i = i + 1
                if end != 0:
                    lexeme = ''.join([l.lexeme for l in lexemes[0:end]])
                    ltoken = LToken(Comment(Monoid.explode(CHAR_SET), c.left, c.right, recursive), lexemes[0].start, lexemes[end-1].end, lexeme)
                    logger.debug(f"Merging multiple lexemes {lexemes[0:end+1]!r} into comment {ltoken!r}")
                    logger.log("DETAIL", f"Merged multiple lexemes into comment {c!r}")
                    return [ltoken] + gobble_comment_instances(json_data, lexemes[end:], tokens)
                else:
                    logger.debug(f"Did not find closing bracket, i={i}")

    return [lexemes[0]] + gobble_comment_instances(json_data, lexemes[1:], tokens)
    #########


    ### TODO: delete, old code
    if isinstance(fst.token, Keyword):
         c = next((c for c in tokens if isinstance(c, Comment) and fst.lexeme == c.left), None)
         if c != None:
            logger.debug(f"Trying to gobble up tokens into comment {c}")
            i, end, level, recursive = 1, 0, 0, False
            while i < len(lexemes):
                if lexemes[i].lexeme == c.right:
                    logger.debug(f"Found closing bracket")
                    if level == 0:
                        end = i
                        break
                    else: 
                        level = level-1
                if lexemes[i].lexeme == c.left:
                    logger.debug(f"Found another opening bracket")
                    level, recursive = level+1, True
                ### TODO: need to check for comments
                i = i + 1
            if end != 0:
                lexeme = ''.join([l.lexeme for l in lexemes[0:end+1]])
                ltoken = LToken(Comment(Monoid.explode(CHAR_SET), c.left, c.right, recursive), lexemes[0].start, lexemes[end].end, lexeme)
                logger.debug(f"Merging multiple text segments {lexemes[0:end+1]!r} into comment {ltoken!r}")
                logger.log("DETAIL", f"Merged multiple text segments into comment {c!r}")
                return [ltoken] + gobble_comment_instances(json_data, lexemes[end+1:], tokens)

    return [lexemes[0]] + gobble_comment_instances(json_data, lexemes[1:], tokens)


def find_existing_guard(lexemes, offset, lexeme):
    if isinstance(lexemes[offset].token, Keyword) and lexemes[offset].lexeme == lexeme:
        logger.debug(f"Found keyword {lexemes[offset]!r} at offset {offset}")
        return offset + 1
    if isinstance(lexemes[offset].token, Monoid) and lexemes[offset].lexeme[-1] == lexeme[0]:
        for i in range(1, len(lexeme)):
            if lexemes[offset+i].token.single_character() != lexeme[i]:
                return None
        logger.debug(f"Found character sequence at end of monoid {lexemes[offset:len(lexeme)]!r} at offset {offset}:{offset+len(lexeme)}")
        return offset + len(lexeme)
    elif lexemes[offset].token.single_character() == lexeme[0]:
        for i in range(0, len(lexeme)):
            if offset+i >= len(lexemes) or lexemes[offset+i].token.single_character() != lexeme[i]:
                return None
        logger.debug(f"Found character sequence {lexemes[offset:len(lexeme)]!r} at offset {offset}:{offset+len(lexeme)}")
        return offset + len(lexeme)
    else:
        return None


#####
#
# Find texts without resorting to keywords as guards
#
#####

def basic_comment(json_data, lexemes, tokens):

    # This is used as backup only if there are no text instances that use
    # keywords as guards.
    if next((c for c in tokens if isinstance(c, Comment)), None):
        return lexemes

    if len(lexemes) < 2:
        return lexemes

    # Find left guard: either a sequence of single characters, or a keyword
    (left, i) = find_guard("left", lexemes, 0)
    if left == None:
        return [lexemes[0]] + basic_comment(json_data, lexemes[1:], tokens)

    # Find body - for the basic case, this must be a single FreeMonoid
    ### TODO: generalize to list of monoids
    if i >= len(lexemes) - 1 or not ((body := lexemes[i]) and isinstance(body.token, FreeMonoid)):
        return [lexemes[0]] + basic_comment(json_data, lexemes[1:], tokens)

    # Find right guard (same condition as left, but guard can be different and is optional)
    (right, j) = find_guard("right", lexemes, i+1)
    if right == None:
        logger.debug(f"Checking for sequence with {body!r} and left guard {lexemes[0:i]!a} and empty right guard")
    else:
        logger.debug(f"Checking for sequence with {body!r} and guards {lexemes[0:i]!a} and {lexemes[i+1:j]!a}")

    # Check that body allows all printable characters except guard characters
    patch    = None
    sequence = None 
    alphabet = Monoid.explode(CHAR_SET) - (Monoid.explode(left) | Monoid.explode(right))
    if right != None and body.token.alphabet == alphabet:
        # Guard characters are not allowed in the body
        sequence = Comment(body.token.alphabet, left, right)
    elif right != None and alphabet <= body.token.alphabet and Monoid.explode(body.lexeme) <= alphabet:
        ### TODO: check, should probably be removed
        # Guard characters are allowed but do not occur in the body
        sequence = Comment(alphabet, left, right)
    else:
        # Check whether the right guard can be patched from the next lexeme
        missing = alphabet-body.token.alphabet
        if right == None and len(missing) == 1 and (patch := lexemes[j].patch_first(missing)) and patch != None: # (*)
            right    = missing
            sequence = Comment(body.token.alphabet, left, right)
            logger.debug(f"Missing character: {Monoid.implode(missing)}, found as next input character")
        else:
            logger.debug(f"Missing characters: {Monoid.implode(missing)}, skipping")

    if sequence != None:
        lexeme = ''.join([l.lexeme for l in lexemes[0:j]])
        if j < len(lexemes):
            # Check that next token doesn't belong to the magma
            nxt = lexemes[j]
            if isinstance(nxt.token, Monoid) and body.token.alphabet == nxt.token.alphabet:
                logger.debug(f"Next token {nxt!r} can be merged, skipping")
                return [lexemes[0]] + basic_comment(json_data, lexemes[1:], tokens)
            else:
                if isinstance(nxt.token, Monoid):
                    bdy_only = Monoid.implode(body.token.alphabet - nxt.token.alphabet)
                    nxt_only = Monoid.implode(nxt.token.alphabet - body.token.alphabet)
                    logger.debug(f"Next token {nxt!r} ok, difference in alphabets is {bdy_only}, {nxt_only}")
                else:
                    logger.debug(f"Next token {nxt!r} ok")
        if patch == None:
            # Right guard found on its own
            ltoken = LToken(sequence, lexemes[0].start, lexemes[j-1].end, lexeme)
            logger.debug(f"Merging {left!a}, {body!r}, and {right!a} into {ltoken!r}")
            logger.log("DETAIL", f"Merging {left!a}, {body.token!r}, and {right!a} into {sequence!r}")
            return [ltoken] + basic_comment(json_data, lexemes[j:], tokens)
        else:
            logger.error(f"Code never tested!")
            # Right guard found by patching; all conditions from (*) must be true
            lexeme += missing
            ltoken = LToken(sequence, lexemes[0].start, lexemes[j-1].end + 1, lexeme)
            logger.debug(f"Merging {left!a}, {body!r}, and {right!a} into {ltoken!r}")
            logger.log("DETAIL", f"Merging {left!a}, {body.token!r}, and {right!a} into {sequence!r}")
            if j+1 > len(lexemes):
                # Patch eats up the rest of the lexemes
                return [ltoken]
            else:
                return [ltoken] + basic_comment(json_data, patch + lexemes[j+1:], tokens)

    # No sequence found, try next position
    return [lexemes[0]] + basic_comment(json_data, lexemes[1:], tokens)

#############################################################################
#
# Auxiliary 
#
#############################################################################


#
# Check whether the lexeme list starts with a given guard string, starting with
# the tail of the first lexeme (which must be a monoid). Split monoid lexemes
# if necessary. Return first lexeme (with split-off guard prefixes) and
# remaining lexemes or None if prefix is not found. 
#
def split_postfix(guard, lexemes):

    mono = lexemes[0]
    assert isinstance(mono.token, Monoid), "Trying to split right guard from a non-monoid token"
    logger.debug(f"Trying to split guard {guard!a} from mono {mono!r}")

    # Check whether first lexeme (== monoid body) ends with (parts of the) guard
    _guard, end = guard, -1
    while _guard != "":
        if (end := mono.lexeme.rfind(_guard) and end == -1):
            # Try shorter part of guard
            _guard = _guard[:-1]
        else:
            break

    if _guard == "":
        # No part of the guard is in the monoid, so check remaining lexemes
        return mono, split_prefix(guard, lexemes[1:])
    else:
        # Split mono, search for remaining guard in remaining lexemes
        end = mono.lexeme.rfind(_guard) ### need to check again, end is treated as boolean
        # assert end != -1
        if end == -1:
            logger.debug(f"Call to rfind({_guard!a}) failed on mono lexeme {mono.lexeme!a} ")
            # TODO: Not sure returning a None for the LToken is right..
            return None, None
        body = LToken(mono.token, mono.start, mono.start + end, mono.lexeme[:end])
        gstart = guard.find(_guard)
        assert gstart != --1
        return body, split_prefix(guard[gstart+len(_guard):], lexemes[1:])


#
# Find a left/right guard
#
# Checks for either a sequence of single characters, or a keyword, which is
# used as guard for the magma's body. Takes as input the list of lexemes and an
# index offset where the search starts, and returns the lexeme (or None) and
# the end position of the guard as lexeme index.
#
def find_guard(kind, lexemes, offset):
    keychr = False  # No single-character keyword found yet
    guard  = ""
    for i, l in enumerate(lexemes[offset:]):
        if (c := l.token.single_character()) == None: 
            break
        elif keychr and isinstance(l.token, Keyword):
            break
        else:
            guard += c
        if isinstance(l.token, Keyword):
            keychr = True
    if i == 0:
        # No single character sequence found, check for keyword
        if isinstance(lexemes[offset].token, Keyword):
            guard = lexemes[offset].lexeme
            index = offset + 1
        else:
            return (None, offset)
    else:
        index = offset + i
    logger.debug(f"Found {kind} guard: {guard!a} at index range {offset}:{index}, source range {lexemes[offset].start}:{lexemes[index-1].end}")
    return (guard, index)


#
# Merge tokens following leading monoid over alphabet into one
#
def merge_leading_monoids(alphabet, mono, lexemes):
    if not isinstance(mono.token, Monoid):
        logger.debug(f"Comment body token {mono!r} not a monoid")
        return [mono] + lexemes
    elif not(set(mono.lexeme) <= alphabet):
        logger.debug(f"Comment body token {mono!r} contains characters {Monoid.explode(set(mono.lexeme) - alphabet)} not in comment alphabet")
        return [mono] + lexemes
    else:
        return __merge_leading_monoids(alphabet, mono, lexemes)

def __merge_leading_monoids(alphabet, mono, lexemes):
    if lexemes == []:
        return [mono]
    nxt = lexemes[0]
    if isinstance(nxt.token, Monoid):
        nxtalpha = nxt.token.alphabet
    elif isinstance(nxt.token, IllegalCharacter):
        nxtalpha = nxt.token.subst
    else:
        logger.debug(f"Found token type {nxt!r}, stopping search")
        return [mono] + lexemes
    if alphabet <= nxtalpha and set(nxt.lexeme) <= alphabet:
        return __merge_leading_monoids(alphabet, LToken(mono.token, mono.start, nxt.end, mono.lexeme + nxt.lexeme), lexemes[1:])
    else:
        logger.debug(f"Alphabet check failed for {nxt!r}, stopping search")
        return [mono] + lexemes

def find_body(alphabet, body, lexemes):
    if lexemes == []:
        return body, []
    nxt = lexemes[0]
    logger.debug(f"{body=}, {nxt=}")
    if isinstance(nxt.token, Monoid):
        nxtalpha = nxt.token.alphabet
    elif isinstance(nxt.token, IllegalCharacter):
        # nxtalpha = nxt.token.subst
        nxtalpha = {nxt.token.char}
    else:
        logger.debug(f"Found unexpected token type {nxt!r} in comment, stopping search")
        return body, lexemes
    if body == None:
        start, lexeme = nxt.start, ""
    else:
        start, lexeme = body.start, body.lexeme
    if nxtalpha <= alphabet:
        return find_body(alphabet, LToken(FreeMonoid(alphabet), start, nxt.end, lexeme + nxt.lexeme), lexemes[1:])
    elif alphabet <= nxtalpha:
        if set(nxt.lexeme) <= alphabet:
            return find_body(alphabet, LToken(FreeMonoid(alphabet), start, nxt.end, lexeme + nxt.lexeme), lexemes[1:])
        else:
            logger.debug(f"Extending alphabet by {Monoid.implode(nxtalpha-alphabet)}")
            return find_body(nxtalpha, LToken(FreeMonoid(nxtalpha), start, nxt.end, lexeme + nxt.lexeme), lexemes[1:])
    else:
        logger.debug(f"Alphabet check failed for {nxt!r}, stopping search")
        return body, lexemes


#
# Check whether a segment of lexemes is compatible with a given monoid token 
#
def check_segment(mono, segment):
    alphabet  = mono.alphabet
    alpha_set = alphabet
    for l in segment:
        if l.token == mono:
            pass
        elif isinstance(l.token, FreeMonoid) and (l.token.alphabet == alphabet):
            pass
        else: 
            # Check whether single character is in the alphabet
            c = l.token.single_character()
            if c != None and (c in alpha_set):
                pass
            else:
                return False
    return True

