# 貢獻指引 / Contributing

歡迎貢獻，尤其是**新增縣市**。

## 開發環境

```bash
pip install -r requirements.txt
python main.py
```

## 最常見的貢獻：新增一個縣市

各縣市是 `scheduler/cities/` 下的一個獨立外掛檔。新增縣市只需複製一個檔並註冊一行，
完整步驟見 **[docs/ADD_A_CITY.md](docs/ADD_A_CITY.md)**。

縣市外掛不依賴 Qt，可直接用 Python 驗證你的 SOAP 格式與回應解析：

```python
from scheduler.cities.<yourcity> import <YourCity>Plugin
p = <YourCity>Plugin()
print(p.build_entry(enabled=True, interval_minutes=10,
                    values={...}, credentials={...})["body"])
```

## 程式風格

- 命名遵循 PEP 8：模組/函式/變數 `snake_case`、類別 `PascalCase`、常數 `UPPER_SNAKE_CASE`。
- 對外交換的 dict key（API/log）用 `camelCase`；內部設定檔 key 用 `snake_case`。
- Log 採 JSONL（每行一個 JSON），欄位見 `scheduler/core/logger.py`。
- 送 PR 前請確認 `python -m pyflakes scheduler main.py` 無警告、
  `python -m py_compile` 全數通過。

## 架構

送較大的改動前，建議先讀 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 與
[docs/FILE_REFERENCE.md](docs/FILE_REFERENCE.md)。

## 回報安全問題

請勿開公開 issue，改依 [SECURITY.md](SECURITY.md) 來信。

## 授權

送出貢獻即表示你同意以本專案的 [Apache-2.0](LICENSE) 授權釋出你的貢獻。
