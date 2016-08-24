all:
	./test/testdeb.sh
	dpkg-buildpackage --source-option="-I .git"
	lintian
	cd contrib/debathena-transform-lighttpd && \
		dpkg-buildpackage -uc -us && \
		lintian && \
		mv ../debathena*.* ../../../
