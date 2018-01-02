# This file was copied from http://git.yoctoproject.org/git/poky
#                           16e22f3e37788afb83044f5089d24187d70094bd
#
# origin location of the file is: 'meta/classes/toolchain-scripts.bbclass'
#
# known authors of the origin file are:
#
# Richard Purdie <richard.purdie@linuxfoundation.org>
# Lianhao Lu <lianhao.lu@intel.com>
# Jessica Zhang <jessica.zhang@intel.com>
# Richard Purdie <rpurdie@linux.intel.com>
# Joshua Lock <joshua.g.lock@intel.com>
# Mark Hatle <mark.hatle@windriver.com>
# Otavio Salvador <otavio@ossystems.com.br>
# Randy Witt <randy.e.witt@linux.intel.com>
# Dongxiao Xu <dongxiao.xu@intel.com>
# Joshua Lock <josh@linux.intel.com>
# Khem Raj <raj.khem@gmail.com>
# Robert Yang <liezhi.yang@windriver.com>
# Ross Burton <ross.burton@intel.com>
# Stephano Cetola <stephano.cetola@linux.intel.com>
# Zongchun Yu <b40527@freescale.com>
# Andre McCurdy <armccurdy@gmail.com>
# Christopher Larson <chris_larson@mentor.com>
# Denys Dmytriyenko <denys@ti.com>
# Fang Jia <fang.jia@windriver.com>
# Jacob Kroon <jacob.kroon@gmail.com>
# Jun Zhang <jun.zhang@windriver.com>
# Kevin Tian <kevin.tian@intel.com>
# Koen Kooi <koen@dominion.thruhere.net>
# Laszlo Papp <lpapp@kde.org>
# Laurentiu Palcu <laurentiu.palcu@intel.com>
# Martin Ertsaas <mertsas@cisco.com>
# Nitin A Kamble <nitin.a.kamble@intel.com>
#
# The 'meta' folder of the origin repo contains a
# COPYING.GPLv2 and COPYING.MIT file.

# Check for LD_LIBRARY_PATH being set, which can break SDK and generally is a bad practice
# http://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html#AEN80
# http://xahlee.info/UnixResource_dir/_/ldpath.html
# Only disable this check if you are absolutely know what you are doing!
if [ ! -z "$LD_LIBRARY_PATH" ]; then
    echo "Your environment is misconfigured, you probably need to 'unset LD_LIBRARY_PATH'"
    echo "but please check why this was set in the first place and that it's safe to unset."
    echo "The SDK will not operate correctly in most cases when LD_LIBRARY_PATH is set."
    echo "For more references see:"
    echo "  http://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html#AEN80"
    echo "  http://xahlee.info/UnixResource_dir/_/ldpath.html"
    return 1
fi
export SDKTARGETSYSROOT="${sdk_path}/sysroots/target"
export PATH="${sdk_path}/sysroots/host/usr/bin:${sdk_path}/sysroots/host/usr/sbin:${sdk_path}/sysroots/host/bin:${sdk_path}/sysroots/host/sbin:$PATH"
export PKG_CONFIG_SYSROOT_DIR=$SDKTARGETSYSROOT
export PKG_CONFIG_PATH=$SDKTARGETSYSROOT/usr/lib/${real_multimach_target_sys}/pkgconfig
export OECORE_NATIVE_SYSROOT="${sdk_path}/sysroots/host"
export OECORE_TARGET_SYSROOT="$SDKTARGETSYSROOT"
export CC="${real_multimach_target_sys}-gcc --sysroot=$SDKTARGETSYSROOT"
export CXX="${real_multimach_target_sys}-g++ --sysroot=$SDKTARGETSYSROOT"
export CPP="${real_multimach_target_sys}-gcc -E --sysroot=$SDKTARGETSYSROOT"
export AS="${real_multimach_target_sys}-as"
export LD="${real_multimach_target_sys}-ld --sysroot=$SDKTARGETSYSROOT"
export GDB=${real_multimach_target_sys}-gdb
export STRIP=${real_multimach_target_sys}-strip
export RANLIB=${real_multimach_target_sys}-ranlib
export OBJCOPY=${real_multimach_target_sys}-objcopy
export OBJDUMP=${real_multimach_target_sys}-objdump
export AR=${real_multimach_target_sys}-ar
export NM=${real_multimach_target_sys}-nm
export M4=m4
export TARGET_PREFIX=${real_multimach_target_sys}-
export CONFIGURE_FLAGS="--target=${sdk_arch}-linux --host=${real_multimach_target_sys} --build=${sdk_arch}-linux --with-libtool-sysroot=$SDKTARGETSYSROOT"
export CFLAGS=" -O2 -pipe -g -feliminate-unused-debug-types "
export CXXFLAGS=" -O2 -pipe -g -feliminate-unused-debug-types "
export LDFLAGS="-Wl,-O1 -Wl,--hash-style=gnu -Wl,--as-needed"
export CPPFLAGS=""
export KCFLAGS="--sysroot=$SDKTARGETSYSROOT"
export OECORE_DISTRO_VERSION="${sdk_version}"
export OECORE_SDK_VERSION="${sdk_version}"
export ARCH=x86
export CROSS_COMPILE=${real_multimach_target_sys}-

# Append environment subscripts
if [ -d "$OECORE_TARGET_SYSROOT/environment-setup.d" ]; then
    for envfile in $OECORE_TARGET_SYSROOT/environment-setup.d/*.sh; do
      . $envfile
    done
fi
if [ -d "$OECORE_NATIVE_SYSROOT/environment-setup.d" ]; then
    for envfile in $OECORE_NATIVE_SYSROOT/environment-setup.d/*.sh; do
      . $envfile
    done
fi
