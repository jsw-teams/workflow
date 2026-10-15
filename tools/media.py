"""Fetch explicitly selected ishare assets for local reproduction; no upload key needed."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def target_path(name):
    target = (ROOT / name).resolve()
    if not target.is_relative_to(ROOT) or target == ROOT:
        raise ValueError('Asset path escapes repository')
    return target


def fetch_asset(name, item, videos=False):
    if item['kind'] == 'video' and not videos:
        return 'stream-link-only'
    url = item.get('original_url') or item['url']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'ishare.js.gripe':
        raise ValueError('Unexpected asset origin')
    target = target_path(name)
    if target.exists():
        if item['kind'] == 'image' and hashlib.sha256(target.read_bytes()).hexdigest() != item['source_sha256']:
            raise ValueError('Existing local image hash mismatch: ' + name)
        return 'cached'
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.part')
    if item['kind'] == 'image':
        subprocess.run(['curl', '-fLsS', '--retry', '2', '--max-time', '120', url, '-o', str(partial)], check=True)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != item['source_sha256']:
            partial.unlink(missing_ok=True)
            raise ValueError('Downloaded original image hash mismatch: ' + name)
    else:
        help_text = subprocess.check_output(['ffmpeg', '-hide_banner', '-h', 'demuxer=hls'], text=True, errors='replace')
        hls_options = []
        for option, value in [('allowed_extensions', 'ALL'), ('allowed_segment_extensions', 'ALL'), ('extension_picky', '0')]:
            if '-' + option in help_text:
                hls_options.extend(['-' + option, value])
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *hls_options, '-i', url,
                        '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy', '-f', 'mp4', str(partial)], check=True)
        # Stream delivery is transcoded. Its bytes must never be compared as an exact original.
        derivative = {'source_sha256': item['source_sha256'], 'delivery': url,
                      'download_sha256': hashlib.sha256(partial.read_bytes()).hexdigest(),
                      'exact_original': False}
        target.with_suffix(target.suffix + '.delivery.json').write_text(json.dumps(derivative, indent=2), encoding='utf-8')
    partial.replace(target)
    return 'downloaded'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['list', 'fetch', 'check'])
    p.add_argument('--prefix', required=True, help='Select a module or exact virtual asset path')
    p.add_argument('--videos', action='store_true', help='Also materialize transcoded video delivery copies')
    args = p.parse_args()
    manifest = json.loads((ROOT / 'media.json').read_text(encoding='utf-8'))
    selected = {k: v for k, v in manifest['assets'].items() if k.startswith(args.prefix)}
    if not selected:
        p.error('No assets match this prefix')
    for name, item in selected.items():
        if args.action == 'list':
            print(name, item['share_url'])
        elif args.action == 'fetch':
            print(name, fetch_asset(name, item, args.videos))
        else:
            target = target_path(name)
            if not target.is_file():
                raise SystemExit('Missing local materialization: ' + name)
            if item['kind'] == 'image' and hashlib.sha256(target.read_bytes()).hexdigest() != item['source_sha256']:
                raise SystemExit('Local image hash mismatch: ' + name)
            print(name, 'image hash PASS' if item['kind'] == 'image' else 'delivery copy; original bytes not asserted')


if __name__ == '__main__':
    main()
