deb:
	echo "build signed package"
	dpkg-buildpackage --source-option="-I .git"
	lintian

test:
	echo "build unsigned package"
	dpkg-buildpackage -b -us -uc  --source-option="-I .git"
