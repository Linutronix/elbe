## This file was copied from
## https://git.yoctoproject.org/poky/tree/meta/classes/toolchain-scripts.bbclass
## ?id=16e22f3e37788afb83044f5089d24187d70094bd
##
## SPDX-License-Identifier: MIT
## SPDX-FileCopyrightText: Richard Purdie <richard.purdie@linuxfoundation.org>
## SPDX-FileCopyrightText: Lianhao Lu <lianhao.lu@intel.com>
## SPDX-FileCopyrightText: Jessica Zhang <jessica.zhang@intel.com>
## SPDX-FileCopyrightText: Richard Purdie <rpurdie@linux.intel.com>
## SPDX-FileCopyrightText: Joshua Lock <joshua.g.lock@intel.com>
## SPDX-FileCopyrightText: Mark Hatle <mark.hatle@windriver.com>
## SPDX-FileCopyrightText: Otavio Salvador <otavio@ossystems.com.br>
## SPDX-FileCopyrightText: Randy Witt <randy.e.witt@linux.intel.com>
## SPDX-FileCopyrightText: Dongxiao Xu <dongxiao.xu@intel.com>
## SPDX-FileCopyrightText: Joshua Lock <josh@linux.intel.com>
## SPDX-FileCopyrightText: Khem Raj <raj.khem@gmail.com>
## SPDX-FileCopyrightText: Robert Yang <liezhi.yang@windriver.com>
## SPDX-FileCopyrightText: Ross Burton <ross.burton@intel.com>
## SPDX-FileCopyrightText: Stephano Cetola <stephano.cetola@linux.intel.com>
## SPDX-FileCopyrightText: Zongchun Yu <b40527@freescale.com>
## SPDX-FileCopyrightText: Andre McCurdy <armccurdy@gmail.com>
## SPDX-FileCopyrightText: Christopher Larson <chris_larson@mentor.com>
## SPDX-FileCopyrightText: Denys Dmytriyenko <denys@ti.com>
## SPDX-FileCopyrightText: Fang Jia <fang.jia@windriver.com>
## SPDX-FileCopyrightText: Jacob Kroon <jacob.kroon@gmail.com>
## SPDX-FileCopyrightText: Jun Zhang <jun.zhang@windriver.com>
## SPDX-FileCopyrightText: Kevin Tian <kevin.tian@intel.com>
## SPDX-FileCopyrightText: Koen Kooi <koen@dominion.thruhere.net>
## SPDX-FileCopyrightText: Laszlo Papp <lpapp@kde.org>
## SPDX-FileCopyrightText: Laurentiu Palcu <laurentiu.palcu@intel.com>
## SPDX-FileCopyrightText: Martin Ertsaas <mertsas@cisco.com>
## SPDX-FileCopyrightText: Nitin A Kamble <nitin.a.kamble@intel.com>
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
## THE SOFTWARE.

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
export GDB=gdb-multiarch
export STRIP=${real_multimach_target_sys}-strip
export RANLIB=${real_multimach_target_sys}-ranlib
export OBJCOPY=${real_multimach_target_sys}-objcopy
export OBJDUMP=${real_multimach_target_sys}-objdump
export AR=${real_multimach_target_sys}-ar
export NM=${real_multimach_target_sys}-nm
export M4=m4
export TARGET_PREFIX=${real_multimach_target_sys}-
export CONFIGURE_FLAGS="--host=${real_multimach_target_sys} --build=${sdk_arch}-linux-gnu --with-libtool-sysroot=$SDKTARGETSYSROOT"
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
