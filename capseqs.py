#!/usr/bin/python

from sys import argv

import pathlib
import shutil
import os
import subprocess

from colorama import Fore, Style


def split_yuyv(input_file, chunk_size=600*1024):
    file_number = 0
    parent_dir = input_file.parent
    with open(input_file, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            output_file = f"frame_{file_number:04d}.yuyv"
            with open(parent_dir / output_file, 'wb') as chunk_file:
                chunk_file.write(chunk)
            file_number += 1


def split_mjpg(input_file, marker=b'\xff\xd9'):
    with open(input_file, 'rb') as f:
        data = f.read()
    
    parent_dir = input_file.parent

    frames = data.split(marker)
    for i in range(len(frames) - 1):
        frames[i] += marker

    for idx, frame in enumerate(frames[:-1]):
        # print(f"{idx=}")
        output_file = f"frame_{idx:04d}.mjpg"
        with open(parent_dir / output_file, 'wb') as out:
            out.write(frame)

    
def run(cmd, silent=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    code = result.returncode
    if code or not silent:
        print(Style.BRIGHT + cmd + Style.RESET_ALL)
        if result.stdout: print(result.stdout)
    if result.stderr: print(Fore.RED, result.stderr, Fore.RESET)
    assert code == 0


path = pathlib.Path(argv[1])
segms_code = argv[2].split(',')


if path.exists():
    shutil.rmtree(path)
os.makedirs(path)


for segm_idx, segm_code in enumerate(segms_code):
    fmat = {
        'm': 'mjpg',
        'y': 'yuyv',
    }[segm_code[-1]]
    nframes = int(segm_code[:-1])
    print(f"{fmat=}")

    sd = f"{segm_idx:02d}"
    os.makedirs(path / sd)

    tmp_file = path / sd / f"tmp.{fmat}"

    cmd = {
        "yuyv": "v4l2-ctl --device /dev/video2 --stream-mmap -v width=640,height=480,pixelformat=YUYV --stream-to={} --stream-count={}",
        "mjpg": "v4l2-ctl --device /dev/video2 --stream-mmap -v width=1280,height=720,pixelformat=MJPG --stream-to={} --stream-count={}",
    }[fmat].format(tmp_file, nframes)

    run(cmd)

    {
        "mjpg": split_mjpg,
        "yuyv": split_yuyv,
    }[fmat](tmp_file)

    tmp_file.unlink()


run(f'find {path} -name "*yuyv" -exec ./yuyv2png {{}} \\;')

    
