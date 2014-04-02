
deb:
	dpkg-buildpackage -b -us -uc  --source-option="-I .git"
