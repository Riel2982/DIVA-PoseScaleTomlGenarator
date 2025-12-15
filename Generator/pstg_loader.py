import os
import configparser
import logging
from pstg_util import get_app_dir, is_match

def load_pose_scale_settings(module_data, app_config):
    """プロファイルとモジュールデータに基づいてPoseScale設定を読み込む"""
    app_dir = get_app_dir() # アプリケーションのディレクトリ
    settings_dir = app_config.get('SettingsDir', os.path.join(app_dir, 'Settings')) # 設定ディレクトリ
    
    # PoseScaleDataをSettingsフォルダから探し、なければrootフォルダから探す
    pose_data_dir = os.path.join(settings_dir, 'PoseScaleData') # PoseScaleDataのディレクトリ
    if not os.path.exists(pose_data_dir): # PoseScaleDataのディレクトリが存在しない場合
        pose_data_dir = os.path.join(app_dir, 'PoseScaleData') # PoseScaleDataのディレクトリ

    config_profile = app_config.get('ProfileConfig', app_config['ConfigParser']) # 設定ファイル
    use_module_name_contains = app_config['UseModuleNameContains'] # モジュール名を含むか
    
    pose_settings = [] # PoseScale設定
    config_files_to_read = [] # 読み込む設定ファイル

    # プロファイル選択は「いずれかのキーワードが含まれるか (OR)」で判定
    if use_module_name_contains:
        # プロファイル選択は「いずれかのキーワードが含まれるか (OR)」で判定
        for section in config_profile.sections():
            if section.startswith('TomlProfile_'):
                # プロファイル選択は「いずれかのキーワードが含まれるか (OR)」で判定
                match_str = config_profile.get(section, 'ModuleMatch', fallback='')
                match_keywords = [m.strip() for m in match_str.split(',') if m.strip()]
                
                # プロファイル選択は「いずれかのキーワードが含まれるか (OR)」で判定
                exclude_str = config_profile.get(section, 'ModuleExclude', fallback='')
                exclude_keywords = [m.strip() for m in exclude_str.split(',') if m.strip()]
                
                logging.debug(f"Checking Profile: {section}, Keywords: {match_keywords}, Exclude: {exclude_keywords}")

                # モジュールデータ内にマッチするキーワードがあるか確認
                is_profile_match = False
                for module in module_data: # モジュールデータを走査
                    name = module.get('name', '')
                    
                    # Check Exclude first（除外キーワードがあるか確認）
                    if any(ex in name for ex in exclude_keywords):
                        continue

                    # プロファイル選択は「いずれかのキーワードが含まれるか (OR)」で判定
                    if any(k in name for k in match_keywords):
                        logging.debug(f"  Match found! Module: {name} contains one of {match_keywords}")
                        is_profile_match = True
                        break
                
                if not is_profile_match:
                     # マッチしなかった場合、最初の数件のモジュール名をログに出して確認
                     sample_names = [m.get('name', '') for m in module_data[:3]]
                     logging.debug(f"  No match in profile {section}. Sample module names: {sample_names}")
                
                if is_profile_match: # マッチした場合
                    config_file_base = config_profile[section]['ConfigFile']
                    config_files_to_read.append(f"{config_file_base}.ini")
                    logging.info(f"Profile matched: {section} -> Loading {config_file_base}.ini")
                else:
                    logging.info(f"Profile skipped (no match in module data): {section}")
        
        # UseModuleNameContainsがTrueの場合、PoseScaleData.iniを読み込む
        # 該当するTomlProfileがない場合、PoseScaleData.iniを読み込む
        if 'PoseScaleData.ini' not in config_files_to_read:
             config_files_to_read.append('PoseScaleData.ini')
             logging.info("該当するTomlProfileがないためデフォルト（PoseScaleData.ini）を使用します")

    else:
        config_files_to_read.append('PoseScaleData.ini')

    # 読み込む設定ファイルを走査
    for config_file in config_files_to_read:
        config_file_path = os.path.join(pose_data_dir, config_file)
        
        # 設定ファイルが存在しない場合
        if not os.path.exists(config_file_path):
            continue
            
        logging.info(f"使用するconfig file: {config_file_path}")
        
        # 設定ファイルを読み込む
        config_pose = configparser.ConfigParser()
        try: # 設定ファイルを読み込む
            config_pose.read(config_file_path, encoding='utf-8-sig')
        except UnicodeDecodeError: # 設定ファイルを読み込む
            logging.warning(f"UTF-8での読み込みに失敗しました。cp932で再試行します: {config_file_path}")
            config_pose.read(config_file_path, encoding='cp932')

        # 読み込んだ設定ファイルを走査
        for section in config_pose.sections():
            # PoseScale設定セクションを走査
            if section.startswith('PoseScaleSetting_'):
                # PoseScale設定を読み込む
                setting = {
                    "Chara": config_pose.get(section, "Chara", fallback=None), # キャラクター名
                    "ModuleNameContains": config_pose.get(section, "ModuleNameContains", fallback=None), # モジュール名を含むか
                    "ModuleExclude": config_pose.get(section, "ModuleExclude", fallback=None), # モジュール名を除外する
                    "PoseID": config_pose.get(section, "PoseID", fallback=None), # ポーズID
                    "Scale": config_pose.get(section, "Scale", fallback=None) # スケール
                }
                pose_settings.append(setting) # pose_settingsに追加
                logging.debug(f"セクションの設定を読み込みます {section}: {setting}")

    logging.info(f"pose_settings を正常に読み込みました。件数: {len(pose_settings)}")
    return pose_settings
