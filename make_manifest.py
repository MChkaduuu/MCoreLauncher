#!/usr/bin/env python3
"""
Генератор manifest.json для лаунчера. Запускать НА СЕРВЕРЕ (или там, где лежат файлы).

Ожидаемая структура папки, которая раздаётся по HTTPS (nginx/caddy/GitHub Pages и т.п.):

    /var/www/mythos/
        manifest.json          <- создаётся этим скриптом
        mods/                  <- сюда кладёшь .jar моды (те же, что стоят на сервере; обязательно Fabric API)
        resourcepacks/         <- сюда кладёшь .zip ресурс-паки
        configs/fancymenu/     <- сюда копируешь папку config/fancymenu из своей игры (дизайн FancyMenu);
                                  скрипт сам упакует её в configs/fancymenu.zip

Использование:
    python3 make_manifest.py /var/www/mythos
    python3 make_manifest.py /var/www/mythos --enable "MyPack.zip" --enable "Another.zip"

Если --enable не указан, в игре включаются ВСЕ ресурс-паки из папки (в алфавитном порядке).
Файлы можно хранить отдельно от manifest.json (GitHub Releases, CDN, S3/R2...):
    python3 make_manifest.py ./pack --mods-url https://github.com/USER/REPO/releases/download/v1 \\
                                    --packs-url https://github.com/USER/REPO/releases/download/v1

Лаунчер берёт manifest по ссылке из Config.MANIFEST_URL, например https://example.com/mythos/manifest.json
"""
import argparse, hashlib, json, os, sys, urllib.parse, zipfile


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


def pack_config_dirs(root):
    """Каждую папку root/configs/<имя>/ упаковывает в configs/<имя>.zip (детерминированно: одинаковый sha1,
    пока содержимое не менялось). В архиве пути относительные: customization/..., assets/... и т.д."""
    cfg = os.path.join(root, "configs")
    if not os.path.isdir(cfg):
        return
    for d in sorted(os.listdir(cfg)):
        src = os.path.join(cfg, d)
        if not os.path.isdir(src):
            continue
        files = []
        for base, _, names in os.walk(src):
            for n in names:
                full = os.path.join(base, n)
                files.append((os.path.relpath(full, src).replace(os.sep, "/"), full))
        with zipfile.ZipFile(os.path.join(cfg, d + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
            for rel, full in sorted(files):
                info = zipfile.ZipInfo(rel, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(full, "rb") as f:
                    z.writestr(info, f.read())
        print(f"Упакован конфиг: configs/{d}.zip ({len(files)} файлов)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="папка с mods/ и resourcepacks/")
    ap.add_argument("--enable", action="append", help="какие ресурс-паки включить (порядок = приоритет, последний сверху)")
    ap.add_argument("--mods-url", help="префикс ссылок на моды, если они лежат НЕ рядом с manifest.json "
                                       "(например GitHub Releases: https://github.com/USER/REPO/releases/download/v1)")
    ap.add_argument("--packs-url", help="то же для ресурс-паков")
    ap.add_argument("--configs-url", help="префикс ссылок на конфиг-архивы (если лежат не рядом с manifest.json)")
    a = ap.parse_args()

    manifest = {
        "version": 1,
        "mods": scan(os.path.join(a.root, "mods"), ".jar", a.mods_url),
        "resourcepacks": scan(os.path.join(a.root, "resourcepacks"), ".zip", a.packs_url),
    }
    if a.enable is not None:
        manifest["enable_resourcepacks"] = a.enable

    pack_config_dirs(a.root)
    manifest["configs"] = scan(os.path.join(a.root, "configs"), ".zip", a.configs_url)
    if not manifest["configs"]:
        del manifest["configs"]

    out = os.path.join(a.root, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"OK: {out}  (модов: {len(manifest['mods'])}, ресурс-паков: {len(manifest['resourcepacks'])})")


if __name__ == "__main__":
    sys.exit(main())