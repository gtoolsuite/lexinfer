# lexinfer 

lexinfer - infers the lexical structure of context-free languages via systematic 
string edit operations. 

## Getting started 

lexinfer requires Python 3 and the `loguru` package:

```bash
python3 -m pip install loguru
```

To compile a generated lexer, also install a Java JDK and download the ANTLR
4.13.1 complete JAR. Java and ANTLR are not needed for inference itself.

> TODO: Document using generated lexers with the Python `antlr4` runtime as
> an alternative to the Java runtime.


New changes have been added since the ASE2026 publication. For the archived
version and its reproduction instructions, see the [Zenodo archive](https://doi.org/10.5281/zenodo.21722193).

## Usage

lexinfer has two stages. First, create training JSON by running a syntax-checking
wrapper for the language under test over a directory of valid source files:

```bash
python3 check_edits.py path/to/sut-wrapper path/to/training-dir \
  --threadnum 12 --outdir path/to/training-json-dir
```

Then infer a lexer from those JSON files. The command writes
`<grammar-name>_Lexer.g4` to the current directory:

```bash
python3 tokenize_json.py path/to/training-json-dir --lex my_language
```

To generate Java sources for an inferred lexer, replace the example ANTLR JAR
path and grammar name below as appropriate:

```bash
java -jar /path/to/antlr-4.13.1-complete.jar -no-listener my_language_Lexer.g4
javac -cp /path/to/antlr-4.13.1-complete.jar:. my_language_Lexer.java
```

The resulting lexer class can be used with the ANTLR Java runtime from an
application-specific driver.

## Quick check with TinyC

The included TinyC data provides a small end-to-end check. The prepared
training JSON is already available, so lexer inference can be run directly:

```bash
python3 tokenize_json.py data/tinyc/suts/tinyc/training --lex inferred_tinyc
```

This creates `inferred_tinyc_Lexer.g4` in the current directory. To regenerate
the training JSON from the six TinyC examples first, use a temporary output
directory so the provided data remains unchanged:

```bash
tinyc_training=$(mktemp -d)
python3 check_edits.py data/tinyc/suts/tinyc/sut/wrapper data/tinyc/training \
  --loglevel DETAIL --threadnum 12 --outdir "$tinyc_training"
python3 tokenize_json.py "$tinyc_training" --lex inferred_tinyc
```

## Bugs 

lexinfer should be considered alpha-quality software. Bugs can be reported on
the [GitHub issue tracker](https://github.com/gtoolsuite/lexinfer/issues).
