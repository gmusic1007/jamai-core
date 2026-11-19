# The JamAI apt repository

```bash
curl -fsSL https://apt.gmusicassembly.com/setup.sh | sudo bash
sudo apt install jamai
```

## How it is served

| piece | where |
|---|---|
| the files | the `gh-pages` branch of this repository, written by `build-repo.sh` |
| publishing | `.github/workflows/apt.yml`, at each published release (or run by hand) |
| the host | GitHub Pages, custom domain `apt.gmusicassembly.com` |
| the address | Cloudflare, zone gmusicassembly.com: `apt` is a CNAME to `gmusic1007.github.io`, **proxied** |
| HTTPS | Cloudflare's certificate for `*.gmusicassembly.com`, SSL mode "Full" |
| caching | a Cloudflare cache rule turns caching off for `apt.gmusicassembly.com`, so a new release's index and packages always match |

Why proxied: on 2026-11-19 GitHub had not issued its own certificate for the domain after 15
minutes, so HTTPS failed. Cloudflare already holds a certificate for every name under the domain.
Without the cache rule, Cloudflare could serve a cached `Packages.gz` next to a new `InRelease`,
and apt would refuse the update with a hash mismatch.

## The signing key

`G.Music Assembly (JamAI apt repository)`, fingerprint `53A00775B61CAA93A047C92C1BA4BD935B04BE3C`,
RSA 4096, no expiry.

- The workflow signs with the repository secret `JAMAI_APT_SIGNING_KEY`.
- On Eury, the keyring is `~/.config/jamai/apt-signing` and a private backup is
  `~/.config/jamai/apt-signing/secret-key.asc` (mode 600). Keep a copy outside Eury.
- `setup.sh` checks this fingerprint before it trusts the key it downloads.

To replace the key, every user has to run `setup.sh` again. Do it only if the key is lost or exposed.

## By hand

```bash
packaging/deb/build.sh                                        # dist/jamai_<version>_all.deb
GNUPGHOME=~/.config/jamai/apt-signing packaging/apt/build-repo.sh <gh-pages checkout> dist/jamai_*_all.deb
```
