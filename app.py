# Premiere フォルダテンプレート
# ステップ2：画面（GUI）。作品名・日付・作る場所を決めて、ボタン1つでフォルダをまとめて作る
#
# 使い方
#   python app.py
#
# 前回選んだ「作る場所」と、チェックの ON・OFF は settings.json に覚えておく

import json
import os
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, font, ttk

from make_folders import (APP_DIR, DATE_FORMAT, TITLE_LIMIT, create_folders, find_bad_chars, is_off,
                          load_template, make_top_name)

SETTINGS_FILE = APP_DIR / "settings.json"  # 前回の場所とチェックを覚えておくファイル
FONT_NAME = "Yu Gothic UI"
FONT = (FONT_NAME, 10)
INDENT_PX = 22  # 一覧で、1段ぶん右へずらす幅

# ── 色（Premiere Pro に近い、暗い画面と紫のアクセント） ──
BG = "#1d1d1f"           # 画面のいちばん奥
CARD = "#28282b"         # 区切りの箱（カード）
FIELD = "#161618"        # 入力欄の中
LINE = "#3a3a3f"         # 枠線
TEXT = "#ececf1"         # ふつうの文字
SUB = "#9d9daa"          # 説明などの薄い文字
DIM = "#5c5c66"          # 押せないときの文字
ACCENT = "#7d78ff"       # 紫（Premiere のロゴに近い色）
ACCENT_HOVER = "#9490ff"
ACCENT_PRESS = "#6762e6"
RED = "#ff7a7a"
GREEN = "#6fd99a"


def load_settings():
    """前回の設定を読む。なかったり壊れていたり、中身の形がおかしかったりしたら、その部分は使わない"""
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    settings = {}
    if isinstance(data.get("base_dir"), str):
        settings["base_dir"] = data["base_dir"]
    if isinstance(data.get("off"), list):
        settings["off"] = [p for p in data["off"] if isinstance(p, str)]
    return settings


def shorten_head(text, max_px, fnt):
    """表示しきれない長い文字は、頭を「…」にして後ろを見せる（パスは後ろのほうが大事なので）"""
    if fnt.measure(text) <= max_px:
        return text
    while text and fnt.measure("…" + text) > max_px:
        text = text[1:]
    return "…" + text


def save_settings(settings):
    """設定を保存する。保存できなくても、アプリは止めない"""
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def dark_title_bar(root):
    """Windows のタイトルバーも暗い色にする（できない Windows では何もしない）"""
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


def check_image(root, fill, border, mark=None, size=16):
    """チェックボックスの印の絵を描く（角の丸い四角。mark があれば中にチェックの線を引く）"""
    # 右に 7px の透明なすき間を足して、印と文字の間をあける
    img = tk.PhotoImage(master=root, width=size + 7, height=size)
    last = size - 1
    for y in range(size):
        for x in range(size):
            corner = (x in (0, last)) and (y in (0, last))
            if corner:
                continue  # 四すみは塗らずに、角を丸く見せる
            edge = x in (0, last) or y in (0, last)
            img.put(border if edge else fill, (x, y))
    if mark:
        # チェックの線：左下へ下りて、右上へ上がる（太さ2）
        points = [(4, 8), (5, 9), (6, 10), (7, 11), (8, 10), (9, 9), (10, 8), (11, 7), (12, 6), (13, 5)]
        for x, y in points:
            img.put(mark, (x, y))
            img.put(mark, (x, y - 1))
    return img


def setup_style(root):
    """画面全体の色と文字をそろえる"""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")  # 色を自由に変えられる見た目
    style.configure(".", font=FONT, background=BG, foreground=TEXT, bordercolor=LINE,
                    lightcolor=LINE, darkcolor=LINE, troughcolor=FIELD, focuscolor=ACCENT)

    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Title.TLabel", font=(FONT_NAME, 15, "bold"))
    style.configure("Lead.TLabel", foreground=SUB)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("CardSub.TLabel", background=CARD, foreground=SUB)
    style.configure("Head.TLabel", background=CARD, foreground=TEXT, font=(FONT_NAME, 11, "bold"))
    style.configure("Badge.TLabel", background=CARD, foreground=ACCENT, font=(FONT_NAME, 10, "bold"))

    # 入力欄
    style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT,
                    bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD, padding=(8, 5))
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    # チェックボックス（印は、角の丸い四角とチェックの絵を自分で描いて使う）
    images = {
        "off": check_image(root, fill=FIELD, border="#6a6a75"),
        "on": check_image(root, fill=ACCENT, border=ACCENT, mark="white"),
        "off_dis": check_image(root, fill=CARD, border="#45454c"),
        "on_dis": check_image(root, fill="#45454c", border="#45454c", mark="#8a8a94"),
    }
    root._check_images = images  # 絵が消えないように持っておく
    style.element_create("Round.indicator", "image", images["off"],
                         ("disabled", "selected", images["on_dis"]), ("disabled", images["off_dis"]),
                         ("selected", images["on"]), sticky="w")
    check_layout = [("Checkbutton.padding", {"sticky": "nswe", "children": [
        ("Round.indicator", {"side": "left", "sticky": ""}),
        ("Checkbutton.label", {"side": "left", "sticky": "nswe"})]})]
    for name in ("TCheckbutton", "Top.TCheckbutton"):
        style.layout(name, check_layout)
        style.configure(name, background=CARD, foreground=TEXT, padding=(2, 3), focuscolor=CARD)
        style.map(name, background=[("active", CARD)], foreground=[("disabled", DIM)])
    style.configure("Top.TCheckbutton", font=(FONT_NAME, 10, "bold"))

    # ふつうのボタン（場所を選ぶ・フォルダを開く）
    style.configure("TButton", background=CARD, foreground=TEXT, bordercolor=LINE,
                    lightcolor=CARD, darkcolor=CARD, padding=(12, 5))
    style.map("TButton",
              background=[("pressed", "#202023"), ("active", "#333338")],
              lightcolor=[("active", "#333338")], darkcolor=[("active", "#333338")],
              bordercolor=[("focus", ACCENT)])
    style.configure("Ghost.TButton", background=BG, lightcolor=BG, darkcolor=BG)

    # 大きな紫のボタン（フォルダを作る）
    style.configure("Big.TButton", font=(FONT_NAME, 12, "bold"), padding=(20, 10),
                    background=ACCENT, foreground="white", bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT)
    style.map("Big.TButton",
              background=[("disabled", "#34343a"), ("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
              foreground=[("disabled", DIM)],
              bordercolor=[("disabled", "#34343a"), ("focus", "white")],
              lightcolor=[("disabled", "#34343a"), ("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
              darkcolor=[("disabled", "#34343a"), ("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)])


def split_two_columns(folders):
    """一覧を左右2列に分ける。いちばん上の段のフォルダ単位で分け、左右の行数がなるべくそろう場所で切る"""
    starts = [i for i, p in enumerate(folders) if len(p) == 1] + [len(folders)]
    best = len(folders)
    for i in starts:
        if max(i, len(folders) - i) < max(best, len(folders) - best):
            best = i
    return folders[:best], folders[best:]


class App:
    def __init__(self, root, folders):
        self.root = root
        self.folders = folders
        self.settings = load_settings()
        self.created = None  # 最後に作ったフォルダの場所

        root.title("Premiere フォルダテンプレート")
        root.resizable(False, False)
        setup_style(root)

        main = ttk.Frame(root, padding=(22, 20, 22, 20))
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)

        # ── 見出し ──
        ttk.Label(main, text="Premiere フォルダテンプレート", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(main, text="作品名と日付を入れて、編集用のフォルダをまとめて作ります",
                  style="Lead.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 14))

        # ── 作品名・日付・作る場所（カード） ──
        form = ttk.Frame(main, style="Card.TFrame", padding=(16, 14))
        form.grid(row=2, column=0, sticky="we")
        form.columnconfigure(1, weight=1, minsize=300)  # 場所の長さで画面の幅が変わらないように

        self.title_var = tk.StringVar()
        self.day_var = tk.StringVar(value=date.today().strftime(DATE_FORMAT))
        self.base_var = tk.StringVar(value=self.settings.get("base_dir", ""))

        ttk.Label(form, text="作品名", style="CardSub.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=5)
        title_entry = ttk.Entry(form, textvariable=self.title_var)
        title_entry.grid(row=0, column=1, columnspan=2, sticky="we", pady=5)

        ttk.Label(form, text="日付", style="CardSub.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=5)
        ttk.Entry(form, textvariable=self.day_var, width=12).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(form, text="作る場所", style="CardSub.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=5)
        self.base_label = ttk.Label(form, style="Card.TLabel")
        self.label_font = font.Font(font=FONT)
        self.base_max_px = 300  # 場所を表示する欄の幅（これより長い場所は頭を「…」にする）
        self.base_label.grid(row=2, column=1, sticky="w", pady=5)
        ttk.Button(form, text="場所を選ぶ", command=self.choose_base).grid(row=2, column=2, sticky="e", padx=(10, 0))

        # ── 作るフォルダの一覧（カード、2列） ──
        box = ttk.Frame(main, style="Card.TFrame", padding=(16, 12, 16, 14))
        box.grid(row=3, column=0, sticky="we", pady=(12, 0))
        box.columnconfigure((0, 1), weight=1, uniform="col")

        head = ttk.Frame(box, style="Card.TFrame")
        head.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 2))
        ttk.Label(head, text="作るフォルダ", style="Head.TLabel").pack(side="left")
        self.count_label = ttk.Label(head, style="Badge.TLabel")
        self.count_label.pack(side="right")
        ttk.Label(box, text="チェックを外したフォルダは作りません", style="CardSub.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        saved_off = {tuple(p.split("/")) for p in self.settings.get("off", [])}
        self.vars = {}    # フォルダ → チェックの ON・OFF
        self.checks = {}  # フォルダ → チェックボックスの部品
        for col, part in enumerate(split_two_columns(folders)):
            column = ttk.Frame(box, style="Card.TFrame")
            column.grid(row=2, column=col, sticky="nw", padx=(0, 16) if col == 0 else 0)
            for i, path in enumerate(part):
                var = tk.BooleanVar(value=path not in saved_off)
                check = ttk.Checkbutton(column, text=path[-1], variable=var,
                                        style="Top.TCheckbutton" if len(path) == 1 else "TCheckbutton",
                                        command=lambda p=path: self.on_check(p))
                top_gap = 8 if len(path) == 1 and i > 0 else 0  # 大きな区切りの前に少しすき間
                check.grid(row=i, column=0, sticky="w", padx=((len(path) - 1) * INDENT_PX, 0), pady=(top_gap, 0))
                self.vars[path] = var
                self.checks[path] = check
        self.refresh_checks()

        # ── できあがりの名前と、作るボタン ──
        self.preview = ttk.Label(main, foreground=SUB)
        self.preview.grid(row=4, column=0, sticky="w", pady=(16, 8))

        buttons = ttk.Frame(main)
        buttons.grid(row=5, column=0, sticky="we")
        buttons.columnconfigure(0, weight=1)
        self.make_button = ttk.Button(buttons, text="フォルダを作る", style="Big.TButton", command=self.make)
        self.make_button.grid(row=0, column=0, sticky="we")
        self.open_button = ttk.Button(buttons, text="フォルダを開く", command=self.open_created)
        # 「フォルダを開く」は、作ったあとにだけ出す

        self.message = ttk.Label(main, wraplength=500, justify="left")
        self.message.grid(row=6, column=0, sticky="w", pady=(10, 0))

        for var in (self.title_var, self.day_var):
            var.trace_add("write", lambda *_: self.update_view())
        self.update_view()
        dark_title_bar(root)
        title_entry.focus_set()

    # ── チェックの動き ──
    def on_check(self, path):
        """親のチェックを変えたら、中のフォルダも同じにそろえる"""
        value = self.vars[path].get()
        for p in self.folders:
            if len(p) > len(path) and p[:len(path)] == path:
                self.vars[p].set(value)
        self.refresh_checks()
        self.save()
        self.update_view()

    def refresh_checks(self):
        """親が OFF のフォルダは、押せないように薄くする"""
        for path, check in self.checks.items():
            parent_off = any(not self.vars[path[:i]].get() for i in range(1, len(path)))
            check.state(["disabled"] if parent_off else ["!disabled"])

    def off_paths(self):
        return {p for p, var in self.vars.items() if not var.get()}

    # ── 作る場所 ──
    def choose_base(self):
        start = self.base_var.get() or str(Path.home() / "Desktop")
        chosen = filedialog.askdirectory(title="フォルダを作る場所を選んでください", initialdir=start)
        if chosen:
            self.base_var.set(str(Path(chosen)))
            self.save()
            self.update_view()

    def save(self):
        self.settings["base_dir"] = self.base_var.get()
        self.settings["off"] = ["/".join(p) for p in sorted(self.off_paths())]
        save_settings(self.settings)

    # ── 表示を今の入力に合わせる ──
    def check_inputs(self):
        """作れない理由があれば、その説明を返す（作れるなら空の文字列）"""
        base = self.base_var.get()
        if base and not Path(base).is_dir():
            return "作る場所が見つかりません。「場所を選ぶ」で選び直してください"
        title = self.title_var.get().strip()
        if not title:
            return "作品名を入れてください"
        if len(title) > TITLE_LIMIT:
            return f"作品名は {TITLE_LIMIT} 文字までにしてください（今は {len(title)} 文字）"
        bad = find_bad_chars(title)
        if bad:
            return f"作品名に、フォルダ名に使えない文字（{bad}）が入っています"
        day = self.day_var.get().strip()
        try:
            datetime.strptime(day, DATE_FORMAT)
            if len(day) != 10:  # 2026-1-1 のような、0 を省いた書き方は受け付けない
                raise ValueError
        except ValueError:
            return "日付は 2026-01-01 のように、「年4けた-月2けた-日2けた」で入れてください"
        if not self.base_var.get():
            return "「場所を選ぶ」で、作る場所を選んでください"
        return ""

    def update_view(self):
        base = self.base_var.get()
        missing = bool(base) and not Path(base).is_dir()
        shown = shorten_head(base, self.base_max_px, self.label_font) if base else "まだ選んでいません"
        self.base_label.config(text=shown, foreground=RED if missing else (TEXT if base else SUB))

        problem = self.check_inputs()
        count = sum(1 for p in self.folders if not is_off(p, self.off_paths()))
        self.count_label.config(text=f"{count} / {len(self.folders)} 個")
        if problem:
            self.preview.config(text="できる名前：—", foreground=SUB)
            self.make_button.state(["disabled"])
            self.message.config(text=problem, foreground=SUB)
        else:
            top = make_top_name(self.title_var.get(), self.day_var.get().strip())
            self.preview.config(text=f"できる名前：{top}", foreground=TEXT)
            self.make_button.state(["!disabled"])
            self.message.config(text="")

    # ── 作る ──
    def make(self):
        if self.check_inputs():
            return
        top_name = make_top_name(self.title_var.get(), self.day_var.get().strip())
        try:
            self.created = create_folders(self.base_var.get(), top_name, self.folders, self.off_paths())
        except RuntimeError as error:
            self.open_button.grid_forget()
            self.message.config(text=str(error), foreground=RED)
            return
        self.message.config(text=f"できました：{self.created}", foreground=GREEN)
        self.open_button.grid(row=0, column=1, sticky="ns", padx=(10, 0))

    def open_created(self):
        if self.created and self.created.exists():
            os.startfile(self.created)  # エクスプローラーで開く


def main():
    root = tk.Tk()
    try:
        folders = load_template()
    except ValueError as error:
        # template.txt がおかしいときは、理由だけ出して終わる
        root.title("Premiere フォルダテンプレート")
        setup_style(root)
        ttk.Label(root, text=f"template.txt を読めませんでした\n\n{error}", padding=20,
                  foreground=RED, wraplength=420).pack()
        ttk.Button(root, text="閉じる", command=root.destroy).pack(pady=(0, 16))
        dark_title_bar(root)
        root.mainloop()
        return
    App(root, folders)
    root.mainloop()


if __name__ == "__main__":
    main()
