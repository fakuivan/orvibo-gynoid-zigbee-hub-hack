if [ "$0" == "-sh" ]; then
    exec ash -l
fi

if [ -z "${PATH_BOOT+x}" ]; then
    echo "PATH_BOOT is not defined" 1>&2
else
    export PATH="$PATH_BOOT"
fi

alias ll="ls -la"
alias vim="vi"
