#!/bin/bash

FILES=`find elbepack | grep -v .pyc$`
MISSING=''

for f in $FILES; do
	MISSING+=`grep -r $f debian/*.install > /dev/null || echo "$f ";`
done

if [ "$MISSING" == "" ]; then
	exit 0
fi

echo add the following files to debian/*.install:
for m in $MISSING; do
	echo $m
done

exit 1
