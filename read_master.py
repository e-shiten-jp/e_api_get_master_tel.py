# -*- coding: utf-8 -*-

# Copyright (c) 2026
#
# read_master.py
#
# 立花証券ｅ支店ＡＰＩ
# マスターファイル読込サンプル（V4r9対応版）
#
# 2022年版サンプルをベースに、
# V4r9の「JSONオブジェクト連結形式」のマスターへ対応。
#
# Python 3.11
#
# ------------------------------------------------------------

import json
from collections import defaultdict

# ==========================================================
# マスター種別ごとの処理関数
# ==========================================================

# 保存したいマスターだけ指定する
SAVE_CLMID = {
    "CLMDateZyouhou",
    "CLMYobine",
}


# ==========================================================
# request項目保存クラス
# ==========================================================

class class_req:

    def __init__(self):
        self.str_key = ''
        self.str_value = ''

    def add_data(self, work_key, work_value):
        self.str_key = func_check_json_dquat(work_key)
        self.str_value = func_check_json_dquat(work_value)


# ==========================================================
# JSON文字列の前後へダブルクォーテーションを付ける
# ==========================================================

def func_check_json_dquat(str_value):

    if str_value is None:
        str_value = ""

    str_value = str(str_value)

    if len(str_value) == 0:
        str_value = '""'

    if not str_value.startswith('"'):
        str_value = '"' + str_value

    if not str_value.endswith('"'):
        str_value = str_value + '"'

    return str_value


# ==========================================================
# 文字列前後のダブルクォーテーションを除去
# ==========================================================

def func_strip_dquot(text):

    if text is None:
        return ""

    if text.startswith('"'):
        text = text[1:]

    if text.endswith("\n"):
        text = text[:-1]

    if text.endswith('"'):
        text = text[:-1]

    return text


# ==========================================================
# class_req → JSON文字列
# ==========================================================

def func_make_json_format(work_class_req):

    json_text = "{\n"

    for item in work_class_req:

        key = func_strip_dquot(item.str_key)

        if len(key) == 0:
            continue

        if key.startswith("a"):
            value = func_strip_dquot(item.str_value)
        else:
            value = func_check_json_dquat(item.str_value)

        json_text += (
            "\t"
            + func_check_json_dquat(key)
            + ":"
            + value
            + ",\n"
        )

    if json_text.endswith(",\n"):
        json_text = json_text[:-2] + "\n"

    json_text += "}"

    return json_text


# ==========================================================
# UTF-8で保存
# ==========================================================

def func_write_to_file(filename, text):

    try:

        with open(filename,
                  "w",
                  encoding="utf-8") as fout:

            fout.write(text)

    except IOError as e:

        print("ファイルへ書き込めません。")
        print(filename)
        print(type(e))


# ==========================================================
# マスターファイル読込ジェネレータ
#
# V4r9では
#
# { ... }
# { ... }
# { ... }
#
# のようにJSONオブジェクトが連続して保存されている。
#
# この関数は1件ずつ辞書(dict)として返す。
#
# 使用例
#
# for master in read_master("master.txt"):
#     print(master["sCLMID"])
#
# ==========================================================

def read_master(filename):

    decoder = json.JSONDecoder()

    buffer = ""

    with open(filename,
              "r",
              encoding="utf-8") as fin:

        while True:

            chunk = fin.read(4096)

            if not chunk:

                # 最後に残っているJSONがあれば処理
                buffer = buffer.lstrip()

                if buffer:

                    try:
                        json_data, pos = decoder.raw_decode(buffer)
                        yield json_data

                    except json.JSONDecodeError:
                        pass

                break

            buffer += chunk

            while True:

                # 先頭の空白・改行を除去
                buffer = buffer.lstrip()

                if not buffer:
                    break

                try:

                    json_data, pos = decoder.raw_decode(buffer)

                except json.JSONDecodeError:

                    # JSONがまだ途中までしか届いていない
                    break

                # ここがポイント
                yield json_data

                # 読み終えたJSONを削除
                buffer = buffer[pos:]


# ==========================================================
# 日付情報(CLMDateZyouhou)
# ==========================================================

def func_read_date(master):

    print()
    print("========== CLMDateZyouhou ==========")

    print(json.dumps(master,
                     ensure_ascii=False,
                     indent=4))

    print()

    print("営業日区分          :", master.get("sDayKey"))
    print("営業日（当日）      :", master.get("sTheDay"))
    print("営業日（翌営業日）  :", master.get("sYokuEigyouDay_1"))

    req_item = []

    item = class_req()
    item.add_data("sDayKey",
                  master.get("sDayKey"))
    req_item.append(item)

    item = class_req()
    item.add_data("sTheDay",
                  master.get("sTheDay"))
    req_item.append(item)

    item = class_req()
    item.add_data("sYokuEigyouDay_1",
                  master.get("sYokuEigyouDay_1"))
    req_item.append(item)

    json_text = func_make_json_format(req_item)

    func_write_to_file(
        "./eigyou_day.txt",
        json_text
    )

# ==========================================================
# 呼値情報(CLMYobine)
# ==========================================================

def func_read_yobine(master):

    print()
    print("========== CLMYobine ==========")

    print("呼値番号      :", master.get("sYobineTaniNumber"))
    print("適用日        :", master.get("sTekiyouDay"))

    print()

    # 呼値テーブル表示
    for i in range(1, 21):

        price = master.get(f"sKizunPrice_{i}")

        if price is None:
            continue

        if float(price) == 0:
            continue

        print(
            f"{i:2d}",
            "基準価格=", price,
            "呼値=", master.get(f"sYobineTanka_{i}"),
            "小数=", master.get(f"sDecimal_{i}")
        )

# ==========================================================
# 市場情報(CLMMarket)
# ==========================================================

def func_read_market(master):

    print()
    print("========== CLMMarket ==========")

    print("市場コード :", master.get("sSizyouC"))
    print("市場名称   :", master.get("sSizyouN"))

    print()

# ==========================================================
# 銘柄情報(CLMMeigara)
# ==========================================================

def func_read_meigara(master):
    #
    # 必要な項目だけ表示
    #

    print(
        master.get("sIssueCode"),
        master.get("sIssueName"),
        master.get("sSizyouC")
    )

# ==========================================================
# 保存しない項目
# ==========================================================

REMOVE_KEYS = {
    "p_sd_date",
    "sCLMID",
}

# ==========================================================
# メイン処理
# ==========================================================
def main():

    save_master = defaultdict(list)

    for master in read_master("./master.txt"):

        clmid = master.get("sCLMID")

        if clmid not in SAVE_CLMID:
            continue

        save_data = {
            k: v
            for k, v in master.items()
            if k not in REMOVE_KEYS
        }

        save_master[clmid].append(save_data)

    # まとめてJSON保存
    for clmid, data in save_master.items():

        filename = clmid + ".json"

        with open(filename, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )
if __name__ == "__main__":
    main()