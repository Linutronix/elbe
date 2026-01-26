==================
ELBE in a nutshell
==================

To understand why the ELBE project was born, we first need to take a look
at the early days of embedded Linux devices and how they evolved.

Early Embedded Linux Devices
============================

The first devices, that were initially called embedded Linux, had about
4MiB flash and around 16MiB of RAM. With these constrains in mind people
started to hack a root file system for their devices. If they had bad
luck you had to start with building a cross toolchain first.

Once that part was completed the focus shifted to the userland. BusyBox is
a good starting as it provided ost of the required programs in a small single
binary. From there, developers could add a few configuration files and any
custom binaries they needed. Once this was done, the system was ready for
deployment.

The rise of Cross-Build Toolkits
================================

Now sum up the single steps which were required to create a root file
from scratch and create a tool to ease your life. This is when tools
like OpenEmbedded, EDLK were born. Those tools are still good as long as
they are well maintained. They aren’t just simple projects anymore, a lot
of them are getting very complex.

Also today embedded devices often have much more RAM and storage, such
as GiBs of NAND flash or even entire disk drives or MMC cards. The
software for these devices has grown more extensive as well, adding layers
of complexity.

Rootfilesystems are getting bigger and bigger
=============================================

As embedded Linux systems grew more powerful, so did the size and
complexity of their root filesystems. A lot of libraries are used to
ease the development of a system. A toolkit for GUI development, several
libraries for multimedia support just to name a few.

Depending on the build environment that is used, it is more or less
difficult to add a package that is not yet included. It depends on the
scripting language that is used, the format keeping the build
instructions and the user’s ability to understand it and make changes.

Adding Debugging Tools is not that easy
======================================

Adding a debug version of a package to the root file system means a
rebuild or restart of the build process to create this piece of the
rootfile system assuming that a debug version can be selected (and not
added to the build process). Even then the debug version isn’t installed
in a jiffy.

There is usually one person in charge of the root filesystem and multiple
application developers working on various parts of the system.
If one of the application developers has a problem and wants just to
install a debug version of a library in or replace it with an updated
version or use a substitute library just to see if his problem goes away
or not. He may not be familiar with the build environment, so he has to ask
the person in charge of the root filesystem to make this change and provide
him the new filesystem.

This problem highlights a key difference between desktop Linux development
and embedded systems development: on a desktop, Linux distributions handle
\package management and dependency resolution automatically, often with
built-in debugging tools. This isn't the case for embedded systems, where
cross-compiling complicates these processes.

Lack of Bugtracking Information
===============================

Another missing feature is the bug tracking against all packages in the
root file system including security updates. This can be a full time job
for one person even just by looking after 10 packages with a reasonable
size. Instead of reinventing the wheel and doing all of this work manually,
why not use the existing work done by larger communities around Linux
distributions, such as Debian? These communities already handle bug
tracking, security updates, and package management, which can
significantly simplify embedded Linux development.

Debian for embedded?
====================

So instead of doing the work again we tried to figure out how Debian could
be reused in a way that will fulfill our needs.

Continue reading :doc:`elbe:article-elbeoverview-en`.
