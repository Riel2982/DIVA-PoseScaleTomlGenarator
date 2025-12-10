import os
import logging
import subprocess
import sys
import pstg_config
import pstg_farc
import pstg_extract
import pstg_loader
import pstg_pose
import pstg_scale
import pstg_util

def launch_editor():
    """FarckPackパスが有効でない場合、PoseScaleConfigEditor.exeを起動する"""
    # 実行ファイルのディレクトリを取得
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable) # 実行ファイルのディレクトリ
        editor_path = os.path.join(app_dir, 'PoseScaleConfigEditor.exe') # 実行ファイルのディレクトリに配置されているPoseScaleConfigEditor.exe
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        editor_path = os.path.join(app_dir, 'psce_main.py') # For dev（開発用）

    # 設定エディタの起動
    if os.path.exists(editor_path):
        print("設定エディタを起動します...")
        # Pythonファイルの場合
        if editor_path.endswith('.py'):
             subprocess.Popen([sys.executable, editor_path])
        else:
             # 完全な分離とファイルロックを避けるためにcreationflagsを使用
             # DETACHED_PROCESS = 0x00000008（分離プロセス）
             # CREATE_NEW_PROCESS_GROUP = 0x00000200（新しいプロセスグループ）
             subprocess.Popen([editor_path], creationflags=0x00000008 | 0x00000200)
    else:
        print(f"エラー: 設定エディタが見つかりません: {editor_path}")
        input("Enterキーを押して終了してください...")

# メイン処理
def main():
    try:
        # 1. 設定の読み込み
        app_config = pstg_config.load_app_config()
        
        # Config.iniが存在しない、または読み込み失敗した場合
        if not app_config:
            print("設定ファイルが見つかりません。")
            launch_editor()
            return

        # FarcPackPathの検証
        farc_pack_path = app_config.get('FarcPackPath', '')
        if not farc_pack_path or not os.path.exists(farc_pack_path) or not os.path.basename(farc_pack_path).lower() == 'farcpack.exe':
            print("有効なFarcPackパスが設定されていません。")
            launch_editor()
            return

        # 2. ログの初期化（削除予定）
        # debug_settings = app_config['DebugSettings'] 
        
        # DebugSettingsの読み込み
        # app_configにはConfigParserオブジェクトが含まれている
        config_parser = app_config['ConfigParser']
        
        show_debug = config_parser.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False)
        output_log = app_config.get('OutputLog', False)
        delete_temp = app_config.get('DeleteTemp', True)

        if not show_debug:
            # デバッグ設定が非表示の場合、デフォルト値を強制的に使用する
            output_log = False
            delete_temp = True
            
        pstg_util.setup_logging(output_log=output_log)
        
        # プログラム開始ログ
        logging.info("プログラムを開始します")

        # 3. ファイルのドラッグ＆ドロップ処理(引数がない場合は使い方を表示して終了
        if len(sys.argv) < 2:
            print("Usage: Drag and drop a file onto this executable, or use the 'Send to' menu.")
            input("Press Enter to exit...")
            return

        dragged_file = pstg_farc.get_dragged_file() # ドラッグ＆ドロップされたファイルのパス
        
        # ファイルをTempにコピーして解凍
        dragged_file_dir = pstg_farc.process_file(dragged_file, farc_pack_path)

        # 4. データの抽出
        module_data = pstg_extract.process_data()
        if not module_data:
            logging.error("データの抽出に失敗しました。処理を中止します。")
            return

        # 5. PoseScale設定の読み込み（設定ファイルが存在しない場合は設定エディタを起動して終了）
        pose_settings = pstg_loader.load_pose_scale_settings(module_data, app_config) # PoseScale設定の読み込み
        if not pose_settings:
            logging.error("有効なPoseScale設定が読み込めませんでした。処理を中止します。")
            launch_editor() # 設定エディタを起動
            return

        # 6. キャラクターマッピングの取得
        map_chara = pstg_util.load_chara_mapping()

        # 7. Pose TOMLの生成
        pose_toml_entries = pstg_pose.generate_pose_toml(module_data, pose_settings, map_chara) 

        # 8. Scale TOMLの生成
        scale_toml_entries = pstg_scale.generate_scale_toml(module_data, pose_settings, map_chara)

        # 9. ファイルの保存
        save_directory = dragged_file_dir
        if app_config['SaveInParentDirectory']:
            save_directory = os.path.dirname(dragged_file_dir)

        # プロファイルごとの保存ロジック（Config依存度高いためmainで処理しつつutilのsaveを呼ぶ)
        
        use_module_name_contains = app_config['UseModuleNameContains'] # モジュール名を含むか
        overwrite_existing = app_config.get('OverwriteExistingFiles', False) # 上書き保存
        config_profile = app_config.get('ProfileConfig', app_config['ConfigParser']) # ConfigParser

        # プロファイルごとの保存
        if use_module_name_contains:
            # モジュール名を含むか
            for section in config_profile.sections():
                # TomlProfile_で始まるセクション
                if section.startswith('TomlProfile_'):
                    match_str = config_profile.get(section, 'ModuleMatch', fallback='')
                    exclude_str = config_profile.get(section, 'ModuleExclude', fallback='')
                    
                    # モジュールデータ内にマッチするキーワードがあるか確認
                    is_match = False
                    # モジュールデータ内を走査
                    for module in module_data:
                        if pstg_util.is_match(module.get('name', ''), match_str, exclude_str):
                            is_match = True
                            break
                    
                    # マッチする場合
                    if is_match:
                        pose_file_name = config_profile[section]['PoseFileName'] # Pose TOMLファイル名
                        save_path = os.path.join(save_directory, f'{pose_file_name}.toml') # 保存パス
                        
                        if pose_toml_entries:
                            pstg_util.save_file_with_timestamp(save_path, '\n'.join(pose_toml_entries), overwrite=overwrite_existing) # Pose TOML保存
                        else:
                            logging.info(f"Pose TOMLの内容が空のため、生成をスキップしました: {save_path}")
        else:
            # モジュール名を含まない
            default_pose_file_name = app_config['DefaultPoseFileName'] # デフォルトPose TOMLファイル名
            save_path = os.path.join(save_directory, f'{default_pose_file_name}.toml') # 保存パス
            
            if pose_toml_entries:
                pstg_util.save_file_with_timestamp(save_path, '\n'.join(pose_toml_entries), overwrite=overwrite_existing) # Pose TOML保存
            else:
                logging.info(f"Pose TOMLの内容が空のため、生成をスキップしました: {save_path}")

        # Scale TOMLは常に保存
        scale_file_name = 'scale_db.toml' # Scale TOMLファイル名
        save_path_scale = os.path.join(save_directory, scale_file_name) # 保存パス
        
        if scale_toml_entries:
            pstg_util.save_file_with_timestamp(save_path_scale, '\n'.join(scale_toml_entries), overwrite=overwrite_existing) # Scale TOML保存
        else:
             logging.info(f"Scale TOMLの内容が空のため、生成をスキップしました: {save_path_scale}")

        logging.info("全処理が完了しました")

    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")
        print(f"予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        input("Enterキーを押して終了してください...")
    finally:
        # 10. クリーンアップ (デバッグ設定に基づく)
        # app_config might be None if load failed, so check carefully
        should_delete = True
        if 'app_config' in locals() and app_config:
             should_delete = app_config.get('DeleteTemp', True)
        
        if should_delete:
            pstg_util.clean_temp_dir()
        else:
            logging.info("デバッグ設定によりTempフォルダの削除をスキップしました")

if __name__ == "__main__":
    main()
