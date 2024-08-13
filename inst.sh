#!/usr/bin/env sh
set -x -e

EXTRAVERSION=-be
VERSION=6.9.5

# turn on the debug messages for UVC_DBG_FRAME
trace="$((2#000010000000))"

# compile .ko
make EXTRAVERSION=$EXTRAVERSION modules_prepare
make EXTRAVERSION=$EXTRAVERSION M=drivers/media/usb/uvc

# compress kernelobject and copy to updates/
zstd drivers/media/usb/uvc/uvcvideo.ko -f
sudo cp -f drivers/media/usb/uvc/uvcvideo.ko.zst /usr/lib/modules/$VERSION$EXTRAVERSION/updates/

# remove old 
sudo depmod
sudo modprobe -r -v uvcvideo

# install new
sudo depmod
sudo modprobe -v uvcvideo trace=$trace

# enable pr_debug
echo 'file uvc_video.c +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
