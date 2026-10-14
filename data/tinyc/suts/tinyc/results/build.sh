#!/bin/bash

Jar=$(realpath ../../../../lib/antlr-4.13.1-complete.jar)

## build the parsers
java -jar "$Jar" -no-listener $1

## we should have the driver program at 
## this point 
if [ ! -e Driver.java ]; then
    echo "Generate a driver program for this parser!"
    exit 1
fi

## compile the (generated) sources
javac -cp "$Jar":. *.java 
