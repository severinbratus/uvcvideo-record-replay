#!/bin/sh
set -e -x

code=4m,3y,2m
code2=3y

./reload

echo 1 Record
echo ===
sudo ./switchrecord
./capseqs.py recorded_u $code
echo

echo 2 k2u
echo ===
sudo ./khron.py k2u recorded_k2u
echo

echo 3 Cmp recorded and restored
echo ===
diff -r recorded_u recorded_k2u
echo 

echo 4 Replay
echo ===
sudo ./switchreplay
./capseqs.py replayed_u $code
echo

echo 5 Cmp recorded and replayed
echo ===
diff -r recorded_u replayed_u
echo

echo 5b Cmp restored and rerestored
echo ---
sudo ./khron.py k2u recorded_k2u_b
diff -r recorded_k2u recorded_k2u_b
echo

echo 6 Mirror
echo ===
./domirror.sh recorded_u mirrored
rm -rf mirrored/00 mirrored/02
mv mirrored/01 mirrored/00
echo

echo 7 u2k
echo ===
sudo ./khron.py u2k mirrored
echo

echo 8 Replay mirrored
echo ===
# reset index
sudo ./switchreplay
./capseqs.py mirrored_replayed $code2
echo

echo 9 Cmp mirrored and replayed
echo ===
diff -r mirrored mirrored_replayed
echo

