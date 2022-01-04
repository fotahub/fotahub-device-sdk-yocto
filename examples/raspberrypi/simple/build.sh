#!/bin/bash
 
create_yocto_project_layout()
{
  # Locate Yocto project
  if [ -z "$YOCTO_PROJECT_ROOT" ]; then
    export YOCTO_PROJECT_ROOT=$PWD/yocto
  fi
  if [ ! -d "$YOCTO_PROJECT_ROOT" ]; then
    mkdir -p "$YOCTO_PROJECT_ROOT"
  fi

  # Locate Yocto layer sources area
  if [ -z "$YOCTO_SOURCES_DIR" ]; then
    export YOCTO_SOURCES_DIR="$YOCTO_PROJECT_ROOT/sources"
  fi

  # Locate Yocto project cockpit area
  if [ -z "$YOCTO_COCKPIT_DIR" ]; then
    export YOCTO_COCKPIT_DIR="$YOCTO_PROJECT_ROOT/cockpit"
  fi

  # Locate Yocto layer sources git-repo manifest
  if [ -z "$YOCTO_LAYER_MANIFEST" ]; then
    YOCTO_LAYER_MANIFEST="$YOCTO_COCKPIT_DIR/manifest.xml"
  fi
  if [ ! -f "$YOCTO_LAYER_MANIFEST" ] || [ ! -s "$YOCTO_LAYER_MANIFEST" ]; then
    echo "ERROR: The Yocto layer git-repo manifest '$YOCTO_LAYER_MANIFEST' is missing."
    return 1
  fi

  # Locate Yocto build area
  if [ -z "$YOCTO_BUILD_DIR" ]; then
    export YOCTO_BUILD_DIR="$YOCTO_PROJECT_ROOT/build"
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
  sed -n 's/MACHINE\s*?*=\s*"\(.*\)"/\1/p' < $YOCTO_BUILD_DIR/conf/local.conf
}

locate_build_results()
{
  local MACHINE=$1

  OS_IMAGE_DIR="$YOCTO_BUILD_DIR/tmp/fotahub-os/deploy/images/$MACHINE"
  APPS_IMAGE_DIR="$YOCTO_BUILD_DIR/tmp/fotahub-apps/deploy/images/$MACHINE"

  OS_OSTREE_REPO_DIR="$OS_IMAGE_DIR/ostree_repo"
  APPS_OSTREE_REPO_DIR="$APPS_IMAGE_DIR/ostree_repo"

  APPS_IMAGE_FILE="$APPS_IMAGE_DIR/fotahub-apps-package-$MACHINE.ext4"
  WIC_IMAGE_FILE="$OS_IMAGE_DIR/fotahub-os-package-$MACHINE.wic"
}

detect_apps()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  if [ -d "$APPS_OSTREE_REPO_DIR" ]; then
    ostree --repo="$APPS_OSTREE_REPO_DIR" refs
  else
    echo ""
  fi
}

exists_apps_image()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  [ -f "$APPS_IMAGE_FILE" ] && return 0 || return 1
}

yield_latest_wic_image()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  if [ -f "$WIC_IMAGE_FILE" ]; then
    mkdir -p "$YOCTO_COCKPIT_DIR/build/images"
    cp "$WIC_IMAGE_FILE" "$YOCTO_COCKPIT_DIR/build/images"
  fi
}

show_latest_os_revision()
{
  local MACHINE=$1

  locate_build_results $MACHINE

  if [ -d "$OS_OSTREE_REPO_DIR" ]; then
    echo "Latest OS revision: $(ostree --repo="$OS_OSTREE_REPO_DIR" rev-parse fotahub-os-$MACHINE)"
  fi
}

show_latest_app_revision()
{
  local MACHINE=$1
  local APP=$2

  locate_build_results $MACHINE

  if [ -d "$APPS_OSTREE_REPO_DIR" ]; then
    echo "Latest '$APP' revision: $(ostree --repo="$APPS_OSTREE_REPO_DIR" rev-parse $APP)"
  fi
}

show_latest_app_revisions()
{
  local MACHINE=$1

  for APP in $(detect_apps $MACHINE); do 
    show_latest_app_revision $MACHINE $APP
  done
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
        Build and publish OS and application images,
        and create machine-dependent live disk image including OS and applications
        (e.g. '.wic' for Raspberry Pi)

    os <bitbake args...>
        Build and publish OS image

    apps <bitbake args...>
        Build and publish all application images

    app <app-name> <bitbake args...>
        Build and publish image of given application

    clean
        Clean OS and all applications

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

  cd "$YOCTO_PROJECT_ROOT"

  case "$COMMAND" in
    sync)
      if [ $# -ne 1 ]; then
        echo "ERROR: The "$COMMAND" command requires exactly 1 argument. Use the 'help' command to get more details."
        exit 1
      fi
      local MACHINE=$1

      if ! sync_yocto_layers "$YOCTO_LAYER_MANIFEST" "$YOCTO_SOURCES_DIR"; then
        exit 1
      fi

      source $YOCTO_SOURCES_DIR/meta-fotahub/fh-pre-init-build-env $MACHINE
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      source $YOCTO_SOURCES_DIR/meta-fotahub/fh-post-init-build-env $MACHINE
      ;;

    wic)
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake fotahub-apps-package -k $@
      DISTRO=fotahub-os bitbake fotahub-os-package -k $@

      yield_latest_wic_image "$MACHINE"
      show_latest_os_revision "$MACHINE"
      show_latest_app_revisions "$MACHINE"
      ;;

    os)
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      # Conceptionally it would not be necessary to build the apps image along with the OS image right here. But technically,
      # there are no means to prevent the do_image_wic task from running when only the OS image is meant to be built, 
      # and that task would cause the build to fail if the apps image does not exist
      if ! exists_apps_image "$MACHINE"; then
        DISTRO=fotahub-apps bitbake fotahub-apps-package -k $@
      fi
      DISTRO=fotahub-os bitbake fotahub-os-package -k $@

      show_latest_os_revision "$MACHINE"
      ;;

    apps)
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake fotahub-apps-package -k $@

      show_latest_app_revisions "$MACHINE"
      ;;

    app)
      if [ $# -lt 1 ]; then
        echo "ERROR: The "$COMMAND" command requires at least 1 argument. Use the 'help' command to get more details."
        exit 1
      fi
      local APP=$1
      shift; set -- "$@"

      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      DISTRO=fotahub-apps bitbake $APP -c cleanall
      DISTRO=fotahub-apps bitbake $APP -k $@
      
      show_latest_app_revision "$MACHINE" "$APP"
      ;;

    clean)
      source $YOCTO_SOURCES_DIR/poky/oe-init-build-env $YOCTO_BUILD_DIR
      local MACHINE=$(detect_machine)

      for APP in $(detect_apps $MACHINE); do
        DISTRO=fotahub-apps bitbake $APP -c cleanall
      done
      DISTRO=fotahub-apps bitbake fotahub-apps-package -c cleanall
      DISTRO=fotahub-os bitbake fotahub-os-package -c cleanall
      ;;

    show-revisions)
      local MACHINE=$(detect_machine)

      show_latest_os_revision "$MACHINE"
      show_latest_app_revisions "$MACHINE"
      ;;
  
    bash)
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