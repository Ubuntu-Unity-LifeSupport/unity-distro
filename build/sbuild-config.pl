# UNITY-20260929-016: passed by scripts/build_sbuild.py as SBUILD_CONFIG, read
# after the user's own config. build_sbuild gives sbuild an explicit
# --chroot=<tarball>, which sbuild never replaces; this is a second guard
# against a chroot sbuild would build on its own.
$unshare_mmdebstrap_auto_create = 0;
1;
