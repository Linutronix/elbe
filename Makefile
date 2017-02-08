all:
	./test/testdeb.sh
	dpkg-buildpackage
	lintian
	cd contrib/debathena-transform-lighttpd && \
		dpkg-buildpackage -uc -us && \
		lintian && \
		mv ../debathena*.* ../../../
