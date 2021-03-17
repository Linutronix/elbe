%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

Name:           elbe
Version:        13.2
Release:        1
Summary:        Elbe (Embedded Linux Build Environment)

Group:          Development/Tools
License:        GPLv3
URL:            http://elbe-rfs.org
Source0:        http://elbe-rfs.org/download/elbe-2.0/elbe-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python3-devel
BuildRequires: python3-setuptools
BuildRequires: asciidoc
BuildRequires: xmlto

requires: qemu-kvm, python3-lxml, python3-mako, wget, python3-suds, libvirt-python

%description
ELBE (Embedded Linux Build Environment)
Debian based system to generate root-filesystems for embedded devices.

%prep
%setup -q -n elbe-%{version}

%build
python3 setup.py build

%install
rm -rf $RPM_BUILD_ROOT
python3 setup.py install --skip-build --root $RPM_BUILD_ROOT --install-lib=%{python_sitearch}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc COPYING
%docdir /usr/share/doc/elbe-doc
%docdir /usr/share/man
/usr/share/doc/elbe-doc/*
/usr/share/man/*
%{python_sitearch}/*
/usr/bin/elbe


%changelog
* Mon Nov 09 2016 Manuel Traut <manut@linutronix.de> - 1.9.15-1
- bump to 1.9.15-1
* Mon Nov 07 2016 Manuel Traut <manut@linutronix.de> - 1.9.14-1
- bump to 1.9.14-1
* Mon Oct 25 2016 Manuel Traut <manut@linutronix.de> - 1.9.13-1
- bump to 1.9.13-1
* Mon Oct 17 2016 Manuel Traut <manut@linutronix.de> - 1.9.12-1
- bump to 1.9.12-1
* Mon Sep 19 2016 Manuel Traut <manut@linutronix.de> - 1.9.11-1
- bump to 1.9.11-1
* Fri Sep 16 2016 Manuel Traut <manut@linutronix.de> - 1.9.10-1
- bump to 1.9.10-1
* Wed Feb 10 2016 Torben Hohn <torbenh@linutronix.de> - 1.9.2-1
- bump to 1.9.2-1
* Mon Feb 8 2016 Torben Hohn <torbenh@linutronix.de> - 1.9.1-1
- bump to 1.9.1-1
* Mon Feb 1 2016 Torben Hohn <torbenh@linutronix.de> - 1.9.0-1
- bump to 1.9.0-1
* Tue Jan 26 2016 Torben Hohn <torbenh@linutronix.de> - 1.0-1
- Initial build
