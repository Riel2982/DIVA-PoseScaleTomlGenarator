import configparser
import os
import tkinter as tk

class KeyManager:
    """
    ショートカットキーを管理するクラス。
    KeyMap.ini の読み込み・保存、およびキーイベントのバインディングとアクションの実行を担当。
    """
    def __init__(self, app):
        self.app = app
        self.config_path = os.path.join(self.app.utils.settings_dir, 'KeyMap.ini')
        self.key_map = configparser.ConfigParser()
        self.key_map.optionxform = str  # 大文字小文字を区別する
        
        # デフォルトのショートカットキー設定
        # Windows標準のショートカット（Ctrl+Cなど）との競合を避けるため、
        # 修飾キー(Ctrl, Alt, Shift)を組み合わせたり、ファンクションキーを使用することを推奨。
        self.default_map = {
            'SaveCurrentTab': '<Control-s>',           # 現在のタブの内容を保存
            'SaveAndExit': '<Control-q>',               # 保存して終了
            'ExitNoSave': '<Escape>',                    # 保存せずに終了
            'RestartNoSave': '<Control-r>',             # 保存せずに再起動
            'SaveAndRestart': '<Control-Shift-R>',      # 保存して再起動
            'Undo': '<Control-Shift-Z>',                # 元に戻す (HistoryManager)
            'Redo': '<Control-Shift-Y>',                # やり直す (HistoryManager)
            'ToggleDebugSettings': '<Shift-F12>',             # Debug設定表示切替
        }
        
        # アクションの定義
        self.actions = {
            'SaveCurrentTab': self.action_save_current_tab,    # 現在のタブの内容を保存
            'SaveAndExit': self.action_save_and_exit,          # 保存して終了
            'ExitNoSave': self.action_exit_no_save,            # 保存せずに終了
            'RestartNoSave': self.action_restart_no_save,      # 保存せずに再起動
            'SaveAndRestart': self.action_save_and_restart,    # 保存して再起動
            'Undo': self.action_undo,                          # 元に戻す (HistoryManager)
            'Redo': self.action_redo,                          # やり直す (HistoryManager)
            'ToggleDebugSettings': self.action_toggle_debug,   # Debug設定表示切替
        }
        
        # キー設定を読み込む
        self.load_key_map()

    def load_key_map(self):
        # KeyMap.ini から設定を読み込み、ファイルが存在しない場合はデフォルト設定で作成。
        if not os.path.exists(self.config_path):
            self.create_default_key_map()
        # KeyMap.ini から設定を読み込む
        else:
            try:
                self.key_map.read(self.config_path, encoding='utf-8-sig')
                # 設定ファイルにセクションがない、またはキーが不足している場合は補完する
                if not self.key_map.has_section('Shortcuts'):
                    self.key_map.add_section('Shortcuts')
                
                changed = False
                
                # 古いキー名から新しいキー名への移行処理
                if self.key_map.has_option('Shortcuts', 'SaveGeneralSettings'):
                    # 古いキー設定を取得
                    old_key = self.key_map.get('Shortcuts', 'SaveGeneralSettings')
                    # 新しいキー名で設定
                    self.key_map.set('Shortcuts', 'SaveCurrentTab', old_key)
                    # 古いキー名を削除
                    self.key_map.remove_option('Shortcuts', 'SaveGeneralSettings')
                    changed = True
                
                # 不足しているキーを補完
                for action, default_key in self.default_map.items():
                    if not self.key_map.has_option('Shortcuts', action):
                        self.key_map.set('Shortcuts', action, default_key)
                        changed = True
                
                if changed:
                    self.save_key_map()
            except Exception as e:
                print(f"Failed to load KeyMap.ini: {e}")
                self.create_default_key_map()

    def create_default_key_map(self):
        # デフォルトの設定で KeyMap.ini を作成
        self.key_map = configparser.ConfigParser()
        self.key_map.optionxform = str
        self.key_map.add_section('Shortcuts')
        for action, key in self.default_map.items():
            self.key_map.set('Shortcuts', action, key)
        self.save_key_map()

    def save_key_map(self):
        # 現在の設定を KeyMap.ini に保存
        try:
            with open(self.config_path, 'w', encoding='utf-8-sig') as f:
                self.key_map.write(f)
        except Exception as e:
            print(f"Failed to save KeyMap.ini: {e}")

    def apply_shortcuts(self, root):
        # ルートウィンドウにショートカットキーをバインド
        # 既存のバインドを上書きして再設定。
        # 古いバインドを追跡して unbind するロジックではなく、シンプルに設定されたキーに対して bind を行う。
        
        if not self.key_map.has_section('Shortcuts'):
            return

        for action, func in self.actions.items():
            key = self.key_map.get('Shortcuts', action, fallback='')
            if key:
                # tkinterのイベントバインド（ラムダ式で event 引数を受け取るようにしないとエラーになる）
                try:
                    root.bind(key, lambda event, f=func: f(event))
                except tk.TclError:
                    print(f"Invalid key format: {key}")

    # --- Actions ---

    def action_save_current_tab(self, event=None):
        """現在のタブの内容を保存するアクション（タブ別処理）"""
        context = self.app.get_current_context()
        
        # KeyMapタブではショートカット無効化（キー入力と競合する可能性があるため）
        if context == 'key':
            return
        
        # コンテキストに応じて保存メソッドを呼び出す
        if context == 'general':
            if hasattr(self.app, 'general_tab'):
                self.app.general_tab.save_general_settings()
        elif context == 'profile':
            if hasattr(self.app, 'ui_profile'):
                self.app.ui_profile.save_profile()
        elif context == 'data':
            if hasattr(self.app, 'pose_data_tab'):
                self.app.pose_data_tab.save_pose_data()
        elif context == 'map':
            if hasattr(self.app, 'map_tab'):
                self.app.map_tab.save_map_entry()

    def action_save_and_exit(self, event=None):
        """現在のタブを保存して終了するアクション"""
        # 現在のタブを保存（SaveCurrentTabと同じロジック）
        self.action_save_current_tab()
        self.app.save_geometry()
        self.app.root.destroy()

    def action_exit_no_save(self, event=None):
        """保存せずに終了するアクション"""
        self.app.root.destroy()

    def action_restart_no_save(self, event=None):
        """保存せずに再起動するアクション"""
        self.restart_app()

    def action_save_and_restart(self, event=None):
        """現在のタブを保存して再起動するアクション"""
        try:
            # 現在のタブを保存（SaveCurrentTabと同じロジック）
            self.action_save_current_tab()
            self.app.save_geometry()
        except Exception as e:
            print(f"Error saving before restart: {e}")
        self.restart_app()

    def action_undo(self, event=None):
        """元に戻すアクション"""
        context = self.app.get_current_context()
        if context:
            self.app.undo()

    def action_redo(self, event=None):
        """やり直すアクション"""
        context = self.app.get_current_context()
        if context:
            self.app.redo()
    
    def action_toggle_debug(self, event=None):
        """Debug設定の表示切替"""
        if hasattr(self.app, 'general_tab'):
            current = self.app.show_debug_var.get()
            new_value = not current
            self.app.show_debug_var.set(new_value)
            self.app.general_tab.toggle_debug_settings()

    def restart_app(self):
        """アプリケーションを再起動する内部メソッド"""
        import sys
        import subprocess
        
    def restart_app(self):
        """アプリケーションを再起動する内部メソッド"""
        import sys
        import subprocess
        
        # 現在のウィンドウを閉じる（リソース解放のため）
        # self.app.root.destroy() # ここでdestroyすると後続の処理が動かない可能性があるため、sys.exit直前に任せるか、非表示にする
        
        # 新しいインスタンスを起動
        if getattr(sys, 'frozen', False):
            # EXEの場合
            try:
                subprocess.Popen([sys.executable], creationflags=subprocess.CREATE_NEW_CONSOLE)
            except Exception as e:
                print(f"Failed to restart exe: {e}")
                # フォールバック
                try:
                    os.startfile(sys.executable)
                except:
                    pass
        else:
            # 開発モードの場合
            try:
                subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NEW_CONSOLE)
            except:
                 subprocess.Popen([sys.executable] + sys.argv)

        # 現在のプロセスを終了
        self.app.perform_cleanup()
        self.app.root.quit() # メインループを抜ける
        sys.exit()
