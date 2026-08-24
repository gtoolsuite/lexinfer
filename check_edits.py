
### TODO: Factor out collapse?

### TODO: probably need common main

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import glob
import json
from loguru import logger
from loginfer import Loginfer
import os
import shutil
import string
import subprocess
import sys
import time
import threading

# Global "constants", may be overwritten by command line options
from config import CHAR_SET, TMP_DIR, OUT_DIR, NUM_THREADS

#
# Auxiliary 
#

# Collapse a list of charcters into a sorted string
def collapse(chars):
    if chars == []:
        return "None"
    else:
        return ''.join(sorted(chars))


#
# Create tmp file and run SUT to check for validity
#
def run_sut(sut, text, tmp_dir, fname, op, position):

    # construct tmp file name and write text
    root, extension = os.path.splitext(fname)
    tmp_file_name = root + "_" + str(position) + "_" + op + extension
    tmp_file_path = tmp_dir + "/" + tmp_file_name

    logger.trace(f"Creating tmp file {tmp_file_name}")

    with open(tmp_file_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Call SUT
    sut_call  = sut + " " + tmp_file_path
    logger.trace(f"SUT call {sut_call}")

    # shell=True is apparently a safety risk but who cares...
    # process = subprocess.run(sut_call, text=True, encoding="utf-8", capture_output=True, shell=True)
    process = subprocess.run(sut_call, capture_output=True, shell=True)

    logger.debug(f"SUT call {sut_call} gives returncode {process.returncode}")

    return (process.returncode < 3)


#
# Check all string edits at given position for validity
#
def check_edits(sut, tmp_dir, fname, orig_text, position, clean_up):

    logger.log("DETAIL", f"Start processing {fname}, position {position}")
    pos_dir = tmp_dir + "/" + str(position)
    os.makedirs(pos_dir, exist_ok=True)

    # Left (backward) deletions
    text = orig_text
    left_deletions = 0
    while(position-left_deletions >= 0):
        text = orig_text[:position-left_deletions] + orig_text[position+1:]
        if not run_sut(sut, text, pos_dir, fname, "ldel_"+str(left_deletions+1), position):
            break
        left_deletions = left_deletions + 1

    # Right (forward) deletions
    if left_deletions == 0:
        right_deletions = 0
    else:
        length = len(orig_text)
        text   = orig_text[:position] + orig_text[position+1:]
        right_deletions = 1
        while(position+right_deletions < length):
            text = text[:position] + text[position+1:]  # delete one more character
            if not run_sut(sut, text, pos_dir, fname, "rdel_"+str(right_deletions+1), position):
                break
            right_deletions = right_deletions + 1

    # Left (backward) insertions; only do for position 0, right insertions are propagated back for other positions
    left_inserts = []
    if position == 0:
        for char in CHAR_SET:
            text = char + orig_text
            if run_sut(sut, text, pos_dir, fname, "lins_"+str(ord(char)), position):
                left_inserts.append(char)

    # Right (forward) insertions
    right_inserts = []
    for char in CHAR_SET:
        text = orig_text[:position+1] + char + orig_text[position+1:]
        if run_sut(sut, text, pos_dir, fname, "rins_"+str(ord(char)), position):
            right_inserts.append(char)

    # Substitutions
    substitutions = []
    for char in CHAR_SET:
        text = orig_text[:position] + char + orig_text[position+1:]
        if run_sut(sut, text, pos_dir, fname, "subst_"+str(ord(char)), position):
            substitutions.append(char)

    # Construct the JSON entry
    result = {
        "Position" : position,
        "Value"    : orig_text[position],
        "Deletion" : {
            "Left" : left_deletions,
            "Right": right_deletions
        },
        "Insertion": {
            "Left" : collapse(left_inserts),
            "Right": collapse(right_inserts)
        },
        "Substitution" : collapse(substitutions)
    }

    logger.debug(f"Done processing {fname}, position {position}")

    if clean_up: 
        logger.debug(f"Removing tmp files {pos_dir}")
        threading.Thread(target = lambda : shutil.rmtree(pos_dir, ignore_errors=True)).start()

    return result


#
# Construct the JSON file for a given input file fname at relative fpath; write to OUT_DIR/fpath/fname.json
#
def construct_JSON(sut, fpath, clean_up):

    logger.info(f"Processing example file {fpath}")

    #
    # Check that example file is actually correct; copy to TMP_DIR so that
    # nothing is written to the original directory
    #
    cpath = TMP_DIR + "/" + os.path.basename(fpath)
    try:
        shutil.copyfile(fpath, cpath)
    except:
        # Pathological cases, just work with original fpath
        cpath = fpath
    subprocesscall = sut + " " + cpath
    logger.debug(f"Calling subprocess: subprocess.run({subprocesscall}, text=True, capture_output=True, shell=True)")
    process = subprocess.run(subprocesscall, text=True, capture_output=True, shell=True)
    if (process.returncode > 2):
        logger.warning(f"Training example {fpath} not syntactically correct (returncode {process.returncode}), ignoring")
        return # what?

    # Create tmp subdirectory for input_file
    # TODO: make sure that path doesn't go up
    tmp_dir = f'{TMP_DIR}/{fpath}'
    os.makedirs(tmp_dir, exist_ok=True)

    results = []    # list to hold the results
    tasks   = []    # list to hold the future tasks

    # Read file once to pass contents into tasks
    with open(fpath, 'r', encoding="utf-8") as file:
        orig_text = file.read()

    # Spawn parallel threads over each position to modify and check results
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # Iterate over each position in the original content and submit tasks
        for position in range(len(orig_text)):
            tasks.append(executor.submit(check_edits, sut, tmp_dir, os.path.basename(fpath), orig_text, position, clean_up))
        # Collect the results as they complete
        for future in as_completed(tasks):
            result = future.result()
            results.append(result)  

    results.sort(key=lambda x: x["Position"])

    # Propagate right insertions forward to the left
    for i in range(1, len(results)):
        results[i]["Insertion"]["Left"] = results[i-1]["Insertion"]["Right"]

    # Create output directory
    ### TBD: make sure that path doesn't go up
    dir_name = os.path.dirname(fpath)
    out_dir  = f"{OUT_DIR}/{dir_name}"
    os.makedirs(out_dir, exist_ok=True)

    # Write results to a JSON file
    fname = os.path.basename(fpath)
    with open(f"{out_dir}/{fname}.json", "w") as json_file:
        json.dump(results, json_file, indent=4)

    if clean_up: 
        logger.log("DETAIL", f"Removing tmp files {TMP_DIR}")
        threading.Thread(target = lambda : shutil.rmtree(TMP_DIR, ignore_errors=True)).start()

    logger.success(f"Processing example file {fpath}")


#
# Parse command line arguments
#
def parse_cmdline():

    ### TODO: add help info

    parser = argparse.ArgumentParser()
    Loginfer.set_cmdline_arguments(parser)
    parser.add_argument("--extension",  type=str, required=False, default="*")
    parser.add_argument("--threadnum",  type=int, required=False, default=NUM_THREADS)
    parser.add_argument("--tmpdir",     type=str, required=False)
    parser.add_argument("--clean",      required=False, action="store_true")  # delete tmp files
    parser.add_argument("--outdir",     type=str, required=False)
    parser.add_argument("sut",          type=str)
    parser.add_argument("examples",     type=str, nargs='+')

    ### TODO: output directory

    return vars(parser.parse_args())


#
# Main entry point
#
if __name__ == "__main__":

    # Collect command line arguments
    args = parse_cmdline()
    sut = args["sut"]           # path to system under test, takes filename as input, returns 
                                # - 0 for completely processed correct programs
                                # - 1 for semantically correct programs
                                # - 2 for syntactically correct programs
                                # - 3 for syntactically incorrect programs
    examples = args["examples"] # list of file paths, produce json-file for each matching item

    extension = args["extension"]   # defaults to'*'

    # Overwrite globals
    NUM_THREADS = args["threadnum"]

    # Customized logging
    Loginfer.process_cmdline_arguments(args)

    logger.info(f"Inference started with {NUM_THREADS} threads")

    # Create tmp and output directories, if necessary; overwrite global variables with time-stamped versions
    time_stamp = str(int(time.time()))
    sut_name   = os.path.basename(sut)
    if args["tmpdir"] == None:
        TMP_DIR = os.path.dirname(TMP_DIR) + "/" + time_stamp
    else:
        TMP_DIR = args["tmpdir"]
    if args["outdir"] == None:
        OUT_DIR = os.path.dirname(OUT_DIR) + "/" + sut_name + "/" + time_stamp 
    else:
        OUT_DIR = args["outdir"]
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    for pattern in examples:
        if os.path.isfile(pattern):
            construct_JSON(sut, pattern, args["clean"])
        else:
            # Sort to force determinism
            for example_file in sorted(glob.glob(f'{pattern}/**/*.{extension}', recursive=True)):
                construct_JSON(sut, example_file, args["clean"])
    
    logger.success("Inference done")

