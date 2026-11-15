#!/bin/sh
set -eu
cd "$(dirname "$0")"

exec qemu-system-x86_64 \
    -m 256M \
    -smp 2 \
    -cpu kvm64,+smep,+smap \
    -kernel bzImage \
    -initrd rootfs.cpio.gz \
    -nographic \
    -monitor /dev/null \
    -no-reboot \
    -append "console=ttyS0 quiet nokaslr randomize_kstack_offset=off pti=on panic=0"
