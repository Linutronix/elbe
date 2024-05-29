==================
ELBE in a nutshell
==================

This article describes why the ELBE project was born.

early embedded Linux devices
============================

Well, first we should look at embedded devices to see what they used to
look like and how some of them look like today.

The first devices, that were initially called embedded Linux, had about
4MiB flash and around 16MiB of RAM. With these constrains in mind people
started to hack a root file system for their devices. If they had bad
luck you had to start with building a cross toolchain first.

Once that part was over you could focus on the user land. Busybox is a
good tool to start with since it contains most of the required programs
in a small single binary. Those programs and a few configurations files
on top and you were done. Maybe you had to compile your “added value”
binary or something else that was not part of busybox but that was it.

Cross-build Toolkits
====================

Now sum up the single steps which were required to create a root file
from scratch and create a tool to ease your life. This is when tools
like OpenEmbedded, EDLK were born. Those tools are still good as long as
they are well maintained. They aren’t just projects that are that small
these days. A lot of them are getting very complex. This includes
hardware that has much more RAM and a GiBs of NAND flash if not replaced
by a disk or mmc card and the software, that is used, is more extensive.

Rootfilesystems are getting bigger and bigger
=============================================

A lot of libraries are used to ease the development of a system. A
toolkit for GUI development, several libraries for multimedia support
just to name a few.

Depending on the build environment that is used, it is more or less
difficult to add a package that is not yet included. It depends on the
scripting language that is used, the format keeping the build
instructions and the user’s ability to understand it and make changes.

Adding Debuging Tools is not that easy
======================================

Adding a debug version of a package to the root file system means a
rebuild or restart of the build process to create this piece of the
rootfile system assuming that a debug version can be selected (and not
added to the build process). Even then the debug version isn’t installed
in a jiffy.

There is usually one person in charge of the root file system and a few
others that are developing the application or a component of the
application. One of the application developers has a problem and wants
just to install a debug version of the library in question or replace it
with a later version of it or a substitute library just to see if his
problem goes away or not. He doesn’t necessarily know how to handle the
build environment to make such changes. So he has to ask the person in
charge of the root filesystem to make this change and send him the new
filesystem.

The application developer never did this kind of work because the Linux
distribution on his desktop computer takes care of these things for him.
The same distribution runs a test suite (if available) of the package
after it has been built to spot problems in the compiled binaries which
can’t be run if the package is cross compiled.

No Bugtracking Informations available
=====================================

Another missing feature is the bug tracking against all packages in the
root file system including security updates. This can be a full time job
for one person even just by looking after 10 packages with a reasonable
size. So why try to do a lot of work alone while this work is already
done by large communities around Linux distribution like Debian?

Debian for embedded?
====================

Instead of doing the work again we tried to figure out how Debian could
be reused in a way that will fulfill our needs.

Continue reading :doc:`elbe:article-elbeoverview-en`.
