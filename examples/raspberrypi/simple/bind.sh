#!/bin/bash
docker volume create yocto-factory-data
docker run \
  --name yocto-factory \
  --interactive --tty --rm \
  --volume yocto-factory-data:/yocto \
  --volume $PWD:/yocto/cockpit \
  fotahub/yocto-factory:2021.1.0 \
  $@