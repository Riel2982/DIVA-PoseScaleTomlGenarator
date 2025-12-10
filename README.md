# DIVA-PoseScaleTomlGenerator

## Overview
This tool reads the gm_module_tbl, obtains PoseScale data matching the module data within it, and converts these into gm_module_pose_tbl.toml (default value) and scale_db.toml.  
The code has been generated using Microsoft Copilot and Antigravity, with some minor adjustments.

## Requirements
- [**FarcPack**](https://github.com/blueskythlikesclouds/MikuMikuLibrary)  

*Note: This tool might be able to easily generate TOML files used in the following two script patches:*

1. [**Customization Poses**](https://gamebanana.com/mods/538857)   
   Changes the poses of the modules in the customization screen.

2. [**Scale**](https://github.com/vixen256/scale)  
   A supplement for module mods to enable characters to be scaled to an appropriate scale.


## ファイル構成
- PoseScaleTomlGenerator.exe : Toml生成ツール（以後Generatorと呼称）
- PoseScaleConfigEditor.exe : データ生成用の設定ツール（以後Editorと呼称）
- Settings フォルダ : 2種類のツールで使用する外部データ格納場所

*Note: GeneratorとEditorは同じフォルダ内に置いて実行してください*


## 使い方
1. Editorを実行
    - 'General Settings'タブにて'FarcPack'のファイルパスを指定。
    - 'Pose Scale Data'タブでPoseとScaleの設定データを編集。
2. Generatorの実行ファイル(.exe)アイコンに"gm_module_tbl.farc"をドラッグ＆ドロップするとPoseとScaleのTomlファイルが生成されます。
    - 通常はFarcファイルと同じ場所にTomlファイルが生成されますが、Editorで'親ディレクトリに保存'をONにするとFarcファイルの一つ上の階層に出力されます。
    - '送る'登録をすれば"Databese Converter"や"Farc Pack"と同じようにFarcファイルを右クリック→送るでも実行できます。〈おすすめ〉
    - 生成先に同名ファイルが存在する時は、既存ファイルをタイムスタンプ付きにリネーム（バックアップ）してから出力しますが、Editorで'既存ファイルを上書き'をONにするとバックアップを無効化します。
    - Editorで'プロファイルを有効化'をONにすると読み込んだモジュールデータと条件が一致するプロファイルを自動で判別し、Tomlファイルを出力します。（複数の設定を使い分けたいときなどに）
        - プロファイルが無効中に使用される設定ファイルは"PoseScaleData.ini"です。


### Toml Profile
- モジュール一致: 指定した単語と読み込んだFarcファイルのいずれかのモジュール名が一致する場合、このプロファイルを使うという条件指定欄。
    - カンマ区切りで複数単語指定できますが or 指定です。
- モジュール除外: 指定した単語が読み込んだFarcファイルのいずれかのモジュール名に含まれている場合、このプロファイルは使わないという要件指定欄。
    - 同じくカンマ区切りと or 指定です。
    - モジュール一致と併用できます。
- PoseScale設定ファイル: このプロファイルの時にどのPoseScale設定ファイルを使用するのかを指定する欄。
    - 'Pose Scale Data'タブで編集したPoseScale設定ファイルの中からプルダウンで選択。
        - 'ファイルを編集'ボタンをクリックすると、該当するPoseScale設定ファイル編集画面に移動します。（移動前にTomlプロファイルを更新するのを忘れないように注意してください）
- Poseファイル名: 生成されるPose用のTomlファイル名を設定する欄。
    - "gm_module_pose_tbl.toml"か、modの"config.toml"で指定するカスタムファイル名を入力してください。
        - カスタムファイル名とは``` module_poses = 'poses.toml' ```の'poses.toml'の部分のこと。


### Pose Scale Data
- キャラ: キャラ枠指定欄（必須）
- モジュール一致: モジュール名に指定した単語が含まれる場合、このSettingデータを使う条件指定欄。
    - プロファイルと同じくカンマ区切りで複数指定可能（or 指定）
- モジュール除外: モジュール名に指定した単語が含まれる場合、このSettingデータの使用をスキップする条件指定欄。
    - プロファイルと同じく以下略。
- Pose ID: 使用するポーズを指定する欄。空欄の場合はPose指定処理をスキップします。
    - PoseID Mapに登録しているポーズに関しては、プルダウンから選択可能です。（もちろんPoseIDを直接入力するのも可）
- Scale: 使用するスケール値を設定する欄。空欄の場合はScale指定処理をスキップします。
    - 現在は数値の直接入力のみ対応していますが、要望があればPoseID Mapのような機能を追加するかも……


#### キャラ枠指定のみでPoseScaleを出力したい場合
- モジュール一致指定欄を空欄にして登録すると、どのSetttingデータにも該当しなかったモジュールの中からキャラ枠が一致するモジュールがあればモジュール名指定条件はなくとも出力できます。
    - モジュール除外と併用可能です。

### Pose ID Map
- Pose ID: "mot_db"などに記述されている"MotionInfo"のIDを入力。
    - 同じPoseIDを重複して登録できません（上書きされます）。
- Pose名: 自分でどのモーションかわかりやすいように設定してください。
- 画像プレビュー: モーション選択の判断材料として参考画像をキープしたい時に使ってください。


## 注意事項
- 編集中にセキュリティソフトのランサムウェア対策が反応してアプリが終了する場合があります。
    - 短時間に連続して複数の画像ファイルに変更を加えるような作業を避ければおそらく回避可能です。
    - セキュリティソフトの許可リストにアプリを追加することでも回避できますが、除外設定はセキュリティリスクを伴う可能性があるため、自己責任でお願いします。
- UI表示は今後変更する可能性があります。
    - Editor用のアイコン設定は仮のものです。
- Toml Profileリスト・PoseScaleリスト・PoseIDリストは自動保存されますが、各タブの右側編集画面およびGeneral Settingsは保存ボタンをクリックする必要があります。
    - Undo / Redo機能で概ね編集ミスをカバー可能です。


## 更新履歴
### beta0 (2025-11-21)
- "gm_module_tbl.farc"を読み込んで対応するPose / ScaleのTomlファイルを生成［Generator］
    - TomlProfileのMatchModule設定を使うことでTomlファイル生成のための設定データを使い分けることが可能
    - 各種設定データ（iniファイル郡）は自力で編集する前提（Editor未実装）

### beta1 (2025-11-30)
- Generatorの起動・処理に必要な各種設定データをGUIから編集可能に［Editor］
    - General Settings: "Farck Pack"パス指定、Tomlファイル出力場所の切り替え、'Toml Profile'使用有無の切り替え、デフォルトPoseTomlファイル名の設定、出力Tomlの上書き保存切り替え
    - Toml Profile: 読み込んだ"gm_module_tbl.farc"からどのToml Profileを使用するかを判別する条件設定編集
    - Pose Scale Data: どのモジュールにどのPose・Scaleを当てはめるか判別する条件設定編集
    - Pose ID Map: PoseIDリストを作成（必須ではない）
- キャラ枠指定でのPose・ScaleのTomlデータを出力可能に［Generator］
- 同名ファイルが存在する場合は常にタイムスタンプ付きでリネームしてバックアップしていたのを、上書き保存するか選べるように［Generator］

### beta2 (2025-12-03)
- Toml Profile有効時でも該当するプロファイルが存在しない場合はデフォルトデータ（PoseScaleData.ini）を使用してTomlファイルを作成するように変更［Generator］
- Undo / Redo 機能を各タブごとに分離・実行できるように変更［Editor］
- テキストボックス入力でのCtl+Z / Ctl+Yのショートカットを有効化［Editor］
    - 'Pose Scale Data'タブのPose ID入力欄は未対応。
- モジュール一致・モジュール除外入力欄にカンマ補正機能を実装［Editor］
    - ```A,B```や```A, B,```のような入力ミスを```A, B```という形式に補正します。
- 'Toml Profile'タブ・'Pose Scale Data'タブ・'Pose ID Map'タブでリストのアイテムをDeleteした時にDelete対象の前後のアイテムを選択状態に切り替えるように変更［Editor］
- 'Toml Profile'タブ・'Pose Scale Data'タブ・'Pose ID Map'タブでリストのアイテムをUndo/Redoで復元した時に復元されたアイテムを選択状態に切り替えるように変更［Editor］
- 各種Save/UpdateおよびDeleate時のポップアップを廃止［Editor］

### beta3 (2025-12-10)
- "FarcPack"のパスが'General Settings'で保存されない不具合の修正［Editor］
- カンマ補正機能に読点の半角カンマ変換を追加［Editor］
    -  ```A、B```を```A, B```という形式に補正します。
- テキストボックス入力欄末尾の不要なスペースを削除する補正機能を追加［Editor］
- 'Pose Scale Data'タブでScale以外の編集内容がUndo/Redoで復元できない不具合を修正［Editor］
- 'Pose Scale Data'タブでカンマ補正が実行されても画面に反映されない不具合を修正［Editor］
- 'General Settings'タブのデフォルトPoseファイル名と'Toml Profile'タブのPoseファイル名設定欄で使用できる文字を半角英数字記号のみに制限［Editor］
- アプリアイコン画像を変更［Editor］
- 有効なPoseScale設定が存在しない場合は設定エディタを起動するように変更［Generator］


### 既知の不具合
- 画像プレビューの削除動作はRedoで再現できない（それ以外の操作はRedoで再現できる）［Editor］
