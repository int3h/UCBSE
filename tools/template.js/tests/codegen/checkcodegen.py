#!/usr/bin/python

"""
Runs template_parse.py and compares the outputed code
with the correct code file (*.out.js) in this directory
"""

import argparse
import sys
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("testname", help="the name of the test")
    args = parser.parse_args()

    correct_codegen_file = open(args.testname + ".out.js")
    expected_output = correct_codegen_file.read()
    correct_codegen_str = " ".join(expected_output.strip().split())
    correct_codegen_file.close()
    
    proc = subprocess.Popen(
            [
                '../../template_parse.py', 
                '../templates/' + args.testname + '.html.te'
            ], 
            stdout=subprocess.PIPE)
    got_output = proc.stdout.read()
    subject_codegen_str = " ".join(got_output.strip().split())

    if correct_codegen_str != subject_codegen_str:
        print "---------------------------------------------------------------"
        print "codegen was incorrect. Expected: "
        print "---------------------------------------------------------------"
        print expected_output
        print "---------------------------------------------------------------"
        print "Got: "
        print "---------------------------------------------------------------"
        print got_output
        sys.exit(1)


if __name__ == "__main__":
    main()
