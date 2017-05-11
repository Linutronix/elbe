DISTRO=unstable

all:
	sed -i 's/unstable/$(DISTRO)/' debian/changelog
	./test/testdeb.sh
	dpkg-buildpackage --source-option="-I .git"
	lintian
