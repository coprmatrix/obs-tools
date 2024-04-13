#!/bin/bash
obs_pkg_install
obs_service_run
(
cd .osc/_output_dir
for i in *.spec
do
rpmbuild "-D_sourcedir $PWD" "${@}" --bs "$i"
done
)
