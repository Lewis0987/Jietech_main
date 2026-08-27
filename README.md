# Jietech — 全網站功能自動化測試

## 1. 專案目的

這是一套針對 **IN V6 網站（`https://in-u6.ttgroup-dev.com/hall`）** 的
**E2E / Smoke Automation Test**，目標是把網站上「可安全操作」的主要功能都實際跑過一次。

目前架構已實作並實測的能力：

- 全站主要功能測試（首頁 Popup / Header / Banner / 導覽選單 / 個人中心 / 帳號 / 帳變明細 / 活動 / 任務中心 / 團隊俱樂部 / 下級資料查詢）
- Flow 模組化，可單獨執行或一次執行全部
- 每個功能一個獨立 Case，做到 Found → Action → Post-condition → Recovery
- Headed / Headless 兩種模式，逐 Case 結果一致
- Case 與 Flow 雙層錯誤隔離：單一失敗不會中斷整體流程
- PASS / FAIL / SKIP 三態結果
- FAIL 自動截圖
- CSV / JSON 測試結果輸出
- DOM 唯讀探查（含 React SPA 的「可互動元素」分析）
- 內頁 DOM Snapshot
- Download APK 端到端測試（含下載完成判定與自動清理）
- Safety L1 破壞性功能保護
- Recovery 自動回到穩定頁面
- Stability / Flaky 驗證（連續多輪 Regression 比對）
- 自動 Regression：Baseline 逐 Case 比對、Known Fail 判定、明確 Exit Code
  （**Regression Automation Ready / Scheduled Deployment Validated / Automatic Schedule Currently Disabled**）

---

## 2. 專案結構

```
D:\Jietech
├─ README.md
└─ test/
    ├─ IN【V6】.py            # 原始參考腳本（不修改）
    ├─ URL.ini                # 環境網址設定（不修改）
    ├─ config.py              # 全域設定：URL / 下載路徑 / SAFE_LEVEL / 逾時
    ├─ full_site_test.py      # 測試入口（CLI）
    │
    ├─ common/                # 共用工具
    │   ├─ driver_utils.py    # ChromeOptions / Driver 建立 / 分頁處理
    │   ├─ wait_utils.py      # WebDriverWait 封裝 / safe_click / probe / catch_toast
    │   ├─ popup_utils.py     # Popup 偵測與關閉 / 通用 modal 判斷
    │   ├─ download_utils.py  # 下載快照 / 完成判定 / 清理 / 路徑診斷
    │   ├─ result_utils.py    # Reporter / Case / CSV / JSON / 截圖
    │   ├─ recovery.py        # 回到穩定頁面
    │   └─ dom_scan.py        # 共用 DOM 掃描 JS（語意元素 + 可互動元素）
    │
    ├─ flows/                 # 各功能區自動化流程
    │   ├─ popup_flow.py      # [A] 首頁 Popup
    │   ├─ header_flow.py     # [B] Header
    │   ├─ banner_flow.py     # [C] 首頁 Banner
    │   ├─ menu_flow.py       # [D] TabBar / 分類 / Search / 跑馬燈
    │   ├─ safety_flow.py     # [E] 破壞性功能 L1 驗證
    │   ├─ mine_flow.py       # [F] MINE 個人中心
    │   ├─ account_flow.py    # [G] Account 個人資料
    │   ├─ record_flow.py     # [H] Balance details 查詢 / 篩選
    │   ├─ promo_flow.py      # [I] PROMO 活動頁
    │   ├─ task_flow.py       # [J] Task Center 安全分類
    │   ├─ earn_flow.py       # [K] EARN / Team Club
    │   └─ subordinate_flow.py # [L] Subordinate Data 查詢
    │
    ├─ baseline/              # Regression Baseline（人工維護，不自動更新）
    │   └─ regression_baseline.json
    ├─ run_scheduled_regression.bat  # Windows 排程入口（尚未註冊排程）
    │
    ├─ tools/                 # 測試產物維護
    │   ├─ cleanup_output.py  # Output Retention 清理（預設 dry-run）
    │   ├─ safety_audit.py    # 測試結果安全稽核（語意判斷，非關鍵字比對）
    │   ├─ stability_runner.py # Stability / Flaky 驗證（連續執行既有 Regression）
    │   └─ scheduled_regression.py # 自動 Regression：Baseline 比對 + Safety + Summary
    │
    ├─ probe/                 # DOM 唯讀探查
    │   ├─ dom_probe.py       # 全站元素盤點 / Banner 輪播取樣 / Popup 佇列快照
    │   └─ deep_probe.py      # /account /record /activity /task_center /teamClub
    │                         #   /subordinateData 可互動元素深度探查
    │
    └─ output/                # 測試產物（已加入 .gitignore）
        ├─ result_<ts>.csv
        ├─ result_<ts>.json
        ├─ screenshots/       # FAIL 截圖
        ├─ probe/             # DOM Snapshot 與探查結果
        ├─ stability/         # Stability 報告（一律保留，不清理）
        └─ automation/        # 自動 Regression Summary + logs/
```

- `common/` — Driver / Wait / Popup / Download / Result / Recovery / DOM 等共用工具
- `flows/` — 各網站功能區的自動化流程，每個模組提供 `run(ctx)`
- `probe/` — DOM 唯讀探查，用來確認 locator，不做任何功能操作
- `tools/` — 測試產物維護工具
- `output/` — CSV / JSON / Screenshot / DOM Snapshot

---

## 3. Flow Coverage

以最後一次完整 Regression 的實際 Case 數為準。

| 代號 | Flow | 主要功能 | Case 數 | 安全限制 |
|---|---|---|---|---|
| **[A]** | `popup` | Subscribe / 充值大輪盤 / 首充 / 任務中心 / 俱樂部 / Telegram / Jackpot，佇列式逐一關閉 | 9 | 只關閉 popup，不點任何活動按鈕 |
| **[B]** | `header` | Download APK 端到端、下載列關閉、充值輪盤、Mail 信箱 | 4 | 輪盤頁的 Deposit / SPIN 只驗證 |
| **[C]** | `banner` | 首頁 Banner 輪播（`data-swiper-slide-index` 定位，Swiper API 逐格控制） | 12 | Collect / SPIN / Deposit 只驗證 |
| **[D]** | `menu` | TabBar HOME / PROMO / 邀請轉盤 / EARN / MINE、7 個遊戲分類、**Lobby Search 完整 E2E**、公告跑馬燈、`ic_volume` | 20 | 不點遊戲卡片、不啟動遊戲；音量類操作需可還原 |
| **[E]** | `safety` | Deposit / Withdraw / First Deposit / LiveChat / 首充金額 / checkbox / Collect / SPIN / Submit / Redeem | 14 | **全部 L1，零點擊** |
| **[F]** | `mine` | My info / Mission / Balance details / Live support / Gifts / Join our community / Download App / Refresh / Logout | 11 | Live support、Download App、Logout 為 L1 |
| **[G]** | `account` | Avatar / Nickname / Gender（開關 modal）、Player ID / 邀請碼（唯讀）、綁定手機 / 登入密碼 / 綁定邀請碼（L1） | 10 | 測試前後比對全部欄位，確認資料未變 |
| **[H]** | `record` | Detail Record Tab / **Withdrawal Record Tab**、All / Income / Expense 篩選、欄位標題驗證、Empty state、查詢控制項覆蓋盤點 | 8 | 純查詢，測試後恢復初始狀態 |
| **[I]** | `promo` | `/activity` 活動卡片盤點與逐一驗證 | 12 | Claim / Redeem / Submit / SPIN / Deposit 只驗證 |
| **[J]** | `task` | Task Center：Claim all + 6 個 Go 的安全分類 | 9 | **全部 L1，零點擊** |
| **[K]** | `earn` | Team Club：My Rewards / Invite Rewards / Rules 分頁、Club Stars Detail（`/subordinateData`）、說明 icon、Rebate 輪播、Invite your friends（`/share`） | 14 | Claim / Claim all / Invite Now! / Telegram / WhatsApp / Copy Link / Save Picture 全部 L1 |
| **[L]** | `subordinate` | Subordinate Data：統計顯示、Tier 1~3、Join Time / Commission 排序、日期選擇、Phone Number 搜尋、Empty state | 12 | 只用測試字串查詢；日期只 Cancel 不 Confirm |

---

## 4. Safety Level

### L1 — 只驗證，禁止執行

只做：`Found` → `Displayed` → `Enabled / Clickable`，**不呼叫 click()**。

目前列為 L1 的功能：

- Deposit
- Withdraw
- First Deposit
- Logout
- Claim
- Claim all
- Task Center 的 Go ×6（目的無法唯讀確認，維持 L1）
- SPIN
- Redeem
- Submit
- Confirm
- Gift code 輸入框與 Confirm
- Bind phone number（modal 內含 Send 簡訊驗證碼）
- Login password（修改密碼）
- Bind invitation code
- My invitation code 的複製
- Live support（開啟客服視窗需跨網域操作 iframe，無法可靠復原）
- Team Club 的 Claim（實測 `disabled=true`，仍不點擊）
- Team Club 的 Invite Now!（導向未經探查確認，依原則維持 L1）
- `/share` 的 Copy Link（會修改剪貼簿）與 Save Picture（會產生下載檔）
- Subordinate Data 日期選擇器的 Confirm（會改變查詢條件；只用 Cancel 關閉）
- 搜尋結果中的遊戲卡片與 `Play` / `Enter` / `Start`（不啟動任何遊戲）
- Telegram / WhatsApp 等外部連結

L1 的 Case 會在步驟中標記 `[SAFE-L1]`。

### L2 — 允許可逆操作

允許執行、但完成後必須 Recovery 或恢復原始狀態：

- 頁面導航（TabBar、MINE 選單、站內返回）
- Tab 切換（Detail / Withdrawal）
- Filter 篩選（All / Income / Expense）
- 遊戲分類切換
- Lobby Search 開啟 / 輸入 / 清空 / 關閉（`/search_game`）
- Modal 開啟 / 關閉（Avatar / Nickname / Gender / Gifts）
- Team Club 分頁切換與 Rebate 輪播（左右各一次後還原）
- Subordinate Data 的 Tier 篩選、排序切換、搜尋輸入（測試字串，事後清空還原）
- Popup 關閉

`config.SAFE_LEVEL` 預設為 `1`；`config.assert_safe()` 會在正式環境
（`INPV6`、`7IND`）強制拒絕提高等級。

### Lobby Search E2E（`D-13` ~ `D-13-5`）

Search 是**獨立頁面** `/search_game`（不是 modal），入口是大廳的 `Search` 按鈕。

| 項目 | 實測結果 |
|---|---|
| input | `placeholder='Find your favorite game'`、`type=text`、`inputMode=text`、**`maxLength=32`** |
| 觸發方式 | React `onChange` / `onInput` -> **即時搜尋，不需要按 Enter** |
| 結果標題 | `Search results for the term “<keyword>” are:` |
| 結果卡片 | 遊戲圖 189×265 + 標題 |
| Empty state | 文字 `It is empty here.` |
| 返回 | `img[alt='ic_back_header']` |

涵蓋的 Case：

| Case | 內容 |
|---|---|
| `D-13` | 開啟 Search UI、確認 input 出現 |
| `D-13-1` | **正常關鍵字**：關鍵字由大廳實際可見的遊戲名稱動態取得（不寫死、不猜遊戲名），驗證結果標題、結果數量、結果標題含關鍵字 |
| `D-13-2` | **部分關鍵字 + 大小寫**：前半段關鍵字可搜到更多結果；大寫關鍵字結果相同 -> 大小寫不敏感 |
| `D-13-3` | **Empty state**：輸入不可能命中的測試字串，驗證結果 0 筆且顯示 `It is empty here.` |
| `D-13-4` | **Clear**：`W.clear_input()` 清空後 value 為空、結果標題消失、卡片歸零 |
| `D-13-5` | **結果只讀驗證 + Recovery**：列出結果卡片但**零點擊**，清空搜尋框、返回大廳、驗證錨點/分頁數/無殘留 modal |

兩個實作重點：

- **`img[alt='img_no_results']` 在有結果時也存在於 DOM**，不能用它判斷 Empty state，必須用文字判斷。
- 輸入框會**過濾底線**（`QA_AUTOMATION_...` 會變成 `QAAUTOMATION...`），因此測試字串不含底線。

輸入一律共用 `W.type_text()` / `W.clear_input()`，未在 flow 內另寫 `send_keys` / `clear()`。

### ⚠ 搜尋結果的遊戲一律零點擊

Search 本身是 **L2**（可逆導覽），但**搜尋結果中的遊戲是 L1**：

- 只驗證 Found / Displayed / 標題 / 結果數量
- **不點擊遊戲卡片、不啟動遊戲、不進入 Provider、不開遊戲 iframe**
- 若結果頁出現 `Play` / `Enter` / `Start`，一律只驗證存在，標記 `[SAFE-L1]`

Phase 10 的目的是測「搜尋功能」，不是「遊戲啟動」。

### ⚠ Withdrawal Record Tab ≠ Withdraw

站上有兩個名稱相近但性質完全不同的東西，測試與稽核都必須分開看待：

| 名稱 | 位置 | 性質 | 分級 |
|---|---|---|---|
| **Withdrawal Record Tab** | `/record` 的查詢頁籤 | 交易紀錄查詢，可逆導覽 | **L2**（Case `H-4`，會實際點擊） |
| **Withdraw** | 大廳帳號區的按鈕 | 真正的提款入口，不可逆 | **L1**（Case `E-2`，零點擊） |

Case 名稱、log 與稽核規則都已明確標示為 `Withdrawal Record Tab`，
避免被誤判成提款操作。

### Safety Audit

`tools/safety_audit.py` 會讀取 result JSON，確認自動化沒有執行破壞性操作。

```bash
python -m tools.safety_audit            # 稽核最新一份 result JSON
python -m tools.safety_audit --last 3   # 稽核最近 3 份
python -m tools.safety_audit -v         # 另外列出所有 [SAFE-L1] case
```

**判斷方式不是單純 grep 關鍵字**，而是結合五項資訊：

| 維度 | 用途 |
|---|---|
| Case ID | 對應到哪一個 case |
| Flow | result JSON 的 `group`（A~L） |
| URL | 由步驟推導該 case 當時所在頁面（同 flow 內沿用最後已知頁面） |
| Action | 只檢查 `[action]` 步驟，不看 `[check]` / `[found]` |
| 元素語意 | 區分 `Withdrawal Record Tab` 與 `Withdraw` 按鈕等 |

另用詞界區分英文單字：`withdraw`（提款動作）與 `withdrawal`（提款紀錄）
不會互相誤判。

規則：

- 標記 `[SAFE-L1]` 的 case **必須完全沒有點擊動作**，有的話一律視為違規
- 含風險關鍵字但確認安全者，必須在 `SAFE_EXEMPTIONS` 明列
  case / flow / 動作樣式 / 頁面 / 元素語意 / **理由**，不是無差別白名單
- 有違規時 exit code 回傳 `1`

---

## 5. Download E2E

Header 的 Download 是唯一會真正下載檔案的測試（Case `B-1`）。

流程：

1. `snapshot(download_path)` — 下載前檔名快照
2. 點擊 Download（若開新分頁，先切過去，**等下載結束後才關閉分頁**）
3. 等待下載完成
   - 排除 `.crdownload` / `.tmp` / `.partial`
   - 要求檔案大小連續穩定
   - 逾時上限 60 秒
4. 確認本次新增的 APK 已完成 → PASS
5. `delete_downloads()` — 只刪除本次新增的檔案
6. `assert_deleted()` — 確認刪除成功
7. 比對 before 快照，確認既有檔案沒有被誤刪

`ChromeOptions.prefs["download.default_directory"]` 與
`download_utils` 監控的路徑**使用完全相同的 `config.DOWNLOAD_PATH`**
（`Path.home() / "Downloads"`，不寫死使用者名稱）。

若下載逾時，`download_utils.diagnose()` 會掃描其他候選資料夾
（含 Windows 登錄檔的「下載」重導向路徑），把靜默逾時變成可診斷訊息。

### CDP

**預設不使用 CDP `setDownloadBehavior`。**

實測結論：在目前 Chrome 環境呼叫 `Page.setDownloadBehavior` 或
`Browser.setDownloadBehavior`（兩者皆然，甚至頁面只是 `about:blank`）時，
Chrome 會把自身的元件 / 擴充套件更新（CRX）當成一般下載寫入下載資料夾，
產生 `downloads.htm*.crdownload` 殘檔。對照組（只用 prefs、不呼叫 CDP）
完全沒有殘檔，且下載路徑正常。

因此正常情況一律使用 ChromeOptions prefs；保留
`--force-download-cdp` 作為特殊主機真的發生下載路徑不一致時的 fallback。

---

## 6. 執行方式

於 `D:\Jietech\test` 目錄下執行。

```bash
# 列出可用 flow（含預設執行順序）
python full_site_test.py --list

# 只跑框架 smoke test（不需要任何 flow）
python full_site_test.py --smoke

# 單獨執行某個 flow
python full_site_test.py --flows header
python full_site_test.py --flows mine
python full_site_test.py --flows account
python full_site_test.py --flows record
python full_site_test.py --flows promo
python full_site_test.py --flows task
python full_site_test.py --flows earn
python full_site_test.py --flows subordinate

# 完整執行
python full_site_test.py --flows popup,header,banner,menu,safety,mine,account,record,promo,task,earn,subordinate

# 不帶 --flows 時預設執行全部 flow
python full_site_test.py

# Headless
python full_site_test.py --headless
```

其他可用參數：

| 參數 | 說明 |
|---|---|
| `--env` | `URL.ini` 的 section，預設 `IN` |
| `--product` | `URL.ini` 的 key，預設 `INV6` |
| `--keep-open` | 結束後不關閉 Chrome |
| `--popup-watcher` | 啟用背景 popup 監控（預設關閉） |
| `--force-download-cdp` | 用 CDP 強制下載目錄（見第 5 節） |
| `--safe-level` | 破壞性保護等級，預設 1 |
| `--inject-failure` | smoke 時加入一個刻意失敗的 case，用來驗證錯誤隔離 |

DOM 探查（唯讀，不做功能操作）：

```bash
python -m probe.dom_probe --routes
python -m probe.dom_probe --banner-watch 45 --popup-queue
python -m probe.deep_probe
python -m probe.deep_probe --only account,record
python -m probe.deep_probe --only teamclub
python -m probe.deep_probe --only subordinate
```

安全稽核與產物清理：

```bash
python -m tools.safety_audit            # 稽核最新一次測試結果
python -m tools.cleanup_output          # 產物清理 dry-run（預設不刪除）
```

---

## 7. Result

每次執行都會輸出到 `test/output/`：

| 產物 | 內容 |
|---|---|
| `result_<timestamp>.csv` | Timestamp / Group / Case ID / 名稱 / 狀態 / 執行時間 / 錯誤類型 / 錯誤訊息 / 截圖路徑 / 驗證步驟 |
| `result_<timestamp>.json` | 同上，另含 meta（瀏覽器版本、目標環境、下載路徑）與統計摘要 |
| `screenshots/FAIL_<caseid>_<time>.png` | FAIL 時自動截圖 |
| `probe/snapshot_*.json` | 內頁 DOM Snapshot |
| `probe/deep_*.json`、`probe/probe_*.json` | DOM 探查結果 |

結果定義：

- **PASS** — 功能符合目前的驗證條件（Found / Action / Post-condition 全部成立）
- **FAIL** — 功能異常，或 Post-condition 不成立
- **SKIP** — 本次條件不存在（popup 未出現、活動未上架）、
  安全限制不執行（L1）、或已知上游問題導致無法執行

Terminal 會即時列出每個 Case 與最後的 Summary，
exit code：全部通過為 `0`，有 FAIL 為 `1`。

### Output Retention（產物清理）

`output/` 會隨每次執行累積，可用 `tools/cleanup_output.py` 依保留規則清理。

```bash
# dry-run（預設）：只列出計畫，不刪除任何檔案
python -m tools.cleanup_output

# 確認無誤後才真的刪除
python -m tools.cleanup_output --apply

# 自訂保留數量
python -m tools.cleanup_output --keep-results 30 --keep-snapshots 5
```

保留規則：

| 產物 | 命名 | 保留 |
|---|---|---|
| result CSV / JSON | `result_<ts>.csv` / `.json` | 最近 **20** 次 execution |
| Automation Summary | `automation/automation_<ts>.*`、`automation/logs/scheduled_<ts>.log` | 最近 **30** 份；**有新 Regression 的永久保留** |
| Stability 報告 | `stability/stability_<ts>.*` | **一律保留**，不參與清理 |
| FAIL 截圖 | `screenshots/FAIL_<caseid>_<HHMMSS>.png` | 與所屬 execution 連動（見下） |
| DOM Snapshot | `probe/snapshot_<name>_<ts>.json` | 每個 `<name>` 最近 **3** 份 |
| dom_probe | `probe/probe_<ts>.json` | 最近 **5** 份 |
| deep_probe | `probe/deep_<ts>.json` | 最近 **5** 份 |

截圖關聯方式：截圖檔名只有 `HHMMSS`、沒有日期，因此**不從檔名推測歸屬**，
而是讀取每個 result JSON 的 `screenshot` 欄位取得確切路徑：

- 被保留的 execution 引用 → KEEP
- 只被將刪除的 execution 引用 → DELETE
- 沒有任何 result 引用到 → **KEEP**（無法可靠關聯，寧可保留）

因此不會出現「保留下來的 CSV/JSON 指向已被刪除的截圖」。

安全守門：

- 預設一定是 dry-run，**只有 `--apply` 才會刪除**
- 只處理 `test/output/` 內符合上述命名規則的檔案
- 不符合命名規則者一律標記 **UNKNOWN，永遠不刪**
- 路徑 resolve 後必須仍位於 `test/output/` 之內；禁止 `..` 逃逸；禁止 symlink
- dry-run 與 `--apply` 使用**完全相同的 selection logic**
- 刪除前會列出：完整路徑 / 類型 / timestamp / size / 刪除原因
- 單一刪除失敗不會中止其他項目，但 exit code 會反映失敗（有失敗回傳 `1`）

---

## 8. Known Issues

### C-00 首頁 Banner 無法顯示 / 無法點擊

**【已確認現象】**

- Banner DOM 存在，`data-swiper-slide-index` 共 10 格
- 圖片已載入完成（`complete=true`，naturalSize 1080×402）
- 但 rendered height 為 0（輪播容器 21px、wrapper 21px，含圖 slide 的圖片高度 = 0px）
- 螢幕截圖確認：使用者畫面上完全沒有 Banner 區塊
- Headed 與 Headless 結果相同

**【疑似原因】**

swiper 的 class 中發現 `min-h-max]`（多一個右中括號），
疑似 Tailwind class 拼寫異常導致高度規則未生效。

> 這仍只是疑似原因，**不是已確認的 Root Cause**，
> 需要前端修改前後驗證才能確認。

因此 `C-00` 維持 FAIL，`C-01`～`C-10` 因 Banner 不可操作而 SKIP。

### I-00 PROMO 活動頁無法操作

**【已確認現象】**

- `/activity` 共 10 張活動卡片，標題文字存在於 DOM
- 卡片容器 rendered height 為 0，標題列以每 16px 間距互相重疊
- `document.elementFromPoint` 驗證：只有 1 張是最上層，其餘 9 張被覆蓋
- 逐一檢查標題列、卡片容器與其上一層：**0 / 10 張帶有 click handler**，
  卡片只有 `cursor: pointer` 樣式而沒有實際綁定點擊事件
- 螢幕截圖確認：使用者只看得到一張空白卡片輪廓
- Headed 與 Headless 結果相同

**【疑似原因】**

與首頁 Banner 相同的版面塌陷型態（卡片背景圖未撐開容器），
且活動卡片未綁定點擊事件。

> 同樣只是疑似原因，**未經前端修改前後驗證，不得視為已確認 Root Cause**。

因此 `I-00` 維持 FAIL，`I-01`～`I-10` SKIP 並附上各自的實測證據。

### Interactive-only Task 在主機睡眠時無法保證準時執行

**這是排程環境限制，不是 Test Regression。**

正式 Task 的 Logon Mode 是 `Interactive only`（僅登入時執行），
當主機處於 Sleep / Modern Standby 時，排程**不保證於原定時間啟動**。

2026/08/27 實際發生：

| 時間 | 事件 | 證據 |
|---|---|---|
| 08:30 | 排程時間到，**未執行** | 主機處於 Modern Standby |
| 08:53:14 | 系統從低耗電狀態恢復 | Kernel-Power **507** + **566** |
| 08:53:12 | Task Scheduler 補跑 | `LastRunTime` |
| ~08:55 | 行程被終止（約 90 秒後） | `LastTaskResult = 0xC000013A`（`STATUS_CONTROL_C_EXIT`） |

分類：**SCHEDULER / ENVIRONMENT FAILURE**
—— 不是 Regression Failure、不是 Safety Failure、不是 Flaky Test。
因此**未**修改任何 Flow、Selenium timeout、retry 或 Baseline。

中斷後環境是乾淨的：無殘存 chromedriver / chrome 行程、
Downloads 殘留 0、未產生半成品 result / summary、Baseline 未被動到。

**技術評估已完成但依需求未啟用**：

- 本機為 **Modern Standby (S0)** 機型（S1/S2/S3 皆不支援）
- Power Plan 的 `Allow wake timers`：**AC = 啟用**、DC = 停用
- `WakeToRun` / `StartWhenAvailable` 可設定且已驗證可寫入，
  但因目前沒有「睡眠中自動喚醒跑測試」的需求，正式 Task 已**還原為 `False`**

若日後需要每日自動執行，建議順序：
重新 Enable Task → 視情況開啟 `WakeToRun` / `StartWhenAvailable` →
實測一次 Sleep → Wake → Full Regression。

### 其他已記錄但非缺陷的項目

- `D-15 ic_volume` — 實測點擊前後 `alt / class / src / 父層 / 祖父層`
  皆無變化，且位於公告跑馬燈列內，判定為裝飾性圖示而非音效開關，記為 SKIP。
- `/task_center` 的 `Go` ×6 — React onClick 已被 minify 成 `h=>{d(h)}`，
  無法唯讀判斷導向何處；任務本身是「投注 1000」流水任務，
  依安全原則維持 L1，未點擊。
- `/teamClub` Rules 分頁的 `Invite Now!` ×3 — onClick 同樣被 minify 成 `m=>{d(m)}`，
  無法唯讀確認導向，維持 L1。
- `/subordinateData` — 開啟日期選擇 modal 會把 `Join Time` 的排序指示
  由 `ic_arrow_down_1` 重置為 `ic_up_and_down`。屬前端暫態（重新載入即回到預設排序），
  非資料異常；`L-99` 會主動還原並驗證。
- `/subordinateData` 的搜尋輸入框是 React 受控元件：一次送整串字只會留下 1 碼，
  且 `element.clear()` 無效。已在 `wait_utils` 提供 `type_text()` / `clear_input()` 因應。
  **其他頁面的 input 一律共用這兩個 helper，不要各 flow 自己重寫輸入邏輯。**
- `/record` **目前沒有** 搜尋 input、日期選擇、排序、分頁控制項
  （Detail 與 Withdrawal Record 兩個分頁、捲動到底皆已確認）。
  因此不建立對應 Case；`H-6` 會持續盤點這些控制項數量，
  一旦網站新增即可從 `H-6` 的輸出發現並補測。
- Lobby Search 的 `img[alt='img_no_results']` **在有結果時也存在於 DOM**，
  判斷 Empty state 必須用文字 `It is empty here.`，不能用該圖片。
- Lobby Search 的輸入框會過濾底線字元，且 `maxLength=32`。
- **`W.probe()` 的 clickable 判定**（Phase 11 由 stability run 找出的測試缺陷，已修正）：
  `WebDriverWait` 預設只忽略 `NoSuchElementException`，
  React 重繪時 `element_to_be_clickable` 內部丟出的
  `StaleElementReferenceException` 會直接穿出，
  讓 `clickable` 在數百毫秒內就被誤判為 `False`。
  實測案例 `D-8 遊戲分類 ic_original`：整個 case 只花 0.46s 就失敗（正常約 1.7s），
  且 `found` / `displayed` / `enabled` 全為 `True`。
  修正方式是把 Stale 列入 `ignored_exceptions`，並讓 clickable 沿用呼叫端的 timeout。
- `/record` 分頁的 active 標記是內部的 `img[alt='active']`，不是 class token。
  Phase 6~8 使用 class 判斷時 `active` 一直讀不到（顯示 `tab=None`），
  Phase 9 已修正，`H-4` / `H-5` 現在能真正驗證 active 分頁。

---

## 9. Stability Test

`tools/stability_runner.py` 用來確認 Regression 結果**可重複、可信**。

它**不重複實作任何 Case** —— 只負責連續呼叫既有的 `full_site_test.py`
（每輪都是全新 Python 行程，因此保證全新 Chrome Driver 與 session），
再收集、比對、統計各輪的 result JSON。

```bash
python -m tools.stability_runner --runs 3 --modes headed
python -m tools.stability_runner --runs 3 --modes headless
python -m tools.stability_runner --runs 2 --modes headed --flows record   # 快速驗證
```

### Case 穩定性分類

| 分類 | 定義 |
|---|---|
| **STABLE PASS** | 每輪都 PASS |
| **STABLE FAIL** | 每輪都 FAIL，且 `error_type` 一致 —— 代表**缺陷可穩定重現**，不是 Flaky |
| **STABLE SKIP** | 每輪都 SKIP，且原因一致 |
| **FLAKY** | 跨輪狀態不一致，或同樣 FAIL 但失敗原因不同 |
| **SLOW** | `MAX` 明顯高於 `AVG`（只標記，不判 FAIL） |

Popup 是佇列式彈出，各輪出現的種類與順序本來就可能不同；
只要未出現者依規則正常 SKIP，就**不視為測試不穩**。

Search 結果數量會隨網站遊戲清單變動，因此**不寫死結果數量**，
只驗證「至少一筆符合關鍵字 + 搜尋功能正常」。

### 報告

輸出到 `test/output/stability/`：

- `stability_<ts>.csv` —— 每輪每個 Case 一列（mode / run / case / status / elapsed / error / classification）
- `stability_<ts>.json` —— 完整彙整，含每 Case 的 AVG / MIN / MAX 與分類理由

原始的 `result_*.csv` / `result_*.json` **不會被覆蓋**。
`cleanup_output.py` 會把 `output/stability/` 一律標記為 KEEP，不參與清理。

每輪結束後會直接呼叫既有的 `tools/safety_audit.py`，不另建第二套稽核。

### 最新 Stability Baseline

**Headed × 3 + Headless × 3（共 6 次 Full Regression，每輪 135 Cases）**

```
每輪結果   : PASS 104 / FAIL 2 / SKIP 29（6 輪完全一致）
STABLE PASS: 104
STABLE FAIL: 2   （C-00、I-00 —— 網站缺陷可穩定重現）
STABLE SKIP: 29
FLAKY      : 0
SLOW       : 0
Safety Audit: 6 輪皆 PASS，違規 0
Downloads 殘留: 0
```

單輪耗時：Headed 362.91 ~ 389.49s、Headless 354.25 ~ 369.38s。

---

## 10. Scheduled / CI Regression

> **目前狀態**
> - **Regression Automation Ready** —— 自動化能力已完成
> - **Scheduled Deployment Validated** —— Windows Task Scheduler 部署與
>   Lock Screen 無人操作執行皆已實測通過
> - **Automatic Schedule Currently Disabled** —— 因目前沒有每日自動 Regression 的
>   實際需求，正式 Task 已**停用（Disable，未刪除）**，需要時可直接重新 Enable
>
> Sleep / Modern Standby 喚醒執行與長期 Scheduled Stability 觀察
> 因目前無實際需求而**暫緩（Deferred）**，非技術失敗。

`tools/scheduled_regression.py` 是自動化的**編排層**，不重複實作任何 Case：

```
Headless full_site_test.py  →  取得 result JSON  →  Safety Audit
      →  Baseline 逐 Case 比對  →  Download 殘留檢查
      →  Automation Summary  →  Exit Code
```

### Raw Result 與 Automation Status 是兩件事

這是本設計最重要的一點。`C-00` / `I-00` 是已知網站缺陷，
因此 CI **不能**用 `raw FAIL > 0 → pipeline FAIL` 這種判定。

| 概念 | 內容 |
|---|---|
| **Raw Result** | `135 / 104 PASS / 2 FAIL / 29 SKIP` —— 原始事實，**絕不篡改** |
| **Baseline Comparison** | `C-00` / `I-00` 屬 KNOWN STABLE FAIL，不算新問題 |
| **Final Automation Status** | `PASS（No New Regression）` |

Reporter 不會被改成假裝 135 全 PASS，`result_*.json` 永遠保留真實的 FAIL。

### Baseline

`test/baseline/regression_baseline.json`，逐 Case 記錄 **Expected Status**
（135 個 Case），而不是只存 `104 / 2 / 29` 這種總數——
只比總數會漏掉「一個 PASS 變 FAIL、另一個 FAIL 剛好變 PASS」的情形。

**Baseline 絕不自動更新。** 自動 Regression 只會讀取它；
要更新必須人工明確執行：

```bash
python -m tools.scheduled_regression --init-baseline
```

### 比較分類

| 分類 | 意義 | 影響 CI |
|---|---|---|
| `EXPECTED PASS` / `EXPECTED SKIP` | 與 Baseline 相同 | 否 |
| `EXPECTED FAIL` | **KNOWN STABLE FAIL**（C-00 / I-00） | 否 |
| `NEW FAIL` | Baseline 非 FAIL，本次 FAIL | **是** |
| `MISSING CASE` | Baseline 有但本次沒跑到 | **是** |
| `NEW SKIP` | PASS 變 SKIP，覆蓋率下降 | 否（警告） |
| `RECOVERED` | Known Fail 變 PASS，網站可能已修好 | 否（提醒人工更新 Baseline） |
| `STATUS CHANGED` | 其他狀態轉換 | 否（警告） |
| `NEW CASE` | 新增的 Case | 否（提醒人工更新 Baseline） |

### Exit Code 契約

| Code | 意義 |
|---|---|
| `0` | 無新 Regression、Safety Audit PASS、Runner 正常 |
| `1` | 出現 `NEW FAIL` / `MISSING CASE` / Safety violation |
| `2` | Runner / Browser / Result 解析失敗 |

**Safety violation 一律讓最終結果 FAIL**，不論 Baseline 比對是否正常。

### 執行方式

```bash
# 正式自動 Regression（Headless）
python -m tools.scheduled_regression

# 人工建立 / 更新 Baseline
python -m tools.scheduled_regression --init-baseline

# 只比對既有結果，不重跑測試（Debug 用）
python -m tools.scheduled_regression --from-result output/result_<ts>.json

# Windows 排程入口（固定工作目錄 / 絕對路徑 Python / UTF-8 / 落 log）
test
un_scheduled_regression.bat
```

正式自動 Regression **預設 Headless**（Phase 11 已證明 6 輪 Headed/Headless 結果一致），
單輪約 6~7 分鐘。Headed 保留給人工 Debug、新 Case 開發、UI 問題確認。

### Windows Scheduled Task

| 項目 | 實際設定 |
|---|---|
| Task Name | `Jietech Regression` |
| Task To Run | `D:\Jietech	est
un_scheduled_regression.bat` |
| Schedule | Daily 08:30（`Every 1 day(s)`） |
| Run As User | `Water` |
| Logon Mode | **Interactive only**（XML `LogonType=InteractiveToken`） |
| Highest Privileges | **OFF**（XML 無 `RunLevel` → LeastPrivilege） |
| Working Directory | 由 BAT 內 `cd /d` 保證，不依賴排程器的 `Start In` |
| **目前 Enabled** | **False（已停用，Task 本身保留）** |
| WakeToRun | `False`（技術評估完成，依需求未啟用） |
| StartWhenAvailable | `False`（技術評估完成，依需求未啟用） |
| DisallowStartIfOnBatteries / StopIfGoingOnBatteries | `True` / `True`（維持 Windows 預設） |

需要重新啟用時：

```
schtasks /Change /TN "Jietech Regression" /ENABLE
```

Task 定義、BAT、Baseline 與所有驗證成果都完整保留，重新啟用不需重建。

建立指令：

```
schtasks /Create /TN "Jietech Regression" /TR "D:\Jietech	est
un_scheduled_regression.bat" ^
         /SC DAILY /ST 08:30 /RU Water /IT /F
```

`/IT` 是關鍵 —— 單純省略 `/RU` **並不保證**等同「僅登入時執行」，
建立後必須用 `/V /FO LIST` 與 `/XML` 讀回確認。

**`run_scheduled_regression.bat` 的兩個 Windows 實作重點**

1. **必須是純 ASCII**。cmd.exe 用 OEM code page（本機 cp950）解析 `.bat`，
   UTF-8 中文寫在 `echo` / `REM` 內會造成語法錯誤。
   Python 輸出的中文靠 `PYTHONUTF8=1` 正常寫進 log，不受影響。
2. **不能用 `wmic`**。Windows 11 已移除 `wmic`（實測 `wmic NOT FOUND`），
   原本用它取時間戳會得到空字串。已改用
   `powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"`，
   並保留 `%DATE%/%TIME%` 後備。

Exit code 以 `endlocal & exit /b %RC%` 傳出，實測 0 / 1 / 2 / 5 都原樣傳給
Task Scheduler 的 **Last Result**。

### Unattended / Lock Screen 驗證

| 驗證項目 | 結果 |
|---|---|
| 不開 VS Code、不開 CMD、無人工操作 | ✅ 由 Task Scheduler 自行啟動 |
| Windows **鎖定畫面**下由排程自行觸發 | ✅ 10:51 觸發，10:57 完成 |
| Headless 自行建立 / 關閉 Driver | ✅ |
| 不依賴 Terminal 工作目錄 | ✅ BAT 自行 `cd /d` |
| Task Last Result 反映 Exit Code | ✅ `0` |

Lock Screen 實測結果：
`Raw 135 / 104 / 2 / 29`、Known Fail `C-00` `I-00`、New Fail `0`、
Safety `PASS`、Download 殘留 `0`、Final `PASS`、Exit Code `0`、耗時 `362.35s`。

> **尚未驗證：使用者完全登出（Logged Off / Session 0）。**
> 目前 Logon Mode 是 `Interactive only`，登出後排程不會執行。
> 若日後需要，得改成「不論是否登入」並另行驗證。

### Automation Report

輸出到 `test/output/automation/`：

- `automation_<ts>.json` —— 完整內容（meta / raw result / 比較分類 / 各清單 / safety / download / final status / exit code / 逐 Case）
- `automation_<ts>.csv` —— 逐 Case（case / expected / actual / classification / elapsed / error / screenshot）
- `logs/scheduled_<ts>.log` —— `.bat` 執行時的 stdout / stderr

不會覆蓋 `result_*`、`stability_*`。

### Failure Evidence

出現 `NEW FAIL` 時，Automation Summary 會保留 Case ID / Flow / Expected / Actual /
Error Type / Error Message / Elapsed / **Screenshot 路徑** / result JSON 與 CSV 路徑。
`cleanup_output.py` 會把**有新 Regression 的那幾份 automation summary 永久保留**。

### Scheduled Run 紀錄

| # | 啟動方式 | 時間 | Raw | New Fail | Safety | 殘留 | Final | Exit | 耗時 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 人工（`python -m`） | 08/26 09:07 | 135/104/2/29 | 0 | PASS | 0 | PASS | 0 | 411.31s |
| 2 | 人工（走 `.bat`） | 08/26 10:23 | 135/104/2/29 | 0 | PASS | 0 | PASS | 0 | 383.69s |
| 3 | **Task Scheduler（鎖定畫面）** | 08/26 10:51 | 135/104/2/29 | 0 | PASS | 0 | PASS | 0 | 362.35s |

| 4 | Task Scheduler（每日 08:30） | 08/27 08:53 | — | — | — | — | **SCHEDULER / ENVIRONMENT FAILURE** | 0xC000013A | 中斷 |

第 4 筆為排程環境問題，非測試問題，詳見 Known Issues。

**長期 Scheduled Stability 觀察已暫緩**（正式 Task 現為 Disabled）。
已驗證的是「Task Scheduler 能在無人操作、螢幕鎖定下完整跑完一輪」，
而非「連續多日自動執行的穩定性」。

---

## 11. Regression Baseline

最後一次完整 Regression（12 個 flow 全部執行；取 Stability 驗證的最後一輪）：

**Headed**

```
Total : 135
PASS  : 104
FAIL  : 2
SKIP  : 29
Time  : 370.72s
Result: FAIL
```

**Headless**

```
Total : 135
PASS  : 104
FAIL  : 2
SKIP  : 29
Time  : 369.38s
Result: FAIL
```

兩者的 Case 集合與逐 Case 狀態完全一致（逐筆比對無差異）。
首頁 popup 為佇列式彈出，`A-2` / `A-3` 的輸出順序每次可能不同，兩次都是 PASS。
2 個 FAIL 皆為第 8 節記錄的網站顯示缺陷（`C-00`、`I-00`），非自動化程式問題。

---

## 12. 開發原則

- `IN【V6】.py` 為原始參考腳本，**不直接修改**
- `URL.ini` **不因自動化重構而修改**
- Selector 一律以**實際 DOM 驗證**為準，**不猜 selector**
  - 不依賴 blob URL、MD5 圖片檔名或動態 CDN URL
  - 優先使用結構化屬性（`data-swiper-slide-index`、`img[alt]`、穩定 class）
- **不為了提高 Coverage 執行破壞性操作**；目的不明的功能一律維持 L1
- Case 彼此隔離：單一 Case FAIL 會記錄 error + 截圖 + Recovery，然後繼續下一個
- Flow 彼此隔離：單一 Flow 整個中斷也只會變成一筆 FAIL，不影響後續 Flow
- 瀏覽器連線中斷時會偵測並中止，避免在死掉的 session 上空轉
- 共用邏輯放 `common/`
- 功能流程放 `flows/`
- DOM 探查放 `probe/`
- Toast 只是輔助性的 Post-condition：`catch_toast()` 抓到就記錄，
  **抓不到不會造成 FAIL**


# Phase	       核心重點	                                        簡單理解
- Phase 1	建立自動化測試框架	                                 先把骨架做好
- Phase 2	搬移既有 V6 測試	                                  把原本會測的功能模組化
- Phase 3	掃描網站 DOM Probe	                                盤點網站還有哪些功能
- Phase 4	首頁功能擴充完整化	                                 把首頁主要功能補齊
- Phase 5	深入MINE	                                          開始深入個人中心
- Phase 6	深入Account / Record / Promo / Task	                深入主要內頁功能
- Phase 7	深入EARN / Team Club	                              繼續擴大全站覆蓋率
- Phase 8 Subordinate Data                                    查詢功能 (建立「輸入、搜尋、篩選」能力。)
- Phase 9 既有功能深度補強                                     主要鎖定 /record
- Phase 10 Search Input                                       Result → Empty → Clear → Recovery 的完整 E2E
- Phase 11 自動化測試穩定性 / Flaky Test 驗證                   重複、穩定測試
- Phase 12 CI / 排程式自動 Regression                          自動排程Regression
- Phase 13 正式排程上線與無人值守驗證 --暫停開發                 每日排程summary --暫停開發