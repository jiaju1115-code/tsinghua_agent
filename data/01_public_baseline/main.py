from __future__ import annotations

import sys
import argparse
from pathlib import Path
import yaml

from crawler.runner import Crawler
from utils.paths import PROJECT_ROOT, ensure_directories

def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f: config=yaml.safe_load(f)
    configured=Path(config.get("project_root",PROJECT_ROOT))
    if configured.resolve()!=PROJECT_ROOT.resolve():
        raise ValueError(f"project_root 必须是 {PROJECT_ROOT}")
    return config

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="清华校园 Raw Knowledge Dataset 采集器")
    parser.add_argument("mode",nargs="?",choices=("public","portal","all"),help="public=公开网页；portal=认证门户；all=依次运行（不默认执行）")
    args=parser.parse_args(argv)
    if not args.mode:
        parser.print_help();return 0
    ensure_directories()
    config=load_config(PROJECT_ROOT/"config.yaml")
    if args.mode in ("public","all"):Crawler(config,PROJECT_ROOT).run()
    if args.mode in ("portal","all"):
        from portal.runner import PortalCrawler
        PortalCrawler(config,PROJECT_ROOT).run()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
