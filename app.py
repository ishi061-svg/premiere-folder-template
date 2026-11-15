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
FONT = ("Yu Gothic UI", 10)
INDENT_PX = 22  # 一覧で、1段ぶん右へずらす幅


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


class App:
    def __init__(self, root, folders):
        self.root = root
        self.folders = folders
        self.settings = load_settings()
        self.created = None  # 最後に作ったフォルダの場所

        root.title("Premiere フォルダテンプレート")
        root.resizable(False, False)
        style = ttk.Style()
        style.configure(".", font=FONT)
        style.configure("Big.TButton", font=(FONT[0], 11, "bold"), padding=(16, 6))

        main = ttk.Frame(root, padding=16)
        main.grid(sticky="nsew")
        main.columnconfigure(1, weight=1)

        # ── 作品名・日付・作る場所 ──
        self.title_var = tk.StringVar()
        self.day_var = tk.StringVar(value=date.today().strftime(DATE_FORMAT))
        self.base_var = tk.StringVar(value=self.settings.get("base_dir", ""))

        ttk.Label(main, text="作品名").grid(row=0, column=0, sticky="w", pady=4)
        title_entry = ttk.Entry(main, textvariable=self.title_var, width=40)
        title_entry.grid(row=0, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(main, text="日付").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(main, textvariable=self.day_var, width=12).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(main, text="作る場所").grid(row=2, column=0, sticky="w", pady=4)
        self.base_label = ttk.Label(main, width=40)
        self.label_font = font.Font(font=FONT)
        self.base_max_px = self.label_font.measure("0") * 40  # width=40 の欄に入る幅
        self.base_label.grid(row=2, column=1, sticky="we", pady=4)
        ttk.Button(main, text="場所を選ぶ", command=self.choose_base).grid(row=2, column=2, sticky="e", padx=(8, 0))

        # ── 作るフォルダの一覧（チェックで ON・OFF） ──
        box = ttk.LabelFrame(main, text=" 作るフォルダ（チェックを外すと作りません） ", padding=(10, 6))
        box.grid(row=3, column=0, columnspan=3, sticky="we", pady=(12, 4))
        saved_off = {tuple(p.split("/")) for p in self.settings.get("off", [])}
        self.vars = {}    # フォルダ → チェックの ON・OFF
        self.checks = {}  # フォルダ → チェックボックスの部品
        for i, path in enumerate(folders):
            var = tk.BooleanVar(value=path not in saved_off)
            check = ttk.Checkbutton(box, text=path[-1], variable=var,
                                    command=lambda p=path: self.on_check(p))
            check.grid(row=i, column=0, sticky="w", padx=((len(path) - 1) * INDENT_PX, 0))
            self.vars[path] = var
            self.checks[path] = check
        self.refresh_checks()

        # ── できあがりの名前と、作るボタン ──
        self.preview = ttk.Label(main, foreground="#333")
        self.preview.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 2))

        buttons = ttk.Frame(main)
        buttons.grid(row=5, column=0, columnspan=3, sticky="we", pady=(6, 0))
        self.make_button = ttk.Button(buttons, text="フォルダを作る", style="Big.TButton", command=self.make)
        self.make_button.pack(side="left")
        self.open_button = ttk.Button(buttons, text="フォルダを開く", command=self.open_created)
        # 「フォルダを開く」は、作ったあとにだけ出す

        self.message = ttk.Label(main, wraplength=420, justify="left")
        self.message.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))

        for var in (self.title_var, self.day_var):
            var.trace_add("write", lambda *_: self.update_view())
        self.update_view()
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
        self.base_label.config(text=shown, foreground="#c62828" if missing else "#333")

        problem = self.check_inputs()
        count = sum(1 for p in self.folders if not is_off(p, self.off_paths()))
        if problem:
            self.preview.config(text=f"作るフォルダ：{count} / {len(self.folders)} 個")
            self.make_button.state(["disabled"])
            self.message.config(text=problem, foreground="#666")
        else:
            top = make_top_name(self.title_var.get(), self.day_var.get().strip())
            self.preview.config(text=f"できる名前：{top}　（中のフォルダ {count} / {len(self.folders)} 個）")
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
            self.open_button.pack_forget()
            self.message.config(text=str(error), foreground="#c62828")
            return
        self.message.config(text=f"できました：{self.created}", foreground="#2e7d32")
        self.open_button.pack(side="left", padx=(10, 0))

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
        ttk.Label(root, text=f"template.txt を読めませんでした\n\n{error}", padding=20,
                  font=FONT, foreground="#c62828", wraplength=420).pack()
        ttk.Button(root, text="閉じる", command=root.destroy).pack(pady=(0, 16))
        root.mainloop()
        return
    App(root, folders)
    root.mainloop()


if __name__ == "__main__":
    main()
