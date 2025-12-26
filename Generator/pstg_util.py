import os
import shutil
import logging
import sys
import ctypes
from logging.handlers import RotatingFileHandler
from datetime import datetime


def get_app_dir():
    """実行ファイルのディレクトリパスを取得"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable) # 実行ファイルのディレクトリ
    else:
        return os.path.dirname(os.path.abspath(__file__)) # 実行ファイルのディレクトリ

def get_temp_dir():
    """Tempディレクトリのパスを取得"""
    return os.path.join(get_app_dir(), 'Temp') # Tempディレクトリ

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
            logging.error("Tempフォルダに隠し属性を設定できませんでした")
            # 失敗しても処理続行（隠し属性が必須ではないため）
            pass

def setup_logging(show_debug=False, output_log=False):
    """ログの初期化"""
    logger = logging.getLogger() # ロガー
    logger.setLevel(logging.DEBUG) # ログレベル

    if logger.hasHandlers(): # ハンドラーが設定されている場合
        logger.handlers.clear()

    app_dir = get_app_dir()  # 実行ファイルのディレクトリ
    log_dir = os.path.join(app_dir, 'logs')  # ログディレクトリ

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
        # デバッグモードがOFFの時、logsフォルダが存在すれば削除する
        if os.path.exists(log_dir):
            try:
                shutil.rmtree(log_dir, ignore_errors=True)
                logging.info(f"Cleaned up logs directory: {log_dir}") # NullHandler行きになるが念のため
            except Exception:
                pass  

    # output_log=Trueの時だけファイル出力
    if output_log:
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

        os.makedirs(log_dir, exist_ok=True)  # ログディレクトリを作成
 
        # ファイルハンドラー
        log_file = os.path.join(log_dir, 'Generator.log') # ログファイル
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
      

def clean_temp_dir():
    """Tempディレクトリを削除"""
    temp_dir = get_temp_dir() # Tempディレクトリ
    if os.path.exists(temp_dir): # Tempディレクトリが存在する場合
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logging.info(f"Tempディレクトリを削除しました: {temp_dir}")
        except Exception as e:
            logging.warning(f"Tempディレクトリの削除に失敗しました (無視します): {e}")

def save_file_with_timestamp(file_path, data, overwrite=False):
    """タイムスタンプ付きでファイルを保存 (overwrite=Trueの場合は上書き)"""
    if os.path.exists(file_path) and not overwrite: # 既存のファイルが存在する場合
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S") # タイムスタンプ
        base, ext = os.path.splitext(file_path) # ファイル名と拡張子
        rename_path = f"{base}_{timestamp}{ext}" # リネーム後のファイル名
        try:
            os.rename(file_path, rename_path)
            logging.info(f"既存のファイルをリネームしました: {rename_path}")
        except OSError as e:
            logging.error(f"ファイルのリネームに失敗しました: {e}")
    elif os.path.exists(file_path) and overwrite: # 既存のファイルが存在する場合
        logging.info(f"既存のファイルを上書きします: {file_path}")

    try: # ファイルを保存
        with open(file_path, 'w', encoding='utf-8') as save_file:
            save_file.write(data)
        logging.info(f'ファイルを保存しました {file_path}')
    except OSError as e: # ファイルの保存に失敗しました
        logging.error(f"ファイルの保存に失敗しました: {e}")

def load_chara_mapping():
    """キャラクター名のマッピング関数を返す"""
    setting_chara_mapping = {
        "MIKU": "MIK", "RIN": "RIN", "LEN": "LEN", "LUKA": "LUK",
        "NERU": "NER", "HAKU": "HAK", "KAITO": "KAI", "MEIKO": "MEI",
        "SAKINE": "SAK", "TETO": "TET"
    }

    toml_chara_mapping = {
        "MIKU": "0", "RIN": "1", "LEN": "2", "LUKA": "3",
        "NERU": "4", "HAKU": "5", "KAITO": "6", "MEIKO": "7",
        "SAKINE": "8", "TETO": "9"
    }

    # キャラクター名のマッピング関数
    def map_chara(chara, mapping_type="module_to_setting"):
        if mapping_type == "module_to_setting": # モジュール名を設定名に変換
            return setting_chara_mapping.get(chara, chara)
        elif mapping_type == "module_to_cos_scale": # モジュール名をCOS値に変換
            return toml_chara_mapping.get(chara, chara)
        else:
            return chara

    return map_chara

def is_match(name, contains_str, exclude_str=None):
    """モジュール名がキーワードにマッチするか判定 (ORマッチ)"""
    if not contains_str: # contains_strが空の場合
        return False
        
    contains = contains_str.split(',') # contains_strをカンマ区切りで分割
    includes = [word.strip() for word in contains if word.strip() and not word.strip().startswith('|')] # includes（含むキーワード）
    
    # contains_str内の|で始まる除外キーワードのサポート（専用設定項目を設けたので無効化中）
    # legacy_excludes = [word.strip()[1:] for word in contains if word.strip().startswith('|')] # legacy_excludes（除外キーワード）
    
    explicit_excludes = [] # explicit_excludes（明示的除外キーワード）
    if exclude_str: # exclude_strが空の場合
        explicit_excludes = [word.strip() for word in exclude_str.split(',') if word.strip()] # explicit_excludes（明示的除外キーワード）
        
    # excludes = legacy_excludes + explicit_excludes # excludes（除外キーワード）
    excludes = explicit_excludes

    # 文字化け対策
    if '\ufffd' in includes:
        logging.warning(f"設定 {contains_str} に無効な文字が含まれているため、そのキーワードは無視します。")
        includes = [i for i in includes if i != '\ufffd']

    logging.debug(f"Checking Module: {name} against Includes: {includes}, Excludes: {excludes}")

    # Exclude check (if ANY exclude word is found, return False)（ANDマッチ）
    if any(exc in name for exc in excludes):
        return False

    # ORマッチで処理
    return any(inc in name for inc in includes)


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

