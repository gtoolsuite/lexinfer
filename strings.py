#############################################################################
#
# Strings with escaping
#
# A string with escape characters is a guarded magma where the magma's alphabet
# comprises only a subset of the full character set while the remaining
# characters are represented by multi-character sequences starting with an
# escape character.
#
#############################################################################

#
# Imports and configuration
#

### Logging
from loguru   import logger
from loginfer import Loginfer

### Token constructors
from tokens   import LToken, TokenT, Keyword, OperatorSymbol, Monoid, FreeMonoid, LeftPointedMonoid, GuardedMagma, IllegalCharacter
from comments import Comment

### Global "constants", may be overwritten by command line options
from config import CHAR_SET, ALPHABET, ESC_LENGTH

### Auxiliary
from auxiliary import split_prefix

#############################################################################
#
# Token class
#
#############################################################################

class String(GuardedMagma):

    def __init__(self, alphabet, left, right, escape_chr, escape_seq=set()):
        GuardedMagma.__init__(self, alphabet, left, right)
        self.escape_chr = escape_chr
        self.escape_seq = escape_seq
        if (esc := next((e for e in escape_seq if e[0] != escape_chr), None)) and esc != None:
            raise ValueError(f"Escape sequence {esc!a} does not start with escape character {escape_chr!a}")

    def __str__(self):
        return f"String({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a}, {self.escape_chr!a}, {TokenT.set_repr(self.escape_seq)})"

    def __repr__(self):
        return f"String({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a}, {self.escape_chr!a}, {self.escape_seq!a})"


#############################################################################
#
# Recognition functions
#
#############################################################################


#####
#
# A basic string literal is a sequence that does not use any escape sequences,
# even though the language supports string escaping; note that strings without
# escape mechanism (e.g., Modula-2's strings with two different quotes) are
# handled as guarded magmas. We assume that there's at most a single printable
# character (except the string quotes) that cannot be used in a string; we
# assume that this is used as escape character.
#
# Note that this requires at least three missing characters if opening and
# closing quotes are different; otherwise this should be matched as a
# comment-like basic sequence.
#
#####

def string_literal(json_data, lexemes, info=None):

    if len(lexemes) < 3:
        return lexemes

    fst, snd, trd = lexemes[0], lexemes[1], lexemes[2]

    if isinstance(fst.token, Keyword) and (isinstance(snd.token, FreeMonoid) or snd.token.single_character()) and isinstance(trd.token, Keyword):
        logger.debug(f"Checking for string literal {[fst, snd, trd]!a}")

        # Get the alphabet; for singleton characters, take the substitution set
        if isinstance(snd.token, FreeMonoid):
            alphabet = snd.token.alphabet
        else:
            alphabet = Monoid.explode(json_data[snd.start]["Substitution"])

        # The lexeme is possibly a string with escapes if there is only a single
        # (printable) character missing in the monoid's alphabet.
        missing    = Monoid.explode(CHAR_SET) - alphabet
        escapees   = {c for c in missing if not c.isprintable()}
        ### TODO: Remove fst.lexeme (== left quote) as well
        ### Note, the current version works if the string uses the same 
        ###  characters as left and right quotes or if the left quote's 
        ###  characters can all be used without escaping (because it is 
        ###  in alphabet then).
        escape_set = list(missing - escapees - Monoid.explode(trd.lexeme))
        logger.debug(f"escapees {escapees!a}, escape_set {escape_set!a}")
        if len(escape_set) == 1:
            strlit = String(alphabet, fst.lexeme, trd.lexeme, escape_set[0])
            newlex = "".join([l.lexeme for l in lexemes[0:3]])
            ltoken = LToken(strlit, fst.start, trd.end, newlex)
            logger.debug(f"Merging {lexemes[0:3]!r} into {ltoken!r}")
            logger.log("DETAIL", f"Merging {[fst.token, snd.token, trd.token]!r} into string literal {strlit!r}, possibly escaped characters {Monoid.implode(escapees)}")
            return [ltoken] + string_literal(json_data, lexemes[3:], info)

    # No string found, try next position
    return [lexemes[0]] + string_literal(json_data, lexemes[1:], info) 


#####
#
# String literals with right guard not a keyword
#
#####

def string_instances(json_data, lexemes, strings):

    if len(lexemes) < 3:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    for s in strings:
        if fst.lexeme == s.left and isinstance(snd.token, FreeMonoid) and snd.token.alphabet == s.alphabet:
            logger.debug(f"Checking for new instance of {s!r}, starting with {fst!r}")
            tail = split_prefix(s.right, lexemes[2:])
            if tail != None:
                if tail == []:
                    end = lexemes[-1].end
                else:
                    end = tail[0].start
                ltoken = LToken(s, fst.start, end, s.left + snd.lexeme + s.right)
                logger.log("DETAIL", f"Identified new instance of string {ltoken!r}")
                return [ltoken] + string_instances(json_data, tail, strings)

    # Nothing found, try next position
    return [lexemes[0]] + string_instances(json_data, lexemes[1:], strings) 


#####
#
# String literals with escape sequence(s)
#
#####

def string_literal_with_escapes(json_data, lexemes, sorted_tokens):

    # Need at least opening and closing quotes, and escape and escaped characters
    if len(lexemes) < 4:
        return lexemes

    fst = lexemes[0]
    for s in [s for s in sorted_tokens if (isinstance(s, String) and (isinstance(fst.token, Keyword) or isinstance(fst.token, OperatorSymbol)) and fst.lexeme == s.left)]:

        logger.debug(f"Checking for escape sequences for {s!r}")

        # right = next((i+1 for (i,l) in enumerate(lexemes[1:]) if lexemes[i].lexeme != s.escape_chr and l.lexeme.startswith(s.right)), len(lexemes))
        ### Search for right quote, unless it is escaped, but find it if the escape is escaped
        right = next((i+1 for (i,l) in enumerate(lexemes[1:]) if (l.lexeme.startswith(s.right) and ((lexemes[i].lexeme != s.escape_chr) or (i>0 and (lexemes[i-1].lexeme == s.escape_chr))))), len(lexemes))
        success, escape_seq, tail = _split_escapes(False, s.escape_chr, s.right, lexemes[1:right+1])
        # if success and lexemes[right].lexeme == s.right:
        if success and lexemes[right].lexeme.startswith(s.right):
            logger.debug(f"Adding escape sequences {escape_seq}")
            newstr = String(s.alphabet, s.left, s.right, s.escape_chr, s.escape_seq | escape_seq)
            # lexeme = ''.join([l.lexeme for l in lexemes[0:right+1]])
            # ltoken = LToken(newstr, fst.start, lexemes[right].end, lexeme)
            if tail == []:
                lexeme = ''.join([l.lexeme for l in lexemes[0:right+1]])
                ltoken = LToken(newstr, fst.start, lexemes[right].end, lexeme)
            else:
                lexeme = ''.join([l.lexeme for l in lexemes[0:right]]) + s.right
                ltoken = LToken(newstr, fst.start, tail[0].start, lexeme)
            logger.log("DETAIL", f"Merged {lexemes[0:right+1]!r} into string {newstr!r}")
            # return [ltoken] + string_literal_with_escapes(json_data, lexemes[right+1:], sorted_tokens) 
            return [ltoken] + string_literal_with_escapes(json_data, tail + lexemes[right+1:], sorted_tokens) 
        else:
            if right + 1 < len(lexemes):
                logger.warning(f"Cannot identify escape sequences for {s!r}, right is {right}, len(lexemes) is {len(lexemes)}, escape sequence is {escape_seq}, matched sequence is {lexemes[0:right]!a}, next tokens are {lexemes[right:right+2]!r}")
            else:
                logger.warning(f"Cannot identify escape sequences for {s!r}, reached end of input, escape sequence is {escape_seq}, matched sequence is {lexemes[0:right]!a}")

    # Nothing found, try next position
    return [lexemes[0]] + string_literal_with_escapes(json_data, lexemes[1:], sorted_tokens) 


#
# Patch escaped string quotes
#
def string_literal_with_escaped_quotes(json_data, lexemes, sorted_tokens):

    # Need at least opening and closing quotes, and escape and escaped characters
    if len(lexemes) < 3:
        return lexemes

    fst, snd, trd = lexemes[0], lexemes[1], lexemes[2]
    if not(isinstance(fst.token, Keyword) and isinstance(snd.token, Keyword) and isinstance(trd.token, String)):
        return [lexemes[0]] + string_literal_with_escaped_quotes(json_data, lexemes[1:], sorted_tokens) 

    for s in [s for s in sorted_tokens if(isinstance(s, String) and s.left == fst.lexeme and s.escape_chr == snd.lexeme)]:

        logger.debug(f"Patching escaped quotes for {s!r}")
        newstr = String(s.alphabet, s.left, s.right, s.escape_chr, s.escape_seq | {s.escape_chr + snd.lexeme} | trd.token.escape_seq)
        lexeme = ''.join([l.lexeme for l in lexemes[0:3]])
        ltoken = LToken(newstr, fst.start, trd.end, lexeme)
        logger.log("DETAIL", f"Merged {lexemes[0:3]!r} into string {newstr!r}")
        return [ltoken] + string_literal_with_escaped_quotes(json_data, lexemes[3:], sorted_tokens) 

    return [lexemes[0]] + string_literal_with_escaped_quotes(json_data, lexemes[1:], sorted_tokens) 


#####
#
# Reclassify comments as strings
# 
# The comment classification may consider escape characters as closing brackets
# and thus misclassify strings (e.g., in JSON). We overwrite this here if we
# have found "proper" basic strings.
#
#####

def reclassify_comment_as_string(json_data, lexemes, sorted_tokens):

    # TODO: Bail early if there are no comments in tokens??
    # if len(lexemes) < 3 or next((c for c in tokens if isinstance(c, Comment)), None) == None:
    # TODO: Instead: split lexems to find next comment, start from there

    if len(lexemes) < 3:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]
    c = fst.token

    # No comment found, try next position
    if not isinstance(c, Comment):
        return [lexemes[0]] + reclassify_comment_as_string(json_data, lexemes[1:], sorted_tokens) 

    for s in [s for s in sorted_tokens if (isinstance(s, String) and s.left == c.left and s.escape_chr == c.right and s.alphabet == c.alphabet)]:

        logger.debug(f"Trying to reclassify comment {fst!r} as string {s!r}")

        ### right = next((i for i in range(2, len(lexemes)) if (l := lexemes[i]) and l.lexeme == s.right or (isinstance(l.token, Comment) and l.token.right == s.right)), None)
        ### right = next((i for i in range(2, len(lexemes)) if (l := lexemes[i]) and (l.lexeme == s.right and not lexemes[i-1].lexeme == s.escape_chr and not lexemes[i-1].token == c) or (isinstance(l.token, Comment) and l.token.right == s.right)), None)
        logger.debug(f"first two ltokens: {lexemes[0:2]!r}")
        right = _find_next_right_guard(lexemes, 2, s.right, s.escape_chr)
        logger.debug(f"{right=}")
        if right != None:
            logger.debug(f"First escaped ltoken is {snd}")
            logger.debug(f"Found right quote {lexemes[right]!r}")
            logger.debug(f"New string is {''.join(t.lexeme for t in lexemes[0:right+1])}")
            logger.debug(f"LTokens are {lexemes[0:right+1]}")
            logger.debug(f"Length of ltokens is {right+1}")
            success, escape_seq, tail = _split_escapes(True, s.escape_chr, s.right, lexemes[1:right+1])
            if success:
                logger.debug(f"Found escape sequences {escape_seq!a}")
                newstr = String(s.alphabet, s.left, s.right, s.escape_chr, s.escape_seq | escape_seq)
                ltoken = LToken(newstr, fst.start, lexemes[right].end, ''.join(t.lexeme for t in lexemes[0:right+1]))
                logger.debug(f"Merged {lexemes[0:right+1]!r} into string {ltoken!r}")
                logger.log("DETAIL", f"Merged {lexemes[0:right+1]!r} into string {newstr!r}")
                # return [ltoken] + reclassify_comment_as_string(json_data, lexemes[right+1:], sorted_tokens) 
                return [ltoken] + reclassify_comment_as_string(json_data, tail + lexemes[right+1:], sorted_tokens) 
            else:
                logger.debug(f"Failed to reclassify")
        else:
            logger.debug(f"Could not find right guard {s.right!a}, remaining lexemes {lexemes[1:]!r}")

    # No string found, try next position
    return [lexemes[0]] + reclassify_comment_as_string(json_data, lexemes[1:], sorted_tokens) 

def _find_next_right_guard(ltokens, i, right, escape):
    if i == len(ltokens):
        return None
    logger.debug(f"Checking {i=}, {ltokens[i]!r}")
    if ltokens[i].lexeme != right:
        logger.debug("not right guard, recursing")
        return _find_next_right_guard(ltokens, i+1, right, escape)
    if i > 0 and ltokens[i-1].lexeme.endswith(escape + escape):
        logger.debug(f"found after double-escape {ltokens[i-1]!r}")
        return i
    if i > 1 and ltokens[i-1].lexeme == escape and ltokens[i-2].lexeme.endswith(escape):
        logger.debug(f"found after two escapes {ltokens[i-2:i]!r}")
        return i
    if ltokens[i-1].lexeme.endswith(escape):
        logger.debug("found escaped guard") 
        return _find_next_right_guard(ltokens, i+1, right, escape)
    logger.debug("found unescaped guard") 
    return i


### recursively split off first character (assumed to be the escaped character if bind==True), process rest
### right is the right quote character of the target string
def _split_escapes(bind, escape_chr, right, lexemes, escape_seq=set()):
    logger.debug(f"_split_escapes called with {bind = } and {len(lexemes)}-element lexeme list {lexemes!r}")
    if len(lexemes) == 0:
        return True, escape_seq, []
    l = lexemes[0]
    t = l.token
    if len(lexemes) == 1 and  isinstance(t, Comment) and t.right == right:
        return True, escape_seq | {t.left}, []
    elif len(lexemes) == 1:
        tail = split_prefix(right, lexemes)
        if tail == None:
            logger.warning(f"Incomplete implementation, missing case for {l!r}")
            return False, set(), lexemes
        else:
            return True, escape_seq, tail
    elif bind:
        if isinstance(t, IllegalCharacter) or isinstance(t, OperatorSymbol):
            logger.debug(f"Adding escaped characters {t.subst!a}")
            return _split_escapes(False, escape_chr, right, lexemes[1:], escape_seq | {escape_chr + e for e in t.subst})
        elif isinstance(t, Comment) and t.right == escape_chr:
            return _split_escapes(False, escape_chr, right, lexemes[1:], escape_seq | {escape_chr + t.left})
        elif isinstance(t, Monoid):
            if len(l.lexeme) == 1:
                return _split_escapes(False, escape_chr, right, lexemes[1:], escape_seq | {escape_chr + e for e in t.initials})
            else:
                ltoken = LToken(FreeMonoid(t.alphabet), l.start+1, l.end, l.lexeme[1:])
                return _split_escapes(False, escape_chr, right, [ltoken] + lexemes[1:], escape_seq | {escape_chr + e for e in t.initials})
        else:
            logger.debug(f"Cannot handle token {t!r}")
            return False, set(), lexemes
    elif not bind:
        ### TODO: ends with -- doesn't work??
        if l.lexeme == escape_chr:
            return _split_escapes(True, escape_chr, right, lexemes[1:], escape_seq)
        else:
            return _split_escapes(False, escape_chr, right, lexemes[1:], escape_seq)
    else:
        logger.error(f"IncompleteImplementation, missing case for {lexemes[0]!r}")
        raise IncompleteImplementation

#####
#
# Resolve inconsistent strings
# 
#####

def resolve_inconsistent_strings(json_data, lexemes, counters):

    # TODO: Bail early if there are no two strings 
    # if len(lexemes) < 3 or next((c for c in tokens if isinstance(c, Comment)), None) == None:
    # TODO: Instead: split lexems to find next comment, start from there

    if len(lexemes) < 3:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    # s_minor is presumed to be the "wrong" string (i.e., the one that has fewer occurrences)
    s_minor = fst.token

    # No comment found, try next position
    if not isinstance(s_minor, String):
        return [lexemes[0]] + resolve_inconsistent_strings(json_data, lexemes[1:], counters) 

    # s_major is presumed to be the "right" string (i.e., the one that has more occurrences)
    s_major = next((s for s in counters.keys()
                    if (isinstance(s, String) and s.left == s_minor.left and s.escape_chr == s_minor.right and s.alphabet == s_minor.alphabet) and counters[s] > counters[s_minor]), None)

    if s_major != None:

        logger.debug(f"Trying to rewrite string {fst!r} into {s_major!r}")

        right = next((i for i in range(2, len(lexemes)) if __check_quote(s_major, s_minor, lexemes, i)), None)
        if right != None:
            logger.debug(f"First escaped ltoken is {snd}")
            logger.debug(f"Found right quote {lexemes[right]!r}")
            logger.debug(f"New string is {''.join(t.lexeme for t in lexemes[0:right+1])}")
            logger.debug(f"LTokens are {lexemes[0:right+1]}")
            logger.debug(f"Length of ltokens is {right+1}")
            success, escape_seq, tail = _split_escapes(True, s_major.escape_chr, s_major.right, lexemes[1:right+1])
            if success:
                logger.debug(f"Found escape sequences {escape_seq!a}")
                newstr = String(s_major.alphabet, s_major.left, s_major.right, s_major.escape_chr, s_major.escape_seq | escape_seq)
                ltoken = LToken(newstr, fst.start, lexemes[right].end, ''.join(t.lexeme for t in lexemes[0:right+1]))
                logger.debug(f"Merged {lexemes[0:right+1]!r} into string {ltoken!r}")
                logger.log("DETAIL", f"Merged {lexemes[0:right+1]!r} into string {newstr!r}")
                # return [ltoken] + resolve_inconsistent_strings(json_data, lexemes[right+1:], counters) 
                return [ltoken] + resolve_inconsistent_strings(json_data, tail + lexemes[right+1:], counters) 
            else:
                logger.debug(f"Failed to rewrite (cannot find escape sequence)")
        else:
            logger.debug(f"Failed to rewrite (cannot find closing quote)")

    # No string found, try next position
    return [lexemes[0]] + resolve_inconsistent_strings(json_data, lexemes[1:], counters) 

def __check_quote(s_major, s_minor, lexemes, i):
    # logger.debug(f"checking position {i}")
    if lexemes[i].lexeme != s_major.right:
        return False
    if lexemes[i-1].lexeme == s_major.escape_chr:
        # logger.debug(f"lexemes[i-2] is {lexemes[i-2]}")
        # logger.debug(f"echcking escpae, returning {lexemes[i-2].lexeme == s_major.escape_chr or lexemes[i-2].token == s_minor}")
        return lexemes[i-2].lexeme == s_major.escape_chr or lexemes[i-2].token == s_minor
    if lexemes[i-1].token == s_minor:
        # logger.debug("found s_minor, returning false")
        return False
    # logger.debug("fallthrough, returning true")
    return True


#####
#
# Merge strings with smaller escape sets into those with larger sets; keep strings with empty escape sequences 
#
#####

def string_merge_escape_sequences(json_data, lexemes, counters):
    for (i, l) in enumerate(lexemes):
        if isinstance(l.token, String) and l.token.escape_seq != set():
             s = next((s for (s, _) in counters.most_common() if isinstance(s, String) and l.token.left == s.left and l.token.right == s.right and l.token.escape_seq < s.escape_seq), None)
             if s != None:
                logger.log("DETAIL", f"Extending escape sequences of string {l.token!r} to {s!r}")
                lexemes[i] = LToken(s , l.start, l.end, l.lexeme)

    return lexemes

#####
#
# Mostly unnecessary / old stuff from here
#
#####


#
# Identify escape sequences in strings and merge them into the character set
#
def string_escape(json_data, lexemes, info=None):

    ### TODO: only works for quotes recognized as keywords; need to extend to alternative quotes
    ### TODO: only works for single-character escape character

    # return lexemes

    if len(lexemes) < 5:
        return lexemes

    fst, snd, trd, frt = lexemes[0], lexemes[1], lexemes[2], lexemes[3]

    ### TODO: refactor code
    if isinstance(fst.token, Keyword) and isinstance(snd.token, FreeMonoid):
        # Escape sequence following monoid
        _, _, esc_chr = check_escape(snd.token.alphabet, fst.token.lexeme, None)
        logger.debug(f"Checking for escape character {Monoid.implode(esc_chr)} in {trd!r}")
        if esc_chr == {trd.lexeme}:
            if isinstance(frt.token, Monoid):
                subst = Monoid.explode(json_data[trd.end-1]["Insertion"]["Right"])
                # Monoid has gobbled up the escapee char
                esc_mono, nxt_mono = frt.split_monoid(subst)
                logger.debug(f"Trying to split off escaped sequence: {esc_mono!r}, {nxt_mono!r}")
                if esc_mono != None:
                    logger.debug(f"Splitting escaped sequence {esc_mono.lexeme!a} off monoid {frt!r}, leaving {nxt_mono!r}")
                    subst = Monoid.explode(json_data[esc_mono.start]["Substitution"])
                    if len(esc_mono.lexeme) == 1:
                        # Single-character escape, just add all possibilities
                        logger.debug(f"Escapes: {subst}")
                        escape = {trd.lexeme + c for c in subst}
                    else:
                        escape = {trd.lexeme + esc_mono.lexeme}
                    new_mono = FreeMonoid(snd.token.alphabet | escape)
                    new_lex  = snd.lexeme + trd.lexeme + esc_mono.lexeme
                    ltoken = LToken(new_mono, snd.start, esc_mono.end, new_lex)
                    logger.debug(f"Adding escape sequences {escape} to {snd.token!r}, new monoid is {ltoken!r}")
                    logger.log("DETAIL", f"Adding escape sequences {escape} to {snd.token!r}")
                    # Try again from the same opening quote, there may be more escapes
                    if nxt_mono == None:
                        assert false
                    else:
                        return string_escape(json_data, [fst, ltoken, nxt_mono] + lexemes[4:], info)
            elif (esc_end := next((i+3 for (i, l) in enumerate(lexemes[3:]) if not possible_escapee(l.token)), None)) and esc_end != None:
                ### TODO: May no longer be necessary
                if esc_end > ESC_LENGTH + 3:
                    logger.warning(f"Escape sequence {lexemes[2:esc_end]!r} too long, skipping")
                    return [lexemes[0]] + string_escape(json_data, lexemes[1:], info)
                logger.debug(f"Found escape sequence {lexemes[2:esc_end]!r}")
                if esc_end == 4:
                    # Single-character escape, just add all possibilities
                    subst = Monoid.explode(json_data[lexemes[esc_end-1].end-1]["Substitution"])
                    # assert esc_set == subst, f"{esc_set} != {subst}"
                    logger.debug(f"Escapes: {subst}")
                    escape = {trd.lexeme + c for c in subst}
                else:
                    escape = {''.join([l.lexeme for l in lexemes[2:esc_end]])}
                new_mono = FreeMonoid(snd.token.alphabet | escape)
                new_lex  = "".join([l.lexeme for l in lexemes[1:esc_end]])
                ltoken = LToken(new_mono, snd.start, lexemes[esc_end-1].end, new_lex)
                logger.debug(f"Adding escape sequences {escape} to {snd.token!r}, new monoid is {ltoken!r}")
                logger.log("DETAIL", f"Adding escape sequences {escape} to {snd.token!r}")
                # Try again from the same opening quote, there may be more escapes
                return string_escape(json_data, [fst, ltoken] + lexemes[esc_end:], info)

    if isinstance(fst.token, Keyword) and possible_escape_char(snd.token) and possible_escapee(trd.token):
        # Escape sequence preceding monoid
        esc_end = next((i for (i, l) in enumerate(lexemes) if isinstance(l.token, FreeMonoid)), None)
        if esc_end != None:
            # Check for singletons and max length
            if not all(l.token.single_character() != None for l in lexemes[1:esc_end]):
                return [lexemes[0]] + string_escape(json_data, lexemes[1:], info)
            _, _, esc_chr = check_escape(lexemes[esc_end].token.alphabet, fst.token.lexeme, None)
            logger.debug(f"Checking for escape character {Monoid.implode(esc_chr)} in {snd!r}")
            if esc_chr == {snd.lexeme}:
                ### TODO: May no longer be necessary
                if esc_end > ESC_LENGTH + 1:
                    logger.warning(f"Escape sequence {lexemes[1:esc_end]!r} too long, skipping")
                    return [lexemes[0]] + string_escape(json_data, lexemes[1:], info)
                logger.debug(f"Found escape sequence {lexemes[1:esc_end]!r}")
                if esc_end == 3:
                    # Single-character escape, just add all possibilities
                    subst = Monoid.explode(json_data[lexemes[esc_end-1].end-1]["Substitution"])
                    logger.debug(f"Escapes: {subst}")
                    escape = {snd.lexeme + c for c in Monoid.explode(json_data[lexemes[esc_end-1].end-1]["Substitution"])}
                else:
                    escape = {''.join([l.lexeme for l in lexemes[1:esc_end]])}
                new_mono = FreeMonoid(lexemes[esc_end].token.alphabet | escape)
                new_lex  = "".join([l.lexeme for l in lexemes[1:esc_end+1]])
                ltoken = LToken(new_mono, snd.start, lexemes[esc_end].end, new_lex)
                logger.debug(f"Adding escape sequences {escape} to {lexemes[esc_end].token!r}, new monoid is {ltoken!r}")
                logger.log("DETAIL", f"Adding escape sequences {escape} to {lexemes[esc_end].token!r}")
                # Try again from the same opening quote, there may be more escapes
                return string_escape(json_data, [fst, ltoken] + lexemes[esc_end+1:], info)

    ### TODO: incomplete, add merging of monoids inside quotes, stemming from multiple escape sequences

    return [fst] + string_escape(json_data, lexemes[1:], info)

#
# Identify escape sequences in strings and merge them into the character set
#
# Note: no recursion, only gobble first character / escape 
def string_gobble_escapes(json_data, lexemes, tokens):

    if len(lexemes) < 3:
        return lexemes

    fst, snd, trd = lexemes[0], lexemes[1], lexemes[2]

    for m in [m for m in tokens if (isinstance(m, GuardedMagma) and m.left == fst.lexeme)]:

        logger.debug(f"Checking magma {m!r}")

        _, _, esc_chr = check_escape(m.alphabet, m.left, m.right)
        if esc_chr == {snd.lexeme}:
            esc_end = next((i+2 for (i, l) in enumerate(lexemes[2:]) if not possible_escapee(l.token)), None)
            escape = ''.join([l.lexeme for l in lexemes[1:esc_end]])
            logger.debug(f"Trying to gobble {lexemes[1:esc_end]!a}")
            if escape in m.alphabet:
                ltoken = LToken(FreeMonoid(m.alphabet), snd.start, lexemes[esc_end-1].end, escape)
                logger.log("DETAIL", f"Identifying leading escape sequence '{escape}' for {m!r}")
                return [fst, ltoken] + lexemes[esc_end:]
        elif possible_escapee(snd.token) and snd.lexeme in m.alphabet and esc_chr == {trd.lexeme}:
            # Generalize first character to FreeMonoid, then let string_escape deal with the escape sequence
            ltoken = LToken(FreeMonoid(m.alphabet), snd.start, snd.end, snd.lexeme)
            logger.log("DETAIL", f"Generalizing single character {snd!a} to monoid {ltoken.token!a}")
            return [fst, ltoken] + lexemes[2:]

    return [fst] + string_gobble_escapes(json_data, lexemes[1:], tokens)

#
# Identify escapes that have been wrapped into a guarded magma and fix
#
def string_unwrap_escapes(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    if isinstance(snd.token, GuardedMagma):
        left_esc  = snd.token.left
        right_esc = snd.token.right
        for m in [m for m in tokens if (isinstance(m, GuardedMagma) and m.left == fst.lexeme)]:
            logger.debug(f"Checking magma {m!r}")
            if left_esc in m.alphabet and right_esc in m.alphabet:
                logger.log("DETAIL", f"Unwrapping escaped sequence'{snd.lexeme}' for {m!r}")
                ltoken = LToken(FreeMonoid(m.alphabet), snd.start, snd.end, snd.lexeme)
                return [fst, ltoken] + string_unwrap_escapes(json_data, lexemes[2:], tokens)
    elif isinstance(snd.token, FreeMonoid) and len(lexemes) > 2 and (trd := lexemes[2]) and isinstance(trd.token, GuardedMagma):
        ### TODO: This is a hack. It needs generalization
        left_esc  = trd.token.left
        right_esc = trd.token.right
        for m in [m for m in tokens if (isinstance(m, GuardedMagma) and m.left == fst.lexeme)]:
            logger.debug(f"Checking magma {m!r}")
            if left_esc in m.alphabet and right_esc == m.right:
                logger.log("DETAIL", f"Unwrapping escaped sequence'{trd.lexeme}' for {m!r}, merging everything")
                ltoken = LToken(GuardedMagma(m.alphabet, m.left, m.right), fst.start, trd.end, fst.lexeme + snd.lexeme + trd.lexeme)
                return [ltoken] + string_unwrap_escapes(json_data, lexemes[3:], tokens)

    return [fst] + string_unwrap_escapes(json_data, lexemes[1:], tokens)


#
# Merge escpaes that have been gobbled up into monoids back into monoids
#
def string_merge_escapes(json_data, lexemes, tokens):

    if len(lexemes) < 3:
        return lexemes

    fst, snd, trd = lexemes[0], lexemes[1], lexemes[2]

    if isinstance(snd.token, FreeMonoid) and isinstance(trd.token, FreeMonoid):
        logger.debug(f"Trying to merge monoid that may represent escape sequence: {snd!r}, {trd!r}")
        # Check whether the second monoid is really an escape sequence that we have seen before
        for g in [g for g in tokens if (isinstance(g, GuardedMagma) and g.left == fst.lexeme)]:
            for m in [m for m in tokens if isinstance(m, FreeMonoid)]:
                logger.debug(f"Trying mono {m!r}, string {g!r}")
                ### TODO old version was: if trd.lexeme in m.alphabet and snd.token.alphabet <= m.alphabet:
                if len(trd.lexeme) > 1 and trd.lexeme in m.alphabet:
                    ltoken = LToken(FreeMonoid(m.alphabet), snd.start, trd.end, snd.lexeme + trd.lexeme)
                    logger.debug(f"Merging escape sequence {trd!r} into monoid {snd!r} using alphabet {Monoid.implode(m.alphabet)}")
                    logger.log("DETAIL", f"Merging escape sequence {trd.lexeme!a} into monoid {snd.token!r}")
                    return string_merge_escapes(json_data, [fst, ltoken] + lexemes[3:], tokens)
                ### TODO old version was: if snd.lexeme in m.alphabet and trd.token.alphabet <= m.alphabet:
                if len(snd.lexeme) > 1 and snd.lexeme in m.alphabet:
                    ltoken = LToken(FreeMonoid(m.alphabet), snd.start, trd.end, snd.lexeme + trd.lexeme)
                    logger.debug(f"Merging escape sequence {snd!r} into monoid {trd!r} using alphabet {Monoid.implode(m.alphabet)}")
                    logger.log("DETAIL", f"Merging escape sequence {snd.lexeme!a} into monoid {trd.token!r}")
                    return string_merge_escapes(json_data, [fst, ltoken] + lexemes[3:], tokens)

    return [fst] + string_merge_escapes(json_data, lexemes[1:], tokens)


#
# Merge monoids in strings that come from gobbling escapes
#
def string_merge_free_monoids(json_data, lexemes, tokens):

    if len(lexemes) < 4:
        return lexemes

    fst, snd, trd, frt = lexemes[0], lexemes[1], lexemes[2], lexemes[3]

    for m in [m for m in tokens if (isinstance(m, GuardedMagma) and m.left == fst.lexeme)]:
        if isinstance(snd.token, FreeMonoid) and isinstance(trd.token, FreeMonoid):
            # Deal with escapes
            if snd.lexeme in trd.token.alphabet:
                alphabet = trd.token.alphabet
            elif trd.lexeme in snd.token.alphabet:
                alphabet = snd.token.alphabet
            else:
                alphabet = snd.token.alphabet | trd.token.alphabet
            ltoken = LToken(FreeMonoid(alphabet), snd.start, trd.end, snd.lexeme + trd.lexeme)
            logger.debug(f"Merging monoids {snd!r} and {trd!r} within string {m!r}, getting {ltoken!r}")
            logger.log("DETAIL", f"Merging string segments {snd.lexeme} and {trd.lexeme}")
            return string_merge_free_monoids(json_data, [fst, ltoken] + lexemes[3:], tokens)
        elif isinstance(snd.token, FreeMonoid) and isinstance(trd.token, IllegalCharacter) and trd.token.char != m.right and frt.token.single_character() == None:
            # Merge a single illegal character into the neighboring monoid, but only if this isn't followed by another single character
            ltoken = LToken(FreeMonoid(snd.token.alphabet | {trd.token.char}), snd.start, trd.end, snd.lexeme + trd.lexeme)
            logger.debug(f"Merging monoid {snd!r} and illegal character {trd!r} within string {m!r}, getting {ltoken!r}")
            logger.log("DETAIL", f"Merging string segments {snd.lexeme} and {trd.lexeme}")
            return string_merge_free_monoids(json_data, [fst, ltoken] + lexemes[3:], tokens)
        elif isinstance(snd.token, IllegalCharacter) and snd.token.char != m.right and isinstance(trd.token, FreeMonoid):
            ltoken = LToken(FreeMonoid({snd.token.char} | trd.token.alphabet), snd.start, trd.end, snd.lexeme + trd.lexeme)
            logger.debug(f"Merging illegal character {snd!r} and monoid {trd!r} within string {m!r}, getting {ltoken!r}")
            logger.log("DETAIL", f"Merging string segments {snd.lexeme} and {trd.lexeme}")
            return string_merge_free_monoids(json_data, [fst, ltoken] + lexemes[3:], tokens)

    return [fst] + string_merge_free_monoids(json_data, lexemes[1:], tokens)


#
# Identify empty strings
#
def string_gobble_empty_strings(json_data, lexemes, tokens):

    if len(lexemes) < 2:
        return lexemes

    fst, snd = lexemes[0], lexemes[1]

    for m in [m for m in tokens if (isinstance(m, GuardedMagma) and m.left == fst.lexeme and m.right == snd.lexeme)]:
        ltoken = LToken(m, fst.start, snd.end, fst.lexeme + snd.lexeme)
        logger.log("DETAIL", f"Identifying empty magma {m!r}")
        return [ltoken] + string_gobble_empty_strings(json_data, lexemes[2:], tokens)

    return [fst] + string_gobble_empty_strings(json_data, lexemes[1:], tokens)


### Categorize characters
def possible_escape_char(t):
    return t.single_character() != None and (isinstance(t, IllegalCharacter) or isinstance(t, Keyword))
def possible_escapee(t):
    return t.single_character() != None and (isinstance(t, IllegalCharacter) or isinstance(t, OperatorSymbol))

### Check alphabet for potential escape character and non-printables that must be escaped (given left/right guards)
def check_escape(alphabet, left, right):
    missing = Monoid.explode(CHAR_SET) - alphabet
    ### TODO: this seems to be wrong, returns empty set
    esc_set = {c for c in missing if not c.isprintable()}
    esc_chr = missing - esc_set - (Monoid.explode(left) | Monoid.explode(right))
    return missing, esc_set, esc_chr

#############################################################################
#
# Auxiliary 
#
#############################################################################

### TODO: split first character from lexeme

