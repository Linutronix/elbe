#!/bin/sh
##
## This file was copied from http://git.yoctoproject.org/git/poky
##                           16e22f3e37788afb83044f5089d24187d70094bd
##
## origin location of the file is: 'meta/files/toolchain-shar-extract.sh'
##
## known authors of the origin file are:
##
## Anibal Limon <anibal.limon@linux.intel.com>
## Brendan Le Foll <brendan.le.foll@intel.com>
## Ed Bartosh <ed.bartosh@linux.intel.com>
## George Nita <george.nita@enea.com>
## Maxin B. John <maxin.john@intel.com>
## Paul Eggleton <paul.eggleton@linux.intel.com>
## Qi.Chen@windriver.com <Qi.Chen@windriver.com>
## Randy Witt <randy.e.witt@linux.intel.com>
## Richard Purdie <richard.purdie@linuxfoundation.org>
## Robert Yang <liezhi.yang@windriver.com>
## Todor Minchev <todor.minchev@linux.intel.com>
## Wenlin Kang <wenlin.kang@windriver.com>
##
## The 'meta' folder of the origin repo contains a
## COPYING.GPLv2 and COPYING.MIT file.

[ -z "$ENVCLEANED" ] && exec /usr/bin/env -i ENVCLEANED=1 HOME="$HOME" \
	LC_ALL=en_US.UTF-8 \
	TERM=$TERM \
	http_proxy="$http_proxy" https_proxy="$https_proxy" ftp_proxy="$ftp_proxy" \
	no_proxy="$no_proxy" all_proxy="$all_proxy" GIT_PROXY_COMMAND="$GIT_PROXY_COMMAND" "$0" "$@"
[ -f /etc/environment ] && . /etc/environment
export PATH=`echo "$PATH" | sed -e 's/:\.//' -e 's/::/:/'`

tweakpath () {
    case ":$PATH:" in
        *:"$1":*)
            ;;
        *)
            PATH=$PATH:$1
    esac
}

# Some systems don't have /usr/sbin or /sbin in the cleaned environment PATH but we make need it 
# for the system's host tooling checks
tweakpath /usr/sbin
tweakpath /sbin

INST_ARCH=$(uname -m | sed -e "s/i[3-6]86/ix86/" -e "s/x86[-_]64/x86_64/")
SDK_ARCH=$(echo ${sdk_arch} | sed -e "s/i[3-6]86/ix86/" -e "s/x86[-_]64/x86_64/")

INST_GCC_VER=$(gcc --version | sed -ne 's/.* \([0-9]\+\.[0-9]\+\)\.[0-9]\+.*/\1/p')
SDK_GCC_VER='${sdk_gcc_ver}'

verlte () {
	[  "$1" = "`printf "$1\n$2" | sort -V | head -n1`" ]
}

verlt() {
	[ "$1" = "$2" ] && return 1 || verlte $1 $2
}

if [ "$INST_ARCH" != "$SDK_ARCH" ]; then
	# Allow for installation of ix86 SDK on x86_64 host
	if [ "$INST_ARCH" != x86_64 -o "$SDK_ARCH" != ix86 ]; then
		echo "Error: Incompatible SDK installer! Your host is $INST_ARCH and this SDK was built for $SDK_ARCH hosts."
		exit 1
	fi
fi

if ! xz -V > /dev/null 2>&1; then
	echo "Error: xz is required for installation of this SDK, please install it first"
	exit 1
fi

DEFAULT_INSTALL_DIR="${sdk_path}"
SUDO_EXEC=""
EXTRA_TAR_OPTIONS=""
target_sdk_dir=""
answer=""
relocate=1
savescripts=0
verbose=0
publish=0
listcontents=0
while getopts ":yd:npDRSl" OPT; do
	case $OPT in
	y)
		answer="Y"
		;;
	d)
		target_sdk_dir=$OPTARG
		;;
	n)
		prepare_buildsystem="no"
		;;
	p)
		prepare_buildsystem="no"
		publish=1
		;;
	D)
		verbose=1
		;;
	R)
		relocate=0
		savescripts=1
		;;
	S)
		savescripts=1
		;;
	l)
		listcontents=1
		;;
	*)
		echo "Usage: $(basename $0) [-y] [-d <dir>]"
		echo "  -y         Automatic yes to all prompts"
		echo "  -d <dir>   Install the SDK to <dir>"
		echo "======== Extensible SDK only options ============"
		echo "  -n         Do not prepare the build system"
		echo "  -p         Publish mode (implies -n)"
		echo "======== Advanced DEBUGGING ONLY OPTIONS ========"
		echo "  -S         Save relocation scripts"
		echo "  -R         Do not relocate executables"
		echo "  -D         use set -x to see what is going on"
		echo "  -l         list files that will be extracted"
		exit 1
		;;
	esac
done

payload_offset=$(($(grep -na -m1 "^MARKER:$" $0|cut -d':' -f1) + 1))
if [ "$listcontents" = "1" ] ; then
    tail -n +$payload_offset $0| tar tvJ || exit 1
    exit
fi

titlestr="${sdk_title} ${sdk_version} SDK installer"
printf "%s\n" "$titlestr"
printf "%${"$"}{#titlestr}s\n" | tr " " "="

if [ $verbose = 1 ] ; then
	set -x
fi


# SDK_EXTENSIBLE is exposed from the SDK_PRE_INSTALL_COMMAND above
if [ "$SDK_EXTENSIBLE" = "1" ]; then
	DEFAULT_INSTALL_DIR="${sdk_ext_path}"
	if [ "$INST_GCC_VER" = '4.8' -a "$SDK_GCC_VER" = '4.9' ] || [ "$INST_GCC_VER" = '4.8' -a "$SDK_GCC_VER" = '' ] || \
		[ "$INST_GCC_VER" = '4.9' -a "$SDK_GCC_VER" = '' ]; then
		echo "Error: Incompatible SDK installer! Your host gcc version is $INST_GCC_VER and this SDK was built by gcc higher version."
		exit 1
	fi
fi

if [ "$target_sdk_dir" = "" ]; then
	if [ "$answer" = "Y" ]; then
		target_sdk_dir="$DEFAULT_INSTALL_DIR"
	else
		read -p "Enter target directory for SDK (default: $DEFAULT_INSTALL_DIR): " target_sdk_dir
		[ "$target_sdk_dir" = "" ] && target_sdk_dir=$DEFAULT_INSTALL_DIR
	fi
fi

eval target_sdk_dir=$(echo "$target_sdk_dir"|sed 's/ /\\ /g')
if [ -d "$target_sdk_dir" ]; then
	target_sdk_dir=$(cd "$target_sdk_dir"; pwd)
else
	target_sdk_dir=$(readlink -m "$target_sdk_dir")
fi

# limit the length for target_sdk_dir, ensure the relocation behaviour in relocate_sdk.py has right result.
if [ ${"$"}{#target_sdk_dir} -gt 2048 ]; then
	echo "Error: The target directory path is too long!!!"
	exit 1
fi

if [ "$SDK_EXTENSIBLE" = "1" ]; then
	# We're going to be running the build system, additional restrictions apply
	if echo "$target_sdk_dir" | grep -q '[+\ @$]'; then
		echo "The target directory path ($target_sdk_dir) contains illegal" \
		     "characters such as spaces, @, \$ or +. Abort!"
		exit 1
	fi
	# The build system doesn't work well with /tmp on NFS
	fs_dev_path="$target_sdk_dir"
	while [ ! -d "$fs_dev_path" ] ; do
		fs_dev_path=`dirname $fs_dev_path`
        done
	fs_dev_type=`stat -f -c '%t' "$fs_dev_path"`
	if [ "$fsdevtype" = "6969" ] ; then
		echo "The target directory path $target_sdk_dir is on NFS, this is not possible. Abort!"
		exit 1
	fi
else
	if [ -n "$(echo $target_sdk_dir|grep ' ')" ]; then
		echo "The target directory path ($target_sdk_dir) contains spaces. Abort!"
		exit 1
	fi
fi

if [ -e "$target_sdk_dir/environment-setup-${real_multimach_target_sys}" ]; then
	echo "The directory \"$target_sdk_dir\" already contains a SDK for this architecture."
	printf "If you continue, existing files will be overwritten! Proceed[y/N]? "

	default_answer="n"
else
	printf "You are about to install the SDK to \"$target_sdk_dir\". Proceed[Y/n]? "

	default_answer="y"
fi

if [ "$answer" = "" ]; then
	read answer
	[ "$answer" = "" ] && answer="$default_answer"
else
	echo $answer
fi

if [ "$answer" != "Y" -a "$answer" != "y" ]; then
	echo "Installation aborted!"
	exit 1
fi

# Try to create the directory (this will not succeed if user doesn't have rights)
mkdir -p $target_sdk_dir >/dev/null 2>&1

# if don't have the right to access dir, gain by sudo 
if [ ! -x $target_sdk_dir -o ! -w $target_sdk_dir -o ! -r $target_sdk_dir ]; then 
	if [ "$SDK_EXTENSIBLE" = "1" ]; then
		echo "Unable to access \"$target_sdk_dir\", will not attempt to use" \
		     "sudo as as extensible SDK cannot be used as root."
		exit 1
	fi

	SUDO_EXEC=$(which "sudo")
	if [ -z $SUDO_EXEC ]; then
		echo "No command 'sudo' found, please install sudo first. Abort!"
		exit 1
	fi

	# test sudo could gain root right
	$SUDO_EXEC pwd >/dev/null 2>&1
	[ $? -ne 0 ] && echo "Sorry, you are not allowed to execute as root." && exit 1

	# now that we have sudo rights, create the directory
	$SUDO_EXEC mkdir -p $target_sdk_dir >/dev/null 2>&1
fi

FILECMD=$(which "file")

if [ x\$FILECMD = "x"  ]; then
        echo "file command not found."
        echo "use 'sudo apt install file' on Debian"
        echo "use 'sudo dnf install file' on Red Hat Enterprise Linux"
        exit 1
fi

printf "Extracting SDK..."
tail -n +$payload_offset $0| $SUDO_EXEC tar xJ -C $target_sdk_dir --checkpoint=.2500 $EXTRA_TAR_OPTIONS || exit 1
echo "done"

printf "Setting it up..."
# fix environment paths
real_env_setup_script=""
for env_setup_script in `ls $target_sdk_dir/environment-setup-*`; do
	if grep -q 'OECORE_NATIVE_SYSROOT=' $env_setup_script; then
		# Handle custom env setup scripts that are only named
		# environment-setup-* so that they have relocation
		# applied - what we want beyond here is the main one
		# rather than the one that simply sorts last
		real_env_setup_script="$env_setup_script"
	fi
	$SUDO_EXEC sed -e "s:${sdk_path}:$target_sdk_dir:g" -i $env_setup_script
done
if [ -n "$real_env_setup_script" ] ; then
	env_setup_script="$real_env_setup_script"
fi

if ! xargs --version > /dev/null 2>&1; then
        echo "xargs is required by the relocation script, please install it first. Abort!"
        exit 1
fi

# fix dynamic loader paths in all ELF SDK binaries
native_sysroot=$target_sdk_dir/sysroots/host
dl_path=$($SUDO_EXEC find -H $native_sysroot/lib -name "ld-linux-x86-64*")
if [ "$dl_path" = "" ] ; then
        echo "SDK could not be set up. Relocate script unable to find ld-linux.so. Abort!"
        exit 1
fi
native_executable_files=$($SUDO_EXEC find $native_sysroot -type f \
        \( -perm -0100 -o -perm -0010 -o -perm -0001 \) \
	-exec sh -c "file {} | grep -P ': ELF 64-bit LSB (shared object|pie executable|executable), x86-64, .*, interpreter' > /dev/null" \; \
        -printf "'%h/%f' ")

native_elf_files=$($SUDO_EXEC find $native_sysroot -type f \
	-exec sh -c "file {} | grep -P ': ELF 64-bit LSB (shared object|pie executable|executable), x86-64' > /dev/null" \; \
        -printf "'%h/%f' ")

target_executable_files=$($SUDO_EXEC find $native_sysroot -type f \
        \( -perm -0100 -o -perm -0010 -o -perm -0001 \) \
	-exec sh -c "file {} | grep -P ': ELF (64|32)-bit LSB (shared object|pie executable|executable), ${target_elfcode}, .*, interpreter' > /dev/null" \; \
        -printf "'%h/%f' ")

target_elf_files=$($SUDO_EXEC find $native_sysroot -type f \
	-exec sh -c "file {} | grep -P ': ELF (64|32)-bit LSB (shared object|pie executable|executable), ${target_elfcode},' > /dev/null" \; \
        -printf "'%h/%f' ")

ascii_so_files=$($SUDO_EXEC find $native_sysroot -type f -name "*.so" \
	-exec sh -c "file {} | grep -P ': ASCII text' > /dev/null" \; \
        -printf "'%h/%f' ")

abs_symbolic_links=$($SUDO_EXEC find $native_sysroot -type l \
    -exec sh -c "file \"{}\" | grep -P 'symbolic link to [\`]?/' > /dev/null" \; \
    -printf "'%h/%f' ")

if [ "x$native_executable_files" = "x" ]; then
   echo "SDK relocate failed, could not get executalbe files"
   exit 1
fi

tdir=`mktemp -d`
if [ x$tdir = x ] ; then
   echo "SDK relocate failed, could not create a temporary directory"
   exit 1
fi
cat <<EOF >> $tdir/relocate_sdk.sh
#!/bin/bash
PATCHELF=\`which patchelf 2>/dev/null\`

if [ x\$PATCHELF = "x"  ]; then
        echo "SDK could not be relocated. No patchelf found."
        echo "use 'sudo apt install patchelf' on Debian"
        echo "use 'sudo dnf install patchelf' on Red Hat Enterprise Linux"
        exit 1
fi

for link in $abs_symbolic_links; do
        target=$native_sysroot\`readlink \$link\`
        rm -f \$link
        ln -s \$target \$link
done

for exe in $native_executable_files; do
        if [ \`readlink -f \$exe\` == \`readlink -f $dl_path\` ]; then
            echo SKIP \$exe
        else
            \$PATCHELF --set-interpreter $dl_path \$exe
        fi
done

for exe in $native_elf_files; do
        if [ \`readlink -f \$exe\` == \`readlink -f $dl_path\` ]; then
            echo SKIP \$exe
        else
            \$PATCHELF --set-rpath $native_sysroot/usr/lib/x86_64-linux-gnu:$native_sysroot/lib/x86_64-linux-gnu/:$native_sysroot/usr/lib:$native_sysroot/lib \$exe
        fi
done

# TODO: target_executable files do not exist yet,
#       to handle these we would need proper identification
#       of the target interpreter.
#
#       the difference to the native interpreter is, that the
#       target interpreter does not necessarily exist.
#
#       do not skip the interpreter, and do not handle target_executable
#       files yet.
for exe in $target_elf_files; do
        if [ "${target_elfcode}" = "x86-64" -a \`readlink -f \$exe\` == \`readlink -f $dl_path\` ]; then
            echo SKIP \$exe
        else
           \$PATCHELF --set-rpath $native_sysroot/usr/lib/${real_multimach_target_sys}/:$native_sysroot/lib/${real_multimach_target_sys}/:$native_sysroot/usr/lib:$native_sysroot/lib \$exe
        fi
done

for exe in $ascii_so_files; do
	sed -i "s%/usr/%$native_sysroot/usr/%g" \$exe
done
EOF

$SUDO_EXEC mv $tdir/relocate_sdk.sh ${"$"}{env_setup_script%/*}/relocate_sdk.sh
$SUDO_EXEC chmod 755 ${"$"}{env_setup_script%/*}/relocate_sdk.sh
rm -rf $tdir
if [ $relocate = 1 ] ; then
        $SUDO_EXEC ${"$"}{env_setup_script%/*}/relocate_sdk.sh
        if [ $? -ne 0 ]; then
                echo "SDK could not be set up. Relocate script failed. Abort!"
                exit 1
        fi
fi

# delete the relocating script, so that user is forced to re-run the installer
# if he/she wants another location for the sdk
if [ $savescripts = 0 ] ; then
	$SUDO_EXEC rm -f ${"$"}{env_setup_script%/*}/relocate_sdk.py ${"$"}{env_setup_script%/*}/relocate_sdk.sh
fi

echo "SDK has been successfully set up and is ready to be used."
echo "Each time you wish to use the SDK in a new shell session, you need to source the environment setup script e.g."
for env_setup_script in `ls $target_sdk_dir/environment-setup-*`; do
	echo " \$ . $env_setup_script"
done

exit 0

MARKER:
