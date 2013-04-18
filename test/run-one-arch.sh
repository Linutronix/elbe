#!/bin/bash

DIR=$1
ELBE=/home/torbenh/elbe/elbe/elbe
HTTP_PROXY=http://192.168.0.1:3142

mkdir -p $DIR
rm -rf $DIR/netinst

$ELBE create --directory $DIR/netinst --proxy $HTTP_PROXY $2
cd $DIR/netinst
/usr/bin/time -o $DIR/netinst.time make

rm -rf $DIR/cdrominst
cp $DIR/netinst/source.xml $DIR
$ELBE setcdrom $DIR/source.xml $DIR/netinst/install.iso

$ELBE create --directory $DIR/cdrominst $DIR/source.xml
cd $DIR/cdrominst
/usr/bin/time -o $DIR/cdrominst.time make

sleep 10
