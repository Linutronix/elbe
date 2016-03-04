#!/bin/bash

FILES=`ls -1 ../examples`
DEST=elbe-examples.tmp
TXT=elbe-examples.txt
rm -f $DEST

echo $FILES

echo "ELBE examples" >>$DEST
echo "=============" >> $DEST
echo "" >> $DEST
for F in $FILES; do
	../elbe show ../examples/$F >> $DEST
	echo "" >> $DEST
done

cat $DEST | sed -e s?'../examples/'?''? > $TXT
