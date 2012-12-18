#!/bin/bash

ABSPATH=$(cd "$(dirname "$0")"; pwd)

echo $ABSPATH

for f in $ABSPATH/*.ast
do
	basename=`basename $f .ast`
	$ABSPATH/check.py $ABSPATH/$basename
done
