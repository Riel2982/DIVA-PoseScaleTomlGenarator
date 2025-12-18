import os
import sys
import time
import configparser
import shutil
import ctypes
import tkinter as tk
from tkinter import ttk
import logging
from logging.handlers import RotatingFileHandler



def make_hidden_folder(path):
    """
    フォルダを作成し、Windows環境では隠し属性を設定
    既に存在する場合も隠し属性を設定
    """
    # フォルダ作成
    os.makedirs(path, exist_ok=True)
    
    # Windows環境でのみ隠し属性を設定
    if os.name == 'nt':  # Windowsかチェック
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            logging.warning("Tempフォルダに隠し属性を設定できませんでした")
            # 失敗しても処理続行（隠し属性が必須ではないため）
            pass

def get_app_dir():
    """実行ファイルのディレクトリパスを取得"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable) # 実行ファイルのディレクトリ
    else:
        return os.path.dirname(os.path.abspath(__file__)) # 実行ファイルのディレクトリ

def setup_editor_logging(show_debug=False, output_log=False):
    """ログの初期化"""
    logger = logging.getLogger() # ロガー
    logger.setLevel(logging.DEBUG) # ログレベル

    if logger.hasHandlers(): # ハンドラーが設定されている場合
        logger.handlers.clear()

    # show_debug=Trueの時だけコンソール出力
    if show_debug:
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler = logging.StreamHandler()    # コンソールハンドラー
        console_handler.setLevel(logging.INFO)   # コンソールログレベル
        console_handler.setFormatter(console_formatter)  # コンソールフォーマッター
        logger.addHandler(console_handler)   # コンソールハンドラーを追加
    else:
        # show_debug=Falseの時はNullHandler（すべてのログメッセージを無視する特殊なハンドラー）で出力を完全に抑制
        logger.addHandler(logging.NullHandler())    # Pythonのloggingモジュールが勝手に「lastResort」ハンドラーを使うのでその対策

    # output_log=Trueの時だけファイル出力
    if output_log:
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

        app_dir = get_app_dir()  # 実行ファイルのディレクトリ
        log_dir = os.path.join(app_dir, 'logs')  # ログディレクトリ
        os.makedirs(log_dir, exist_ok=True)  # ログディレクトリを作成
 
        # ファイルハンドラー
        log_file = os.path.join(log_dir, 'Editor.log') # ログファイル
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024, # ログファイルサイズ
            backupCount=5, # バックアップファイル数
            encoding='utf-8' # エンコーディング
        ) # ログハンドラー
        file_handler.setLevel(logging.INFO) # ファイルログレベル
        file_handler.setFormatter(file_formatter) # ファイルフォーマッター
        logger.addHandler(file_handler) # ファイルハンドラーを追加

        debug_log_file = os.path.join(log_dir, 'debug_data.log') # デバッグログファイル
        debug_handler = RotatingFileHandler(
            debug_log_file,
            maxBytes=10 * 1024 * 1024, # デバッグログファイルサイズ
            backupCount=5, # バックアップファイル数
            encoding='utf-8' # エンコーディング
        ) # デバッグハンドラー
        debug_handler.setLevel(logging.DEBUG) # デバッグログレベル
        debug_handler.setFormatter(file_formatter) # デバッグフォーマッター
        debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG) # デバッグフィルター
        logger.addHandler(debug_handler) # デバッグハンドラーを追加

        logging.info("=== Editor started ===")
        

# 様々な処理関数クラス
class ConfigUtility:
    # 初期化
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))

        self.settings_dir = os.path.join(self.app_dir, 'Settings')  # 設定ディレクトリ
        self.pose_data_dir = os.path.join(self.settings_dir, 'PoseScaleData')  # ポーズデータディレクトリ
        self.pose_images_dir = os.path.join(self.settings_dir, 'PoseImages')  # ポーズ画像ディレクトリ
        
        self.main_config_path = os.path.join(self.settings_dir, 'Config.ini')  # メイン設定ファイル
        self.profile_config_path = os.path.join(self.settings_dir, 'TomlProfile.ini')  # プロファイル設定ファイル
        self.pose_id_map_path = os.path.join(self.settings_dir, 'PoseIDMap.ini')  # ポーズIDマップファイル
        
        self._ensure_directories()  # ディレクトリの確保
        self._ensure_default_files()  # デフォルトファイルの確保

    # ディレクトリの確保
    def _ensure_directories(self):
        os.makedirs(self.settings_dir, exist_ok=True)
        os.makedirs(self.pose_data_dir, exist_ok=True)
        os.makedirs(self.pose_images_dir, exist_ok=True)

    # デフォルトファイルの確保
    def _ensure_default_files(self):
        # Main Config（メイン設定ファイル）
        if not os.path.exists(self.main_config_path):
            # メイン設定ファイルが存在しない場合の初期設定
            config = configparser.ConfigParser()
            config.optionxform = str # Preserve case  （大文字小文字を区別する）
            config['FarcPack'] = {'FarcPackPath': ''}
            config['GeneralSettings'] = {
                'SaveInParentDirectory': 'False',
                'DefaultPoseFileName': 'gm_module_pose_tbl',
                'UseModuleNameContains': 'False',
                'Language': 'en'
            }
            config['DebugSettings'] = {
                'ShowDebugSettings': 'False',
                'OutputLog': 'False',
                'DeleteTemp': 'True',
                'HistoryLimit': '50'
            }
            self.save_config(config, self.main_config_path)

        # Profile Config（プロファイル設定）
        if not os.path.exists(self.profile_config_path):
            with open(self.profile_config_path, 'w', encoding='utf-8-sig') as f:
                f.write("")

        # Pose ID Map（ポーズIDマップ）
        if not os.path.exists(self.pose_id_map_path):
            with open(self.pose_id_map_path, 'w', encoding='utf-8-sig') as f:
                f.write("[PoseIDs]\n")

        # Default Pose Data（デフォルトのポーズデータ）
        default_pose_data_path = os.path.join(self.pose_data_dir, 'PoseScaleData.ini')
        if not os.path.exists(default_pose_data_path): 
            # デフォルトのポーズデータが存在しない場合の初期設定
            config = configparser.ConfigParser()
            config.optionxform = str # Preserve case（大文字小文字を区別する）
            config.add_section('PoseScaleSetting_Default')
            config.set('PoseScaleSetting_Default', 'Chara', 'MIKU')
            config.set('PoseScaleSetting_Default', 'ModuleNameContains', 'ミク, Miku')
            config.set('PoseScaleSetting_Default', 'PoseID', '')
            config.set('PoseScaleSetting_Default', 'Scale', '1.0')
            self.save_config(config, default_pose_data_path)

    def create_restart_vbs(self):
        """再起動用のVBScriptを作成（EXE用）"""
        if not getattr(sys, 'frozen', False):
            return  # 開発モードでは不要
        
        exe_path = sys.executable
        vbs_path = os.path.join(self.settings_dir, 'restart.vbs')
        
        # VBScriptで再起動（環境変数の問題を回避）
        # 2秒待機してからEXEを起動
        content = f'Set WshShell = CreateObject("WScript.Shell")\n'
        content += 'WScript.Sleep 2000\n'
        content += f'WshShell.Run "{exe_path}", 1, False\n'
        
        try:
            # VBScriptはShift_JIS(cp932)またはASCIIで保存する必要がある
            # UTF-8だと日本語パスでエラーになる
            with open(vbs_path, 'w', encoding='cp932') as f:
                f.write(content)
        except Exception as e:
            logging.error(f"Failed to create restart.vbs: {e}")

    # Configファイルの読み込み
    def load_config(self, path):
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case
        if os.path.exists(path):
            try:
                # 開けないファイルがロックされている場合のエラーを取得する（config.read()はエラーを無視するため、空のconfigとデータの損失を引き起こす可能性がある）
                with open(path, 'r', encoding='utf-8-sig') as f:
                    config.read_file(f)
            except UnicodeDecodeError: # UnicodeDecodeErrorを取得する
                try:
                    with open(path, 'r', encoding='utf-8-sig') as f:
                        config.read_file(f)
                except UnicodeDecodeError: # UnicodeDecodeErrorを取得する
                    with open(path, 'r', encoding='cp932') as f:
                        config.read_file(f)
            except OSError as e:
                # ファイルがロックされているか、読み取れない場合、再起動または処理を停止する（空のconfigを返すと、データが失われることを危険とする）
                logging.error(f"Error loading config {path}: {e}")
                # 呼び出し元はConfigParserを期待するため、失敗を示すためにNoneを返す（空のconfigを返すと、アプリケーションは既定値でファイルを上書き）
                # データを失うことよりもクラッシュまたはエラーを表示する方が良いので、Noneを返して呼び出し元を処理する（psce_gui.pyはconfigオブジェクトを期待するのでpsce_gui.pyを更新してNoneまたは、raiseを返すことを検討する）
                return None
        return config

    # Configファイルの保存
    def save_config(self, config, path):
        config.optionxform = str
        
        # ファイルがロックされている場合の再試行ロジック）
        max_retries = 3
        for i in range(max_retries):
            try:
                # 直接書き込みを避けるために「Ransomware」のヒューリスティクスを回避する
                # 原子的ではない（クラッシュ時に破損のリスクが高い）、しかしAVがリネームをブロックする場合、必要不可欠
                with open(path, 'w', encoding='utf-8-sig') as f:
                    config.write(f)
                return True
            except OSError as e:
                if i < max_retries - 1:
                    time.sleep(0.2) # Wait a bit
                    continue
                else:
                    logging.error(f"Failed to save config {path}: {e}")
                    raise e
        return False

    # 画像ファイルのパスを取得
    def get_image_path(self, image_name):
        if not image_name: return None
        path = os.path.join(self.pose_images_dir, image_name)
        if os.path.exists(path):
            return path
        return None

    # ポーズIDに対応する画像ファイルを検索
    def find_image_for_pose(self, pose_id):
        """Find image matching PoseID_*.ext"""
        if not pose_id: return None
        for f in os.listdir(self.pose_images_dir):
            if f.startswith(f"{pose_id}_") and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                return os.path.join(self.pose_images_dir, f)
        return None

    # 画像ファイルをインポート
    def import_image(self, source_path, target_filename=None):
        if not source_path or not os.path.exists(source_path):
            return None
        
        # ファイル名を設定
        if target_filename:
            filename = target_filename
            # 拡張子が一致するか、有効な拡張子であるかを確認する
            _, ext = os.path.splitext(source_path)
            if not filename.lower().endswith(ext.lower()):
                 filename += ext
        else:
            filename = os.path.basename(source_path)
            
        dest_path = os.path.join(self.pose_images_dir, filename)
        try:
            shutil.copy2(source_path, dest_path)
            return filename
        except Exception:
            return None

    # 画像ファイルをリネーム
    def rename_image(self, old_filename, new_filename):
        if not old_filename or not new_filename: return False
        old_path = os.path.join(self.pose_images_dir, old_filename)
        new_path = os.path.join(self.pose_images_dir, new_filename)
        
        # 画像ファイルが存在するか、新しいファイル名が存在しないかを確認する
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                os.rename(old_path, new_path)
                return True
            except Exception:
                return False
        return False


class CustomMessagebox:
    @staticmethod
    def _center_window(win, parent=None):
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        
        # マウスカーソル位置を取得
        ptr_x, ptr_y = win.winfo_pointerxy()
        logging.info(f"DEBUG: Mouse Ptr: ({ptr_x}, {ptr_y})") 
        
        # マウス位置の少し右下に表示
        x = ptr_x - (width // 2)
        y = ptr_y + 20
        
        # 画面外にはみ出さないように調整（簡易版）
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()
        

        win.geometry(f'+{x}+{y}')

        """
        if parent:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        else:
            screen_width = win.winfo_screenwidth()
            screen_height = win.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
        win.geometry(f'+{x}+{y}')
        """

        
    @staticmethod
    def show_info(title, message, parent=None):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        lbl = ttk.Label(frame, text=message, wraplength=400)
        lbl.pack(pady=(0, 20))
        
        btn = ttk.Button(frame, text="OK", command=dialog.destroy)
        btn.pack()
        
        CustomMessagebox._center_window(dialog, parent)
        parent.wait_window(dialog)

    @staticmethod
    def show_error(title, message, parent=None):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Error icon could be added here
        lbl = ttk.Label(frame, text=message, wraplength=400, foreground='red')
        lbl.pack(pady=(0, 20))
        
        btn = ttk.Button(frame, text="OK", command=dialog.destroy)
        btn.pack()
        
        CustomMessagebox._center_window(dialog, parent)
        parent.wait_window(dialog)

    @staticmethod
    def ask_yes_no(title, message, parent=None):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        
        result = {'value': False}
        
        def on_yes():
            result['value'] = True
            dialog.destroy()
            
        def on_no():
            result['value'] = False
            dialog.destroy()
            
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        
        lbl = ttk.Label(frame, text=message, wraplength=400)
        lbl.pack(pady=(0, 20))
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()
        
        ttk.Button(btn_frame, text="Yes", command=on_yes).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="No", command=on_no).pack(side='left', padx=5)
        
        CustomMessagebox._center_window(dialog, parent)
        parent.wait_window(dialog)
        return result['value']


def normalize_comma_separated_string(text_or_var):
    """
    カンマ区切り文字列（または変数）を正規化する。
    - 全角カンマ・読点を半角に変換
    - 前後の空白を削除
    - 空の要素を削除
    - カンマ+スペース区切りで再結合
    StringVarが渡された場合、値を正規化してセットし直す（画面更新）
    """
    # StringVar対応
    target = text_or_var
    is_var = hasattr(text_or_var, 'get') and hasattr(text_or_var, 'set')
    
    if is_var:
        target = text_or_var.get()
        
    if not isinstance(target, str):
        target = str(target)
    
    if not target:
        normalized = ""
    else:
        # --- 既存ロジックの適用 ---
        # 全角カンマと読点を半角に
        s = target.replace('，', ',').replace('、', ',')
        
        # 分割して空白削除
        parts = [p.strip() for p in s.split(',')]
        
        # 空の要素を削除して再結合（カンマ+スペース形式）
        normalized = ", ".join([p for p in parts if p])
        # ------------------------
    
    # 画面更新
    if is_var and target != normalized:
        text_or_var.set(normalized)
        
    return normalized


def normalize_text(text_or_var):
    """
    テキスト（または変数）を正規化する
    - 前後の空白（半角・全角）を削除
    StringVarが渡された場合、値を正規化してセットし直す（画面更新）
    """
    # StringVar対応
    target = text_or_var
    is_var = hasattr(text_or_var, 'get') and hasattr(text_or_var, 'set')
    
    if is_var:
        target = text_or_var.get()
    
    if not isinstance(target, str):
        target = str(target)
        
    if not target:
        normalized = ""
    else:
        # Pythonのstrip()は全角スペースも削除する
        normalized = target.strip()
    
    # 画面更新
    if is_var and target != normalized:
        text_or_var.set(normalized)
        
    return normalized


"""
# 半角補正
def normalize_comma_separated_string(s):
    # カンマ区切り文字列を正規化する
    # - 全角カンマ・読点を半角に変換
    # - 前後の空白を削除
    # - 空の要素を削除

    if not s:
        return ""
    
    # 全角カンマと読点を半角に
    s = s.replace('，', ',').replace('、', ',')
    
    # 分割して空白削除
    parts = [p.strip() for p in s.split(',')]
    
    # 空の要素を削除して再結合（カンマ+スペース形式）
    return ", ".join([p for p in parts if p])

# 末尾のスペースを削除
def normalize_text(text):
    if not text:
        return ""
    # Pythonのstrip()は全角スペースも削除する
    return text.strip()
"""



def get_app_version():
    """EXEのバージョンリソースを取得する（開発環境はversion.txt）"""
    
    # 1. 凍結アプリ(EXE)の場合: ctypesで自分自身のバージョンリソースを読む
    if getattr(sys, 'frozen', False):
        try:
            filename = sys.executable
            size = ctypes.windll.version.GetFileVersionInfoSizeW(filename, None)
            if size > 0:
                res = ctypes.create_string_buffer(size)
                ctypes.windll.version.GetFileVersionInfoW(filename, None, size, res)
                r = ctypes.c_void_p()
                l = ctypes.c_uint()
                
                # VS_FIXEDFILEINFO構造体を取得
                # ルートブロック "\" を指定すると固定情報が取れる
                if ctypes.windll.version.VerQueryValueW(res, "\\", ctypes.byref(r), ctypes.byref(l)):
                    class VS_FIXEDFILEINFO(ctypes.Structure):
                        _fields_ = [
                            ("dwSignature", ctypes.c_long),
                            ("dwStrucVersion", ctypes.c_long),
                            ("dwFileVersionMS", ctypes.c_long),
                            ("dwFileVersionLS", ctypes.c_long),
                            ("dwProductVersionMS", ctypes.c_long),
                            ("dwProductVersionLS", ctypes.c_long),
                            ("dwFileFlagsMask", ctypes.c_long),
                            ("dwFileFlags", ctypes.c_long),
                            ("dwFileOS", ctypes.c_long),
                            ("dwFileType", ctypes.c_long),
                            ("dwFileSubtype", ctypes.c_long),
                            ("dwFileDateMS", ctypes.c_long),
                            ("dwFileDateLS", ctypes.c_long),
                        ]
                    
                    # メモリキャスト
                    fi = ctypes.cast(r, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
                    # バージョン番号の抽出 (MSの上位・下位, LSの上位・下位)
                    major = fi.dwFileVersionMS >> 16
                    minor = fi.dwFileVersionMS & 0xFFFF
                    build = fi.dwFileVersionLS >> 16
                    revision = fi.dwFileVersionLS & 0xFFFF
                    
                    # "v1.0.0" 形式に整形（revisionが0なら省略などの調整はお好みで）
                    if revision > 0:
                        return f"v{major}.{minor}.{build}.{revision}"
                    else:
                        return f"v{major}.{minor}.{build}"
                        
        except Exception as e:
            logging.error(f"Failed to read version resource: {e}")
            pass

    # 2. 開発環境または取得失敗時: version.txt を読む
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        version_path = os.path.join(app_dir, 'version.txt')
        if os.path.exists(version_path):
            with open(version_path, 'r', encoding='utf-8') as f:
                ver = f.read().strip()
                return f"v{ver}" if not ver.startswith("v") else ver
    except:
        pass

    return "v0.0.0-dev"

VERSION = get_app_version()