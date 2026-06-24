import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests


BASE_URL = "https://jjg.spc.org.cn"
REQUEST_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_standard(value: str) -> tuple[str, str]:
    """Parse a standard type and number from a current/legacy URL or identifier."""
    value = value.strip()
    if not value:
        raise ValueError("输入不能为空")

    parsed = urlparse(value)

    # Current format: detail.html?standno=JJF+1070-2023
    standno_values = parse_qs(parsed.query).get("standno")
    if standno_values:
        match = re.fullmatch(
            r"\s*([A-Za-z]{2,5})[\s+]+([0-9][0-9A-Za-z().-]*)\s*",
            standno_values[0],
        )
        if match:
            return match.group(1).upper(), match.group(2)

    # Legacy format: /standard/JJF%25201261.9-2013/
    if parsed.scheme and parsed.path:
        path_part = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        decoded = unquote(unquote(path_part))
        match = re.fullmatch(
            r"\s*([A-Za-z]{2,5})[\s+]+([0-9][0-9A-Za-z().-]*)\s*", decoded
        )
        if match:
            return match.group(1).upper(), match.group(2)

    # Also allow a standard identifier directly, for example JJF 1070-2023.
    if not parsed.scheme:
        match = re.fullmatch(
            r"\s*([A-Za-z]{2,5})[\s+]+([0-9][0-9A-Za-z().-]*)\s*", value
        )
        if match:
            return match.group(1).upper(), match.group(2)

    raise ValueError(
        "无法解析规范编号；请输入 detail.html?standno=... 页面网址、旧版详情网址，"
        "或类似 JJF 1070-2023 的编号"
    )


def input_and_parse_url() -> tuple[str, str, str]:
    while True:
        try:
            raw_value = input(
                "请输入“查看详细”页网址或规范编号，例如：\n"
                "https://jjg.spc.org.cn/resmea/standard/detail.html?standno=JJF+1070-2023\n"
            )
            try:
                std_type, std_no = parse_standard(raw_value)
                return std_type, std_no, raw_value
            except ValueError as exc:
                print(f"输入格式有误：{exc}\n")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit("\n程序已退出")


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
    )
    return session


def _decode_javascript_string(value: str) -> str:
    r"""Decode escapes such as ``\/`` found in JavaScript string literals."""
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value.replace(r"\/", "/")


def extract_reader_args(html: str) -> tuple[str, str]:
    string_value = r'"((?:\\.|[^"\\])*)"'
    enc_match = re.search(r"var\s+enc\s*=\s*" + string_value, html)

    # The old page assigned the value directly to `rc`.  The current page first
    # assigns it to `token` and then runs `var rc = token`.
    token_match = re.search(r"var\s+token\s*=\s*" + string_value, html)
    if token_match is None:
        token_match = re.search(r"var\s+rc\s*=\s*" + string_value, html)

    if enc_match is None or token_match is None:
        raise RuntimeError(
            "在线预览页中没有找到 enc/token 参数，站点页面结构可能再次发生了变化"
        )

    return (
        _decode_javascript_string(enc_match.group(1)),
        _decode_javascript_string(token_match.group(1)),
    )


def get_reader_args(
    session: requests.Session, std_type: str, std_no: str
) -> tuple[str, str, str]:
    response = session.get(
        f"{BASE_URL}/resmea/view/stdonline",
        params={"a100": f"{std_type} {std_no}", "standclass": ""},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    myfoxit, token = extract_reader_args(response.text)
    return myfoxit, token, response.url


def _safe_filename(std_type: str, std_no: str) -> str:
    filename = f"{std_type} {std_no}.pdf"
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def download_standard(
    value: str, output_dir: str | Path = "."
) -> tuple[Path, requests.Response]:
    std_type, std_no = parse_standard(value)
    session = create_session()
    myfoxit, token, referer = get_reader_args(session, std_type, std_no)

    response = session.get(
        f"{BASE_URL}/resmea/view/onlinereading",
        params={"token": token, "Myfoxit": myfoxit},
        headers={"Referer": referer, "myfoxit": myfoxit, "Accept": "application/pdf,*/*"},
        timeout=DOWNLOAD_TIMEOUT,
    )
    response.raise_for_status()

    if b"%PDF-" not in response.content[:1024]:
        content_type = response.headers.get("Content-Type", "未知")
        raise RuntimeError(
            f"下载接口返回的不是 PDF（Content-Type: {content_type}），未写入文件"
        )

    output_path = Path(output_dir).expanduser().resolve() / _safe_filename(
        std_type, std_no
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path, response


def welcome() -> bool:
    print("--------------------程序开始--------------------")
    print("仅供学习参考；产生任何后果由用户承担")
    print("继续使用即代表同意上述声明")
    while True:
        try:
            choice = input("是否同意上述声明？ (y/n) ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if choice in {"y", "n"}:
            return choice == "y"
        print("输入无效，请输入 y 或 n。")


def run_download(value: str, output_dir: str | Path) -> bool:
    start_time = time.time()
    try:
        output_path, response = download_standard(value, output_dir)
    except (ValueError, RuntimeError, requests.RequestException, OSError) as exc:
        logger.error("下载失败：%s", exc)
        return False

    elapsed = time.time() - start_time
    print(
        f"下载成功 | {output_path} | {len(response.content)} 字节 | {elapsed:.2f} 秒"
    )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="国家计量技术规范全文公开系统下载工具"
    )
    parser.add_argument(
        "standard",
        nargs="?",
        help="详情页网址或规范编号，例如 JJF 1070-2023",
    )
    parser.add_argument(
        "-o", "--output-dir", default=".", help="PDF 保存目录（默认：当前目录）"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="同意使用声明并跳过确认提示"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.yes and not welcome():
        print("程序已退出")
        return 0

    if args.standard:
        return 0 if run_download(args.standard, args.output_dir) else 1

    while True:
        _, _, value = input_and_parse_url()
        run_download(value, args.output_dir)
        try:
            choice = input("是否继续下载？ (y/n) ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"
        while choice not in {"y", "n"}:
            choice = input("输入无效，请输入 y 或 n：").strip().lower()
        if choice == "n":
            print("--------------------程序结束--------------------")
            return 0


if __name__ == "__main__":
    sys.exit(main())
