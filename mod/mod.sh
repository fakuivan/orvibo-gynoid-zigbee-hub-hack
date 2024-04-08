#!/bin/ash
# shellcheck shell=dash
set -euo pipefail
MOD_INSTALLING=/mnt/hack/installing
MOD_REMOVING=/mnt/hack/removing
MOD_DONE=/mnt/hack/done

err () { "$@" 1>&2; }
echoerr () { err echo "$@"; }

check_platform () {
    if [ "3.4.1.1" != "$(cat /version)" ]; then
        echoerr Hack not tested to work on this version
        exit 1
    fi
}

check_not_in_progress () {
    if [ -e "$MOD_INSTALLING" ]; then
        echoerr "Mod install is in in progress or was interrupted at some point"
        exit 1
    fi
    if [ -e "$MOD_REMOVING" ]; then
        echoerr "Mod removal is in progress or was interrupted at some point"
        exit 1
    fi
}

mod_install () {
    local init_path=ProgramFiles/etc/init.d

    echo Copying hack to persistent storage
    cp -r /tmp/hack/ /mnt/hack
    touch "$MOD_INSTALLING"

    echo Moving unused vihome app data
    mkdir /mnt/hack/unused/
    (
        cd /mnt/ &&
        mv device_manager.db \
        kvdata.db \
        log.db \
        logs \
        vihome2.db \
        zigbee_information \
        hack/unused/
    )

    echo Modifying init sequence
    mkdir -p /mnt/hack/unused/"$init_path"/
    cp /mnt/"$init_path"/rc.local /mnt/hack/unused/"$init_path"/ &&
        ln -sf ../../../hack/init/main.sh /mnt/"$init_path"/rc.local

    echo Install done
    touch "$MOD_DONE" && rm "$MOD_INSTALLING"
}

mod_remove () {
    touch "$MOD_REMOVING"
    local init_path=ProgramFiles/etc/init.d

    echo Restoring init script
    cp /mnt/hack/unused/"$init_path"/rc.local /mnt/"$init_path"/rc.local

    echo Restoring vihome app data and removing hack files
    (
        cd /mnt/hack/unused/ &&
        mv device_manager.db \
        kvdata.db \
        log.db \
        logs \
        vihome2.db \
        zigbee_information \
        ../../
    )
    rm -rf /mnt/hack/

    echo Uninstall done
}

check_platform
check_not_in_progress

case "$1" in
    install)
        if [ -e "$MOD_DONE" ]; then
            echoerr "Mod already installed"
            exit 0
        fi
        mod_install
    ;;
    remove)
        if ! [ -e "$MOD_DONE" ]; then
            echoerr "Mod not installed"
            exit 0
        fi
        mod_remove
    ;;
    *)
        echoerr "Not a command: $1"
        exit 1
    ;;
esac