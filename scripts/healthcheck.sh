#!/bin/bash
set -eu

REQUIRED_CIRCUIT_DIRS=${REQUIRED_CIRCUIT_DIRS:-/gpfs/bbp.cscs.ch /sbo/data/project/bbp.cscs.ch}

for DIR in ${REQUIRED_CIRCUIT_DIRS}; do
  if [[ ! -r $DIR ]]; then
    echo "Required directory $DIR isn't readable" >&2
    exit 1
  fi
done
