#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="$1"
COPY_PATH="$2"
quote_c () {
    printf "%s" "$1" | jq -RsaM
}

apt update
DEBIAN_FRONTEND="noninteractive" apt install git jq make -y
. /sdk/*-activate
ln -s mips-linux-uclibc-gcc-4.4.7 /sdk/bin/mips-linux-uclibc-gcc

git clone https://github.com/mkj/dropbear.git /program
cd /program
git checkout DROPBEAR_2024.84

# Preserve tabs in diff using:
# git diff |
#     python3 -c 'import sys, shlex; print("$" + shlex.quote(sys.stdin.read()).replace("\t", "\\t"))'
printf "%s" $'\
diff --git a/src/common-session.c b/src/common-session.c
index a045adf..2337301 100644
--- a/src/common-session.c
+++ b/src/common-session.c
@@ -648,7 +648,7 @@ void fill_passwd(const char* username) {
 \tses.authstate.pw_uid = pw->pw_uid;
 \tses.authstate.pw_gid = pw->pw_gid;
 \tses.authstate.pw_name = m_strdup(pw->pw_name);
-\tses.authstate.pw_dir = m_strdup(pw->pw_dir);
+\tses.authstate.pw_dir = m_strdup('"$(quote_c "$HOME_DIR")"$');
 \tses.authstate.pw_shell = m_strdup(pw->pw_shell);
 \t{
 \t\tchar *passwd_crypt = pw->pw_passwd;
' | git apply

eval $'shopt -s expand_aliases; \ncross_configure --enable-static --disable-zlib'

make -f <(
    # I've had issues with the stack guards not being able to be linked, maybe this
    # arch doesn't provide that?
    sed '0,/^-fstack-protector/{s/-fstack-protector/-fno-stack-protector/}' Makefile
    ) MULTI=1

cp dropbearmulti "$COPY_PATH"
