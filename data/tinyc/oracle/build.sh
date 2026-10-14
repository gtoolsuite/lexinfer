#!/bin/bash

Jar=$(realpath ../../lib/antlr-4.13.1-complete.jar)
## build the parsers
java -jar "$Jar" -no-listener tinyc.g4

## compile the (generated) sources
javac -cp "$Jar":. *.java 
