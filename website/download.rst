Downloads
#########

The current elbe version is |version| .

There are several ways to install a binary version of elbe.

The easiest way is to install the Debian packages via apt.

Debian Binary Packages
======================

The recommended way to use ELBE is running it on a Debian PC.
Linutronix provides a signed repository that can be included in apt.

Debian bookworm or later
------------------------

.. code-block:: bash

    su -
    apt install elbe-archive-keyring
    echo "deb [signed-by=/usr/share/keyrings/elbe-archive-keyring.gpg] http://debian.linutronix.de/elbe bookworm main" >> /etc/apt/sources.list
    apt update
    apt install elbe

Debian buster or bullseye
-------------------------

.. code-block:: bash

    su -
    source /etc/os-release
    apt install wget
    wget -O /usr/share/keyrings/elbe-archive-keyring.gpg http://debian.linutronix.de/elbe/elbe-repo.pub.gpg
    echo "deb [signed-by=/usr/share/keyrings/elbe-archive-keyring.gpg] http://debian.linutronix.de/elbe $VERSION_CODENAME main" >> /etc/apt/sources.list
    apt update
    apt install elbe
