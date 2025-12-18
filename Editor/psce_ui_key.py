import tkinter as tk
from tkinter import ttk, messagebox
import configparser 
import logging

# ショートカットキー登録ダイアログ
class KeyCaptureDialog(tk.Toplevel):
    def __init__(self, parent, trans, app, initial_value=""):
        super().__init__(parent)
        self.trans = trans
        self.app = app  # appを保存
        self.result = None
        self.current_keys = []
        
        self.title(self.trans.get("key_capture_title"))    # ウィンドウタイトル
        self.geometry("400x250")    # ウィンドウサイズ
        self.resizable(False, False)    # ウィンドウリサイズ禁止
        self.grab_set() # Modal

        self.create_widgets()
        
        # 初期値を解析
        if initial_value:
            # 表示用のシンプルな解析（このロジックはフォーマットによって改善が必要かも）
            # 仮想キーコードの形式 （例：<Control-s>）
            self.current_keys = [initial_value]
            self.update_display()

        self.bind("<Key>", self.on_key_press)
        self.focus_set()

    # UIウィンドウの作成
    def create_widgets(self):

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill='both', expand=True)
        
        # ウィンドウ説明
        ttk.Label(frame, text=self.trans.get("key_capture_desc"), justify='center').pack(pady=(0, 20))
        
        # キー表示エリア
        self.display_var = tk.StringVar()
        self.display_entry = ttk.Entry(frame, textvariable=self.display_var, font=("", 14), state='readonly', justify='center')
        self.display_entry.pack(fill='x', pady=(0, 20))
        
        # ボタンエリア  
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=10)
        
        # OKボタン
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side='left', expand=True, padx=5)
        # Clearボタン
        ttk.Button(btn_frame, text=self.trans.get("clear"), command=self.on_clear).pack(side='left', expand=True, padx=5)
        ttk.Button(btn_frame, text=self.trans.get("cancel"), command=self.destroy).pack(side='left', expand=True, padx=5)

    # キー押下時の処理
    def on_key_press(self, event):
        # 最終文字列の修飾キーのみを無視する（Tkinterのショートカットキーの場合、最終組み合わせを表示する）
        # Logic:
        # 1. 修飾キーの識別
        # 2. キーの識別
        # 3. <修飾キー-キー>のような文字列を構築する
        
        key = event.keysym
        
        # 修飾キーのみを無視する
        if key in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Win_L", "Win_R"):
            return

        parts = []
        # 修飾キーの状態を確認する
        # 0x0004はControl、0x0001はShift、0x0008はAlt（現在NumLock/CapsLockの問題を無視）
        # event.stateは信頼できる
        
        state = event.state
        
        # Control
        if state & 0x0004:
            parts.append("Control")
        
        # Alt
        # Windowsの場合、Altは通常0x20000。0x0008は通常NumLockまたは無視される
        if state & 0x20000:
            parts.append("Alt")
            
        # Shift
        if state & 0x0001:
            parts.append("Shift")
            
        # The key itself（キーそのもの）
        # Tkinter keysyms: 'a', 'B', 'F1', 'Return', etc.（Tkinterのキーシム：'a', 'B', 'F1', 'Return', など）
        if len(key) == 1:
            # Shiftが押された場合、keysymは通常大文字または押された文字。
            # <Control-s>のようなショートカットキーの場合、通常Control修飾子と小文字's'を使用する。
            # Shiftも押された<Control-Shift-S>のようなショートカットキーの場合、Sかもしれないので、正規化を試みる。
            pass
            
        parts.append(key)
        
        shortcut = f"<{'-'.join(parts)}>"
        
        self.current_keys = [shortcut] # 単一のストロークのショートカットキーのみをサポート
        self.update_display()
        
        # Prevent default behavior（デフォルトの動作を防ぐ）
        return "break"

    # 表示更新
    def update_display(self):
        self.display_var.set(" ".join(self.current_keys))

    # Clearボタン押下時の処理
    def on_clear(self):
        self.current_keys = []
        self.update_display()

    # OKボタン押下時の処理
    def on_ok(self):
        self.result = " ".join(self.current_keys)
        self.destroy()

class KeyMapTab:
    """ショートカットキー設定を編集するためのUIタブ（DebugSettingsが有効な場合のみ表示"""
    def __init__(self, notebook, app):
        self.app = app
        self.trans = app.trans
        self.tab = ttk.Frame(notebook)
        # タブの追加は psce_gui.py で制御されますが、ここではウィジェットの作成を行う。
        self.create_widgets()

    def create_widgets(self):

        """ウィジェットを作成・配置する"""
        # 説明ラベル
        ttk.Label(self.tab, text=self.trans.get("keymap_tab_title"), font=("Meiryo UI", 10, "bold")).pack(pady=10)   # 太字指定されている
        
        # 設定リストを表示するフレーム
        self.frame_list = ttk.Frame(self.tab)
        self.frame_list.pack(fill='both', expand=True, padx=20)

        # スクロールバー付きキャンバス (項目が多い場合に備えて)
        canvas = tk.Canvas(self.frame_list)
        scrollbar = ttk.Scrollbar(self.frame_list, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 各アクションのエントリを作成（key_managerのdefault_mapから動的に生成）
        self.entries = {}
        
        # アクション名の翻訳マッピング
        action_labels = {
            'SaveCurrentTab': self.trans.get('action_save_current_tab'),
            'SaveAndExit': self.trans.get('action_save_and_exit'),
            'ExitNoSave': self.trans.get('action_exit_no_save'),
            'RestartNoSave': self.trans.get('action_restart_no_save'),
            'SaveAndRestart': self.trans.get('action_save_and_restart'),
            'Undo': self.trans.get('action_undo'),
            'Redo': self.trans.get('action_redo'),
            'ToggleDebugSettings': self.trans.get('action_toggle_debug'),
        }

        row = 0
        for action_key in self.app.key_manager.default_map.keys():
            # ラベルテキスト取得（翻訳があればそれを使用、なければアクション名をそのまま表示）
            label_text = action_labels.get(action_key, action_key)
            
            ttk.Label(self.scrollable_frame, text=label_text).grid(row=row, column=0, sticky='w', padx=5, pady=5)
            
            current_val = self.app.key_manager.key_map.get('Shortcuts', action_key, fallback='')
            var = tk.StringVar(value=current_val)
            
            # 現在の値を表示する読み取り専用エントリ
            entry = ttk.Entry(self.scrollable_frame, textvariable=var, width=20, state='readonly')
            entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
            
            # 編集ボタン
            btn_edit = ttk.Button(self.scrollable_frame, text=self.trans.get("edit"), command=lambda k=action_key, v=var: self.open_key_capture(k, v))
            btn_edit.grid(row=row, column=2, sticky='w', padx=2, pady=5)
            
            # Delete Button（削除ボタン）
            btn_del = ttk.Button(self.scrollable_frame, text=self.trans.get("delete"), command=lambda v=var: self.delete_key(v))
            btn_del.grid(row=row, column=3, sticky='w', padx=2, pady=5)
            
            # Default Button（デフォルトに戻すボタン）
            btn_default = ttk.Button(self.scrollable_frame, text=self.trans.get("keymap_restore_default"), command=lambda k=action_key, v=var: self.restore_default(k, v))
            btn_default.grid(row=row, column=4, sticky='w', padx=2, pady=5)
            
            self.entries[action_key] = var
            row += 1

        # 保存ボタン
        ttk.Button(self.tab, text=self.trans.get("save_keymap"), command=self.save_key_map).pack(pady=20)

    # キャプチャダイアログを開く
    def open_key_capture(self, action_key, var):
        dialog = KeyCaptureDialog(self.tab, self.trans, self.app, initial_value=var.get())

        # --- 位置合わせ ---
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        ptr_x, ptr_y = dialog.winfo_pointerxy()
        logging.info(f"DEBUG: KeyMap Mouse Ptr: ({ptr_x}, {ptr_y})") 
        
        x = ptr_x - (width // 2)
        y = ptr_y + 20
        
        # 画面補正 (簡易)
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        
        dialog.geometry(f"+{x}+{y}")

        self.app.root.wait_window(dialog)
        if dialog.result is not None:
            var.set(dialog.result)

    def save_key_map(self):
        self.app.history.snapshot('key')
        """設定を保存して適用する"""
        changed = False
        for action, var in self.entries.items():
            new_val = var.get().strip()
            old_val = self.app.key_manager.key_map.get('Shortcuts', action, fallback='')
            
            # 変更があった場合
            if new_val != old_val:
                self.app.key_manager.key_map.set('Shortcuts', action, new_val)
                changed = True
        
        # 変更があった場合、保存して適用する
        if changed:
            self.app.key_manager.save_key_map()
            self.app.key_manager.apply_shortcuts(self.app.root)
            # messagebox.showinfo(self.trans.get("success"), self.trans.get("keymap_saved"))
            self.app.show_status_message(self.trans.get("keymap_saved"), "success")
        else:
            # messagebox.showinfo(self.trans.get("success"), self.trans.get("keymap_no_changes"))
            self.app.show_status_message(self.trans.get("keymap_no_changes"), "warning")

    def reset_key_map(self):
        # CustomMessageboxを使用する場合
        # if CustomMessagebox.ask_yes_no(self.trans.get("confirm"), self.trans.get("reset_confirm"), self.app.root):
        if messagebox.askyesno(self.trans.get("confirm"), self.trans.get("reset_confirm")):
            self.app.history.snapshot('key')
            self.app.key_manager.key_map = configparser.ConfigParser()
            self.app.key_manager.key_map.optionxform = str
            self.app.key_manager.key_map['Shortcuts'] = {}
            self.app.key_manager.save_key_map()
            self.app.key_manager.apply_shortcuts(self.app.root)
            
            # Refresh UI
            for action, var in self.entries.items():
                var.set("")
            
            # messagebox.showinfo(self.trans.get("success"), "KeyMap settings reset.")
            self.app.show_status_message(self.trans.get("keymap_reset"), "info")
    
    def refresh_key_list(self):
        """KeyMap設定をリロードしてGUIを更新"""
        for action, var in self.entries.items():
            current_val = self.app.key_manager.key_map.get('Shortcuts', action, fallback='')
            var.set(current_val)
    
    def restore_default(self, action_key, var):
        """指定されたアクションをデフォルト値に復元"""
        self.app.history.snapshot('key')  # Undo/Redo対応
        default_key = self.app.key_manager.default_map.get(action_key, '')
        var.set(default_key)
    
    def delete_key(self, var):
        """指定されたアクションのキーを削除"""
        self.app.history.snapshot('key')  # Undo/Redo対応
        var.set("")

