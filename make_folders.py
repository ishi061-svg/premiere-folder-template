# Premiere フォルダテンプレート
# ステップ1：画面なしで、template.txt に書いた形のフォルダをまとめて作る
#
# できるもの
#   作る場所\作品名_2026-11-15\01_プロジェクト\バックアップ …（template.txt のとおり）
#   チェックを外した（OFF にした）フォルダは作らない。親を OFF にすると、その中も作らない
#
# 使い方（ステップ1の確認用）
#   python make_folders.py 作品名 作る場所 [--off 03_音声/ナレーション --off 02_映像素材/スマホ素材 ...]

import shutil
import sys
from datetime import date
from pathlib import Path

# exe のときは exe と同じフォルダ、そうでなければこのプログラムと同じフォルダ
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
TEMPLATE_FILE = APP_DIR / "template.txt"  # メモ帳で書き換える template.txt
# exe の中に入れておく、最初の形の template.txt（exe の隣に template.txt がないときに使う）
BUNDLED_TEMPLATE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "template.txt"
INDENT = 2                         # 字下げ1段ぶんの空白の数
BAD_CHARS = '\\/:*?"<>|'           # Windows のフォルダ名に使えない文字
DATE_FORMAT = "%Y-%m-%d"           # 日付の形（2026-01-01）
TITLE_LIMIT = 50                   # 作品名の長さの上限（長すぎると Windows や Premiere で扱いにくい）
# Windows がもともと使っている名前（予約名）。フォルダ名にすると、消したり開いたりしにくくなる
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def find_bad_chars(name):
    """フォルダ名に使えない文字が入っていたら、その文字を返す（なければ空の文字列）"""
    return "".join(sorted(set(c for c in name if c in BAD_CHARS)))


def is_reserved(name):
    """予約名なら True。「NUL.txt」のように「.」のあとに何か付いていても予約名になる"""
    return name.split(".")[0].strip().upper() in RESERVED_NAMES


def parse_template(text):
    """template.txt の中身を読んで、作るフォルダの一覧を返す
    1つのフォルダは「上からの道のり」のタプルで表す。例：("03_音声", "BGM")
    書き方がおかしいときは、何行目がどうおかしいかを書いた ValueError を出す"""
    folders = []
    stack = []  # 今の行より上にある、親フォルダの並び
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue  # 空の行と「#」の行は読みとばす
        if "\t" in line:
            raise ValueError(f"{number}行目：字下げにタブが使われています。空白（スペース）2つで字下げしてください")

        spaces = len(line) - len(line.lstrip(" "))
        if spaces % INDENT != 0:
            raise ValueError(f"{number}行目：字下げの空白は {INDENT} つずつにしてください")
        level = spaces // INDENT
        if level > len(stack):
            raise ValueError(f"{number}行目：1つ上の行より、2段以上深く字下げされています")

        name = line.strip()
        bad = find_bad_chars(name)
        if bad:
            raise ValueError(f"{number}行目：フォルダ名に使えない文字（{bad}）が入っています：{name}")
        if is_reserved(name):
            raise ValueError(f"{number}行目：「{name}」は Windows が使っている名前なので、フォルダ名にできません")
        if name.endswith("."):
            raise ValueError(f"{number}行目：最後が「.」の名前は、Windows が「.」を消してしまうので使えません：{name}")

        stack = stack[:level] + [name]
        path = tuple(stack)
        if path in folders:
            raise ValueError(f"{number}行目：同じ場所に、同じ名前のフォルダが2回書かれています：{name}")
        folders.append(path)
    if not folders:
        raise ValueError("template.txt に、作るフォルダが1つも書かれていません")
    return folders


def prepare_template():
    """template.txt がなければ、最初の形を置く。置けない場所なら、exe の中のものをそのまま読む"""
    if TEMPLATE_FILE.exists() or not BUNDLED_TEMPLATE.exists():
        return TEMPLATE_FILE
    try:
        shutil.copyfile(BUNDLED_TEMPLATE, TEMPLATE_FILE)
        return TEMPLATE_FILE
    except OSError:
        return BUNDLED_TEMPLATE


def load_template(template_file=None):
    """template.txt を読んで、作るフォルダの一覧を返す"""
    template_file = template_file or prepare_template()
    try:
        text = Path(template_file).read_text(encoding="utf-8-sig")  # メモ帳で保存したときに付く印（BOM）も読みとばす
    except FileNotFoundError:
        raise ValueError(f"template.txt が見つかりません：{template_file}")
    return parse_template(text)


def make_top_name(title, day=None):
    """いちばん上のフォルダ名「作品名_2026-11-15」を作る。日付を渡さなければ今日"""
    day = day or date.today().strftime(DATE_FORMAT)
    return f"{title.strip()}_{day}"


def is_off(path, off_paths):
    """そのフォルダ、またはその親のどれかが OFF なら True（親を OFF にすると、中も作らない）"""
    return any(path[:i] in off_paths for i in range(1, len(path) + 1))


def create_folders(base_dir, top_name, folders, off_paths=()):
    """base_dir の中に top_name のフォルダを作り、その中に folders を作る
    off_paths に入っているフォルダ（とその中）は作らない
    作ったいちばん上のフォルダの場所を返す。うまくいかないときは、理由を書いた RuntimeError を出す"""
    off_paths = set(off_paths)
    base_dir = Path(base_dir)

    bad = find_bad_chars(top_name)
    if bad:
        raise RuntimeError(f"作品名に、フォルダ名に使えない文字（{bad}）が入っています")
    if not base_dir.is_dir():
        raise RuntimeError(f"作る場所が見つかりません：{base_dir}")

    top = base_dir / top_name
    if top.exists():
        # 中に足したり上書きしたりはせず、何も作らずに止める
        raise RuntimeError(f"同じ名前のフォルダがすでにあります：{top}")

    targets = [p for p in folders if not is_off(p, off_paths)]
    try:
        top.mkdir()
    except OSError as error:  # 書き込めない場所など
        raise RuntimeError(f"フォルダを作れませんでした。この場所には書き込めないようです：{base_dir}（{error.strerror}）")

    try:
        for path in targets:
            top.joinpath(*path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        # 途中で失敗したら、今回作った空のフォルダを片付ける（ファイルが入っているフォルダは消さない）
        remove_empty_folders(top)
        raise RuntimeError(f"フォルダを作る途中で失敗しました（{error.strerror}）：{error.filename}")
    return top


def remove_empty_folders(top):
    """top とその中の、空のフォルダだけを消す（下の階層から順に。ファイルが入っていれば残る）"""
    for folder in sorted([p for p in top.rglob("*") if p.is_dir()] + [top], key=lambda p: len(p.parts), reverse=True):
        try:
            folder.rmdir()  # rmdir は、空のフォルダしか消せない
        except OSError:
            pass


def main():
    args = sys.argv[1:]
    off_paths = set()
    rest = []
    while args:
        a = args.pop(0)
        if a == "--off" and args:
            off_paths.add(tuple(args.pop(0).split("/")))
        else:
            rest.append(a)
    if len(rest) != 2:
        print("使い方：python make_folders.py 作品名 作る場所 [--off 03_音声/ナレーション ...]")
        return 1

    title, base_dir = rest
    if len(title.strip()) > TITLE_LIMIT:
        print(f"作品名は {TITLE_LIMIT} 文字までにしてください")
        return 1
    try:
        folders = load_template()
        top = create_folders(base_dir, make_top_name(title), folders, off_paths)
    except (ValueError, RuntimeError) as error:
        print(error)
        return 1
    print(f"できました：{top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
