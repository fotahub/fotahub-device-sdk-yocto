#!/bin/bash
docker volume create fotahub-yocto-factory-data-rpi
docker run \
  --name fotahub-yocto-factory-rpi \
  --interactive --tty --rm \
  --volume fotahub-yocto-factory-data-rpi:/yocto \
  --volume $PWD:/yocto/cockpit \
  fotahub/yocto-factory:2021.1.0 \
  $@