all:
	./test/testdeb.sh
	dpkg-buildpackage --source-option="-I .git"
	lintian
