#!/bin/bash
typeset -i "iterations=$1"
typeset -i "timeout=$2"
shift
shift

for ((i=1; i<=iterations; i++))
do
    dnf provides "${@}" && break
    sleep "${timeout}"
done

