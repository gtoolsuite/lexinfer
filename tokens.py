#############################################################################
#
# Default token classes
#
#############################################################################

### Logging
from loguru import logger
from loginfer import Loginfer

#####
#
# Abstract super class for tokens
#
#####
class TokenT:

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __hash__(self):
        # return hash(repr(self))
        return hash(str(self))

    def __str__(self):
        return repr(self)

    #
    # Predicates 
    #

    ### Return true if lexeme has unbounded length
    def is_unbounded(self):
        return False

    ### Return true if lexeme is arbitrarily right-extensible
    def is_right_extensible(self):
        return False

    #
    # Accessors
    #

    ### Return representation if fixed string, None otherwise
    def fixed_string(self):
        return None

    ### Return representation if single character, None otherwise
    def single_character(self):
        return None

    #
    # Class methods - generally useful but small auxiliary routines
    #
    ### TODO: move Monoid.explode etc to here
    #

    ### Convert alphabet string into set, if necessary
    @classmethod
    def to_set(cls, alphabet):
        if isinstance(alphabet, set):
            return alphabet
        elif isinstance(alphabet, str):
            return Monoid.explode(alphabet)
        else:
            raise TypeError(f"Illegal argument type {type(alphabet)} for {cls.__name__}")

    ### Deterministic (sorted) representation of string set
    @classmethod
    def set_repr(cls, s):
        alt_rep = [repr(a) for a in sorted(list(s))]
        return "{" + (', '.join(alt_rep)) + "}"


#####
#
# Illegal character (i.e., individual character not falling into any other
# class)
#
# TODO: IllegalCharacters should only be constructed by the more complex token
#       construction routines, not by the muncher.
#
#####
class IllegalCharacter(TokenT):

    def __init__(self, char, subst=set()):
        self.char  = char
        self.subst = TokenT.to_set(subst) ### subst empty means ignored

    def __repr__(self):
        return f"IllegalCharacter({self.char!a}, {Monoid.implode(self.subst)})"

    def single_character(self):
        return self.char


#############################################################################
#
# Various styles of keywords (syntactic units with finite lexeme variance)
#
#############################################################################

#####
#
# Abstract superclass representing all fixed string tokens
#
#####
class Keyphrase(TokenT):
    pass


#####
#
# Strict keywords (fixed strings)
#
# Keywords lexemes are fixed strings that must occur as is in their position,
# i.e., no substitutions, deletions, or insertions (inside the lexeme) are
# allowed.
#
# Note that the classification as keyword depends on the syntactic context;
# compare for example
#
#   not(a and b)
#
# with
#
#   not a and b
#
# Tn the former case, "not" is not classified as keyword because a modified
# lexeme (e.g., "no") still allows a legal (albeit different) parse of the
# program (here a function call), while the latter case does not allow this.
#
# Note also that this does not handle classify lexemes as keywords if the
# language has multiple keyphrases with a string edit distance of one that can
# occur at the same position as the lexeme (e.g., "+=", "*=", ...).
#
#####

class Keyword(Keyphrase):

    def __init__(self, lexeme):
        self.lexeme = lexeme

    def __repr__(self):
        return f"Keyword({self.lexeme!a})"

    def lexeme(self):
        return self.lexeme

    def single_character(self):
        if len(self.lexeme) == 1:
            return self.lexeme
        else:
            return None

    def fixed_string(self):
        return self.lexeme


#####
#
# Fixed length sequences 
#
# A multi-character lexeme is classified as a fixed length sequence if the
# character at each position can be substituted by a non-empty set of different
# characters (like a free monoid) but the lexeme cannot be shortened or
# extended by any of the equivalent characters.
#
#####

class FixedLengthSequence(Keyphrase):

    def __init__(self, charsets):
        self.charsets = charsets

    def __str__(self):
        return f"FixedLengthSequence({[TokenT.set_repr(s) for s in self.charsets]})"

    def __repr__(self):
        return f"FixedLengthSequence({self.charsets!a})"


#####
#
# Operator symbols
#
# An operator symbol is a fixed length string of length one.
#
# TODO: Should only ever be length one?
# TODO: rename? OperatorChar? SingleChar?
#
#####

class OperatorSymbol(Keyphrase):

    ### TODO: change field to 'lexeme'
    def __init__(self, char, subst=set()):
        self.char  = char
        self.subst = subst

    def __str__(self):
        return f"OperatorSymbol({self.char!a}, {Monoid.implode(self.subst)})"

    def __repr__(self):
        return f"OperatorSymbol({self.char!a}, {self.subst})"

    def single_character(self):
        if len(self.char) == 1:
            return self.char
        else:
            return None

#####
#
# Operator
#
# An operator is a keyphrase with a fixed set of alternatives
#
#####

class Operator(Keyphrase):

    def __init__(self, alternatives):
        if alternatives == set():
            logger.error("Initializing operator without alternatives")
        if alternatives == "":
            logger.error("Initializing operator with empty alternatives string")
        if isinstance(alternatives, set):
            self.alternatives = alternatives    
        else:
            self.alternatives = {alternatives}    

    def __str__(self):
        return f"Operator({Monoid.implode(self.alternatives)})"

    def __repr__(self):
        return f"Operator({self.alternatives})"

    def single_character(self):
        if all([len(a) == 1 for a in self.alternatives]):
            return lexeme
        #if len(self.alternatives) == 1:
        #    [lexeme] = self.alternatives
        #    if len(lexeme) == 1:
        #        return lexeme
        return None

    def fixed_string(self):
        if len(self.alternatives) == 1:
            [lexeme] = self.alternatives
            return lexeme
        else:
            return None


#############################################################################
#
# Arbitrary-length sequences
#
#############################################################################


#####
#
# A magma is an arbitrary-length sequence of characters drawn from a given
# alphabet; no other assumptions are made.
#
# Magmas shouldn't be identified as tokens, but the class isn't abstract
# because there may be intermediate magma instances.
#
#####

class Magma(TokenT):

    def __init__(self, alphabet):
        self.alphabet = alphabet

    def __repr__(self):
        return f"Magma({self.alphabet!a})"

    ### Magma lexemes have unbounded length
    def is_unbounded(self):
        return True


#####
#
# Abstract class to group both monoid structures
#
# Also provides class methods useful for monoids
#
# TODO: add field declarations? add constructor that raises exception?
#
#####

class Monoid(Magma):

    ### Convert an alphabet set into a lex-like representation, maintains equality
    @classmethod
    def implode(cls, alphabet):
        # sort lexcially, then by length
        if isinstance(alphabet, set):
            return '\'' + ''.join([Monoid.__format(c) for c in sorted(sorted(alphabet), key=len)]) + '\''
        elif alphabet == "None":
            raise ValueError(f"Cannot implode 'None'")
        else:
            return f"{alphabet!a}"      ### temporary fail-safe

    @classmethod
    def __format(cls, char):
        # ASCII-escaped formatting, with quotes removed
        if char == '\'':
            formatted = '\'\\\'\''
        elif len(char) == 1:
            formatted = f"{char!a}"
        else:
            formatted = f"({char!a})"
        return formatted[1:-1]

    ### Explode a string into the set of characters, except for "None"
    ### Get rid of carriage return characters
    @classmethod
    def explode(cls, s):
        return set(s) - {"\r"} if s != None and s != "None" else set()

    ### TODO base representation for lex notation. 
    ### would be nice to have a range notation
    @classmethod
    def lex_notation(cls, alphabet):
        if isinstance(alphabet, set):
            return '[' + ''.join([Monoid.__format(c) for c in sorted(sorted(alphabet), key=len)]) + ']'
        elif alphabet == "None":
            raise ValueError(f"Cannot implode 'None'")
        else:
            return f"{alphabet}"


#####
#
# Free monoids (strings over given alphabet); 
#
#####

class FreeMonoid(Monoid):

    def __init__(self, alphabet):
        ### initials is set to alphabet so that both Monoid-types can be used uniformly.
        self.alphabet = self.to_set(alphabet)
        self.initials = self.alphabet

    def __repr__(self):
        return f"FreeMonoid({Monoid.implode(self.alphabet)})"

    ### FreeMonoid lexemes are arbitrarily right-extensible
    def is_right_extensible(self):
        return True


#####
#
# Left-pointed monoids 
#
# Left-pointed monoids are monoids where the first character is from a subset
# of the alphabet (e.g., identifiers).
#
#####

class LeftPointedMonoid(Monoid):

    def __init__(self, initials, alphabet):
        self.initials = self.to_set(initials)
        self.alphabet = self.to_set(alphabet)
        ### Ensure initials are actually a subset
        if not(set(initials) < set(alphabet)):
            raise ValueError(f"Initials {Monoid.implode(self.initials)} are not a proper subset of alphabet {Monoid.implode(self.alphabet)}")

    def __repr__(self):
        return f"LeftPointedMonoid({Monoid.implode(self.initials)}, {Monoid.implode(self.alphabet)})"

    ### LeftPointedMonoid lexemes are arbitrarily right-extensible
    def is_right_extensible(self):
        return True


#####
#
# Guarded magma 
#
# Guarded magmas are non-empty strings over given alphabet with possible guards
# at the string's left and right ends; either side may be missing (i.e., None).
# The guards may be fixed strings or single characters drawn from a character
# set; single character guards may or may not be members of the alphabet.
#
#####

class GuardedMagma(Magma):

    def __init__(self, alphabet, left, right):
        self.alphabet  = self.to_set(alphabet)
        self.left      = left        # CharClass, fixed string, or None
        self.right     = right       # CharClass, fixed string, or None
        ### TODO: Dangleberry, added to not break existing code, to be removed
        self.recursive = False       

    def __repr__(self):
        return f"GuardedMagma({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a})"


#####
#
# Split magma 
#
# Split magmas are a more complex version of guarded magmas; in addition to the
# guards, they also allow a finite number of internal splits that break the
# monoid structure. Each split is characterized by a finite set of split
# sequences. The characters in the split sequences must be disjoint from the
# alphabet.
#
#####

class SplitMagma(Magma):

    def __init__(self, alphabet, left, right, splits):
        self.alphabet = self.to_set(alphabet)
        self.left     = left        # CharClass, fixed string, or None
        self.right    = right       # CharClass, fixed string, or None
        self.splits   = splits

    def __str__(self):
        return f"SplitMagma({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a}, {[TokenT.set_repr(s) for s in self.splits]})"

    def __repr__(self):
        return f"SplitMagma({Monoid.implode(self.alphabet)}, {self.left!a}, {self.right!a}, {self.splits!a})"

#############################################################################
#
# Fully dressed tokens (token + source-code information)
#
#############################################################################

### TODO: Find a better name
class LToken:

    # TokenT, int, int, str -> Token
    def __init__(self, token, start, end, lexeme):
        self.token  = token
        self.start  = start
        self.end    = end
        self.lexeme = lexeme
        ### DEBUG
        if len(lexeme) != end - start:
            raise ValueError(f"Length of lexeme {lexeme!a} of token {token!r} does not match given source positions ({start}:{end})")

    def __str__(self):
        return f"LToken({self.token!s}, {self.start}, {self.end}, {self.lexeme!a})"

    def __repr__(self):
        return f"LToken({self.token!r}, {self.start}, {self.end}, {self.lexeme!a})"

    # Check wether the lexeme starts with the given character, and split it off;
    # return the patched token rest as list (if found), None otherwise
    def patch_first(self, char):
        if self.lexeme == char:
            return []
        elif isinstance(self.token, FreeMonoid) and char == self.lexeme[0]:
            return [LToken(self.token, self.start + 1, self.end, self.lexeme[1:])]
        elif isinstance(self.token, LeftPointedMonoid) and char == self.lexeme[0]:
            return [LToken(FreeMonoid(self.alphabet), self.start + 1, self.end, self.lexeme[1:])]
        else:
            return None

    # Merge following LToken into monoid LToken if alphabets are identical
    def merge_monoid(self, other):
        if isinstance(self.token, Monoid) and isinstance(other.token, Monoid) and self.token.alphabet == other.token.alphabet:
            return LToken(self.token, self.start, other.end, self.lexeme + other.lexeme)
        else:
            return None


    # Split a monoid LToken into two if the first character is in chars 
    def split_monoid(self, chars):
        start = self.start
        char  = self.lexeme[0]
        if isinstance(self.token, Monoid) and char in chars:
            fst = LToken(IllegalCharacter(char), start, start+1, char)
            if self.lexeme[1:] != []:
                snd = LToken(FreeMonoid(self.token.alphabet), start+1, self.end, self.lexeme[1:])
            else:
                # Return None if nothing is left
                snd = None
        else:
            fst, snd = None, None
        return fst, snd

