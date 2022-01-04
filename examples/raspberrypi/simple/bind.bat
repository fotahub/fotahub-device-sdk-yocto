@echo off
setlocal

rem Make sure that 'yocto-factory' container's time syncs with that of host
wsl -d docker-desktop -e /sbin/hwclock -s

docker volume create yocto-factory-data
docker run ^
  --name yocto-factory ^
  --interactive --tty --rm ^
  --volume yocto-factory-data:/yocto ^
  --volume %~dp0:/yocto/cockpit ^
  fotahub/yocto-factory:2021.1.0 ^
  %*
  
endlocal
