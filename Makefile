all:
	dpkg-buildpackage --source-option="-I .git"
	lintian
