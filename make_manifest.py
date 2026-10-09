#!/usr/bin/env python3
"""
Генератор manifest.json для лаунчера. Запускать НА СЕРВЕРЕ (или там, где лежат файлы).

Ожидаемая структура папки, которая раздаётся по HTTPS (nginx/caddy/GitHub Pages и т.п.):

    /var/www/mythos/
        manifest.json          <- создаётся этим скриптом
        mods/                  <- сюда кладёшь .jar моды (те же, что стоят на сервере; обязательно Fabric API)
        resourcepacks/         <- сюда кладёшь .zip ресурс-паки

Использование:
    python3 make_manifest.py /var/www/mythos
    python3 make_manifest.py /var/www/mythos --enable "MyPack.zip" --enable "Another.zip"

Если --enable не указан, в игре включаются ВСЕ ресурс-паки из папки (в алфавитном порядке).
Файлы можно хранить отдельно от manifest.json (GitHub Releases, CDN, S3/R2...):
    python3 make_manifest.py ./pack --mods-url https://github.com/USER/REPO/releases/download/v1 \\
                                    --packs-url https://github.com/USER/REPO/releases/download/v1

Лаунчер берёт manifest по ссылке из Config.MANIFEST_URL, например https://example.com/mythos/manifest.json
"""
import argparse, hashlib, json, os, sys, urllib.parse


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(folder, ext, url_prefix=None):
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        p = os.path.join(folder, name)
        if os.path.isfile(p) and name.lower().endswith(ext):
            e = {"name": name, "sha1": sha1(p), "size": os.path.getsize(p)}
            if url_prefix:
                e["url"] = url_prefix.rstrip("/") + "/" + urllib.parse.quote(name)
            out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="папка с mods/ и resourcepacks/")
    ap.add_argument("--enable", action="append", help="какие ресурс-паки включить (порядок = приоритет, последний сверху)")
    ap.add_argument("--mods-url", help="префикс ссылок на моды, если они лежат НЕ рядом с manifest.json "
                                       "(например GitHub Releases: https://github.com/USER/REPO/releases/download/v1)")
    ap.add_argument("--packs-url", help="то же для ресурс-паков")
    a = ap.parse_args()

    manifest = {
        "version": 1,
        "mods": scan(os.path.join(a.root, "mods"), ".jar", a.mods_url),
        "resourcepacks": scan(os.path.join(a.root, "resourcepacks"), ".zip", a.packs_url),
    }
    if a.enable is not None:
        manifest["enable_resourcepacks"] = a.enable

    out = os.path.join(a.root, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"OK: {out}  (модов: {len(manifest['mods'])}, ресурс-паков: {len(manifest['resourcepacks'])})")


if __name__ == "__main__":
    sys.exit(main())
