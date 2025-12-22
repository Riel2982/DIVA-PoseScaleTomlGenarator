import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import io
import configparser
import sys
import shutil
import ctypes
import logging
import traceback
import threading
from psce_util import ConfigUtility, VERSION
from psce_translation import TranslationManager
from psce_history import HistoryManager
from psce_ui_general import GeneralSettingsTab
from psce_ui_profile import ProfileTab
from psce_ui_data import PoseDataTab
from psce_ui_map import PoseIDMapTab
from psce_key import KeyManager
from psce_ui_key import KeyMapTab
from psce_update import load_status, perform_update_gui, check_update


class ConfigEditorApp:
    def __init__(self, root):
 
        # 初期化コード
        self.root = root
        self.utils = ConfigUtility()
        self.trans = TranslationManager()

        # 未削除画像リストの初期化（追加）
        self.pending_delete_images = []

        # Load Configs
        self.main_config = self.utils.load_config(self.utils.main_config_path)
        if self.main_config is None:
            # Configが読み込まれなかった場合のエラー（ロード失敗時の致命的エラーは、アプリ終了を伴うためポップアップのままにしておく）
            try:
                # messagebox.showerror("Error", "Failed to load Config.ini.\nFile might be locked or corrupted.\nApplication will exit to prevent data loss.")
                # 翻訳対応
                messagebox.showerror(self.trans.get("error"), self.trans.get("err_load_config_fatal"))
                self.root.destroy()
                sys.exit()
            except:
                pass
            sys.exit(1)
        self.profile_config = self.utils.load_config(self.utils.profile_config_path)
        self.pose_id_map = self.utils.load_config(self.utils.pose_id_map_path)
        
        # KeyManagerの初期化
        self.key_manager = KeyManager(self)
        
        # 言語設定
        lang = self.main_config.get('GeneralSettings', 'Language', fallback='en')
        self.trans.set_language(lang)
        
        # self.root.title(self.trans.get("window_title"))   # GUIのウィンドウタイトルを翻訳対応する場合
        if VERSION != "v0.0.0-dev": # バージョン情報の埋め込み有り
            self.root.title(f"Pose Scale Config Editor - {VERSION}")
        else:   # バージョンが埋め込まれていない時（バージョンは表示しない）
            self.root.title(self.trans.get("window_title"))
        
        # Set Icon（アイコンの設定）
        icon_path = None
        if getattr(sys, 'frozen', False):
            # 凍結されている場合、PyInstallerがファイルを抽出する一時フォルダを検索する
            icon_path = os.path.join(sys._MEIPASS, 'PoseScaleConfigEditor.ico')
        
        # Fallback or dev mode（フォールバックまたは開発モード）
        if not icon_path or not os.path.exists(icon_path):
            icon_path = os.path.join(self.utils.app_dir, 'PoseScaleConfigEditor.ico')
            
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Failed to set icon: {e}")
        
        # ウィンドウの復元
        geometry = self.main_config.get('GeneralSettings', 'WindowGeometry', fallback="1100x800")
        self.root.geometry(geometry)

        self.current_pose_config = None
        self.current_pose_file_path = None
        
        self.selected_profile_section = None
        self.selected_pose_data_section = None
        self.selected_map_key = None
        
        
        self.history = HistoryManager(self)
        
        # Undo/Redoボタンの配置
        self.create_toolbar()
        
        # ステータスバーの作成（メッセージボックスの配置）
        self.create_statusbar()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # タブ切り替え時にUndo/Redoボタンを更新
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        
        # タブの初期化
        self.general_tab = GeneralSettingsTab(self.notebook, self)
        self.ui_profile = ProfileTab(self.notebook, self)
        self.pose_data_tab = PoseDataTab(self.notebook, self)
        self.map_tab = PoseIDMapTab(self.notebook, self)
        
        # HistoryManager用のタブマッピング
        self.tab_map = {
            str(self.general_tab.tab): 'general',
            str(self.ui_profile.tab): 'profile',
            str(self.pose_data_tab.tab): 'data',
            str(self.map_tab.tab): 'map'
        }
        
        # KeyMapタブ（デバッグモードが有効な場合のみ表示）
        self.ui_key = KeyMapTab(self.notebook, self)
        self.tab_map[str(self.ui_key.tab)] = 'key'
        
        if self.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False):
            self.notebook.add(self.ui_key.tab, text=self.trans.get("tab_key_map"))
        
        # ショートカットを適用
        self.key_manager.apply_shortcuts(self.root)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ツールバーの作成
    def create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=2)
        toolbar.pack(side='top', fill='x')
        
        self.btn_undo = ttk.Button(toolbar, text=self.trans.get("undo"), command=self.undo, state='disabled')   # Undoボタン
        self.btn_undo.pack(side='left', padx=2)
        
        self.btn_redo = ttk.Button(toolbar, text=self.trans.get("redo"), command=self.redo, state='disabled')   # Redoボタン
        self.btn_redo.pack(side='left', padx=2)
        
        # スペーサー
        ttk.Frame(toolbar, width=10).pack(side='left')
        
        # タブの再読み込みボタン（左側）- 初期状態では非表示（GeneralSettingsTabで制御）
        self.refresh_btn = ttk.Button(toolbar, text=self.trans.get("refresh_tab"), command=self.refresh_current_tab)

        # 更新があるときだけGitHubリンクボタンの左横に表示（バックグラウンドチェック開始）
        # self.update_btn = ttk.Button(toolbar, text=self.trans.get("Update!"), command=self.check_and_show_update_button)
        # self.check_and_show_update_button(toolbar, update_btn)

        # GitHubアイコンパス取得
        if hasattr(sys, '_MEIPASS'):    # PyInstallerでビルドされた場合、一時フォルダ(_MEIPASS)を参照
            app_dir = sys._MEIPASS        
        else:   # PyInstallerでビルドされていない場合、実行ファイルのディレクトリを参照（開発用）
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(app_dir, 'icons', 'github-mark.png')
        
        if os.path.exists(icon_path): # GitHubリンク（画像式）
            # github_icon = tk.PhotoImage(file=icon_path)   # 
            github_icon_raw = tk.PhotoImage(file=icon_path)
            github_icon = github_icon_raw.subsample(10, 10)     #subsampleで1/15に縮小するとラベルボタンと同じ高さ
            github_btn = ttk.Button(toolbar, image=github_icon, command=self.open_github)
            github_btn.image = github_icon  # 参照を保持
            github_btn.pack(side='right', padx=2)
        else: # GitHubリンク（テキストボックス式）
            ttk.Button(toolbar, text="GitHub", command=self.open_github).pack(side='right', padx=2)  

        # GitHubボタンの配置後にチェックを開始（anchorとして使用するため）
        self.start_background_update_check(toolbar, github_btn if 'github_btn' in locals() else None)


            

    def toggle_refresh_button(self, visible):
        """リフレッシュボタンの表示/非表示を切り替え"""
        if visible:
            self.refresh_btn.pack(side='left', padx=2)
        else:
            self.refresh_btn.pack_forget()

    def open_github(self):
        """GitHubリポジトリを開く"""
        import webbrowser
        webbrowser.open("https://github.com/Riel2982/DIVA-PoseScaleTomlGenarator")


    def start_background_update_check(self, toolbar, anchor_widget):
        """バックグラウンドでアップデートを確認し、結果があればボタンを表示"""
        from psce_update import run_background_update_check
        
        def run_check():
            run_background_update_check()
            # メインスレッドでUI更新をスケジュール
            self.root.after(0, lambda: self.check_and_show_update_button(toolbar, anchor_widget))
            
        # デーモンスレッドで実行（アプリ終了時に道連れ停止）
        threading.Thread(target=run_check, daemon=True).start()

    def check_and_show_update_button(self, toolbar, anchor_widget):
        """アップデート情報を確認して通知ボタンを表示"""
        from psce_update import get_update_info
        
        try:
            update_info = get_update_info()
            
            if update_info['show_button']:
                update_btn = ttk.Button(
                    toolbar, 
                    text=update_info['button_text'], 
                    command=self.on_update_click
                )
                # GitHubボタンの左側に配置
                update_btn.pack(side='right', padx=5)
        except Exception as e:
            logging.error(f"Update check error: {e}")

    if False:
        def start_background_update_check(self, toolbar, anchor_widget):
            """バックグラウンドでアップデートを確認し、結果があればボタンを表示"""
            def run_check():
                try:
                    # Editor自身のチェック
                    check_update(current_version=VERSION, exe_name="PoseScaleConfigEditor.exe")
                    
                    # Generatorのステータスも確認（EditorとGeneratorは同じディレクトリにあると仮定）
                    app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                    generator_path = os.path.join(app_dir, "PoseScaleTomlGenerator.exe")
                    
                    if os.path.exists(generator_path):
                        # Generatorのバージョンを取得（pstg_util.VERSIONと同じロジック）
                        # ここでは簡易的に、status.jsonから前回のgenerator versionを取得
                        status = load_status()
                        gen_status = status.get('PoseScaleTomlGenerator.exe', {})
                        gen_version = gen_status.get('current_version', VERSION)  # フォールバック
                        
                        # Generatorのステータスも更新
                        check_update(current_version=gen_version, exe_name="PoseScaleTomlGenerator.exe")
                        
                except Exception as e:
                    logging.error(f"Background update check failed: {e}")
                
                # メインスレッドでUI更新をスケジュール
                self.root.after(0, lambda: self.check_and_show_update_button(toolbar, anchor_widget))
                
            # デーモンスレッドで実行（アプリ終了時に道連れ停止）
            threading.Thread(target=run_check, daemon=True).start()

        def check_and_show_update_button(self, toolbar, anchor_widget):
            """アップデート情報を確認して通知ボタンを表示"""
            try:
                from packaging import version as pkg_version
                
                status = load_status()
                latest_version = status.get('latest_version', '')
                
                if not latest_version:
                    return
                
                editor_status = status.get('PoseScaleConfigEditor.exe', {})
                gen_status = status.get('PoseScaleTomlGenerator.exe', {})
                
                # availableフラグを信頼せず、その場でバージョン比較
                editor_available = False
                gen_available = False
                
                try:
                    latest_clean = latest_version.lstrip('v')
                    
                    # Editorのバージョン確認
                    editor_current = editor_status.get('current_version', VERSION)
                    editor_clean = editor_current.lstrip('v')
                    editor_available = pkg_version.parse(latest_clean) > pkg_version.parse(editor_clean)
                    
                    # Generatorのバージョン確認
                    gen_current = gen_status.get('current_version', '')
                    if gen_current:
                        gen_clean = gen_current.lstrip('v')
                        gen_available = pkg_version.parse(latest_clean) > pkg_version.parse(gen_clean)
                except Exception as e:
                    logging.error(f"Version comparison error: {e}")
                    return
                
                ver_text = f"v{latest_version}" if not latest_version.startswith('v') else latest_version
                
                # どちらかが更新可能な場合にボタン表示
                if editor_available or gen_available:
                    # ボタンテキストの決定
                    if editor_available and gen_available:
                        btn_text = f"New Release: v{ver_text}"
                    elif editor_available:
                        btn_text = f"Editor Update: v{ver_text}"
                    else:
                        btn_text = f"Generator Update: v{ver_text}"
                    
                    update_btn = ttk.Button(
                        toolbar, 
                        text=btn_text, 
                        command=self.on_update_click
                    )
                    update_btn.pack(side='right', padx=5)
                    
            except Exception as e:
                logging.error(f"Update check error: {e}")

    def on_update_click(self):
        """アップデートボタン押下時：詳細ダイアログを表示して更新確認"""
        
        # perform_update_gui を呼び出す（これが詳細ダイアログを出す）
        perform_update_gui(self.root)

    def create_statusbar(self):
        """ステータスバーを作成"""
        # メインコンテンツと同じパディングを持たせるためのコンテナ（背景色なし、位置調整用）

        # self.statusbar_frame = ttk.Frame(self.root, padding=2)
        self.statusbar_frame = tk.Frame(self.root, height=25)   # 高さ設定
        self.statusbar_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 5))    # pady=(0, 5)で下部に少し余白を持たせる
        self.statusbar_frame.pack_propagate(False) # サイズ固定

        # 区切り線（オプション：より一体感を出すなら削除しても良い）
        separator = ttk.Separator(self.statusbar_frame, orient='horizontal')
        separator.pack(fill='x', pady=(0, 2))
        
        self.status_var = tk.StringVar()
        """
        # フォントを少し小さくして控えめに
        self.status_label = ttk.Label(self.statusbar_frame, textvariable=self.status_var, anchor='w', font=("", 9))
        self.status_label.pack(side='left', fill='x', expand=True)
        """
        # 白いボックス風のデザイン（メッセージ部分のみ）
        self.status_label = tk.Label(
            self.statusbar_frame, 
            textvariable=self.status_var, 
            font=("Meiryo UI", 9),  # フォントを指定するなら"Meiryo UI"など（Windws規定フォントだとINFOアイコンがただのiになるっぽい）
            bg='white',             
            fg='#333333',           
            relief='solid',         
            bd=1,                   
            padx=20, pady=2         
        )
        # 初期状態では非表示（packしない）

        
    def show_status_message(self, message, msg_type="info", duration=3000):     # 特に指定しない時のアイコンはINFO
        """ステータスバーにメッセージを表示し、一定時間後に消去する
        
        Args:
            message (str): 表示するメッセージ
            msg_type (str): "info", "success", "warning", "error" のいずれか
            duration (int): 表示時間（ミリ秒）。Noneの場合は消去しない。
        """
        # アイコン定義
        icons = {
            "info": "ℹ️ ",
            "success": "✅ ",
            "warning": "⚠️ ",
            "error": "❌ "
        }
        icon = icons.get(msg_type, "")
        
        full_message = f"{icon} {message}"
        self.status_var.set(full_message)
        
        # 中央に配置して表示
        self.status_label.pack(expand=True)

        # 既存のタイマーがあればキャンセル（連続してメッセージが来た場合用）
        if hasattr(self, '_status_timer') and self._status_timer:
            self.root.after_cancel(self._status_timer)
            self._status_timer = None
            
        if duration:
            # 指定時間後に非表示にする処理
            def hide():
                self.status_label.pack_forget()
                self.status_var.set("")

            self._status_timer = self.root.after(duration, hide)

    # 現在のタブを取得
    def get_current_context(self):
        """現在のタブを取得"""
        current_tab = self.notebook.select()
        return self.tab_map.get(current_tab)
    
    # タブ切り替え時にUndo/Redoボタンの状態を更新
    def on_tab_changed(self, event=None):
        """タブ切り替え時にUndo/Redoボタンの状態を更新"""
        self.update_undo_redo_buttons()

    def undo(self):
        """Undo操作"""
        context = self.get_current_context()
        self.history.undo(context)

    def redo(self):
        """Redo操作"""
        context = self.get_current_context()
        self.history.redo(context)

    def refresh_current_tab(self):
        # 現在のコンテキストを取得
        context = self.get_current_context()
        
        # 現在の状態を保存して再読み込み
        self.history.snapshot(context)
        
        # コンテキストに基づいて特定のファイルを再読み込み
        if context == 'general':
            self.main_config = self.utils.load_config(self.utils.main_config_path)
        elif context == 'profile':
            self.profile_config = self.utils.load_config(self.utils.profile_config_path)
        elif context == 'data':
            # PoseScaleDataタブは内部で再読み込みを処理します（ディレクトリスキャン + ファイルの再読み込み）
            self.pose_data_tab.refresh_pose_files()
            # 再読み込みを処理する必要はありません
            return
        elif context == 'map':
            self.pose_id_map = self.utils.load_config(self.utils.pose_id_map_path)
        elif context == 'key':
            self.key_manager.load_key_map()
            self.key_manager.apply_shortcuts(self.root)
            self.ui_key.refresh_key_list()
            
        # UIを更新
        self.refresh_current_tab_ui()

    def update_undo_redo_buttons(self):
        """Undo/Redoボタンの状態を更新"""
        context = self.get_current_context()
        if not context:
            self.btn_undo['state'] = 'disabled'
            self.btn_redo['state'] = 'disabled'
            return

        stack = self.history._get_stack(context)
        self.btn_undo['state'] = 'normal' if stack['undo'] else 'disabled'
        self.btn_redo['state'] = 'normal' if stack['redo'] else 'disabled'

    def enable_text_undo_redo(self, widget):
        """テキストボックスのUndo/Redoを有効にする"""
        if not isinstance(widget, ttk.Entry) and not isinstance(widget, tk.Entry):
            return

        # 各ウィジェット独立のUndo/Redoスタック
        widget.undo_stack = []
        widget.redo_stack = []
        widget.last_value = widget.get()
        widget.programmatic_change = False  # プログラムによる変更フラグ
        
        def on_change(event=None):
            """テキストボックスの変更を監視"""
            # プログラムによる変更の場合はスキップ
            if widget.programmatic_change:
                return
                
            current_value = widget.get()
            if current_value != widget.last_value:
                widget.undo_stack.append(widget.last_value)
                widget.redo_stack.clear()
                widget.last_value = current_value
                # スタックサイズ制限
                if len(widget.undo_stack) > 50:
                    widget.undo_stack.pop(0)

        def undo(event):
            """Undo操作"""
            if widget.undo_stack:
                widget.programmatic_change = True
                val = widget.undo_stack.pop()
                widget.redo_stack.append(widget.get())
                
                widget.delete(0, 'end')
                widget.insert(0, val)
                widget.last_value = val
                widget.icursor('end')
                widget.programmatic_change = False
                
            return "break"

        def redo(event):
            """Redo操作"""
            if widget.redo_stack:
                widget.programmatic_change = True
                val = widget.redo_stack.pop()
                widget.undo_stack.append(widget.get())
                
                widget.delete(0, 'end')
                widget.insert(0, val)
                widget.last_value = val
                widget.icursor('end')
                widget.programmatic_change = False
                
            return "break"
        
        def reset_stack(new_value=None):
            """外部からの値変更時にスタックをリセット"""
            if new_value is None:
                new_value = widget.get()
            widget.programmatic_change = True
            widget.undo_stack.clear()
            widget.redo_stack.clear()
            widget.last_value = new_value
            widget.programmatic_change = False

        # リセット関数をウィジェットに公開
        widget.reset_undo_stack = reset_stack

        # イベントバインド
        widget.bind('<KeyRelease>', on_change)
        widget.bind('<Control-z>', undo)
        widget.bind('<Control-y>', redo)

    def refresh_current_tab_ui(self):
        """すべてのタブを更新して一貫性を保つ"""
         
        # General Settings
        self.general_tab.app.farc_path_var.set(self.main_config.get('FarcPack', 'FarcPackPath', fallback=''))
        self.general_tab.app.save_parent_var.set(self.main_config.getboolean('GeneralSettings', 'SaveInParentDirectory', fallback=False))
        self.general_tab.app.def_pose_name_var.set(self.main_config.get('GeneralSettings', 'DefaultPoseFileName', fallback='gm_module_pose_tbl'))
        self.general_tab.app.use_module_name_contains_var.set(self.main_config.getboolean('GeneralSettings', 'UseModuleNameContains', fallback=True))
        self.general_tab.app.overwrite_existing_var.set(self.main_config.getboolean('GeneralSettings', 'OverwriteExistingFiles', fallback=False))
        
        # Language
        lang_code = self.main_config.get('GeneralSettings', 'Language', fallback='en')
        lang_display = "English" if lang_code == 'en' else "日本語"
        self.general_tab.app.lang_var.set(lang_display)
        
        # Debug Settings
        self.general_tab.app.show_debug_var.set(self.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False))
        self.general_tab.toggle_debug_settings()
        self.general_tab.app.debug_log_var.set(self.main_config.getboolean('DebugSettings', 'OutputLog', fallback=False))
        self.general_tab.app.del_temp_var.set(self.main_config.getboolean('DebugSettings', 'DeleteTemp', fallback=True))
        self.general_tab.app.history_limit_var.set(self.main_config.getint('DebugSettings', 'HistoryLimit', fallback=50))
        
        # Profile Settings
        self.ui_profile.refresh_profile_list()
        # Restore selection if possible（リストの再読み込みは通常、選択をクリアするため、選択を復元することはできません）
        
        # Pose Data Settings
        self.pose_data_tab.refresh_pose_data_list()
        
        # Map Settings
        self.map_tab.refresh_pose_id_map_list()
        
        # 復元する画像を復元する
        if self.pending_delete_images:
            try:
                # 現在のインメモリのconfigをチェック
                used_images = set()
                if self.pose_id_map.has_section('PoseImages'):
                    for _, filename in self.pose_id_map.items('PoseImages'):
                        used_images.add(filename)
                
                # 待機中の削除画像が使用されている場合は、待機中の削除画像から削除する
                restored = set()
                for image_path in self.pending_delete_images:
                    filename = os.path.basename(image_path)
                    if filename in used_images:
                        restored.add(image_path)
                
                for r in restored:
                    self.pending_delete_images.remove(r)
                    logging.warning(f"Restored image from pending delete: {r}")
                    
            except Exception as e:
                logging.error(f"Error checking restored images: {e}")

        # Map Image Previewを更新する
        if self.map_tab.app.selected_map_key:
            self.map_tab.load_map_image(self.map_tab.app.selected_map_key)

    def refresh_all_tabs(self):
        # General Settings
        self.general_tab.app.farc_path_var.set(self.main_config.get('FarcPack', 'FarcPackPath', fallback=''))
        self.general_tab.app.save_parent_var.set(self.main_config.getboolean('GeneralSettings', 'SaveInParentDirectory', fallback=False))
        self.general_tab.app.def_pose_name_var.set(self.main_config.get('GeneralSettings', 'DefaultPoseFileName', fallback='gm_module_pose_tbl'))
        self.general_tab.app.use_module_name_contains_var.set(self.main_config.getboolean('GeneralSettings', 'UseModuleNameContains', fallback=True))
        self.general_tab.app.overwrite_existing_var.set(self.main_config.getboolean('GeneralSettings', 'OverwriteExistingFiles', fallback=False))
        
        # Language（言語切り替え）
        lang_code = self.main_config.get('GeneralSettings', 'Language', fallback='en')
        lang_display = "English" if lang_code == 'en' else "日本語"
        self.general_tab.app.lang_var.set(lang_display)
        
        # Debug Settings（デバッグ設定）
        self.general_tab.app.show_debug_var.set(self.main_config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False))
        self.general_tab.toggle_debug_settings()
        self.general_tab.app.debug_log_var.set(self.main_config.getboolean('DebugSettings', 'OutputLog', fallback=False))
        self.general_tab.app.del_temp_var.set(self.main_config.getboolean('DebugSettings', 'DeleteTemp', fallback=True))
        self.general_tab.app.history_limit_var.set(self.main_config.getint('DebugSettings', 'HistoryLimit', fallback=50))
        
        # Profile Settings（プロファイル設定）
        self.ui_profile.refresh_profile_list()
        self.ui_profile.app.prof_section_suffix_var.set("")
        self.ui_profile.app.prof_match_var.set("")
        self.ui_profile.app.prof_exclude_var.set("")
        self.ui_profile.app.prof_config_var.set("")
        self.ui_profile.app.prof_pose_file_var.set("")
        
        # Pose Data Settings（ポーズデータ設定）
        self.pose_data_tab.refresh_pose_files()
        if self.current_pose_file_path:
             self.pose_data_tab.app.pose_file_combo.set(os.path.basename(self.current_pose_file_path))
             self.pose_data_tab.refresh_pose_data_list()
        self.pose_data_tab.app.pd_section_suffix_var.set("")
        self.pose_data_tab.app.pd_chara_var.set("")
        self.pose_data_tab.app.pd_match_var.set("")
        self.pose_data_tab.app.pd_exclude_var.set("")
        self.pose_data_tab.app.pd_pose_id_var.set("")
        self.pose_data_tab.app.pd_scale_var.set("")
        
        # Map Settings（マップ設定）
        self.map_tab.refresh_pose_id_map_list()
        self.map_tab.app.map_id_var.set("")
        self.map_tab.app.map_name_var.set("")
        self.map_tab.app.map_image_label.configure(image='')
        self.map_tab.app.map_image_label.image = None

    # ウィンドウの位置とサイズを保存する
    def save_geometry(self):
        try:
            current_config = self.utils.load_config(self.utils.main_config_path)
            if current_config is None:
                logging.error("Failed to load config for saving geometry. Skipping save.")  # 読み込み失敗をログに出力
                return
            # このチェックは、Noneチェックが失敗を処理する場合、不要になりました
            #     current_config = self.main_config # Fallback（バックアップ）  
        except Exception:
            current_config = self.main_config
            logging.error("Failed to load config for saving geometry. Using fallback config.")  # 読み込み失敗をログに出力

        if 'GeneralSettings' not in current_config: current_config['GeneralSettings'] = {}
        current_config['GeneralSettings']['WindowGeometry'] = self.root.geometry()
        logging.info(f"Saving geometry: {self.root.geometry()}")  # 保存する値をログに出力
        self.utils.save_config(current_config, self.utils.main_config_path)
        logging.info("Geometry saved successfully.")  # 保存成功をログに出力

    def perform_cleanup(self):
        """終了時のクリーンアップ処理（画像削除など）"""
        # 関数が呼ばれたことを確認
        logging.info("====== perform_cleanup() CALLED ======")

        # ゴミ箱フォルダを空にする
        trash_dir = os.path.join(self.utils.pose_images_dir, '_trash')
        logging.info(f"Cleanup: Checking trash directory: {trash_dir}")

        if os.path.exists(trash_dir):
            logging.info(f"Cleanup: Trash directory exists, attempting to delete...")
            try:
                # フォルダ内のファイルを個別に削除
                for root, dirs, files in os.walk(trash_dir, topdown=False):
                    for name in files:
                        file_path = os.path.join(root, name)
                        try:
                            os.chmod(file_path, 0o777)
                            os.remove(file_path)
                            logging.info(f"Deleted file: {file_path}")
                        except Exception as e:
                            logging.warning(f"Failed to delete file {file_path}: {e}")
                    
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            os.rmdir(dir_path)
                            logging.info(f"Deleted directory: {dir_path}")
                        except Exception as e:
                            logging.warning(f"Failed to delete directory {dir_path}: {e}")
                
                # trashディレクトリ自体を削除
                try:
                    os.rmdir(trash_dir)
                    logging.info(f"Successfully cleaned up trash directory")
                except Exception as e:
                    logging.warning(f"Failed to remove trash directory: {e}")
                    shutil.rmtree(trash_dir, ignore_errors=True)
                    
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
        else:
            logging.info(f"Cleanup: Trash directory does not exist")            
            """
            try:
                # ignore_errors=True で強制削除
                shutil.rmtree(trash_dir, ignore_errors=True)
                logging.info(f"Cleaned up trash directory: {trash_dir}")
            except Exception as e:
                logging.warning(f"Failed to clean up trash (ignored): {e}")
                # エラーでも処理を続行
            """
        # 関数の終了を確認
        logging.info("====== perform_cleanup() FINISHED ======")
        
        # ログを即座にフラッシュ
        for handler in logging.getLogger().handlers:
            handler.flush()

    def on_closing(self):
        logging.info("====== on_closing() CALLED ======")        

        try:
            logging.info("Step 1: Saving geometry")
            self.save_geometry()

            logging.info("Step 2: Processing pending delete images")            
            # 未削除の画像を処理
            if hasattr(self, 'pending_delete_images') and self.pending_delete_images:
            # if self.pending_delete_images:
                try:
                    # PoseIDMapを再読み込みして最新の状態を取得
                    current_map = self.utils.load_config(self.utils.pose_id_map_path)
                    if current_map:
                        # 現在使用されている画像を集める
                        used_images = set()
                        if current_map.has_section('PoseImages'):
                            for _, filename in current_map.items('PoseImages'):
                                used_images.add(filename)
                        
                        for image_path in self.pending_delete_images:
                            filename = os.path.basename(image_path)
                            # 未使用の画像のみ削除
                            if filename not in used_images:
                                try:
                                    if os.path.exists(image_path):
                                        os.remove(image_path)
                                        print(f"Deleted unused image: {image_path}")
                                        logging.info(f"Deleted unused image: {image_path}")
                                except Exception as e:
                                    print(f"Failed to delete image {image_path}: {e}")
                                    logging.warning(f"Failed to delete image {image_path}: {e}")
                            else:
                                print(f"Skipped deletion of restored image: {filename}")
                                logging.info(f"Skipped deletion of restored image: {filename}")
                except Exception as e:
                    print(f"Error processing image deletions: {e}")
                    logging.error(f"Error processing image deletions: {e}")
            else:
                logging.info("No pending delete images")
            
            logging.info("Step 3: Calling perform_cleanup()")       
            
            # クリーンアップ処理
            self.perform_cleanup()
            logging.info("Step 4: Flushing logs")
            # ログをフラッシュ
            logging.info("=== Editor closing ===")
            for handler in logging.getLogger().handlers:
                handler.flush()            
        
            logging.info("Step 5: Cleanup completed successfully")       

        except Exception as e:
            print(f"Error during shutdown: {e}")
            logging.error(f"Error during shutdown: {e}")
            logging.error(traceback.format_exc())
            # エラーでもログをフラッシュ
            for handler in logging.getLogger().handlers:
                handler.flush()            
        finally:
            logging.info("Step 6: Destroying root window")
            for handler in logging.getLogger().handlers:
                handler.flush()            
            self.root.destroy()

    def select_listbox_item(self, listbox, item_text):
        # リストボックス内の項目を選択するヘルパー
        items = listbox.get(0, 'end')
        try:
            idx = items.index(item_text)
            listbox.selection_clear(0, 'end')
            listbox.selection_set(idx)
            listbox.activate(idx)
            listbox.see(idx)
            listbox.event_generate("<<ListboxSelect>>")
        except ValueError:
            pass
