#!/usr/bin/env sh

set -e

src="$1"
dest="$2"

if [[ -z "$1" || -z "$2" ]]; then
    echo "incomplete args!"
    exit 1
fi

# overwrite
rm -rf $dest
cp $src $dest -r

echo "Mirror *mjpg frames"
find $dest -name "*.mjpg" -print -exec jpegtran -flip horizontal -perfect -outfile {}.tmp {} \;
find $dest -name "*.mjpg" -exec mv {}.tmp {}  \;

echo "Mirror *yuyv frames"
find $dest -name "*.yuyv" -exec rm {}.png \;
find $dest -name "*.yuyv" -print -exec python mirror_yuyv.py {} {} \;

find $dest -name "*.yuyv" -exec ./yuyv2png {} \;

