#!/bin/bash

for f in *.html.te
do
	basename=`basename $f .html.te`
	../template_parse.py --ast $f > $basename.ast
done
