#!/bin/bash
 
create_yocto_project_layout()
{
  # Locate Yocto project
  if [ -z "$YOCTO_PROJECT_ROOT" ]; then
    export YOCTO_PROJECT_ROOT=$PWD/yocto
  fi
  mkdir -p $YOCTO_PROJECT_ROOT

  # Locate Yocto layers area
  if [ -z "$YOCTO_LAYERS_DIR" ]; then
    export YOCTO_LAYERS_DIR=$YOCTO_PROJECT_ROOT/layers
  fi
  mkdir -p $YOCTO_LAYERS_DIR

  # Locate Yocto downloads area
  if [ -z "$YOCTO_DOWNLOADS_DIR" ]; then
    export YOCTO_DOWNLOADS_DIR=$YOCTO_PROJECT_ROOT/downloads
  fi
  mkdir -p $YOCTO_DOWNLOADS_DIR

  # Locate Yocto project cockpit area
  if [ -z "$YOCTO_COCKPIT_DIR" ]; then
    export YOCTO_COCKPIT_DIR=$YOCTO_PROJECT_ROOT/cockpit
  fi

  # Locate Yocto layer git-repo manifest
  if [ -z "$YOCTO_LAYER_MANIFEST" ]; then
    YOCTO_LAYER_MANIFEST=$YOCTO_COCKPIT_DIR/manifest.xml
  fi
  if [ ! -f "$YOCTO_LAYER_MANIFEST" ] || [ ! -s "$YOCTO_LAYER_MANIFEST" ]; then
    echo "ERROR: The Yocto layer git-repo manifest '$YOCTO_LAYER_MANIFEST' does not exist."
    return 1
  fi

  # Locate Yocto build area
  if [ -z "$YOCTO_BUILD_DIR" ]; then
    export YOCTO_BUILD_DIR=$YOCTO_PROJECT_ROOT/build
  fi

  return 0
}

sync_yocto_layers()
{
  local MANIFEST_FILE=$1
  local LAYERS_DIR=$2
  local MANIFEST_REPO_DIR=$LAYERS_DIR/manifest
  local CURRENT_DIR=$PWD

  mkdir -p $MANIFEST_REPO_DIR
  cd $MANIFEST_REPO_DIR
  cp $MANIFEST_FILE .
  if [ ! -d .git ]; then
    git init
    git config --local user.name $(whoami)
    git config --local user.email $(whoami)@localhost
  fi
  if [ -n "$(git status --porcelain)" ]; then
    git add $(basename $MANIFEST_FILE)
    git commit --allow-empty-message -m ''
  fi

  cd $LAYERS_DIR
  echo "N" | repo init -u "file://$MANIFEST_REPO_DIR" -b master -m $(basename $MANIFEST_FILE)
  repo sync --force-sync
  
  cd $CURRENT_DIR
}

detect_machine()
{
  sed -n 's/MACHINE\s*?*=\s*"\(.*\)"/\1/p' < $YOCTO_BUILD_DIR/conf/local.conf
}

locate_build_results()
{
  local MACHINE=$1

  OS_IMAGE_DIR=$YOCTO_BUILD_DIR/tmp/fotahub-os/deploy/images/$MACHINE
  OS_OSTREE_REPO_DIR=$OS_IMAGE_DIR/ostree_repo

  WIC_IMAGE_FILE=$OS_IMAGE_DIR/fotahub-os-package-$MACHINE.wic
}

yield_latest_wic_image()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  if [ -f "$WIC_IMAGE_FILE" ]; then
    mkdir -p $YOCTO_COCKPIT_DIR/build/images
    cp $WIC_IMAGE_FILE $YOCTO_COCKPIT_DIR/build/images
  fi
}

show_latest_os_revision()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  if [ -d "$OS_OSTREE_REPO_DIR" ]; then
    echo "Latest OS revision: $(ostree --repo=$OS_OSTREE_REPO_DIR rev-parse fotahub-os-$MACHINE)"
  fi
}

show_usage()
{
  cat << EOF

Usage: $(basename $0) command [args...]

Commands:
    sync <machine>
        Initialize/synchronize Yocto project for given machine
        (e.g. sync raspberrypi3)

    wic <bitbake args...>
        Build and publish OS image, and create machine-dependent live disk image including it
        (e.g. '.wic' for Raspberry Pi)

    clean
        Clean build results

    show-revision
        Show latest OS revision

    bash
        Start an interactive bash shell in the build container

    help
        Show this text

EOF
}

main()
{
  if [ $# -lt 1 ]; then
    show_usage
    exit 1
  fi
  local COMMAND=$1
  shift

  if ! create_yocto_project_layout; then
    exit 1
  fi

  if [ ! -d "$YOCTO_BUILD_DIR/conf" ] && [ "$COMMAND" != "sync" ] && [ "$COMMAND" != "help" ]; then
    echo "ERROR: The Yocto build directory '$YOCTO_BUILD_DIR' has not yet been initialized. Use the 'sync' command first. Use the 'help' command to get more details."
    exit 1
  fi

  cd $YOCTO_PROJECT_ROOT

  case $COMMAND in
    sync)
      if [ $# -ne 1 ]; then
        echo "ERROR: The '$COMMAND' command requires exactly 1 argument. Use the 'help' command to get more details."
        exit 1
      fi
      local MACHINE=$1

      if ! sync_yocto_layers $YOCTO_LAYER_MANIFEST $YOCTO_LAYERS_DIR; then
        exit 1
      fi

      source $YOCTO_LAYERS_DIR/meta-fotahub/fh-pre-init-build-env $MACHINE
      source $YOCTO_LAYERS_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      source $YOCTO_LAYERS_DIR/meta-fotahub/fh-post-init-build-env $MACHINE
      ;;

    wic)
      source $YOCTO_LAYERS_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      bitbake fotahub-os-package -k $@

      yield_latest_wic_image $MACHINE
      show_latest_os_revision $MACHINE
      ;;

    clean)
      source $YOCTO_LAYERS_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      bitbake fotahub-os-package -c cleanall
      ;;

    show-revision)
      local MACHINE=$(detect_machine)

      show_latest_os_revision $MACHINE
      ;;
  
    bash)
      source $YOCTO_LAYERS_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      export MACHINE=$(detect_machine)

      bash
      ;;

    help)
      show_usage
      ;;

    *)
      echo "ERROR: Command not supported: $COMMAND. Use the 'help' command to get more details."
      exit 1
  esac
}

main $@