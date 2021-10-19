#!/bin/bash

create_yocto_project_layout()
{
  # Locate Yocto project
  if [ -z "$YOCTO_PROJECT_DIR" ]; then
    export YOCTO_PROJECT_DIR=$PWD
  fi

  # Locate/create Yocto data area
  if [ -z "$YOCTO_DATA_DIR" ]; then
    export YOCTO_DATA_DIR=$PWD/build/yocto
  fi
  if [ ! -d "$YOCTO_DATA_DIR" ]; then
    mkdir -p "$YOCTO_DATA_DIR"
  fi

  # Locate Yocto layer sources area
  if [ -z "$YOCTO_SOURCES_DIR" ]; then
    export YOCTO_SOURCES_DIR="$YOCTO_DATA_DIR/sources"
  fi

  # Locate Yocto layer sources git-repo manifest
  if [ -z "$YOCTO_LAYER_MANIFEST_FILE" ]; then
    YOCTO_LAYER_MANIFEST_FILE="$YOCTO_PROJECT_DIR/manifest.xml"
  fi
  if [ ! -f "$YOCTO_LAYER_MANIFEST_FILE" ] || [ ! -s "$YOCTO_LAYER_MANIFEST_FILE" ]; then
    echo "ERROR: The Yocto layer git-repo manifest '$YOCTO_LAYER_MANIFEST_FILE' is missing."
    return 1
  fi

  # Locate Yocto build area
  if [ -z "$YOCTO_BUILD_DIR" ]; then
    export YOCTO_BUILD_DIR="$YOCTO_DATA_DIR/build"
  fi

  return 0
}

sync_yocto_layers()
{
  local MANIFEST_FILE=$1
  local SOURCES_DIR=$2
  local MANIFEST_REPO_DIR="$SOURCES_DIR/manifest"
  local CURRENT_DIR="$PWD"

  mkdir -p "$MANIFEST_REPO_DIR"
  cd "$MANIFEST_REPO_DIR"
  cp "$MANIFEST_FILE" .
  if [ ! -d .git ]; then
    git init
    git config --local user.name $(whoami)
    git config --local user.email $(whoami)@localhost
  fi
  if [ -n "$(git status --porcelain)" ]; then
    git add $(basename "$MANIFEST_FILE")
    git commit --allow-empty-message -m ''
  fi

  cd "$SOURCES_DIR"
  echo "N" | repo init -u "file://$MANIFEST_REPO_DIR" -b master -m $(basename "$MANIFEST_FILE")
  repo sync --force-sync
  
  cd "$CURRENT_DIR"
}

detect_machine()
{
  sed -n "s/^MACHINE\s*?*=\s*'\(.*\)'/\1/p" < $YOCTO_BUILD_DIR/conf/local.conf
}

yield_latest_os_disk_image()
{
  local MACHINE=$1
  local WIC_FILE="$YOCTO_BUILD_DIR/tmp/fotahub-os/deploy/images/$MACHINE/fotahub-os-package-$MACHINE.wic"

  if [ -f "$WIC_FILE" ]; then
    mkdir -p "$YOCTO_PROJECT_DIR/build/images"
    cp "$WIC_FILE" "$YOCTO_PROJECT_DIR/build/images"
  fi
}

show_latest_os_revision()
{
  local MACHINE=$1
  local OSTREE_REPO_DIR="$YOCTO_BUILD_DIR/tmp/fotahub-os/deploy/images/$MACHINE/ostree_repo"

  if [ -d "$OSTREE_REPO_DIR" ]; then
    echo "Latest OS revision: $(ostree --repo="$OSTREE_REPO_DIR" rev-parse fotahub-os-$MACHINE)"
  fi
}

show_latest_app_revision()
{
  local MACHINE=$1
  local APP=$2
  local OSTREE_REPO_DIR="$YOCTO_BUILD_DIR/tmp/fotahub-apps/deploy/images/$MACHINE/ostree_repo"

  if [ -d "$OSTREE_REPO_DIR" ]; then
    echo "Latest '$APP' revision: $(ostree --repo="$OSTREE_REPO_DIR" rev-parse $APP)"
  fi
}

show_latest_app_revisions()
{
  local MACHINE=$1
  local OSTREE_REPO_DIR="$YOCTO_BUILD_DIR/tmp/fotahub-apps/deploy/images/$MACHINE/ostree_repo"

  if [ -d "$OSTREE_REPO_DIR" ]; then
    for REF in $(ostree --repo="$OSTREE_REPO_DIR" refs); do 
      show_latest_app_revision $MACHINE $REF
    done
  fi
}

show_usage()
{
  cat << EOF

Usage: $(basename $0) command [args]

Commands:
    sync <machine>
        Initialize/synchronize Yocto project for given machine
        (e.g. sync raspberrypi3)

    all
        Build OS including all applications as well as machine-dependent live image
        (e.g. '.wic' for Raspberry Pi)

    all-apps
        Build all applications

    app <app-name>
        Rebuild given application

    show-revisions
        Show latest OS and app revisions

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
  local COMMAND="$1"
  shift; set -- "$@"

  if ! create_yocto_project_layout; then
    exit 1
  fi

  if [ ! -d "$YOCTO_BUILD_DIR/conf" ] && [ "$COMMAND" != "sync" ] && [ "$COMMAND" != "help" ]; then
    echo "ERROR: The Yocto build directory '$YOCTO_BUILD_DIR' has not yet been initialized. Use the 'sync' command first. Use the 'help' command to get more details."
    exit 1
  fi

  case "$COMMAND" in
    sync)
      if [ $# -ne 1 ]; then
        echo "ERROR: The "$COMMAND" command requires exactly 1 argument. Use the 'help' command to get more details."
        exit 1
      fi
      local MACHINE=$1

      if ! sync_yocto_layers "$YOCTO_LAYER_MANIFEST_FILE" "$YOCTO_SOURCES_DIR"; then
        exit 1
      fi

      cd "$YOCTO_DATA_DIR"
      source $YOCTO_SOURCES_DIR/meta-fotahub/fh-pre-init-build-env $MACHINE
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      source $YOCTO_SOURCES_DIR/meta-fotahub/fh-post-init-build-env $MACHINE
      ;;

    all)
      cd "$YOCTO_DATA_DIR"
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake fotahub-apps-package -k $@
      DISTRO=fotahub-os bitbake fotahub-os-package -k $@

      yield_latest_os_disk_image "$MACHINE"
      show_latest_os_revision "$MACHINE"
      show_latest_app_revisions "$MACHINE"
      ;;

    all-apps)
      cd "$YOCTO_DATA_DIR"
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake fotahub-apps-package -k $@

      show_latest_app_revisions "$MACHINE"
      ;;

    app)
      if [ $# -ne 1 ]; then
        echo "ERROR: The "$COMMAND" command requires exactly 1 argument. Use the 'help' command to get more details."
        exit 1
      fi
      local APP=$1

      cd "$YOCTO_DATA_DIR"
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake $APP -f -k
      
      show_latest_app_revision "$MACHINE" "$APP"
      ;;

    show-revisions)
      local MACHINE=$(detect_machine)

      show_latest_os_revision "$MACHINE"
      show_latest_app_revisions "$MACHINE"
      ;;
  
    bash)
      cd "$YOCTO_DATA_DIR"
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
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