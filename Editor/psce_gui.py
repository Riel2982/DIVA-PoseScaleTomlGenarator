import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import io
import configparser
import sys
from psce_util import ConfigUtility
from psce_translation import TranslationManager
from psce_history import HistoryManager
from psce_ui_general import GeneralSettingsTab
from psce_ui_profile import ProfileTab
from psce_ui_data import PoseDataTab
from psce_ui_map import PoseIDMapTab
from psce_key import KeyManager
from psce_ui_key import KeyMapTab

class ConfigEditorApp:
    def __init__(self, root):
        self.root = root
        self.utils = ConfigUtility()
        self.trans = TranslationManager()
        
        # Load Configs
        self.main_config = self.utils.load_config(self.utils.main_config_path)
        if self.main_config is None:
            # Configが読み込まれなかった場合のエラー
            # 言語設定はconfigに含まれているため、self.transを使用することはできません。標準のmessageboxを使用します。
            try:
                messagebox.showerror("Error", "Failed to load Config.ini.\nFile might be locked or corrupted.\nApplication will exit to prevent data loss.")
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
        
        self.root.title(self.trans.get("window_title"))
        
        # Set Icon（アイコンの設定）
        icon_path = None
        if getattr(sys, 'frozen', False):
            # If frozen, look in the temp folder where PyInstaller extracts files（凍結されている場合、PyInstallerがファイルを抽出する一時フォルダを検索する）
            icon_path = os.path.join(sys._MEIPASS, 'PoseScaleConfigEditor.ico')
        
        # Fallback or dev mode（フォールバックまたは開発モード）
        if not icon_path or not os.path.exists(icon_path):
            icon_path = os.path.join(self.utils.app_dir, 'PoseScaleConfigEditor.ico')
            
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except Exception as e:
                print(f"Failed to set icon: {e}")
        
        # Restore geometry（ウィンドウの復元）
        geometry = self.main_config.get('GeneralSettings', 'WindowGeometry', fallback="1100x800")
        self.root.geometry(geometry)

        self.current_pose_config = None
        self.current_pose_file_path = None
        
        self.selected_profile_section = None
        self.selected_pose_data_section = None
        self.selected_map_key = None
        
        
        self.history = HistoryManager(self)
        
        self.create_toolbar()
        
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


    def create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=2)
        toolbar.pack(side='top', fill='x')
        
        self.btn_undo = ttk.Button(toolbar, text=self.trans.get("undo"), command=self.undo, state='disabled')
        self.btn_undo.pack(side='left', padx=2)
        
        self.btn_redo = ttk.Button(toolbar, text=self.trans.get("redo"), command=self.redo, state='disabled')
        self.btn_redo.pack(side='left', padx=2)

        # タブの再読み込みボタン（右端）- 初期状態では非表示（GeneralSettingsTabで制御）
        self.refresh_btn = ttk.Button(toolbar, text=self.trans.get("refresh_tab"), command=self.refresh_current_tab)
        
    def toggle_refresh_button(self, visible):
        """リフレッシュボタンの表示/非表示を切り替え"""
        if visible:
            self.refresh_btn.pack(side='right', padx=2)
        else:
            self.refresh_btn.pack_forget()

    def get_current_context(self):
        """現在のタブを取得"""
        current_tab = self.notebook.select()
        return self.tab_map.get(current_tab)
    
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
                    print(f"Restored image from pending delete: {r}")
                    
            except Exception as e:
                print(f"Error checking restored images: {e}")

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

    def save_geometry(self):
        try:
            current_config = self.utils.load_config(self.utils.main_config_path)
            if current_config is None:
                print("Failed to load config for saving geometry. Skipping save.")
                return
            # このチェックは、Noneチェックが失敗を処理する場合、不要になりました
            #     current_config = self.main_config # Fallback（バックアップ）  
        except Exception:
            current_config = self.main_config

        if 'GeneralSettings' not in current_config: current_config['GeneralSettings'] = {}
        current_config['GeneralSettings']['WindowGeometry'] = self.root.geometry()
        
        self.utils.save_config(current_config, self.utils.main_config_path)

    def perform_cleanup(self):
        """終了時のクリーンアップ処理（画像削除など）"""
        # ゴミ箱フォルダを空にする
        trash_dir = os.path.join(self.utils.pose_images_dir, '_trash')
        if os.path.exists(trash_dir):
            try:
                import shutil
                shutil.rmtree(trash_dir)
                print(f"Cleaned up trash directory: {trash_dir}")
            except Exception as e:
                print(f"Failed to clean up trash: {e}")

    def on_closing(self):
        try:
            self.save_geometry()
            
            # 未削除の画像を処理
            if self.pending_delete_images:
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
                                except Exception as e:
                                    print(f"Failed to delete image {image_path}: {e}")
                            else:
                                print(f"Skipped deletion of restored image: {filename}")
                except Exception as e:
                    print(f"Error processing image deletions: {e}")
            
            # クリーンアップ処理
            self.perform_cleanup()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
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
