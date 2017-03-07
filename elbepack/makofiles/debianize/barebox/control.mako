Source: barebox-${p_name}-${k_version}
Section: admin
Priority: optional
Maintainer: ${m_name} <${m_mail}>
Build-Depends: debhelper (>= 9), bc
Standards-Version: 3.8.4
Homepage: http://www.barebox.org/

Package: barebox-image-${p_name}-${k_version}
Provides: barebox-image
Architecture: ${p_arch}
Description: Barebox, version ${p_name} ${k_version}
 This package contains barebox

Package: barebox-tools-${p_name}-${k_version}
Provides: barebox-tools 
Architecture: ${p_arch}
Description: Barebox tools 
 This package provides Barebox Userspace tools
