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
    ├─ tools/                 # 測試產物維護
    │   └─ cleanup_output.py  # Output Retention 清理（預設 dry-run）
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
        └─ probe/             # DOM Snapshot 與探查結果
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
| **[D]** | `menu` | TabBar HOME / PROMO / 邀請轉盤 / EARN / MINE、7 個遊戲分類、Search、公告跑馬燈、`ic_volume` | 15 | 不點遊戲卡片；音量類操作需可還原 |
| **[E]** | `safety` | Deposit / Withdraw / First Deposit / LiveChat / 首充金額 / checkbox / Collect / SPIN / Submit / Redeem | 14 | **全部 L1，零點擊** |
| **[F]** | `mine` | My info / Mission / Balance details / Live support / Gifts / Join our community / Download App / Refresh / Logout | 11 | Live support、Download App、Logout 為 L1 |
| **[G]** | `account` | Avatar / Nickname / Gender（開關 modal）、Player ID / 邀請碼（唯讀）、綁定手機 / 登入密碼 / 綁定邀請碼（L1） | 10 | 測試前後比對全部欄位，確認資料未變 |
| **[H]** | `record` | Detail / Withdrawal 分頁、All / Income / Expense 篩選 | 7 | 純查詢，測試後恢復初始狀態 |
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
- Telegram / WhatsApp 等外部連結

L1 的 Case 會在步驟中標記 `[SAFE-L1]`。

### L2 — 允許可逆操作

允許執行、但完成後必須 Recovery 或恢復原始狀態：

- 頁面導航（TabBar、MINE 選單、站內返回）
- Tab 切換（Detail / Withdrawal）
- Filter 篩選（All / Income / Expense）
- 遊戲分類切換
- Search 開啟 / 關閉
- Modal 開啟 / 關閉（Avatar / Nickname / Gender / Gifts）
- Team Club 分頁切換與 Rebate 輪播（左右各一次後還原）
- Subordinate Data 的 Tier 篩選、排序切換、搜尋輸入（測試字串，事後清空還原）
- Popup 關閉

`config.SAFE_LEVEL` 預設為 `1`；`config.assert_safe()` 會在正式環境
（`INPV6`、`7IND`）強制拒絕提高等級。

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

---

## 9. Regression Baseline

最後一次完整 Regression（12 個 flow 全部執行）：

**Headed**

```
Total : 129
PASS  : 98
FAIL  : 2
SKIP  : 29
Time  : 326.26s
Result: FAIL
```

**Headless**

```
Total : 129
PASS  : 98
FAIL  : 2
SKIP  : 29
Time  : 302.45s
Result: FAIL
```

兩者的 Case 集合與逐 Case 狀態完全一致（逐筆比對無差異）。
首頁 popup 為佇列式彈出，`A-2` / `A-3` 的輸出順序每次可能不同，兩次都是 PASS。
2 個 FAIL 皆為第 8 節記錄的網站顯示缺陷（`C-00`、`I-00`），非自動化程式問題。

---

## 10. 開發原則

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
- Phase 9 既有功能深度補強                                      主要鎖定 /record