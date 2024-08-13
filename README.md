# Linux USB Video Class (UVC) Driver with RECORD & REPLAY modes

Done as a proof of concept for spoofing face verification software and the like.

# Example Usage

1. Run `./inst.sh` to install the kernel module, and replace the default `uvcvideo` driver.
2. Run `./switchrecord` to switch the module to RECORD mode.
3. Turn on the camera, e.g. via Cheese. Multiple streams possible.
4. Run `./styx.py k2u recorded` to transfer the frames from kernelspace to userspace (as a nested directory of images named `recorded`).
5. (Opt.) Run `./mirror.sh recorded/ mirrored/` to mirror (horisontally flip) the frames. This will produce a directory `mirrored`.
6. Run `sudo ./styx.py u2k mirrored` to transfer the modified frames back to kernelspace.
7. Run `./switchreplay` to switch to REPLAY mode.
3. Turn on the camera again. Now the frames should be mirrored.
