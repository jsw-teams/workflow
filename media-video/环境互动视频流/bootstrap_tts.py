import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
target=ROOT/'vendor/wangwangit-tts'
if not target.exists():
    target.parent.mkdir(exist_ok=True)
    subprocess.run(['git','clone','https://github.com/wangwangit/tts.git',str(target)],check=True)
subprocess.run(['git','-C',str(target),'checkout','749645c46df7e080561ad0585240f2a29c53e554'],check=True)
print('Pinned upstream MIT speech source prepared in ignored vendor folder.')
