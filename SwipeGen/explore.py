from core.phase1_explorer import Phase1Explorer
from core.phase2_swiper import Phase2Swiper
from summary import summary

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("explore.log", encoding="utf-8")
    ]
)

from utils.packages import PACKAGE_ANDROID_WORLD, PACKAGE_NEW, PACKAGE_HOT_GLOBAL, PACKAGE_INSTALLED

for name, pkg in PACKAGE_INSTALLED.items():
    logging.info(f"\n=== [Phase 1] Exploring App: {name} ({pkg}) ===")
    explorer = Phase1Explorer(package_name=pkg, max_depth=2)
    explorer.run_exploration()

    logging.info(f"\n=== [Phase 2] Synthesizing Swipe Data: {name} ({pkg}) ===")
    swiper = Phase2Swiper(package_name=pkg, remote_vlm=True, url="http://localhost:8000")
    swiper.run_synthesis()
    
    logging.info(f"\n=== [Phase 3] Aggregating Dataset Incrementally: {name} ({pkg}) ===")
    summary(target_pkg=pkg)