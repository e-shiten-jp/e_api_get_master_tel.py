# -*- coding: utf-8 -*-
# Copyright (c) 2026 Tachibana Securities Co., Ltd. All rights reserved.

# 2022.04.12, yo.
# 2022.11.18 reviced, yo.
# 2025.08.13 reviced, yo.
# 2026.06.21 reviced,   yo.
#
# 立花証券ｅ支店ＡＰＩ利用のサンプルコード
#
# 動作確認
# Python 3.13.5 / debian13
# API v4r9
#
# ------------------------------------------------------------------
#
# APIの基本設計について
# 
# 本APIは、プログラミング初心者や非ITエンジニアの方にも
# 利用しやすいよう、URLにJSON形式のパラメーターを付加して
# 送信する独自方式を採用しています。
# 
# 一般的なWeb APIとは異なる構成ですが、
# HTTPヘッダーやPOSTデータなどの知識を最小限に
# 抑えながら利用できることを重視しています。
# 
# このため、本APIは、URLとJSON文字列を組み立てて
# 送信するだけで利用でき、特別な知識を必要とせず、
# 各種スクリプト言語からも実装しやすいことを
# 優先した設計となっています。
#  
# ------------------------------------------------------------------
# 
# 固定IP指定の推奨
# 
# 秘密鍵、第2パスワードファイル、またはログインレスポンスファイルが
# 万が一流出した場合、第三者に不正ログインされるリスクがあります。
# 
# 安全のため、接続元を固定IPに限定する設定（IP制限）を
# 行っての利用を強く推奨いたします。
# 
# ------------------------------------------------------------------
# 
# 機能: マスターを一括ダウンロードします。
#
# 必要な設定項目
# 出力ファイル名:   FNAME_OUTPUT  マスターデータの出力ファル名
# 
# 利用方法: 
# 事前に「e_api_login_pubkey.py」を実行して、仮想URL等を取得しておいてください。
# 実行は「e_api_login_pubkey.py」と同じディレクトリで行ってください。
#
# ファイル構成：
# ~/e_api/                        ← API実行基盤（権限: 700 / 所有者のみアクセス可）
# ├── .auth/                      ← 鍵・暗号化データ格納（権限: 700）
# │   ├── file_pwd2.txt           ← 第2パスワード保存ファイル（手動作成。注文・訂正・取消以外は不要）
# │   └── file_login_response.txt ← ログイン応答出力先（自動生成）
# ├── file_url_info.txt           ← API接続情報ファイル（手動作成）
# ├── e_api_login_pubkey.py
# │
# └── [本実行プログラム]
# 
# 
# ~/e_api/file_url_info.txtの内容例：
# {
#     "sUrl": "https://demo-kabuka.e-shiten.jp/e_api_v4r9/",
#     "sJsonOfmt": "5"
# }
# 
#
# == ご注意: ========================================
#   本番環境にに接続した場合、実際に市場に注文が出ます。
#   市場で約定した場合取り消せません。
# ==================================================
#

import urllib3
import datetime
import json
import os
import urllib.parse
from zoneinfo import ZoneInfo

# =========================================================================
# --- 設定項目（定数定義） ---
# =========================================================================
# コマンド用パラメーター -------------------    
FNAME_OUTPUT = './master.txt'   # 書き込むファイル名。カレントディレクトリに上書きモードでファイルが作成される。

# --- 共通設定項目 ------------------------------------------------------------
FNAME_URL_INFO = "file_url_info.txt"                # API接続情報ファイル
FNAME_PASSWD2 = "./.auth/file_pwd2.txt"              # 第二パスワード保存ファイル
FNAME_LOGIN_RESPONSE = "./.auth/file_login_response.txt"  # ログイン応答保存先
FNAME_INFO_P_NO = "file_info_p_no.txt"              # p_no保存ファイル

# --- 通信堅牢化のための設定項目 ---
API_TIMEOUT_SECONDS = 15.0  # タイムアウト時間（秒）: 応答がない場合15秒で切り上げる
MAX_RETRY_COUNT = 3         # 最大リトライ回数: 通信エラー時に自動再試行する回数
RETRY_INTERVAL_SECONDS = 5  # リトライ間隔（秒）: 再試行する前に待機する時間
# =========================================================================

S_ISSUE_CODE = '9432'   # 10.銘柄コード。実際の銘柄コードを入れてください。
S_SIZYOU_C = '00'       # 11.市場。  00:東証   現在(2021/07/01)、東証のみ可能。



# --- 共通ユーティリティ関数 ----------------------------------------------

def func_p_sd_date():
    """
    機能: システム時刻を"p_sd_date"の書式の文字列で返す。
    返値: "p_sd_date"の書式の文字列。 API規定書式 "YYYY.MM.DD-hh:mm:ss.sss"
    引数1: なし
    備考: 
        日本標準時（Japan Standard Time、JST）を利用のこと。
    """
    dt_now = datetime.datetime.now(
        # 日本標準時（Japan Standard Time、JST）を利用
        ZoneInfo("Asia/Tokyo")
    )
    # 年.月.日-時:分:秒 の部分を作成
    str_date = dt_now.strftime("%Y.%m.%d-%H:%M:%S")
    
    # マイクロ秒（6桁ゼロ埋め）から先頭の3桁を切り出してミリ秒を作成
    str_micro = f"{dt_now.microsecond:06d}"
    str_ms = str_micro[0:3]
    
    # ドットで結合してAPI規定書式を完成
    return str_date + "." + str_ms


def func_replace_urlencode(str_input):
    """
    URLエンコードを行う。

    URLでは、スペースや「&」「+」「?」などの記号が
    特別な意味を持つため、そのまま送信できない場合がある。
    そのため、これらの文字を「%xx」形式へ変換する。

    例:
        "A B+C" → "A%20B%2BC"

    本サンプルでは Python標準ライブラリの
    urllib.parse.quote() を利用してURLエンコードを行う。

    他言語へ移植する場合も、自前で変換処理を作成するのではなく、
    各言語が提供する標準のURLエンコード関数を利用することを推奨する。

    主な対応例:
        Python      : urllib.parse.quote()
        Java        : java.net.URLEncoder.encode()
        C#          : Uri.EscapeDataString()
        JavaScript  : encodeURIComponent()
        Go          : url.QueryEscape()

    Parameters
    ----------
    str_input : str
        URLエンコード対象文字列

    Returns
    -------
    str
        URLエンコード後の文字列
    """
    return urllib.parse.quote(str_input, safe='')


def func_read_from_file(str_fname):
    """ファイルから文字情報を一括読み込み（BOMを排除）"""
    str_read = ''
    try:
        # utf-8-sig を指定してBOMを自動的に排除しファイルを開く
        with open(str_fname, 'r', encoding='utf-8-sig') as fin:
            while True:
                line = fin.readline()
                if not line:
                    break
                str_read = str_read + line
        return str_read
    except IOError as e:
        print(f"[エラー] ファイルを読み込めません: {str_fname}")
        raise e


def func_write_to_file(str_fname_output, str_data):
    """ファイルに書き込み、権限を所有者のみ(600)に制限"""
    try:
        # 出力先フォルダの存在を確認し、存在しない場合は自動作成
        str_dir = os.path.dirname(str_fname_output)
        if str_dir and not os.path.exists(str_dir):
            os.makedirs(str_dir, exist_ok=True)

        # データをファイルへ書き込み
        with open(str_fname_output, 'w', encoding='utf-8') as fout:
            fout.write(str_data)
        
        # パーミッションを600（所有者のみ読み書き可能）に制限
        os.chmod(str_fname_output, 0o600)
    except IOError as e:
        print(f"[エラー] ファイルに書き込めません: {str_fname_output}")
        raise e


def func_get_url_info(fname):
    """
    file_url_info.txt からAPI接続設定を取得

    機能: API接続情報をファイルから取得し辞書型で返す
    引数1: 接続先情報を保存したファイル名: fname_url_info

    サポートへの問い合わせは、sJsonOfmt:'5'でお願いします。
    """
    str_url_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    return  json.loads(str_url_info)    


def func_get_login_response(str_fname):
    '''
    ログインレスポンスを取得
    '''
    str_login_response = func_read_from_file(str_fname)
    dic_login_response = json.loads(str_login_response)
    return dic_login_response
    

def func_get_p_no(fname):
    """ 
    機能: p_noをファイルから取得する
    引数1: p_noを保存したファイル名（fname_info_p_no = "e_api_info_p_no.txt"）
    """
    str_p_no_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    json_p_no_info = json.loads(str_p_no_info)
    int_p_no = int(json_p_no_info.get('p_no'))
    return int_p_no


def func_save_p_no(str_fname_output, int_p_no):
    """p_noを保存するためのJSONファイルを生成"""
    p_no_dict = {"p_no": str(int_p_no)}
    json_data = json.dumps(p_no_dict, indent=4)
    func_write_to_file(str_fname_output, json_data)
    print(f'現在の "p_no" を保存しました。 p_no = {int_p_no} -> {str_fname_output}')


def func_make_url_request_from_dic(
                                    auth_flg,       # ログインFlag。    login:true   login以外:false
                                    url_target,     # 接続先URL
                                    work_dic_req    # API要求項目
):
    '''
    API問合せ用完全URL（クエリパラメータ付）を作成
    
    ------------------------------------------------------------------

    APIの基本設計について

    本APIは、プログラミング初心者や非ITエンジニアの方にも
    利用しやすいよう、URLにJSON形式のパラメーターを付加して
    送信する独自方式を採用しています。

    一般的なWeb APIとは異なる構成ですが、
    HTTPヘッダーやPOSTデータなどの知識を最小限に
    抑えながら利用できることを重視しています。

    このため、本APIは、URLとJSON文字列を組み立てて
    送信するだけで利用でき、特別な知識を必要とせず、
    各種スクリプト言語からも実装しやすいことを
    優先した設計となっています。
    
    ------------------------------------------------------------------
    JSONをHTTPボディではなくURLに付加して送信します。
    詳細はAPIマニュアル参照。
    備考：
        サポートへの問い合わせを考慮し、項目ごとの改行とタブを入れてあります。
    '''
    str_url = url_target
    if auth_flg:
        str_url = urllib.parse.urljoin(str_url, 'auth/')
    json_param = json.dumps(work_dic_req, indent=4, ensure_ascii=False)
    return f"{str_url}?{json_param}"


def func_api_req(str_request_method, str_url): 
    """
    APIリクエストの送信と、Shift-JIS応答のデコード（リトライ・タイムアウト対応版）
    """
    # HTTP通信ライブラリ urllib3 を利用します。
    #
    # requests ライブラリでも同様の処理は可能ですが、
    # 本サンプルでは APIサーバーへの接続処理が分かりやすいよう、
    # より基本的な urllib3 を利用しています。
    #
    # 他言語へ移植する場合も、
    # 「HTTPクライアント生成 → リクエスト送信 → レスポンス受信」
    # の流れを対応するライブラリへ置き換えてください。

    print('--- 送信電文 -------------------------------------------')
    print(str_url)

    # 接続および読み込みのタイムアウト時間を設定
    timeout_config = urllib3.Timeout(connect=API_TIMEOUT_SECONDS, read=API_TIMEOUT_SECONDS)
    http = urllib3.PoolManager()
    
    response_data = None
    status_code = None

    # 最大試行回数に達するまで通信をリトライ
    for attempt in range(1, MAX_RETRY_COUNT + 1):
        try:
            # 2回目以降の試行（再接続）の前に、指定されたインターバル時間待機
            if attempt > 1:
                print(f"[{attempt}/{MAX_RETRY_COUNT} 回目] 再接続を試みます...（{RETRY_INTERVAL_SECONDS}秒待機）")
                time.sleep(RETRY_INTERVAL_SECONDS)

            req = http.request(str_request_method, str_url, timeout=timeout_config)
            status_code = req.status
            response_data = req.data
            break  # 正常に通信できた場合はループを抜ける

        except (TimeoutError, MaxRetryError) as ce:
            print(f"\n[警告] 通信エラーが発生しました (試行: {attempt}/{MAX_RETRY_COUNT})")
            print(f"エラー詳細: {ce}")
            
            # 最大リトライ回数を超えて失敗した場合はConnectionErrorを発生
            if attempt == MAX_RETRY_COUNT:
                raise ConnectionError(
                    f"APIサーバーへの接続に規定回数失敗しました。サーバーがメンテナンス中か、停止している可能性があります。\n"
                    f"設定されたタイムアウト時間: {API_TIMEOUT_SECONDS}秒"
                )
        except Exception as ex:
            print(f"\n[警告] 予期せぬネットワーク例外が発生しました: {ex}")
            if attempt == MAX_RETRY_COUNT:
                raise ex

    print(f"HTTP Status: {status_code}")

    # 受信した電文をShift-JISからUTF-8へデコード（不正なバイトは無視）
    str_response = response_data.decode("shift-jis", errors="ignore")
    print('--- 受信電文 -------------------------------------------')
    print(str_response[:2000])
    print('--------------------------------------------------------')

    return str_response


def func_api_request_from_dic(
                                flg_login,          # ログインFlag。    login:true   login以外:false
                                destination_url,    # 接続先URL。
                                                    #   ログイン時は、FNAME_URL_INFOから取得する接続先。
                                                    #   それ以外はログインレスポンスで指定される仮想URL。
                                dic_req_item        # API要求項目
):
    '''
    APIへの問い合わせを実行する。
    '''
    # URL文字列の作成
    str_url = func_make_url_request_from_dic(
                                                flg_login,          # ログインFlag。    login:true   login以外:false
                                                destination_url,    # 接続先URL
                                                dic_req_item        # API要求項目
    )

    # APIへの問い合わせ。
    # リクエストメソッドの指定('GET'、'POST'どちらでも動作します。)
    str_api_response = func_api_req('POST', str_url)

    # apiの返り値（JSON形式の文字列）を辞書型で取り出す
    dic_api_response = json.loads(str_api_response)
    
    return dic_api_response

# --- 共通ユーティリティ関数 ----------------------------------------------




# 機能： ダウンロード用の接続。APIに接続しマスターダウンロードを開始する。
# 引数1： API問合せ用URL
# 引数2： 保存するマスターのファイル名
# 引数3： 顧客属性クラス
# 備考： 通常のrequestの接続とは異なる接続。ストリーミングでの接続。

# 受信
#  ↓
# bufferへ追加
#  ↓
# raw_decode()
#  ↓
# JSONが1件完成していれば取り出す
#  ↓
# 残りをbufferへ残す
#  ↓
# またraw_decode()
# 
def func_api_req_master_download(str_url, str_master_filename):

    bool_download = False
    int_down_no = 0
    str_terminate = 'CLMEventDownloadComplete'

    print('送信文字列＝')
    print(str_url)

    print('マスターダウンロード開始')
    print('データが大きいため時間がかかります。')
    print('約21MB。')

    http = urllib3.PoolManager()

    resp = http.request(
        'GET',
        str_url,
        preload_content=False)

    print(resp.status)
    print(resp.headers)

    decoder = json.JSONDecoder()

    buffer = ""

    try:

        with open(str_master_filename,
                  "w",
                  encoding="utf-8") as fout:

            for chunk in resp.stream(4096):

                # CP932で文字列へ変換
                buffer += chunk.decode("cp932")

                while True:

                    # 前のJSONとの空白や改行を除去
                    buffer = buffer.lstrip()

                    if not buffer:
                        break

                    try:
                        obj, pos = decoder.raw_decode(buffer)

                    except json.JSONDecodeError:
                        # JSONがまだ最後まで届いていない
                        break

                    #
                    # JSON一件完成
                    #

                    json_text = buffer[:pos]

                    fout.write(json_text)
                    fout.write("\n")

                    int_down_no += 1

                    if int_down_no % 2000 == 0:
                        print("down_load_item:", int_down_no)

                    if obj.get("sCLMID") == str_terminate:

                        print()
                        print("down_load_item:", int_down_no)
                        print()
                        print("terminate_string:",
                              obj.get("sCLMID"))

                        bool_download = True

                        return bool_download

                    # 処理済みを削除
                    buffer = buffer[pos:]

    finally:
        resp.release_conn()

    return bool_download


# def func_api_req_master_download(str_url, str_master_filename):
#     byte_data = b''
#     str_data = ''
#     bool_download = False
#     int_down_no = 0

#     # マスターの終端文字列をセット
#     str_terminate = 'CLMEventDownloadComplete'
#     # マニュアル「立花証券・ｅ支店・ＡＰＩ（ｖ４ｒ２）、REQUEST I/F、利用方法、データ仕様」
#     # p3/6 ２．利用方法、(3)業務機能、
#     # No20-16 初期ダウンロード終了通知 CLMEventDownloadComplete 参照。
    
#     print('送信文字列＝')
#     print(str_url)  # 送信する文字列

#     print('マスターダウンロード開始')
#     print('データが大きいため時間がかかります。')
#     print('約21MB。')
    
#     # APIに接続
#     http = urllib3.PoolManager()

#     # ストリーム形式で接続（** 重要 **）
#     resp = http.request(
#         'GET',
#         str_url,
#         preload_content=False)
#     print(resp.status)
#     print(resp.headers)
#     try :            
#         with open(str_master_filename, 'w') as f:
#             for chunk in resp.stream(1024):
#                 byte_data += chunk
#                 byte_data = byte_data + chunk
#                 # if byte_data[-1:] == b'}' :         # 1データの終わりを判定する。
#                 if byte_data.rstrip().endswith(b'}'):    # 1データの終わりを判定する。
#                     int_down_no = int_down_no + 1
#                     str_data = byte_data.decode('shift-jis', errors = 'replace')
#                     str_data = str_data + '\n'      # 簡単に扱えるようにするため、１行1データとして保存する。
#                     f.write(str_data)
#                     byte_data = b''
                    
#                     if int_down_no % 2000 == 0:
#                         # 取得データ数の画面表示
#                         print('down_load_item:', int_down_no)

#                     json_data = json.loads(str_data)
#                     if json_data.get('sCLMID') == str_terminate :   # 初期ダウンロード終了通知をチェック。
#                         print('down_load_item:', int_down_no)
#                         print()
#                         print('最終データ=', str_data)
#                         print('terminate_string: "sCLMID":', json_data.get('sCLMID'))
#                         f.close()
#                         bool_download = True
#                         break
#                     else :
#                         str_data = ''
                
#     except IOError as e:
#         print('File can not write!!!')
#         print('filename:', str_master_filename)
#         print(type(e))
            
#     resp.release_conn()

#     return bool_download
# def func_api_req_master_download(str_url, str_master_filename):

#     bool_download = False
#     int_down_no = 0
#     str_terminate = 'CLMEventDownloadComplete'

#     print('送信文字列＝')
#     print(str_url)

#     print('マスターダウンロード開始')
#     print('データが大きいため時間がかかります。')
#     print('約21MB。')

#     http = urllib3.PoolManager()

#     resp = http.request(
#         'GET',
#         str_url,
#         preload_content=False)

#     print(resp.status)
#     print(resp.headers)

#     byte_buffer = b''

#     try:
#         with open("raw_dump.txt", "wb") as f:
#             for chunk in resp.stream(1024):
#                 f.write(chunk)
#         # UTF-8保存をお勧めします
#         with open(str_master_filename, 'w', encoding='utf-8') as f:

#             for chunk in resp.stream(1024):

#                 # バッファへ追加
#                 byte_buffer += chunk

#                 # 改行単位で処理
#                 while b'\n' in byte_buffer:

#                     line, byte_buffer = byte_buffer.split(b'\n', 1)

#                     if not line.strip():
#                         continue

#                     # CP932として復元
#                     str_data = line.decode('cp932')

#                     # ファイルへ保存
#                     f.write(str_data + '\n')

#                     int_down_no += 1

#                     if int_down_no % 2000 == 0:
#                         print('down_load_item:', int_down_no)

#                     json_data = json.loads(str_data)

#                     if json_data.get('sCLMID') == str_terminate:

#                         print()
#                         print('down_load_item:', int_down_no)
#                         print()
#                         print('最終データ=')
#                         print(str_data)

#                         bool_download = True
#                         return bool_download

#         return bool_download
#     except json.JSONDecodeError as e:
#         print("===================================")
#         print(e)
#         print("repr =", repr(str_data))
#         print("len  =", len(str_data))
#         raise

#     finally:
#         resp.release_conn()
# def func_api_req_master_download(str_url, str_master_filename):

#     print('送信文字列＝')
#     print(str_url)

#     print('マスターダウンロード開始')
#     print('データが大きいため時間がかかります。')
#     print('約21MB。')

#     http = urllib3.PoolManager()

#     resp = http.request(
#         'GET',
#         str_url,
#         preload_content=False)

#     print(resp.status)
#     print(resp.headers)

#     try:
#         with open("raw_dump.txt", "wb") as f:
#             for chunk in resp.stream(1024):
#                 f.write(chunk)

#         print("raw_dump.txt に保存しました。")

#     finally:
#         resp.release_conn()

#     return True



# # 機能： マスターダウンロード
# # 引数1：str_master_filename ダウンロードしたマスターデータを保存するファイル名
# # 引数2：class_login_property（口座属性クラス）
# # 返値： 無し（''）
# def func_get_master(int_p_no, str_master_filename, class_login_property):
#     # 送信項目の解説は、マニュアル、（2）インタフェース概要の「立花証券・ｅ支店・ＡＰＩ、インタフェース概要」
#     # p7/10 sd 5.マスタダウンロード を参照してください。

#     req_item = [class_req()]
#     str_p_sd_date = func_p_sd_date(datetime.datetime.now())     # システム時刻を所定の書式で取得
#     bool_req_download = False
    
#     str_key = '"p_no"'
#     str_value = func_check_json_dquat(str(int_p_no))
#     #req_item.append(class_req())
#     req_item[-1].add_data(str_key, str_value)

#     str_key = '"p_sd_date"'
#     str_value = str_p_sd_date
#     req_item.append(class_req())
#     req_item[-1].add_data(str_key, str_value)
    
#     str_key = 'sCLMID'
#     str_value = 'CLMEventDownload'  # 。
#     req_item.append(class_req())
#     req_item[-1].add_data(str_key, str_value)

    
#     # 返り値の表示形式指定
#     str_key = '"sJsonOfmt"'
#     str_value = '4'    # ファイル保存後の処理を考え、”4”を指定。
#     req_item.append(class_req())
#     req_item[-1].add_data(str_key, str_value)

#     # URL文字列の作成
#     str_url = func_make_url_request(False, \
#                                      class_login_property.sUrlMaster, \
#                                      req_item)
# ##    str_url = func_make_url_request(False, \
# ##                                     class_login_property.sUrlRequest, \
# ##                                     req_item)

#     # マスターデータ取得専用のAPI呼び出し
#     bool_req_download = func_api_req_master_download(str_url, str_master_filename)
#     # マスターの解説は、マニュアル「立花証券・ｅ支店・ＡＰＩ、REQUEST I/F、マスタデータ利用方法」参照。

#     return bool_req_download





    
# ======================================================================================================
#     プログラム始点 
# ======================================================================================================

if __name__ == "__main__":

    # 表示形式を接続情報ファイルから読み込む。
    dic_url_info = func_get_url_info(FNAME_URL_INFO)
    str_sJsonOfmt = dic_url_info.get("sJsonOfmt")

    # ログイン応答を保存した「file_login_response.txt」から、仮想URLと口座情報を取得
    dic_login_property = func_get_login_response(FNAME_LOGIN_RESPONSE)

    # 現在（前回利用した）のp_noをファイルから取得する
    my_p_no = func_get_p_no(FNAME_INFO_P_NO)
    my_p_no = my_p_no + 1
    # 更新した"p_no"を保存する。
    func_save_p_no(FNAME_INFO_P_NO, my_p_no)
    
    print()
    print('-- マスター 取得 -------------------------------------------------------------')
    # API要求項目のセット
    dic_req_item = {
        'p_no':                 str(my_p_no),
        'p_sd_date':            func_p_sd_date(),

        'sCLMID':               'CLMEventDownload',     # マスターダウンロードを指定。
        'sJsonOfmt':            str_sJsonOfmt                   # 表示形式（サポートへの問い合わせでは'5'を指定指定した送信電文と受信電文で。）
    }

    # 'CLMEventDownload'は、仮想URL:'sUrlMaster'
    destination_url = dic_login_property.get('sUrlMaster')
    # URL文字列の作成
    str_url = func_make_url_request_from_dic(
                                                False,          # ログインFlag。    login:true   login以外:false
                                                destination_url,    # 接続先URL
                                                dic_req_item        # API要求項目
    )

    # API問い合わせ実行
    # マスターデータ取得専用のAPI呼び出し
    bool_my_download = False
    bool_my_download = func_api_req_master_download(str_url, FNAME_OUTPUT)
    # マスターの解説は、マニュアル「立花証券・ｅ支店・ＡＰＩ、REQUEST I/F、マスタデータ利用方法」参照。
    # カレントディレクトリに「FNAME_OUTPUT」で指定した名前でファイルを作成する。
    
    if bool_my_download:
        print('マスターの取得が終了しました。')
        print('出力ファイル:', FNAME_OUTPUT)
    else:
        # 仮想URLが無効になっている場合
        print()
        print()    
        print('マスターのダウンロードに失敗しました。')    
        print()    
        print("仮想URLは、有効ですか。")
        print("有効でない場合、")
        print("電話認証 + e_api_login_tel.py実行")
        print("を再度行い、新しく仮想URL（1日券）を取得してください。")    

