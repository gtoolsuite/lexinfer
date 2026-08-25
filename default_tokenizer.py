
import argparse
import glob
import os
from loguru   import logger
from loginfer import Loginfer

### Global character sets
space  = set(' \n\t\r')
digit  = set('1234567890')
letter = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
alnum  = digit | letter

#
# Add and report a token, to be called whenever the boundaries are crossed
#
def found(lexemes, token, lexeme):
    lexemes.append(lexeme)
    logger.log("DETAIL", f"Found token {token!a}, lexeme {lexeme!a}")

#
# Read and tokenize a file
#
def tokenize(file_path):
    logger.info(f"Tokenizing {file_path}")
    with open(file_path, 'r') as f:
        text    = f.read()
        lexemes = []
        lexeme  = ''
        token   = None
        for c in text:
            logger.debug(f"Checking >{c!a}<, current lexeme >{lexeme!a}<, token is {token}")
            if c in space:
                if token == None:
                    lexeme, token = c, 'space'
                elif token == 'space':
                    lexeme = lexeme + c
                else:
                    found(lexemes, token, lexeme)
                    lexeme, token = c, 'space'
            elif c in digit:
                if token == None:
                    lexeme, token = c, 'digit'
                elif token == 'digit' or token == 'alnum':
                    lexeme = lexeme + c
                elif token == 'letter':
                    lexeme = lexeme + c
                    token  = 'alnum'
                else:
                    found(lexemes, token, lexeme)
                    lexeme, token = c, 'digit'
            elif c in letter:
                if token == None:
                    lexeme, token = c, 'letter'
                elif token == 'alnum' or token == 'letter':
                    lexeme = lexeme + c
                else:
                    found(lexemes, token, lexeme)
                    lexeme, token = c, 'letter'
            else:
                found(lexemes, token, lexeme)
                lexeme, token = c, 'op'
    
        return lexemes + [lexeme]


def produce_segmentations(tokens):
    """
    A (rather) simple function to print each token 
    line by line. The idea is to hook this up 
    in the comparison with oracle lexers 
    """
    for token in tokens:
        print(token)
        print() ## we also spit out an explicit new line 
#
# Parse command line arguments
#
def parse_cmdline():

    parser = argparse.ArgumentParser()

    Loginfer.set_cmdline_arguments(parser)
    parser.add_argument("--extension",  type=str, required=False, default="*")
    parser.add_argument("files",        type=str, nargs='+')

    return vars(parser.parse_args())

#
# Main entry point
#
if __name__ == "__main__":

    # Collect command line arguments
    args = parse_cmdline()
    files     = args["files"]      # list of file paths, produce tokenization for each matching item
    extension = args["extension"]  # defaults to '*'
    # Customized logging
    Loginfer.process_cmdline_arguments(args)

    for pattern in files:
        if os.path.isfile(pattern):
            tokens = tokenize(pattern)
            print(tokens)
        else:
            # Sort to force determinism
            for file_path in sorted(glob.glob(f'{pattern}/**/*.{extension}', recursive=True)):
                tokens = tokenize(file_path)
                # print(tokens)
                produce_segmentations(tokens)

    

