Format: 3.0 (native)
Source: compiz
Binary: compiz, compiz-core, compiz-dev, compiz-gnome, compiz-mate, compiz-plugins-default, compiz-plugins, libdecoration0t64, libdecoration0-dev, libcompizconfig0, libcompizconfig0-dev, python3-compizconfig, compizconfig-settings-manager, compiz-plugins-main, compiz-plugins-main-default, compiz-plugins-main-dev, compiz-plugins-extra
Architecture: any all
Version: 1:0.9.14.2+25.10.20250930-0ubuntu3+unity3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: David Nusinow <dnusinow@debian.org>, Sean Finney <seanius@debian.org>, Cyril Brulebois <kibi@debian.org>
Homepage: https://launchpad.net/compiz
Standards-Version: 3.9.8
Vcs-Browser: https://git.launchpad.net/~compiz-team/compiz?h=master
Vcs-Git: https://git.launchpad.net/~compiz-team/compiz
Build-Depends: cmake (>= 3.17.0), debhelper (>= 9~), dh-python, dh-translations, dpkg-dev (>= 1.22.5), libgtest-dev (>= 1.8.0), libgmock-dev (>= 1.8.0), intltool, libtool, pkg-config (>= 0.29.1), quilt (>= 0.40), libcairo2-dev, libdbus-glib-1-dev, libgl1-mesa-dev (>= 6.5.1) [!armhf !armel] | libgl-dev [!armhf !armel], libegl1-mesa-dev [armhf armel], libgles2-mesa-dev [armhf armel], libboost-dev, libboost-serialization-dev, libglib2.0-dev, libglibmm-2.4-dev, libgtk-3-dev, libice-dev (>= 1:1.0.1), libmetacity-dev (>= 1:3.22.0), libpango1.0-dev, libpng-dev, librsvg2-dev, libsm-dev (>= 1:1.0.1), libwnck-3-dev, libx11-dev, libxcomposite-dev (>= 1:0.3-2), libxext-dev, libxdamage-dev (>= 1:1.0.3), libxfixes-dev (>= 1:4.0.1), libxi-dev, libxinerama-dev, libxml-parser-perl, libxrandr-dev (>= 2:1.1.0.2), libxrender-dev (>= 1:0.9.1), libxcursor-dev, libxml2-dev, libxslt1-dev, xsltproc, libstartup-notification0-dev (>= 0.7), x11proto-gl-dev (>= 1.4.8), libglu1-mesa-dev [!armhf !armel], libjpeg-dev, libnotify-dev (>= 0.7.0), libx11-xcb-dev, libprotobuf-dev, protobuf-compiler, python3-dev, python3-setuptools, cython3, gsettings-desktop-schemas-dev, xserver-xorg-dev (>= 0.7.0)
Package-List:
 compiz deb x11 optional arch=all
 compiz-core deb x11 optional arch=any
 compiz-dev deb x11 optional arch=any
 compiz-gnome deb x11 optional arch=any
 compiz-mate deb x11 optional arch=any
 compiz-plugins deb x11 optional arch=any
 compiz-plugins-default deb x11 optional arch=any
 compiz-plugins-extra deb oldlibs optional arch=all
 compiz-plugins-main deb oldlibs optional arch=all
 compiz-plugins-main-default deb oldlibs optional arch=all
 compiz-plugins-main-dev deb oldlibs optional arch=all
 compizconfig-settings-manager deb x11 optional arch=all
 libcompizconfig0 deb x11 optional arch=any
 libcompizconfig0-dev deb libdevel optional arch=any
 libdecoration0-dev deb libdevel optional arch=any
 libdecoration0t64 deb x11 optional arch=any
 python3-compizconfig deb python optional arch=any
Checksums-Sha1:
 bcde1fd807c8d50cfa1a0f5d56628b4ceb1c3bf5 4123964 compiz_0.9.14.2+25.10.20250930-0ubuntu3+unity3.tar.xz
Checksums-Sha256:
 1fb432404892aeeff6a9b5236fc9f3758df6f48786a63daab0544fa1f9c4fca1 4123964 compiz_0.9.14.2+25.10.20250930-0ubuntu3+unity3.tar.xz
Files:
 1f27a404575e19ef81755f0c425aa57b 4123964 compiz_0.9.14.2+25.10.20250930-0ubuntu3+unity3.tar.xz
Original-Maintainer: Debian X Strike Force <debian-x@lists.debian.org>
