from __future__ import annotations

import getpass
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.security import hash_password  # noqa: E402


def main() -> None:
    password = getpass.getpass("请输入要设置的系统密码：")
    confirm = getpass.getpass("请再次输入系统密码：")
    if password != confirm:
        raise SystemExit("两次输入的密码不一致")
    if not password:
        raise SystemExit("密码不能为空")
    print(hash_password(password))


if __name__ == "__main__":
    main()

