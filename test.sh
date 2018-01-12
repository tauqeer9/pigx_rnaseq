#!/usr/bin/bash

set -e
set -u

export PIGX_UGLY=1
export PIGX_UNINSTALLED=1

# We do not use "readlink -f" here, because macos does not support it.
export srcdir=$(/home/buyar/.conda/envs/pigx_rnaseq/bin/python -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' ${srcdir:-.})

chmod -R +w ${srcdir}/tests

./pigx-rnaseq -s ${srcdir}/tests/settings.yaml ${srcdir}/tests/sample_sheet.csv

if ! test -f "${srcdir}/tests/output/report/analysis1.salmon.deseq.report.html" 
then
  echo "ERROR: could not find report"
  exit 1
fi


message=$(./pigx-rnaseq -s ${srcdir}/tests/settings.yaml ${srcdir}/tests/sample_sheet.csv 2>&1 >/dev/null | tail -n1)

if test "$message" != "Nothing to be done."
then
   echo "ERROR: pipeline should not process files a second time"
   exit 1
fi