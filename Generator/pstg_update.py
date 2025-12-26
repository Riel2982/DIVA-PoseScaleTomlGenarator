import sys
import os
import json
import time
import urllib.request
import urllib.error
import subprocess
import logging
import re
from datetime import datetime # 日時用
# from packaging import version # 軽量関数に置き換え
from pstg_util import VERSION

UPDATE_STATUS_FILE = "Settings/update_status.json"
REPO_OWNER = "Riel2982"
REPO_NAME = "DIVA-PoseScaleTomlGenarator"

def get_status_path():
    if getattr(sys, 'frozen', False): # PyInstallerでビルドされた場合
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else: # デバッグ用
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, UPDATE_STATUS_FILE)

def load_status():
    path = get_status_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_status(data):
    path = get_status_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, indent=4)

def parse_version(v_str):
    """バージョン文字列を数値タプルに変換 (例: 'v1.2.3' -> (1, 2, 3))"""
    if not v_str:
        return (0, 0, 0)
    # v除去とbeta除去 (例: v1.0.0-beta -> 1.0.0)
    v_clean = v_str.lstrip('v').split('-')[0]
    try:
        return tuple(map(int, v_clean.split('.')))
    except ValueError:
        return (0, 0, 0)

def parse_release_filename(filename):
    # 例: PoseScaleTomlGenerator_v0.1.1-beta.zip → {"version": "0.1.1-beta"}
    base = os.path.splitext(filename)[0]
    # parts = base.split("_")

    # 単純にアンダースコアで分割して、最後の部分を取得する
    if "_" in base:
        ver_str = base.split("_")[-1]
    else:
        ver_str = base
    # もし "v0.1.1" のように "v" が付いていたら除去
    if ver_str.startswith("v"):
        ver_str = ver_str[1:]
     
    # "beta数字" の形式のみ "0.0.数字" に変換 (v0.1.1-beta のような形式は除外)
    match = re.match(r"^beta(\d+)$", ver_str)
    if match:
        return {"version": f"0.0.{match.group(1)}"}
        
    return {"version": ver_str}
    # return {"version": parts[-1]}


def check_update(current_version, exe_name, force=False):
    """
    GitHubから最新リリースを確認して update_status.json に保存
    exe_name: 実行ファイル名 ("PoseScaleTomlGenerator.exe" / "PoseScaleConfigEditor.exe")
    current_version: 実行中のアプリバージョン
    """
    status = load_status()
    current_time = datetime.now()

    # current_versionが指定されていなければVERSIONを使用
    if current_version is None:
        current_version = VERSION

    # 毎回 current_version を更新
    if exe_name not in status:
        status[exe_name] = {}

    # 実際の内容が違う場合のみ更新フラグを立てる
    if status[exe_name].get('current_version') != current_version:
        status[exe_name]['current_version'] = current_version
        needs_save = True   # 要バージョン情報更新
    else:
        needs_save = False

    # 頻度制限チェック
    if not force and 'last_checked_iso' in status:
        try:
            last_checked = datetime.fromisoformat(status['last_checked_iso'])
            if (current_time - last_checked).total_seconds() < 3600:
                if needs_save:  # Trueの時
                    save_status(status) # status保存
                return status
        except Exception:
            pass

    # GitHub API呼び出し
    try:
        # urllibライブラリ使用
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        
        # タイムアウト設定付きでリクエスト作成
        req = urllib.request.Request(url)
        # GitHub APIはUser-Agentがないと拒否される場合があるため設定推奨（なくても動くことが多いが念のため）
        req.add_header('User-Agent', 'PoseScaleTomlGenerator-Updater')

        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status != 200:
                logging.error(f"Update Check Error: Status Code {res.status}")
                return None
            
            # JSON読み込み
            release = json.loads(res.read().decode('utf-8'))         
            latest_version = ""

            # ZIPファイルからバージョン抽出
            for asset in release.get('assets', []):
                if asset['name'].endswith(".zip"):
                    info = parse_release_filename(asset['name'])
                    latest_version = info['version']
                    break

            # exeアセット一覧
            exe_assets = {}
            for asset in release.get('assets', []):
                if asset['name'].endswith(".exe"):
                    exe_assets[asset['name']] = asset['browser_download_url']

            # 共通情報更新
            # status['last_checked_iso'] = current_time.isoformat() # マイクロ秒記録
            # status['latest_version'] = latest_version
            # status['release_url'] = release.get('html_url', '')
            # status['exe_assets'] = exe_assets

            # 更新
            status.update({
                "last_checked_iso": current_time.replace(microsecond=0).isoformat(),
                "latest_version": latest_version,
                "release_url": release.get('html_url', ''),
                "exe_assets": exe_assets
            })

            # availableフラグは削除 (もし残っていれば)
            status.pop('available', None)
            for exe in ['PoseScaleConfigEditor.exe', 'PoseScaleTomlGenerator.exe']:
                if exe in status:
                    status[exe].pop('available', None)

            save_status(status)
            return status

    except urllib.error.URLError as e:
        # ネットワークエラーやタイムアウト
        logging.error(f"Update check failed (URLError): {e}")
        return status
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return status

def check_and_notify_update_console(force=False):
    """アップデート情報を確認してコンソールに通知"""
    # from packaging import version as pkg_version

    try:
        # 更新チェックを実行して status を更新
        status = check_update(VERSION, "PoseScaleTomlGenerator.exe", force=force)
        latest_version = status.get('latest_version', '')

        if not latest_version:
            logging.info("No new updates.")
            return

        # Generator 用のキーを取得
        gen_status = status.get("PoseScaleTomlGenerator.exe", {})
        gen_available = False

        try:
            latest_clean = latest_version.lstrip('v')
            
            # Generatorのバージョン確認
            gen_current = gen_status.get('current_version', VERSION)
            gen_clean = gen_current.lstrip('v')
            gen_available = parse_version(latest_clean) > parse_version(gen_clean)
        except Exception as e:
            logging.error(f"Version comparison error: {e}")
            return
        
        ver_text = f"v{latest_version}" if not latest_version.startswith('v') else latest_version

        # アップデート通知をコンソールに表示
        if gen_available:
            logging.info(f"[UPDATE] New Release available: {ver_text}")
            logging.info(f"Current version: {gen_status.get('current_version')}")
            logging.info(f"Download here: {status.get('release_url', '')}")
            print("-" * 50)
            print(f"GitHub has a recent release: {ver_text}")
            print(f"For details, please check the GitHub release page.")
        else:
            logging.info("No new updates.")     

    except Exception as e:
        logging.error(f"Update check error: {e}")

if False:
    # 更新確認
    def generator_check_update():
        status = load_status()
        last_checked = status.get('last_checked', 0)
        now = time.time()

        # 指定期間以上経過していたら再チェック
        if now - last_checked > 86400:  # 1日以上経過
            logging.info("リリース情報が古いので再チェックします")
            editor_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "PoseScaleConfigEditor.exe")
            if os.path.exists(editor_path):
                subprocess.Popen([editor_path, "--check"])

        else:
            logging.info("リリース情報は最新です")
