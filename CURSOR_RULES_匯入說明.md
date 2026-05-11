# Cursor Rule 匯入筆電（簡短說明）

## 方式 A：整個專案 clone 到筆電（建議）

1. 筆電 clone 本 repo（含 `.cursor/rules/`）。
2. 用 Cursor 開啟專案資料夾 → **Project Rules** 會自動讀取 `.cursor/rules/*.mdc`。
3. 確認規則檔：`/.cursor/rules/tw-stock-advisor.mdc`（已設 `alwaysApply: true`）。

## 方式 B：只貼到「使用者規則」（全專案共用）

1. 筆電 Cursor：**Settings → Rules**（或 General → Rules for AI）。
2. 開啟本 repo 檔案 **`investment_strategy.md`**（最完整），或較短的 **`.cursor/rules/tw-stock-advisor.mdc`** 內文。
3. **複製全文**貼入 **User rules** 區塊並儲存。
4. 注意：**User rules** 不含 `portfolio.json` 數值；實際持股仍以各電腦上的 repo／檔案為準。

## 方式 C：僅複製精簡版

貼 **`.cursor/rules/tw-stock-advisor.mdc`** 中 `---` **下方**的 Markdown 正文到 User rules（frontmatter 可省略或保留由 Cursor 決定是否報錯；若報錯則只貼正文）。

---

同步檔案時請一併維護：`portfolio.json`、`investment_policy.json`、`investment_strategy.md`。
