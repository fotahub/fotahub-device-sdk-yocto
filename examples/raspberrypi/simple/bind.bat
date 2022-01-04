@echo off
setlocal

rem Make sure that 'fotahub-yocto-factory' container's time syncs with that of host
wsl -d docker-desktop -e /sbin/hwclock -s

docker volume create fotahub-yocto-factory-data
docker run ^
  --name fotahub-yocto-factory ^
  --interactive --tty --rm ^
  --volume fotahub-yocto-factory-data:/yocto ^
  --volume %~dp0:/yocto/cockpit ^
  fotahub/yocto-factory:2021.1.0 ^
  %*
  
endlocal
