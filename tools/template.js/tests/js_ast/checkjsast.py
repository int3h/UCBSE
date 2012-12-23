#!/usr/bin/python

"""
Runs template_parse.py with the --jsast option and compares the outputed ast 
with a the correct ast file in this directory
"""

import argparse
import sys
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("testname", help="the name of the test")
    args = parser.parse_args()

    correct_ast_file = open(args.testname + ".jsast")
    expected_output = correct_ast_file.read()
    correct_ast_str = " ".join(expected_output.strip().split())
    correct_ast_file.close()
    
    proc = subprocess.Popen(
            [
                '../../template_parse.py', 
                '--jsast', 
                '../js_files/' + args.testname + '.js'
            ], 
            stdout=subprocess.PIPE)
    got_output = proc.stdout.read()
    subject_ast_str = " ".join(got_output.strip().split())

    if correct_ast_str != subject_ast_str:
        print "---------------------------------------------------------------"
        print "ast was incorrect. Expected: "
        print "---------------------------------------------------------------"
        print expected_output
        print "---------------------------------------------------------------"
        print "Got: "
        print "---------------------------------------------------------------"
        print got_output
        sys.exit(1)


if __name__ == "__main__":
    main()
