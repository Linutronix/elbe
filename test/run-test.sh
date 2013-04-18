#!/bin/bash

SCRATCH_DIR=/media/x1/torbenh/elbetest02

mkdir -p $SCRATCH_DIR

for ex in examples/*.xml; do
	screen test/run-one-arch.sh $SCRATCH_DIR/`basename $ex .xml` $ex;
done


