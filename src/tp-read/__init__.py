import os
from platformdirs import PlatformDirs

from . import import_files, export

dirs = PlatformDirs("tp-read", "hartpa")
for dir in [dirs.user_config_dir, dirs.user_data_dir]:
    if not os.path.exists(dir):
        os.makedirs(dir)