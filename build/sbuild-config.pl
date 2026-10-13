# UNITY-20260929-016: passed by scripts/build_sbuild.py as SBUILD_CONFIG, read
# after the user's own config (~/.config/sbuild/config.pl). It pins what
# decides the chroot and the apt sources of a build, whatever the user's
# config says; build_sbuild.py then checks the log.
#
# build_sbuild gives sbuild an explicit --chroot=<tarball>, which sbuild never
# replaces; this is a second guard against a chroot sbuild would build itself.
$unshare_mmdebstrap_auto_create = 0;
# No apt sources besides the tarball's snapshot lines and sbuild's own archive
# of the build dependencies (Verifier round 1: a local repository from the
# user's config would have passed).
$extra_repositories = [];
$extra_repository_keys = [];
$apt_allow_unauthenticated = 0;
# No packages besides build_sbuild's own --extra-package copies (Verifier
# round 2: the command line appends to the user's list instead of replacing
# it). The command-line options are applied after this file.
$extra_packages = [];
# apt, the build environment command and bind mounts as sbuild ships them: a
# wrapper or a mount over /etc/apt could add or hide sources.
$apt_get = 'apt-get';
$build_env_cmnd = '';
$unshare_bind_mounts = [];
# No commands that change the chroot or the build around sbuild.
$chroot_setup_script = undef;
$external_commands = {
    "pre-build-commands"            => [],
    "chroot-setup-commands"         => [],
    "chroot-user-setup-commands"    => [],
    "chroot-update-failed-commands" => [],
    "build-deps-failed-commands"    => [],
    "build-failed-commands"         => [],
    "starting-build-commands"       => [],
    "finished-build-commands"       => [],
    "chroot-cleanup-commands"       => [],
    "post-build-commands"           => [],
};
# apt-get update and dist-upgrade against the snapshot in every build: with the
# tarball from the same snapshot they change nothing ("0 upgraded"), and they
# prove the sources in the log.
$apt_update = 1;
$apt_distupgrade = 1;
1;
