#!/usr/bin/env python

import sys
import zipfile
import xml.etree.ElementTree as ET
import subprocess
import os
import shutil
import glob
import argparse
import re

# =======
# PREPARE
# =======
# Constants
tmp_dir = './tmp'
default_separator = '\t'

# Variables
csv_file = ""
tpzx_files = []
question_count = {}
names = {}
clicker_results = {}

# =========
# ARGUMENTS
# =========
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="subcommand")

parser_a = subparsers.add_parser("interactive", help="run in interactive mode")
parser_b = subparsers.add_parser("standard", help="run in standard mode")

for subparser in [parser_a, parser_b]:
    subparser.add_argument("-f", "--format", help="print output with specified format", choices=["csv", "csv-all", "prettyprint"], default="prettyprint")
    subparser.add_argument("-s", "--separator", help="use specified separator for csv output. defaults to '\\t' since that's what excel uses", type=str, default=default_separator)
parser_b.add_argument("-r", "--roster", help=".csv file containing a class roster. defaults to 'roster.csv'", default="roster.csv")
parser_b.add_argument("clickerfiles", help="files containing clicker data separated by spaces", nargs='+', default="all")

args = parser.parse_args()

# Helpers
def extract_to_tmpdir(file, tmp_dir):
    """
    Extract a specified zip-format file to
    a specified directory. Uses `zipfile`
    since it's stdlib and os-agnostic.
    """
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
        
def hexstr_to_int(string):
    return int(string, 16)

def display_results(names, clicker_results, valign=False):
    max_length = max(map(len, names.values()))
    for device_id in names.keys():
        name = names[device_id] if (device_id in names.keys() or f"0{device_id}" in names.keys()) else device_id
        number_answered = clicker_results[device_id] if device_id in clicker_results.keys() else 0
        if valign:
            print(f'{name + args.separator:<{max_length + 2}}{number_answered}')
        else:
            print(f'{name}{args.separator}{number_answered}')
    return max_length

def usage():
    parser.print_help()
    exit()

def find_all_clickerfiles(cwd):
    return ["./" + os.path.basename(filename) for filename in glob.glob(glob.escape(cwd) + "/*.tpzx")]

# make sure we have valid input
if len(sys.argv) == 1:
    usage()

# prepare filenames, question_count, name -> clicker id dict and id -> question results dict
if args.subcommand == 'interactive':
    # Get roster
    csv_files = glob.glob(glob.escape(os.getcwd()) + "/*.csv")
    csv_files = ["./" + os.path.basename(filename) for filename in csv_files]
    if len(csv_files) == 0:
        print("No .csv files found. Please specify file to pull roster from:")
        usage()
    elif len(csv_files) == 1:
        csv_file = csv_files[0]
    else:
        print("Please select file to pull roster from.")
        for i in range(len(csv_files)):
            print(f"{i + 1}. {csv_files[i]}")
        number = int(input("Please enter a number> ")) - 1
        csv_file = csv_files[number]
    print(f"Found roster: {csv_file}\n")
    
    # Get list of tpzx files
    tpzx = find_all_clickerfiles(os.getcwd())
    if len(tpzx) == 0:
        print("No .tpzx files found. Please specify file to pull clicker data from:")
        usage()
    else:
        print("Please select file(s) to pull clicker data from.")
        for i in range(len(tpzx)):
            print(f" {i + 1}. {tpzx[i]}")
        number = input("Enter a number, a range separated by '-', or 'all' for all\n> ")
        if number.rstrip().lower() == 'all':
            tpzx_files = tpzx
        elif '-' in number:
            numbers = number.rstrip().split('-')
            print(f"Got range: {numbers[0]} to {numbers[1]}")
            tpzx_files = tpzx[(int(numbers[0])-1):(int(numbers[1]))]
        else:
            tpzx_files.append(tpzx[int(number) - 1])
        print(f"Found clicker data: {', '.join(tpzx_files)}\n")
else:
    csv_file = args.roster
    tpzx_files = args.clickerfiles
    if tpzx_files[0] == "all":
        tpzx_files = find_all_clickerfiles(os.getcwd())
    else:
        print(tpzx_files)

# =======
# PROCESS
# =======
# read in names and clicker ids from file
with open(csv_file, "r") as file:
    for line in file.readlines()[1:]:
        line = line.rstrip()
        if line == '':
            continue
        sline = re.split(r'[,;\t]', line)
        id_number, name = hexstr_to_int(sline[0]), f"{sline[1]}{args.separator}{sline[2]}".rstrip()
        names[id_number] = name

# Process clicker data
for tpzx_file in tpzx_files:
    results = {}
    tdir = tmp_dir + f"/{tpzx_file[0:-6]}"
    extract_to_tmpdir(tpzx_file, tdir)

    # This could be much cleaner
    tree = ET.parse(f"{tdir}/TTSession.xml")
    root = tree.getroot()
    questions = root.findall("./questionlist/questions/multichoice")
    question_count[tpzx_file] = len(questions)
    for question in questions:
        for response in question.findall("./responses/response"):
            device_id = hexstr_to_int(response.find("./deviceid").text)
            if device_id in results.keys():
                results[device_id] += 1
            else:
                results[device_id] = 1
    clicker_results[tpzx_file] = results

# ======
# OUTPUT
# ======
# fix this to be actually nice lol
for tpzx_file in tpzx_files:
    if args.format == 'csv':
        print(tpzx_file)
        print(f"total{args.separator}{question_count[tpzx_file]}")
        display_results(names, clicker_results[tpzx_file])
    elif args.format == 'prettyprint':
        print(tpzx_file)
        display_results(names, clicker_results[tpzx_file], valign=True)
        max_length = max(map(len, names.values()))
        print(f"/ {question_count[tpzx_file]}".rjust(max_length + len(str(question_count[tpzx_file])) + 2))
    elif args.format == 'csv-all':
        break # since this only prints once, not for every file
    print()
if args.format == 'csv-all':
    print(f"last{args.separator}first{args.separator}" + args.separator.join([file[2:-5] for file in tpzx_files]))
    for device_id in names.keys():
        name = names[device_id] if (device_id in names.keys() or f"0{device_id}" in names.keys()) else device_id
        numbers = []
        for file in tpzx_files:
            numbers.append(clicker_results[file][device_id] if device_id in clicker_results[file].keys() else 0)
        print(f"{name}{args.separator}" + args.separator.join([str(num) for num in numbers]))
    print(f"total{args.separator}{args.separator}" + args.separator.join([str(question_count[file]) for file in tpzx_files]))

# =======
# CLEANUP
# =======
shutil.rmtree(tmp_dir)