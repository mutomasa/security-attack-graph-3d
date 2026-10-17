# デモ台本（3〜5 分）

## 0. 事前準備（デモ前）
```bash
./scripts/run_vllm.sh        # 任意。無ければルールベース + テンプレート説明で動作
./scripts/run_backend.sh     # Neo4j 起動 + seed + FastAPI :8010
./scripts/run_streamlit.sh   # http://localhost:8501
```
ブラウザで Scenario A を開いた状態にしておく。

## 1. 背景（30 秒）
- 脆弱性スキャナは CVE を何百件も並べるが、どれから直すべきかは分からない
- 本当に知りたいのは「**どこから侵入し、どの権限を奪い、どのデータに届くか**」という経路

## 2. シナリオ読み込み（30 秒）
- 3D ビューを回して見せる。左の Internet から右の Customer Data へ攻撃が進む向きに並んでいる
- 凡例: 赤の八面体 = 脆弱性、紫の立方体 = Identity、緑に光る球 = 守るべきデータ

## 3. 質問（1 分）
- サイドバーの「顧客データに到達する最も危険な経路は？」を押す
- **赤い太線と流れる光**が最も危険な経路。Top Risk Path を読み上げる
  > Internet → Web Server → CVE-XXXX → Credential Leak → Service Account → S3 Bucket → Customer Data

## 4. 説明（1 分）
- Result Summary の説明文を読む（グラフから組み立てた文なので内容は正確）
- AI 解説は Qwen による補足。小型モデルなので注意書きを付けている、と一言添える
- 経路一覧: 2 位は Application 経由、3 位は VPN 経由。**同じ顧客データへの経路が複数ある**
- 3D ビューで Service Account をクリック → 隣接ノードだけが明るくなり、権限 `s3:GetObject` が見える

## 5. 追加の質問（任意・30 秒ずつ）
- 「S3 Bucket に到達するまでに必要な権限は？」→ `s3:GetObject`
- 「Service Account が漏洩した場合の影響範囲は？」→ S3 Bucket と Customer Data
- シナリオ B（API Key 漏洩）、C（認可過剰）に切り替えて同じ質問

## 6. 価値（30 秒）
- 脆弱性の一覧ではなく**攻撃経路**で判断できる → CVE-XXXX か Credential Leak を断てば Top 経路が消える
- 経路が説明できるので、経営層・現場の両方と対策の優先順位を合意しやすい
- 実データ（クラウド構成、IAM、スキャナ結果）を流し込めば継続診断の原型になる

## トラブル時
| 症状 | 対処 |
|---|---|
| 「バックエンドに接続できません」 | `./scripts/run_backend.sh` を確認 |
| 「シナリオが未投入です」 | サイドバー最下部の Seed ボタン |
| AI 解説が出ない | vLLM 停止中。テンプレート説明だけで進める |
| Neo4j が無い環境 | `GRAPH_BACKEND=memory ./scripts/run_backend.sh` |
