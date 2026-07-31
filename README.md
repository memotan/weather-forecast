# weather-forecast

複数の気象情報ソースを組み合わせて確度を高めた天気予報を、定時にスマホへ通知するシステムです。
GitHub Actions のスケジュール実行で、[ntfy.sh](https://ntfy.sh) 経由でプッシュ通知します。

## 仕組み

1. **Open-Meteo** ([api.open-meteo.com](https://open-meteo.com/)) から、JMA / GFS / ICON / ECMWF
   の4つの独立した予報モデル（すべてAPIキー不要）を取得
2. **気象庁（JMA）公式予報API**から、テキスト形式の天気予報と降水確率を取得
3. 各ソースの天気カテゴリ（晴れ・くもり・雨・雪・雷雨・霧）を集計し、一致度から
   **確度（高／中／低）** を算出。降水確率・気温は全ソースの平均とばらつき（範囲）を表示
4. 結果を [ntfy.sh](https://ntfy.sh) でスマホに通知

対象地域: 日野市・墨田区（東京）。`weather_notify/config.py` の `LOCATIONS` で変更できます。

## 通知の見方

1地域につき1行で表示されます。例: `日野市  ☀️晴れ🟢  ☔20%  🌡29/21℃`

- 天気の絵文字（☀️晴れ / ☁️くもり / 🌧️雨 / ❄️雪 / ⛈️雷雨 / 🌫️霧）
- 確度: 🟢高（各ソースがほぼ一致）／🟡中／🔴低（ソース間で予報が割れている）
- ☔ 降水確率（全ソース平均）
- 🌡 最高/最低気温（全ソース平均、℃）

## 通知タイミング

GitHub Actions の `schedule` (cron, UTC) で3回/日実行します。

| JST   | UTC (cron)      | 内容                     |
| ----- | ---------------- | ------------------------ |
| 7:30  | `30 22 * * *`    | 本日1日分の予報           |
| 12:00 | `0 3 * * *`      | 本日午後〜夜（12時以降）の予報 |
| 20:00 | `0 11 * * *`     | 翌日1日分の予報           |

## セットアップ

1. スマホに [ntfy](https://ntfy.sh/) アプリをインストールし、任意のトピック名（例:
   `weather-yourname-xyz123` のような推測されにくい名前を推奨）を購読する
2. このリポジトリの **Settings → Secrets and variables → Actions** で以下を設定
   - `NTFY_TOPIC`（必須）: 上記で決めたトピック名
   - `NTFY_SERVER`（任意）: 自前のntfyサーバーを使う場合のURL。省略時は `https://ntfy.sh`
3. `.github/workflows/notify.yml` が自動的にスケジュール実行される
   - 手動実行・動作確認は **Actions → Weather Notify → Run workflow** から `window` を選んで実行

## ローカルでの動作確認

```bash
pip install -r requirements-dev.txt

# 通知を送らず内容を標準出力に表示
NTFY_TOPIC=dummy python -m weather_notify.cli --window morning --dry-run
python -m weather_notify.cli --window afternoon --dry-run
python -m weather_notify.cli --window evening --dry-run

# 実際にntfy.shへ通知を送る場合
export NTFY_TOPIC=your-topic-name
python -m weather_notify.cli --window morning
```

## テスト

ネットワークアクセスを伴わないロジック（カテゴリ判定・集計・時間帯フィルタ）はユニットテストで検証しています。

```bash
pip install -r requirements-dev.txt
pytest
```

## ディレクトリ構成

```
weather_notify/
  config.py        # 対象地域・使用モデルなどの設定
  wmo.py            # 気象コード/JMAテキスト → 天気カテゴリのマッピング
  ensemble.py        # 複数ソースの集計・確度算出
  notify.py          # ntfy.shへの通知送信
  cli.py            # エントリポイント（時間帯ごとのデータ収集とメッセージ生成）
  sources/
    open_meteo.py    # Open-Meteo マルチモデル予報の取得
    jma.py            # 気象庁公式予報APIの取得・パース
tests/                # ユニットテスト
.github/workflows/
  notify.yml          # 定時通知ワークフロー
  test.yml            # テスト実行ワークフロー
```
