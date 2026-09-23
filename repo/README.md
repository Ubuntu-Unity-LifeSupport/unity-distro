# Local apt repository

`aptly` on builder, published over the host-only network so target installs our
packages with `apt` rather than by hand.

## Layout

| | |
|---|---|
| aptly root | `/srv/aptly` - deliberately not under `$HOME`, so nginx can read it without loosening permissions on the home directory |
| config | `~/.aptly.conf` |
| repo name | `unity-resolute`, distribution `resolute`, component `main`, amd64 |
| published tree | `/srv/aptly/public` |
| served at | `http://192.168.56.10:8080/` |
| signing key | `7BF3F77FC27B152C`, "unity-distro archive signing key", no passphrase |
| public key | `http://192.168.56.10:8080/unity-distro-archive.asc` |

nginx listens on `192.168.56.10:8080` only - the host-only address, never
`0.0.0.0`. The repository is not reachable from the NAT interface; verified
with `curl http://10.0.2.15:8080/`, which refuses to connect.

## Adding packages

```
aptly repo add unity-resolute path/to/*.deb
aptly publish update -gpg-key=7BF3F77FC27B152C -batch resolute
```

`publish update` refreshes an existing publication; `publish repo` is only for
the first time.

## What goes in, and what does not

Only packages whose version is genuinely higher than the archive's, or which
the archive does not have at all.

**Never publish a package at the same version as the archive with different
contents.** A version string is supposed to identify the bits. Two different
builds sharing one version means whoever installs from us gets something
different from whoever installs from Ubuntu, with nothing to tell them apart.

So the repository holds only what the archive does not: `nux` 0ubuntu13 (a
revision the archive does not carry), and packages with our own changes under a
`+unityN` suffix - `light-locker`, `unity` - plus `unity-gtk4-menu`, which is
ours outright. A plain rebuild of an archive version never goes in: it would be
indistinguishable from the archive's.

## Client setup (target)

Drop the key in `/etc/apt/keyrings/` and write
`/etc/apt/sources.list.d/unity-distro.sources`:

```
Types: deb
URIs: http://192.168.56.10:8080/
Suites: resolute
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/unity-distro.asc
```

Copy the key with `scp`, not `curl` - **curl is not installed on target**. A
pipeline such as `curl ... | sudo tee keyring.asc` silently writes an empty file
and still reports success, and apt then fails with `NO_PUBKEY`, which points
nowhere near the real cause.

## Upgrading a single package on target

```
sudo apt-get install --only-upgrade libnux-4.0-0 libnux-4.0-common
```

Use `--only-upgrade`, not `apt-get upgrade`. Target carries several hundred
pending updates; a bare `upgrade` pulls all of them and quietly turns a
one-package test into a full system update.
