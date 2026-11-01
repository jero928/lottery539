今彩539 自動同步與雙尾驗證修復版

排程：GitHub Actions 每小時7、37分檢查（約30分鐘一次；GitHub可能延遲）。
手動首次執行：GitHub > Actions > Sync official 539 results and predictions > Run workflow > main。
推送 main 也會自動執行。

必要檔案：.github/workflows/sync-pages.yml、scripts/、tests/、requirements.txt、archive/，以及現有前端檔案。
使用 Python 3.13 + numpy；無付費資料庫、無前端API Key。
本次修復以儲存庫實際舊版為基礎，維持原Logistic Regression與頁面設計。模型只使用台北日期最近180天的有效歷史；不捏造缺失年份，不以本機未上架的10年版宣稱線上已具有10年資料。

命中規則：兩個不同尾數必須都出現在當期5個獎號內。例如預測1、6尾，只有1尾（即使出現多顆1尾）仍算未同時命中。
原本任一尾命中的約70%基準不再適用。新基準用精確組合公式計算兩尾同時出現；0尾3個號碼、其餘4個號碼。
實際發布成績與最近100期歷史模擬分開統計。未開獎不進分母；逾時發布不列入實績；無已結算期數時顯示「—」。

完整流程：
1. 讀取舊資料；每次核對最近180天涵蓋的月份；月份邊界之外的紀錄不加入本次分析。
2. 取得台灣彩券官方月查詢API；驗證日期、期別、5個不重複1–39獎號、月份總筆數及期別連續性。
3. 相同紀錄去重，衝突或缺期停止更新；舊資料永遠保留。
4. 新資料成功驗證後才重算模型。沒有新期別則保留同一份模型與預測。
5. 以目標期別保存固定2尾、生成時間、訓練資料雜湊與模型版本；同一期別不覆寫。
6. 提交資料後依原Pages設定部署，核對公開data.json與status.json版本。
7. 部署成功且公開資料核對一致後，追加獨立發布時間事件，再將確認狀態更新到網站。
8. 官方公布目標期別後才結算；以實際開獎日期20:30檢查是否事前發布。
9. 網頁每60秒先讀小型status.json，版本不同才更新完整資料，不需重新整理。

保存檔案：
archive/history.json：所有有效歷史（不隨半年顯示範圍刪除）。
archive/raw/：官方原始回應（SHA256命名）。
archive/model.json：模型輸出與歷史模擬。
archive/predictions.json：不可覆寫預測內容，雜湊鏈。
archive/publications.json：成功部署後的發布時間事件。
archive/settlements.json：官方結果公布後的結算事件。
archive/updates.jsonl：每次同步、來源回應及錯誤紀錄。
status.json：最近檢查、最後成功更新、最新期別、狀態。

Pages／權限：
工作流程使用 contents: write（保存紀錄）、pages: write（部署）、id-token: write（Actions型部署）。
會讀取既有Pages模式：若是分支部署，要求main與根目錄，保留原方式並呼叫官方Pages build API，避免GITHUB_TOKEN提交不自動觸發Pages的問題；若是GitHub Actions型則使用官方Pages artifact部署。沒有修改Pages來源設定。
若寫入被分支保護阻擋，流程會失敗而不強制推送。若Pages環境要求人工批准，需依既有設定批准。若排程被停用，須於Actions重新啟用。
狀態顯示失敗時，請查看Actions失敗步驟與archive/updates.jsonl。不要刪除預測紀錄來重建更好看的命中率。

本機驗證：
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  python -m unittest discover -s tests -v
  python scripts/update_data.py
  python -m http.server 8793
本機執行只產生候選，不會冒充網站已發布。GitHub工作流程確認公開部署後才開始累計實際發布。

來源：https://www.taiwanlottery.com/lotto/history/history_result/
API：https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result
GitHub Pages build API：https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build

限制：下一期日期依現有週一至週六20:30推估，官方異動以公告為準；結算使用官方實際期別與日期，不以推估日期取代開獎資料。命中率不保證未來表現。

半年資料更新（2026-11-01）：抓取與AI訓練窗口固定最近180天，舊歷史保留但不納入當前模型。既有已保存的同一期預測不覆寫，新規則於下一筆新期別預測生效。
