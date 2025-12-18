import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import subprocess
import logging
from psce_util import CustomMessagebox, normalize_text, setup_editor_logging

# General Settings（一般設定）
class GeneralSettingsTab:
    def __init__(self, notebook, app):
        self.app = app
        self.trans = app.trans
        self.tab = ttk.Frame(notebook)
        notebook.add(self.tab, text=self.trans.get("tab_general"))
        self.create_widgets()

    # Create Widgets（ウィジェット作成）
    def create_widgets(self):


        # FarcPack（FarcPack設定）
        frame_farc = ttk.LabelFrame(self.tab, text=self.trans.get("farc_settings"), padding=10)
        frame_farc.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_farc, text=self.trans.get("farc_path")).pack(anchor='w')
        self.app.farc_path_var = tk.StringVar(value=self.app.main_config.get('FarcPack', 'FarcPackPath', fallback=''))
        entry_farc = ttk.Entry(frame_farc, textvariable=self.app.farc_path_var, width=60)
        entry_farc.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.app.enable_text_undo_redo(entry_farc)
        ttk.Button(frame_farc, text=self.trans.get("browse"), command=self.browse_farc).pack(side='right')

        # General（一般設定）
        frame_gen = ttk.LabelFrame(self.tab, text=self.trans.get("gen_settings"), padding=10)
        frame_gen.pack(fill='x', padx=10, pady=5)

        # Save in parent directory（親ディレクトリに保存）
        self.app.save_parent_var = tk.BooleanVar(value=self.app.main_config.getboolean('GeneralSettings', 'SaveInParentDirectory', fallback=False))
        ttk.Checkbutton(frame_gen, text=self.trans.get("save_parent"), variable=self.app.save_parent_var).pack(anchor='w')

        # Default pose name（デフォルトポーズ名）
        frame_def_pose = ttk.Frame(frame_gen)
        frame_def_pose.pack(fill='x', pady=(5, 0))
        ttk.Label(frame_def_pose, text=self.trans.get("def_pose_name")).pack(side='left')
        self.app.def_pose_name_var = tk.StringVar(value=self.app.main_config.get('GeneralSettings', 'DefaultPoseFileName', fallback='gm_module_pose_tbl'))
        entry_def_pose = ttk.Entry(frame_def_pose, textvariable=self.app.def_pose_name_var)
        entry_def_pose.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.app.enable_text_undo_redo(entry_def_pose)

        # Use module name contains（モジュール名に含まれる）    
        self.app.use_module_name_contains_var = tk.BooleanVar(value=self.app.main_config.getboolean('GeneralSettings', 'UseModuleNameContains', fallback=False))
        ttk.Checkbutton(frame_gen, text=self.trans.get("use_module_name_contains"), variable=self.app.use_module_name_contains_var).pack(anchor='w', pady=(5, 0))

        # Overwrite existing files（既存ファイル上書き）
        self.app.overwrite_existing_var = tk.BooleanVar(value=self.app.main_config.getboolean('GeneralSettings', 'OverwriteExistingFiles', fallback=False))
        ttk.Checkbutton(frame_gen, text=self.trans.get("overwrite_existing"), variable=self.app.overwrite_existing_var).pack(anchor='w', pady=(5, 0))
        
        # Language（言語切替）
        ttk.Label(frame_gen, text=self.trans.get("lang_settings")).pack(anchor='w', pady=(10, 0))
        lang_code = self.app.main_config.get('GeneralSettings', 'Language', fallback='en')
        lang_display = "English" if lang_code == 'en' else "日本語"
        self.app.lang_var = tk.StringVar(value=lang_display)
        
        frame_lang_row = ttk.Frame(frame_gen)
        frame_lang_row.pack(fill='x', anchor='w')
        
        lang_combo = ttk.Combobox(frame_lang_row, textvariable=self.app.lang_var, values=['English', '日本語'], state='readonly')
        lang_combo.pack(side='left')
        
        # １回しか再起動できないため再起動ボタンを無効化中（ショートカット機能には残っている）
        # ttk.Button(frame_lang_row, text=self.trans.get("save_restart"), command=self.save_and_restart).pack(side='left', padx=10)
        
        # 言語切り替え後は再起動が必要案内
        ttk.Label(frame_gen, text=self.trans.get("restart_req"), font=("", 8)).pack(anchor='w', padx=5, pady=(2, 0))

        # 保存ボタン
        ttk.Button(self.tab, text=self.trans.get("save_gen_settings"), command=self.save_general_settings).pack(pady=10)

        # Debug（デバッグ設定）
        self.app.show_debug_var = tk.BooleanVar(value=self.app.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False))
        if self.app.show_debug_var.get():
             ttk.Checkbutton(self.tab, text=self.trans.get("show_debug"), variable=self.app.show_debug_var, command=self.toggle_debug_settings).pack(anchor='w', padx=10, pady=(10, 0))

        self.frame_debug = ttk.LabelFrame(self.tab, text=self.trans.get("debug_settings"), padding=10)
        # Pack handled by toggle（Packはtoggleで処理）

        # ログ出力切り替え
        self.app.debug_log_var = tk.BooleanVar(value=self.app.main_config.getboolean('DebugSettings', 'OutputLog', fallback=False))
        ttk.Checkbutton(self.frame_debug, text=self.trans.get("output_log"), variable=self.app.debug_log_var).pack(anchor='w')

        # 一時ファイル削除切り替え
        self.app.del_temp_var = tk.BooleanVar(value=self.app.main_config.getboolean('DebugSettings', 'DeleteTemp', fallback=True))
        ttk.Checkbutton(self.frame_debug, text=self.trans.get("delete_temp"), variable=self.app.del_temp_var).pack(anchor='w')

        # History Limit（履歴制限）
        frame_history = ttk.Frame(self.frame_debug)
        frame_history.pack(fill='x', pady=(5, 0))
        ttk.Label(frame_history, text=self.trans.get("undo_limit")).pack(side='left')
        self.app.history_limit_var = tk.IntVar(value=self.app.main_config.getint('DebugSettings', 'HistoryLimit', fallback=50))
        spin_history = ttk.Spinbox(frame_history, from_=50, to=150, textvariable=self.app.history_limit_var, width=5)
        spin_history.pack(side='left', padx=5)

        self.toggle_debug_settings()



    # デバッグ設定切り替え
    def toggle_debug_settings(self):
        # リフレッシュボタンの表示切り替え
        if hasattr(self.app, 'toggle_refresh_button'):
            self.app.toggle_refresh_button(self.app.show_debug_var.get())

        if self.app.show_debug_var.get():
            self.frame_debug.pack(fill='x', padx=10, pady=5)
            # KeyMapタブ表示
            if hasattr(self.app, 'ui_key'):
                # notebook.tabs()は文字列のタプルを返すので、tabオブジェクトのパスと比較
                tab_id = str(self.app.ui_key.tab)
                if tab_id not in self.app.notebook.tabs():
                    self.app.notebook.add(self.app.ui_key.tab, text=self.trans.get("tab_key_map"))
        # デバッグ設定非表示
        else:
            self.frame_debug.pack_forget()
            # KeyMapタブ非表示
            if hasattr(self.app, 'ui_key'):
                tab_id = str(self.app.ui_key.tab)
                if tab_id in self.app.notebook.tabs():
                    self.app.notebook.forget(self.app.ui_key.tab)

    # FarcPack選択ダイアログ
    def browse_farc(self):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
        if path:
            self.app.farc_path_var.set(path)

    # 保存
    def save_general_settings(self):
        # 変数を渡して正規化＆画面更新
        norm_path = normalize_text(self.app.farc_path_var)
        norm_def_pose = normalize_text(self.app.def_pose_name_var)
        
        
        # Check for changes (変更があるか確認)
        has_changes = False
        
        """
        # UIから値を取得して正規化
        path_ui = normalize_text(self.app.farc_path_var.get())
        def_pose_name_ui = normalize_text(self.app.def_pose_name_var.get())
        
        # Check for changes (変更があるか確認)
        has_changes = False
        """
        
        # FarcPackPath
        current_path = self.app.main_config.get('FarcPack', 'FarcPackPath', fallback='')
        if norm_path != current_path: has_changes = True
        # if path_ui != current_path: has_changes = True
        # GeneralSettings
        if str(self.app.save_parent_var.get()) != self.app.main_config.get('GeneralSettings', 'SaveInParentDirectory', fallback='False'): has_changes = True
        
        # DefaultPoseFileName (バリデーションは変更がある場合または保存時に実施されるが、ここでは単純比較)
        current_def_pose = self.app.main_config.get('GeneralSettings', 'DefaultPoseFileName', fallback='gm_module_pose_tbl')
        if norm_def_pose != current_def_pose: has_changes = True
        # if def_pose_name_ui != current_def_pose: has_changes = True
        if str(self.app.use_module_name_contains_var.get()) != self.app.main_config.get('GeneralSettings', 'UseModuleNameContains', fallback='False'): has_changes = True
        if str(self.app.overwrite_existing_var.get()) != self.app.main_config.get('GeneralSettings', 'OverwriteExistingFiles', fallback='False'): has_changes = True
        
        # Language
        lang_disp = self.app.lang_var.get()
        lang_code = 'en' if lang_disp == 'English' else 'ja'
        if lang_code != self.app.main_config.get('GeneralSettings', 'Language', fallback='en'): has_changes = True
        # DebugSettings
        if str(self.app.show_debug_var.get()) != self.app.main_config.get('DebugSettings', 'ShowDebugSettings', fallback='False'): has_changes = True
        if self.app.show_debug_var.get():
            if str(self.app.debug_log_var.get()) != self.app.main_config.get('DebugSettings', 'OutputLog', fallback='False'): has_changes = True
            if str(self.app.del_temp_var.get()) != self.app.main_config.get('DebugSettings', 'DeleteTemp', fallback='True'): has_changes = True
            if str(self.app.history_limit_var.get()) != self.app.main_config.get('DebugSettings', 'HistoryLimit', fallback='50'): has_changes = True

        # 変更がない場合
        if not has_changes:
             self.app.show_status_message(self.trans.get("msg_no_changes"), "warning")
             return # 画面変数は既に normalize_text 内で更新済み       

        """
        # 変更がない場合
        if not has_changes:
            self.app.show_status_message(self.trans.get("msg_no_changes")) # 変更事項がない場合の案内
            return
        """
            
        # 変更が検出された場合のみスナップショットを取る
        self.app.history.snapshot('general')

        # GeneralSettings保存
        if 'FarcPack' not in self.app.main_config: self.app.main_config['FarcPack'] = {}
        self.app.main_config['FarcPack']['FarcPackPath'] = normalize_text(self.app.farc_path_var.get())

        if 'GeneralSettings' not in self.app.main_config: self.app.main_config['GeneralSettings'] = {}
        self.app.main_config['GeneralSettings']['SaveInParentDirectory'] = str(self.app.save_parent_var.get())
        
        # DefaultPoseFileName検証
        def_pose_name = normalize_text(self.app.def_pose_name_var.get())
        # 半角英数字と記号のみで構成されているか検証
        if not all(c.isascii() and (c.isalnum() or c in ('_', '-', '.')) for c in norm_def_pose):
        # if not all(c.isascii() and (c.isalnum() or c in ('_', '-', '.')) for c in def_pose_name):
             # CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("err_filename_chars"), self.app.root)
             self.app.show_status_message(self.trans.get("err_filename_chars"), "error")
             return

        # DefaultPoseFileName保存
        self.app.main_config['GeneralSettings']['DefaultPoseFileName'] = norm_def_pose
        # self.app.main_config['GeneralSettings']['DefaultPoseFileName'] = def_pose_name

        # UseModuleNameContains保存
        self.app.main_config['GeneralSettings']['UseModuleNameContains'] = str(self.app.use_module_name_contains_var.get())
        # OverwriteExistingFiles保存
        self.app.main_config['GeneralSettings']['OverwriteExistingFiles'] = str(self.app.overwrite_existing_var.get())
        
        # Language conversion（言語変換）
        lang_disp = self.app.lang_var.get()
        lang_code = 'en' if lang_disp == 'English' else 'ja'
        self.app.main_config['GeneralSettings']['Language'] = lang_code

        # DebugSettings保存
        if 'DebugSettings' not in self.app.main_config: self.app.main_config['DebugSettings'] = {}
        self.app.main_config['DebugSettings']['ShowDebugSettings'] = str(self.app.show_debug_var.get())
        
        # ShowDebugSettingsがONの場合
        if self.app.show_debug_var.get():
            self.app.main_config['DebugSettings']['OutputLog'] = str(self.app.debug_log_var.get())
            self.app.main_config['DebugSettings']['DeleteTemp'] = str(self.app.del_temp_var.get())
            
            # HistoryLimit保存
            try:
                limit = self.app.history_limit_var.get()
                if limit < 50: limit = 50
                if limit > 150: limit = 150
            except:
                limit = 50
            self.app.main_config['DebugSettings']['HistoryLimit'] = str(limit)
            self.app.history.max_history = limit # Update immediately
        # ShowDebugSettingsがOFFの場合
        else:
            # Force defaults if hidden（非表示の場合、強制的にデフォルト値を設定）
            self.app.main_config['DebugSettings']['OutputLog'] = 'False'
            self.app.main_config['DebugSettings']['DeleteTemp'] = 'True'
            self.app.main_config['DebugSettings']['HistoryLimit'] = '50'
            self.app.history.max_history = 50

        # 設定保存
        self.app.utils.save_config(self.app.main_config, self.app.utils.main_config_path)

        # OutputLogの設定が変更された場合、ログ設定を再構築
        new_output_log = self.app.main_config.getboolean('DebugSettings', 'OutputLog', fallback=False)
        new_show_debug = self.app.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False)
        logging.info(f"ログ設定が変更されました")
        # ログ設定を再構築
        setup_editor_logging(show_debug=new_show_debug, output_log=new_output_log)

        self.app.show_status_message(self.trans.get("msg_saved_general")) # 保存完了の案内
        
        # 設定反映（可能であれば即時反映）
        self.app.trans.load_language(lang_code)
        # UIテキスト更新はノーマライズ処理内で実行済
        
        self.app.show_status_message("General settings saved.")

    # 設定読み込み
    def load_settings(self):
        """Restore UI state from main_config"""
        self.app.farc_path_var.set(self.app.main_config.get('FarcPack', 'FarcPackPath', fallback=''))
        self.app.save_parent_var.set(self.app.main_config.getboolean('GeneralSettings', 'SaveInParentDirectory', fallback=False))
        self.app.def_pose_name_var.set(self.app.main_config.get('GeneralSettings', 'DefaultPoseFileName', fallback='gm_module_pose_tbl'))
        self.app.use_module_name_contains_var.set(self.app.main_config.getboolean('GeneralSettings', 'UseModuleNameContains', fallback=False))
        self.app.overwrite_existing_var.set(self.app.main_config.getboolean('GeneralSettings', 'OverwriteExistingFiles', fallback=False))
        
        lang_code = self.app.main_config.get('GeneralSettings', 'Language', fallback='en')
        lang_display = "English" if lang_code == 'en' else "日本語"
        self.app.lang_var.set(lang_display)
        
        self.app.show_debug_var.set(self.app.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False))
        self.app.debug_log_var.set(self.app.main_config.getboolean('DebugSettings', 'OutputLog', fallback=False))
        self.app.del_temp_var.set(self.app.main_config.getboolean('DebugSettings', 'DeleteTemp', fallback=True))
        self.app.history_limit_var.set(self.app.main_config.getint('DebugSettings', 'HistoryLimit', fallback=50))
        
        self.toggle_debug_settings()
