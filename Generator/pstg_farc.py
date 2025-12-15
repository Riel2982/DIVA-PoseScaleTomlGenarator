import sys
import os
import shutil
import subprocess
import logging
from pstg_util import get_temp_dir, make_hidden_folder


def get_dragged_file():
    """コマンドライン引数からドラッグされたファイルを取得"""
    if len(sys.argv) != 2:
        print("ファイルをドラッグアンドドロップしてください")
        logging.error("引数が正しくありません。ファイルをドラッグアンドドロップしてください。")
        sys.exit(1)
    dragged_file = sys.argv[1] # ドラッグアンドドロップされたファイル
    logging.info(f"ドラッグアンドドロップされたファイルパス: {dragged_file}")
    return dragged_file

def process_file(dragged_file, farc_pack_path):
    """ファイルをTempにコピーし、FarcPackで解凍する"""
    dragged_file = dragged_file.strip('{}') # ドラッグアンドドロップされたファイル
    temp_dir = get_temp_dir() # 一時ディレクトリ
    
    # Tempフォルダの作成（存在しない場合）
    # os.makedirs(temp_dir, exist_ok=True)
    # Tempフォルダの作成（存在しない場合）+ 隠し属性設定
    make_hidden_folder(temp_dir)

    basename = os.path.basename(dragged_file) # ドラッグアンドドロップされたファイル
    temp_file_path = os.path.join(temp_dir, basename) # 一時ファイルパス

    # ファイルコピー
    try:
        shutil.copy(dragged_file, temp_file_path)
        logging.info(f"ファイルがTempフォルダにコピーされました: {temp_file_path}")
    except Exception as e:
        logging.error(f"ファイルコピー中にエラーが発生しました: {e}")
        raise

    # FarcPackで解凍
    open_with_farcPack(temp_file_path, farc_pack_path)
    
    return os.path.dirname(dragged_file)

def open_with_farcPack(file_path, farc_pack_path):
    """FarcPackを実行してファイルを解凍"""
    if not os.path.exists(farc_pack_path):
        logging.error(f"FarcPackが存在しません: {farc_pack_path}")
        return

    command = f'"{farc_pack_path}" "{file_path}"'
    logging.info(f"実行コマンド: {command}")
    
    try:
        # cwdをTempディレクトリに設定して実行することで、その場に解凍する（FarcPackの仕様依存）
        result = subprocess.run(command, shell=True, capture_output=True, text=True) # FarcPackを実行
        
        # FarcPackの実行結果をログに出力する
        if result.returncode == 0:
            logging.info("FarcPackでファイルを開きました")
            temp_dir = get_temp_dir()
            extracted_dirs = os.listdir(temp_dir)
            logging.info(f"解凍後のディレクトリ内容: {extracted_dirs}")
        else: # FarcPackの実行に失敗した場合
            logging.error(f"FarcPackの実行に失敗しました: {result.stderr}")
            
    except Exception as e:
        logging.error(f"FarcPack実行中にエラーが発生しました: {e}")
