#!/usr/bin/python

# Like the underworld river Styx of the Greek myth, styx.py connects two worlds: userspace & kernelspace,
# converting framestore representations back and forth.
# In userspace frames are stored as a nested directory of images.
# In kernelspace -- as One Big Buffer (and the necessary offset info)

from pathlib import Path
from sys import argv
from itertools import takewhile
from fnmatch import fnmatch

from colorama import Fore, Style

import os
import shutil

import struct
import subprocess

MJPG_FRAME_SIZE_MAX = 0x80000
YUYV_FRAME_SIZE = 614400
FDATA_MAX = 2000 * YUYV_FRAME_SIZE

N_SEGMS_MAX = 20

kd = kspace_dir = debugfs_dir_path = Path("/sys/kernel/debug/usb/uvcvideo/sb/framestore/")


def first_nonzero(lst):
    return list(takewhile(lambda x: x != 0, lst))


def run(cmd, silent=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if not silent or result.returncode != 0:
        print(Style.BRIGHT + cmd + Style.RESET_ALL)
        print(result.stdout)
        print(Fore.RED + result.stderr + Fore.RESET)
    # print("Return code:", result.returncode)


uintfmats = {
    1: 'B',
    2: 'H',
    4: 'I',
    8: 'L',
    16: 'Q',
}

def read_uints(path, uintbits):
    with open(path, 'rb') as f:
        content = f.read()
    uintbytes = uintbits // 8
    assert len(content) % uintbytes == 0
    n_ints = len(content) // uintbytes
    uintfmat = uintfmats[uintbytes]
    ints = struct.unpack(f'={n_ints}{uintfmat}', content)
    return ints


def write_uints(path, uintbits, uints):
    uintbytes = uintbits // 8
    uintfmat = uintfmats[uintbytes]
    n_ints = len(uints)
    content = struct.pack(f'={n_ints}{uintfmat}', *uints)
    assert len(content) % uintbytes == 0
    with open(path, 'wb') as f:
        f.write(content)


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def read_plain_uint(path):
    return int(read_bytes(path))


def write_plain_uint(path, uint):
    with open(path, 'wb') as f:
        f.write(bytes(str(uint), 'ascii'))


def read_ascii(path):
    return read_bytes(path).decode('ascii')


def xxd(input_string):
    byte_array = input_string.encode('utf-8')
    hex_string = byte_array.hex()
    formatted_hex_string = ' '.join(hex_string[i:i+4] for i in range(0, len(hex_string), 4))
    return formatted_hex_string


def group(fsizes, offsets, segm_nframes):
    return [fsizes[offset:offset + nframes] for offset, nframes in zip(offsets, segm_nframes)]


def prettyprint(grouped_fsizes, segm_fmats):
    print()
    for segm_idx, (group, fmat) in enumerate(zip(grouped_fsizes, segm_fmats)):
        print(segm_idx, fmat, f"({len(group)})", group)
    print()


def warn(msg):
    print(Fore.RED + "WARNING:", msg + Fore.RESET)


def k2u(uspace_dir):
    ud = uspace_dir

    if os.path.exists(ud):
        shutil.rmtree(ud)
        print(f"Directory '{ud}' existed and was removed.")
    os.makedirs(ud)

    # Read the fstore struct attr-s
    n_segms = read_plain_uint(kd / "n_segms")
    print(f"{n_segms=}")

    segm_fmats = read_ascii(kd / "segm_fmats")
    segm_nframes = read_uints(kd / "segm_nframes", 16)

    offsets_fdata = read_uints(kd / "offsets_fdata", 32)
    offsets_fsizes = read_uints(kd / "offsets_fsizes", 16)

    fsizes = read_uints(kd / "fsizes", 32)

    # print(f"{first_nonzero(fsizes)=}")
    # print(f"{segm_fmats=}")
    # print(f"{segm_nframes=}")
    # print(f"{offsets_fdata=}")
    # print(f"{offsets_fsizes=}")

    prettyprint(group(fsizes, offsets_fsizes, segm_nframes), segm_fmats.replace('\x00', ''))

    for segm_idx in range(n_segms):
        sd = "%02d" % segm_idx

        assert segm_fmats[segm_idx] in 'MY'
        fmat = 'mjpg' if segm_fmats[segm_idx] == 'M' else 'yuyv'
        nframes = segm_nframes[segm_idx]
        print(f"{nframes=}")
        segm_offset = offsets_fdata[segm_idx]
        segm_offset_fsizes = offsets_fsizes[segm_idx]

        os.makedirs(ud / sd)

        cur_frame_max = YUYV_FRAME_SIZE if fmat == 'yuyv' else MJPG_FRAME_SIZE_MAX

        for frame_idx in range(nframes):
            frame_size = fsizes[segm_offset_fsizes + frame_idx]
            print(f"{frame_idx=}, {frame_size=}")
            offset = segm_offset + cur_frame_max * frame_idx
            if fmat == 'mjpg':
                assert frame_size <= cur_frame_max, f"{segm_idx=}, {frame_idx=}, {frame_size=}, {cur_frame_max=}"
            elif fmat == 'yuyv':
                if frame_size > cur_frame_max:
                    warn(f"frame too large: {segm_idx=}, {frame_idx=}, {frame_size=}, {cur_frame_max=}")
                frame_size = YUYV_FRAME_SIZE
            if frame_size == 0:
                warn(f"empty frame: {frame_idx=} {fmat=}")
                continue
            with open(kd / "fdata", 'rb') as f:
                f.seek(offset)
                data = f.read(frame_size)
                if fmat == 'mjpg':
                    assert data[:2] == b'\xff\xd8'
            fname = f"frame_{frame_idx:04}.{fmat}"
            with open(ud / sd / fname, 'wb') as f:
                f.write(data)
            if fmat == 'yuyv':
                run(f"./yuyv2png {ud / sd / fname}")


def zeroed():
    return [0 for _ in range(N_SEGMS_MAX)]


def fmat2fmax(fmat):
    return {
        'M': MJPG_FRAME_SIZE_MAX,
        'Y': YUYV_FRAME_SIZE,
    }[fmat]


def abbr(fmat):
    return fmat[0].upper()


def u2k(uspace_dir):
    ud = uspace_dir
    assert ud.exists()
    
    segm_dirs = sorted([path for path in ud.iterdir()
                       if path.is_dir() and path.name.isnumeric()])
    n_segms = len(segm_dirs)

    segm_fmats = zeroed()
    segm_nframes = zeroed()
    offsets_fdata = zeroed()
    offsets_fsizes = zeroed()

    fsizes = []

    for segm_dir in segm_dirs:
        segm_idx = int(segm_dir.name)
        if segm_idx != 0:
            fmax = fmat2fmax(segm_fmats[segm_idx - 1])
            # DP to compute offsets
            offsets_fdata[segm_idx] = offsets_fdata[segm_idx - 1] + segm_nframes[segm_idx - 1] * fmax
            offsets_fsizes[segm_idx] = offsets_fsizes[segm_idx - 1] + segm_nframes[segm_idx - 1]

        frame_files = sorted([path for path in segm_dir.iterdir()
                              if path.is_file() and fnmatch(path.name, 'frame_????.????')])

        fmat = frame_files[0].name[-4:]
        cur_frame_max = YUYV_FRAME_SIZE if fmat == 'yuyv' else MJPG_FRAME_SIZE_MAX

        assert all(file.name.endswith('.' + fmat) for file in frame_files)
        nframes = len(frame_files)

        count = 0
        for frame_idx, frame_file in enumerate(frame_files):
            assert str(frame_idx) in frame_file.name

            with open(frame_file, 'rb') as f:
                frame_data = f.read()
            
            count += cur_frame_max
            assert count <= FDATA_MAX

            # Record frame size
            fsize = len(frame_data)
            fsizes.append(fsize)

            offset = offsets_fdata[segm_idx] + frame_idx * cur_frame_max

            # Write directly to kspace
            with open(kd / 'fdata', 'rb+') as f:
                f.seek(offset)
                f.write(frame_data)

        segm_fmats[segm_idx] = abbr(fmat)
        segm_nframes[segm_idx] = nframes

    print(f"{n_segms=}")
    print(f"{segm_fmats=}")
    print(f"{segm_nframes=}")
    print(f"{offsets_fdata=}")
    print(f"{offsets_fsizes=}")
    print(f"{fsizes=}")

    segm_fmats = [(ord(x) if type(x) == str else x) for x in segm_fmats]

    write_plain_uint(kd / "n_segms", n_segms)
    write_uints(kd / "segm_fmats", 8, segm_fmats)
    write_uints(kd / "segm_nframes", 16, segm_nframes)
    write_uints(kd / "offsets_fdata", 32, offsets_fdata)
    write_uints(kd / "offsets_fsizes", 16, offsets_fsizes)
    # (fdata is written frame by frame, file to file)
    write_uints(kd / "fsizes", 32, fsizes)


if __name__ == '__main__':
    cmd_name = argv[1]
    cmds = {
        'u2k': u2k,
        'k2u': k2u,
    }
    arg = Path(argv[2])
    cmd = cmds[cmd_name]
    cmd(arg)
