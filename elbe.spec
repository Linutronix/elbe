%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

Name:           elbe
Version:        1.9.0
Release:        1
Summary:        Elbe (Embedded Linux Build Environment)

Group:          Development/Tools
License:        GPLv3
URL:            http://elbe-rfs.org
Source0:        http://elbe-rfs.org/download/elbe-2.0/elbe-1.9.0.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python-devel
BuildRequires: python-setuptools
BuildRequires: asciidoc
BuildRequires: xmlto

requires: qemu-kvm, python-lxml, tmux, python-mako, wget, python-suds

%description
ELBE (Embedded Linux Build Environment)
Debian based system to generate root-filesystems for embedded devices.

%prep
%setup -q -n elbe-1.9.0

%build
python setup.py build

%install
rm -rf $RPM_BUILD_ROOT
python setup.py install --skip-build --root $RPM_BUILD_ROOT --install-lib=%{python_sitearch}

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
* Mon Feb 1 2016 Torben Hohn <torbenh@linutronix.de> - 1.9.0-1 
- Initial build
* Tue Jan 26 2016 Torben Hohn <torbenh@linutronix.de> - 1.0-1 
- Initial build
