#!/bin/sh

# Setup JFFS2 partition so that is not excessively
# written to
umount /mnt &&
mount -t ramfs ramfs /mnt &&
mkdir /mnt/actually_mnt &&
mount -t jffs2 /dev/mtdblock2 /mnt/actually_mnt/ &&
ln -s /mnt/actually_mnt/hack /mnt/hack &&
ln -s /mnt/actually_mnt/ProgramFiles /mnt/ProgramFiles &&
ln -s /tmp/logs /mnt/logs &&

/mnt/hack/init/continue.sh