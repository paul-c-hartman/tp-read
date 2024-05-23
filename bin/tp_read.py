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
import math
from contextlib import redirect_stdout

# =======
# PREPARE
# =======
# Constants
tmp_dir = './tmp'
std_default_sep = '\t'
interactive_default_sep = ';'
format_choices = ["csv", "csv-all", "prettyprint"]
default_format = format_choices[0]
tab_size = 8

# Variables
csv_file = ""
tpzx_files = []
print_format = ""
separator = ""
output_file = ""
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

parser_b.add_argument("-f", "--format", help="print output with specified format", choices=format_choices, default=default_format)
parser_b.add_argument("-s", "--separator", help=f"use specified separator for csv output. defaults to '\\t' since that's what Excel uses", type=str, default=std_default_sep)
parser_b.add_argument("-r", "--roster", help=".csv file containing a class roster. defaults to 'roster.csv'", default="roster.csv")
parser_b.add_argument("-o", "--output", help="name of output file", default = "")
parser_b.add_argument("clickerfiles", help="files containing clicker data separated by spaces. can use glob or 'all' (equivalent to '*.tpzx')", nargs='+', default="all")

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

def pad_with_tabs(string, max_length):
  return string + "\t" * (int((max_length - len(string)) / tab_size) + 1)

def display_results(names, clicker_results, valign=False):
  max_length = max([len(f"{i[0]}{separator}{i[1]}") for i in names.values()])
  lname_max = max([len(i[0])+1 for i in names.values()])
  fname_max = max([len(i[1])+2 for i in names.values()])
  for device_id in names.keys():
    name = names[device_id] if (device_id in names.keys() or f"0{device_id}" in names.keys()) else device_id
    lname = name[0]
    fname = name[1]
    name = f"{lname}{separator}{fname}"
    number_answered = clicker_results[device_id] if device_id in clicker_results.keys() else 0
    if valign:
      if separator == "\t":
        max_length = math.ceil(max_length / 8.0) * 8
        
        print(f'{pad_with_tabs(lname, lname_max)}{pad_with_tabs(fname, fname_max)}{number_answered}')
      else:
        print(f'{name + separator:<{max_length + 2}}{number_answered}')
    else:
      print(f'{name}{separator}{number_answered}')
  return max_length

def usage():
  parser.print_help()
  exit()

def int_to_hexstr(num):
  return hex(num)[2:].rjust(5, "0").upper()

def find_all_clickerfiles(cwd, glob_string="*.tpzx"):
  return ["./" + os.path.basename(filename) for filename in glob.glob(glob.escape(cwd) + "/" + glob_string)]

def flatten(list):
  return [item for row in list for item in row]

# make sure we have valid input
if len(sys.argv) == 1:
  usage()

# prepare filenames, question_count, name -> clicker id dict and id -> question results dict
if args.subcommand == 'interactive':
  # Set defaults
  print_format = default_format
  separator = interactive_default_sep

  # Get roster
  csv_files = glob.glob(glob.escape(os.getcwd()) + "/**/*.csv") + glob.glob(glob.escape(os.getcwd()) + "/*.csv")
  csv_files = [".\\" + os.path.relpath(filename, os.getcwd()) for filename in csv_files]
  if len(csv_files) == 0:
    print("No .csv files found. Please specify file to pull roster from with --roster")
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

  # Get format
  print("Please select a format.")
  number = 1
  for choice in format_choices:
    print(f"{number}. {choice}")
    number += 1
  number = int(input("Enter a number:\n> "))
  print_format = format_choices[number - 1]
  if print_format == 'csv-all':
    separator = "\t"
  
  # Get output file
  output_file = input("Enter a filename, or <enter> to print\n> ").rstrip()
else:
  csv_file = args.roster
  print_format = args.format
  separator = args.separator
  output_file = args.output
  if args.clickerfiles[0] == "all":
    tpzx_files = find_all_clickerfiles(os.getcwd())
  else:
    # Allow for globs
    tpzx_files = flatten([find_all_clickerfiles(os.getcwd(), str) for str in args.clickerfiles])

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
    id_number, name = hexstr_to_int(sline[0]), (sline[1], sline[2].rstrip())
    names[id_number] = name

# Process clicker data
for tpzx_file in tpzx_files:
  results = {}
  tdir = tmp_dir + f"/{tpzx_file[2:-5]}"
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
      # Fill in entries not in roster
      if device_id not in names.keys():
        names[device_id] = (int_to_hexstr(device_id), "")
  clicker_results[tpzx_file] = results

# ======
# OUTPUT
# ======
# fix this to be actually nice lol
def do_output():
  for tpzx_file in tpzx_files:
    if print_format == 'csv':
      print(tpzx_file[2:-5])
      print(f"total{separator}{question_count[tpzx_file]}")
      display_results(names, clicker_results[tpzx_file])
    elif print_format == 'prettyprint':
      print(tpzx_file[2:-5])
      max_length = display_results(names, clicker_results[tpzx_file], valign=True)
      if separator == '\t':
        print(pad_with_tabs("", max_length - (10 + len(str(question_count[tpzx_file])))) + (' ' * (tab_size - 2)) + f"/ {question_count[tpzx_file]}")
      else:
        print(f"/ {question_count[tpzx_file]}".rjust(max_length + len(str(question_count[tpzx_file])) + 2))
    elif print_format == 'csv-all':
      break # since this only prints once, not for every file
    print()
  if print_format == 'csv-all':
    print(f"last{separator}first{separator}" + separator.join([file[2:-5] for file in tpzx_files]))
    for device_id in names.keys():
      name = names[device_id] if (device_id in names.keys() or f"0{device_id}" in names.keys()) else device_id
      name = f"{name[0]}{separator}{name[1]}"
      numbers = []
      for file in tpzx_files:
        numbers.append(clicker_results[file][device_id] if device_id in clicker_results[file].keys() else 0)
      print(f"{name}{separator}" + separator.join([str(num) for num in numbers]))
    print(f"total{separator}{separator}" + separator.join([str(question_count[file]) for file in tpzx_files]))

if output_file != "":
  with open(output_file, 'w') as f:
    with redirect_stdout(f):
      do_output()
else:
  do_output()

# =======
# CLEANUP
# =======
shutil.rmtree(tmp_dir)
