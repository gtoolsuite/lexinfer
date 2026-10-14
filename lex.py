from pathlib import Path 
from collections import defaultdict 

import json
import re
import uuid

### Logging
from loguru import logger
from loginfer import Loginfer

### Cutoffs
from cutoffs import get_cutoff

##Token constructors
from tokens import (
    LToken,
    TokenT,
    Keyphrase,
    Keyword,
    Magma,
    FreeMonoid,
    LeftPointedMonoid,
    OperatorSymbol,
    IllegalCharacter,
    GuardedMagma,
    Monoid,
    Operator,
    SplitMagma,
    FixedLengthSequence
)

from strings import String
## TODO: currently treating comments as guarded magmas and 
## and keeping the code as is 
from comments import Comment

def short_uuid8():
    """
    """
    return str(uuid.uuid4())[:8]  # First 8 characters

#
# Eyploitig the trie data structure in order to handle longest match policy
# enforced by most lexers (e.g., antlr, (j?f)?lex)
#
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_the_word = False 

class Trie:
    """
    """
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        """
        Insert a word into the Trie
        """
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_the_word = True 

    def dfs(self, node=None, prefix=""):
        """
        Perform a depth-first traversal of the Trie, 
        and collect all (?) prefixes
        """
        if node is None:
            # start dfs from the root node
            node = self.root

        if node.is_end_of_the_word:
            print(prefix)

        for char, child in sorted(node.children.items()): # Sort for lexicographic order
            # Recur with updated prefix
            self.dfs(child, prefix + char)

    def longest_prefix_match(self, query):
        """
        Finds the longest prefxi for a given query
        """
        node = self.root
        prefix = ""
        longest_match = ""

        for char in query:
            if char in node.children:
                prefix += char 
                node = node.children[char]
                if node.is_end_of_the_word:
                    if prefix == query:
                        break
                    longest_match = prefix
            else:
                # not needed in our context 
                #longest_match = prefix 
                break

        return longest_match

def convert_to_antlr_characters(charset):
    """
    """
    antlr_chars = []
    alts = []
    for c in charset:
        if isinstance(c, str) and len(c) == 1:
            # check if the character is a known escape sequence
            if c in ('\n', '\t', '\r', '\b', '\f', '\v'):
                if c == '\x0b':
                    # antlr barfs of \v
                    continue
                elif c == '\x0c':
                    antlr_chars.append(r'\f')
                else:
                    antlr_chars.append(repr(c)[1:-1])
            # escape for antlr, so far we know we have to escape ] if we
            # throw the charset in []
            elif c in (']', '\\', '-'):
                antlr_chars.append(f"\\{c}")
            elif c not in ("\x0b", "\x0c"):
                ## antlr complains if \x0b and \x0c are also 
                ## enclosed in []
                antlr_chars.append(c)
        elif isinstance(c, str) and len(c) == 2:
            ## for length 2 chars, we throw them in alternatives 
            alts.append(repr(c))
    return "".join(sorted(antlr_chars)), alts

def generate_antlr_charclass(charset):
    """
    """
    antlr_chars, alternatives = convert_to_antlr_characters(charset)
    regex = f"[{antlr_chars}]" if len(alternatives) == 0 else "(" + " | ".join(alternatives) + ") | " + f"[{antlr_chars}]"

    return regex

def handle_extended_chars(alphabet, extended_chars):
    """
    """
    # exts = [ f"'\\\\{c}'" if "'" in c else repr(c) for c in sorted(extended_chars)]
    exts = []  
    for char in sorted(extended_chars):
        if "\x0b" in char or "\x0c" in char:
            continue
        elif char == "\\'":
            exts.append(f"'\\\\{char}'")
        elif "'" in char:
            exts.append("'" + char.replace("'", "\\'") + "'")
        else:
            exts.append(repr(char))

    return "(" + " | ".join(exts) + ") | " + f"{alphabet}"

def emit_antlr_lexer_grammar(grammar_name, data):
    """
    Generate a lex grammar in antlr formalism. 
    data: a default dict of tokens rules grouped together. 
           we will have leftpointedmonoids before free monoids
           we can also have guarded_magmas before keywords
    """
    first_line = f"lexer grammar {grammar_name}_Lexer;\n"
    #
    # options? TODO
    # imports? TODO
    # channel declarations 
    #
    rules = ""

    for guarded in data['guarded_magmas']:
        rules += "\n" + guarded + ";\n"
    
    for string in data['strings']:
        rules += "\n" + string + ";\n"

    for split_magma in data['split_magmas']:
        rules += "\n" + split_magma + ";\n"

    for keyword in data['keywords']:
        rules += "\n" + keyword + ";\n"

    for lefty in data['leftpointedmonoids']:
        rules += "\n" + lefty + ";\n"

    for freemonoid in data['free_monoids']:
        rules += "\n" + freemonoid + ";\n"

    for illegal in data['illegal']:
        rules += "\n" + illegal + ";\n"

    ## 
    rules += "\nCHAR :  . ;\n" 

    # write to file 
    with open(f"{grammar_name}_Lexer.g4", "w") as fp:
        fp.write(first_line)
        fp.write(rules)

def write_lex_in_json(grammar_name, fuzz):
    """
    """
    with open(f"{grammar_name}Lexer.json", "w") as fp:
        json.dump(fuzz, fp, indent = 4)

def filter_guarded_magmas(guarded_magmas):
    """
    If we have two or more guarded magmas with 
    the same guards and same pattern, but with at 
    least one of them recursive. we generalize 
    to the recursive one and drop non-recursive ones
    """
    filtered = {}
    for left, right, pattern, recursive in guarded_magmas:
        key = (left, right, pattern)

        if key in filtered:
            ## check if we have a recursive one 
            if recursive:
                filtered[key] = (left, right, pattern, recursive)
        else:
            filtered[key] = (left, right, pattern, recursive)

    return sorted(filtered.values(), key=lambda t : (len(t[0]), len(t[1]), len(t[2])))

def filter_subsumed_string_sets(strings):
    """
    The idea here is if we have two or more strings 
    with the same guards, but others are subsumed by the 
    other(s). We only return the most general, i.e.,
    the one(s) that subsume others.
    """
    subsumes = {}
    for i, (left, right, alphabet, escape_chars, extended_chars) in enumerate(strings):
        new_alphabet = alphabet.union(extended_chars)
        # key = (left, right, alphabet)
        key = (left, right)
        for j, (left1, right1, alphabet1, escape_chars1, extended_chars1) in enumerate(strings):
            if i != j:
                new_alphabet1 = alphabet1.union(extended_chars1)
                if key in subsumes:    
                    if new_alphabet.issuperset(new_alphabet1):
                        subsumes[key] = (left, right, alphabet, escape_chars, extended_chars)
                else: 
                    subsumes[key] = (left, right, alphabet, escape_chars, extended_chars)
    return sorted(subsumes.values(), key=lambda t : (len(t[0]), len(t[1]), len(t[2])))

def filter_subsumed_string_sets_1(strings):
    best = defaultdict(list)

    for i, (left, right, alpha, esc, ext) in enumerate(strings):
        key = (left, right)
        alph = alpha.union(ext)
        is_subsumed = False

        # Check against existing best configurations
        new_best = []
        for (a, e, ex) in best[key]:
            full = a.union(ex)
            if full.issuperset(alph):
                is_subsumed = True
                break
            elif alph.issuperset(full):
                continue  # Current one is more general, so skip old one
            else:
                new_best.append((a, e, ex))

        if not is_subsumed:
            new_best.append((alpha, esc, ext))
            best[key] = new_best

    # Flatten results
    result = []
    for (left, right), configs in best.items():
        for alpha, esc, ext in configs:
            result.append((left, right, alpha, esc, ext))

    return sorted(result, key=lambda t: (len(t[0]), len(t[1]), len(t[2])))


def check_cutoff(lexemes, token):
    num_occs = len(lexemes[token])
    cutoff   = get_cutoff(token)
    if num_occs <= cutoff:
        logger.warning(f"Dropping token {token!r}, number of instances ({num_occs}) below specified cutoff of {cutoff}")
        return True
    return False


def produce_lex(lexemes, grammar_name):
    """
    """
    tokens = lexemes.keys()

    words = set() # this is a set for keywords and operator symbols 
    free_monoids = set() # TODO optionality omitted here 
    guarded_magmas = set() # a set of tuples, where each 
                           # tuple is (left, right, alphabet, recursive)
    
    left_pointed_monoids = set() # identifiers fall here. leftpointedmonoids 
                                 # need to come before monoids
    illegals = set() #for illegal character. we just dump 
                     # at the end of the lex file. 
    strings = set() # split guarded magmas into two 
                    # subclasses, strings and comments 
                    # so lets handle each individually
    split_magmas = set()

    fixed_length_seqs = list()
    
    for token in tokens:
        if check_cutoff(lexemes, token):
            continue
        if isinstance(token, Keyword):
            words.add(token.lexeme)
        elif isinstance(token, OperatorSymbol):
            words.add(token.char)
        elif isinstance(token, Operator):
            alts = token.alternatives
            for alt in alts:
                words.add(alt)
        elif isinstance(token, FixedLengthSequence):
            cs = []
            for chars in token.charsets:
                cs.append(sorted(chars))
            fixed_length_seqs.append(cs)
        elif isinstance(token, FreeMonoid):
            free_monoids.add(frozenset(token.alphabet))
        elif isinstance(token, SplitMagma):
            if token.left is None:
                left_guard = ""
            else:
                left_guard = repr(token.left) if not "'" in token.left else  token.left 
            if token.right is None:
                right_guard = ""
            else:
                right_guard = repr(token.right) if not "'" in token.right else token.right 
            alphabet = token.alphabet
            ## these splits are list of sets 
            splits = token.splits 

            split_magmas.add((left_guard, right_guard, frozenset(alphabet), tuple(frozenset(s) for s in splits)))
        elif isinstance(token, String):
            if token.left is None:
                left_guard = ""
            else:
                left_guard = repr(token.left) if not "'" in token.left else  token.left 
            if token.right is None:
                right_guard = ""
            else:
                right_guard = repr(token.right) if not "'" in token.right else token.right 
            alphabet = token.alphabet
            ## we can ignore the escape seqs for 
            ## now. but lets collect them in a tuple
            escape_char = token.escape_chr
            ## The escape sequences are the same as the extended
            ## characters
            escape_seq = token.escape_seq

            strings.add((left_guard, right_guard, frozenset(alphabet), escape_char, frozenset(escape_seq)))
        elif isinstance(token, GuardedMagma):
            ## wrap around repr for cases when one or 
            ## both of the guards are, for example, escape chars like \n
            if token.left is None:
                left_guard = ""
            else:
                left_guard = repr(token.left) if not "'" in token.left else  token.left
            if token.right is None:
                right_guard = ""
            else:
                right_guard = repr(token.right) if not "'" in token.right else token.right
            recursive = token.recursive
            #alphabet = "".join(token.alphabet)
            alphabet = token.alphabet

            guarded_magmas.add((left_guard, right_guard, frozenset(alphabet), recursive))
        elif isinstance(token, LeftPointedMonoid):
            left_pointed_monoids.add((frozenset(token.initials), frozenset(token.alphabet)))
        elif isinstance(token, IllegalCharacter):
            illegals.add(token.char)
        else: # not yet supported tokens 
            pass 
    
    fuzz = {}
    #
    ## the dict is a collection of rules in antlr formalism
    #
    rules = defaultdict(list)
    
    #
    ## initialize the trie data structure 
    #
    trie = Trie()

    for word in words:
        trie.insert(word)

    longest_matches = defaultdict(str)

    for word in sorted(words):
        longest_matches[word] = trie.longest_prefix_match(word)
    
    #
    ## enforce longest match by doing a cheap sorting 
    ## based on a length of a longest prefix. longer pref. 
    ## is preferred. TODO. longest_matches is no longer a defaultdict after the 
    ## following line. gotta love python. 
    #
    longest_matches = sorted(longest_matches.keys(), key=lambda k : len(longest_matches[k]), 
            reverse=True)
    
    for keyword in longest_matches:
        escaped_keyword = "'" + keyword.replace("'", "\\'") + "'"  if "'" in keyword else repr(keyword)
        temp_id = short_uuid8()
        rule = f"Keyword_{temp_id}  : {escaped_keyword}"
        rules['keywords'].append(rule)
        fuzz[f"Keyword_{temp_id}"] = keyword
    
    ##
    ## fixed length sequences here 
    ##
    for sequence in sorted(fixed_length_seqs, key=lambda k : [TokenT.set_repr(s) for s in k]):
        fixed_length_rule = ""
        for charset in sequence:
            fixed_length_rule += generate_antlr_charclass(charset)

        temp_id = short_uuid8()
        rule = f"Keyword_{temp_id}  : {fixed_length_rule}"
        rules['keywords'].append(rule)
    #
    ## expand and process free monoids 
    #
    f_monoids = sorted(free_monoids, key=len)

    for alphabet in f_monoids:
        temp_id = short_uuid8()
        pattern = generate_antlr_charclass(alphabet)
        rule = f"FreeMonoid_{temp_id}  : {pattern}{pattern}*" 
        rules['free_monoids'].append(rule)

        fuzz[f"FreeMonoid_{temp_id}"] = sorted(alphabet)
    
    ##
    ## strings: lets filter out strings which are subsumed by 
    ## others 
    ##
    strings = filter_subsumed_string_sets_1(strings)

    for string in strings:
        left_guard = f"'\\{string[0]}'" if "'" == string[0] else string[0]
        right_guard = f"'\\{string[1]}'" if "'" == string[1] else string[1]
        alphabet = string[2]
        ## TODO: ignore the escapes for now 

        pattern1 = generate_antlr_charclass(alphabet)

        extended_chars = string[4]

        pattern = handle_extended_chars(pattern1, extended_chars) if len(extended_chars) > 0 else pattern1

        temp_id = short_uuid8()
        rule = f"String_{temp_id} : {left_guard} ({pattern})*? {right_guard}"

        fuzz[f"String_{temp_id}"] = { "leftguard" : string[0][1:-1], "alphabet" : sorted(alphabet.union(extended_chars)), "rightguard" : string[1][1:-1] }

        rules["strings"].append(rule)

    ## 
    ## Split magmas 
    ##

    def split_magma_size(split_magma_tuple):
        lg, rg, pa, splits = split_magma_tuple

        return (
            len(lg) + len(rg) + len(pa)
            + sum(len(split) for split in splits)
        )
    
    for split_magma in sorted(split_magmas, key=split_magma_size):
        left_guard = f"'\\{split_magma[0]}'" if "'" == split_magma[0] else split_magma[0]
        right_guard = f"'\\{split_magma[1]}'" if "'" ==  split_magma[1] else split_magma[1]

        alphabet = split_magma[2]
        
        splits = sorted(split_magma[3], key=len)

        pattern = generate_antlr_charclass(alphabet)
        
        split_subrules = []
        for split in splits:
            split_alts = "(" + " | ".join(repr(c) for c in sorted(split)) + ")"
            split_subrules.append(split_alts)

        ## rule is of the form, guard alphabet+ split_rule1 alphabet+ split_rule2 ... guard
        temp_id = short_uuid8()
        rule = f"SplitMagma_{temp_id} :  {left_guard}"
        for subrule in split_subrules:
            rule += f"{pattern}+{subrule}"
        ## lets finish it 
        rule += f"{pattern}+{right_guard}"

        rules['split_magmas'].append(rule)
        
    #
    ## guarded monoids here. care should be taken if they are 
    ## recursive or not. now we treat we treat each case 
    ## of guarded monoid individually
    ## First filter those non-recursive one with similar recursive ones
    #
    guarded_magmas = filter_guarded_magmas(guarded_magmas)

    for guard_ma in guarded_magmas:
        left_guard = f"'\\{guard_ma[0]}'" if "'" == guard_ma[0] else guard_ma[0]
        right_guard = f"'\\{guard_ma[1]}'" if guard_ma[1] == "'" else guard_ma[1]
        alphabet = guard_ma[2]
        recursive = guard_ma[3]

        rule = ""
        if recursive:
            # should be of size 1
            pattern = generate_antlr_charclass(alphabet)
            # make it recursive. in antlr this 
            # will represented like, rule : left (rule | pattern)*? right
            temp_id = short_uuid8()
            
            if len(left_guard) == 0 or len(right_guard) == 0:
                rule = f"GuardedMagma_{temp_id}  : {left_guard} (GuardedMagma_{temp_id} | {pattern}+) {right_guard}"
            else:
                rule = f"GuardedMagma_{temp_id}  : {left_guard} (GuardedMagma_{temp_id} | {pattern})*? {right_guard}" 
            
            fuzz[f"GuardedMagma_{temp_id}"] = {"leftguard" : guard_ma[0][1:-1], "rightguard" : guard_ma[1][1:-1], "alphabet" : sorted(alphabet), "recursive" : True}
        else:
            # should be of size 1
            pattern = generate_antlr_charclass(alphabet)
            temp_id = short_uuid8()
            if len(left_guard) == 0 or len(right_guard) == 0:
                rule = f"GuardedMagma_{temp_id}  : {left_guard} {pattern}+ {right_guard}"
            else: 
                rule = f"GuardedMagma_{temp_id}  : {left_guard} ({pattern})*? {right_guard}"
            
            fuzz[f"GuardedMagma_{temp_id}"] = {"leftguard" : guard_ma[0][1:-1], "rightguard" : guard_ma[1][1:-1], "alphabet" : sorted(alphabet), "recursive" : False}

        rules['guarded_magmas'].append(rule)
    #
    ## left pointed monoids here 
    #
    # lefty_monoids = MagmaMatcher(left_pointed_monoids)
    # for pattern in lefty_monoids.magma_patterns:
    def pointed_monoids_size(lpm):
        init, alpha = lpm

        return (
            len(init) + len(alpha)
        )

    for initials, pattern in sorted(left_pointed_monoids, key=pointed_monoids_size):
        # initials_matcher = MagmaMatcher([initials])
        # pattern_matcher = MagmaMatcher([pattern])

        # initials_pattern = initials_matcher.magma_patterns[0]
        # follow_pattern = pattern_matcher.magma_patterns[0]
        initials_pattern = generate_antlr_charclass(initials)
        follow_pattern = generate_antlr_charclass(pattern)
        
        temp_id = short_uuid8()
        rule = f"LeftPointedMonoid_{temp_id}  : {initials_pattern}{follow_pattern}*"
        rules['leftpointedmonoids'].append(rule)

        fuzz[f"LeftPointedMonoid_{temp_id}"] = {"initials": sorted(initials), "alphabet": sorted(pattern)}

    #
    ## illegal characters
    #
    for character in sorted(illegals):
        escaped_char = "'" + character.replace("'", "\\'") + "'" if "'" in character else repr(character)
        temp_id = short_uuid8()
        rule = f"Illegal_{temp_id} : {escaped_char}"
        rules['illegal'].append(rule)

        fuzz[f"Illegal_{temp_id}"] = character 
    
    emit_antlr_lexer_grammar(grammar_name, rules)

