#!/bin/bash

# Generates ast files for all template files

for f in ../templates/*.html.te
do
	basename=`basename $f .html.te`
	../template_parse.py --ast $f > $basename.ast
done
