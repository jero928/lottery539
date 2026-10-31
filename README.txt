GitHub Pages 自動同步版（純HTML/CSS/JS，含本機AI預測）
1. 將解壓縮後的所有內容上傳至儲存庫根目錄。必須包含隱藏資料夾 .github/workflows/sync-pages.yml 及 scripts/update_data.py。
2. 預設分支使用 main；若使用其他名稱，修改 workflow 的 push.branches。
3. Settings → Pages → Build and deployment → Source 選 GitHub Actions。
4. Actions → Sync lottery data and deploy Pages → Run workflow，執行首次同步及部署。
5. 成功後從 Settings → Pages 開啟網址。需要啟用 Actions 並允許 Pages 部署。

排程每小時17、47分執行，名義上每30分鐘同步一次；GitHub可能延遲或跳過排程。
開啟中的網頁每分鐘讀取已部署的data.json，不會直接跨網域抓台彩。
Python僅在GitHub Actions中執行；瀏覽器端仍為純HTML/CSS/JS，無需API金鑰。
抓取失敗或資料驗證失敗時工作流程會失敗、不部署，線上保留前次成功版本。請查看Actions錯誤。
更新時間超過2小時，頁面會顯示提醒。倒數依例行時程估算。
資料在部署產物內更新，儲存庫中的data.js/data.json不會自動產生提交。
公開儲存庫若60天沒有活動，GitHub可能停用排程；到Actions重新啟用或提交變更。
下載到本機直接開啟只讀取隨附快照，不具雲端同步。
尚未替你上傳或設定GitHub儲存庫；完成上述設定後才會開始自動同步。

AI使用瀏覽器內的正則化邏輯迴歸，無需API金鑰，資料同步後會重新計算。預設180天，可切換60/90天。請一併上傳ai-model.js、ai-view.js及更新的workflow。
每期選2個尾數，任一出現算命中。畫面會顯示模型估計、理論基準、逐期回測命中率與近似95%信賴區間，不能視為保證。

介面更新：已移除模型方法及兩段Brier/回測結論文字；回測獎號以綠色標示符合當期事前預測尾數的數字。歷史開獎每頁10期，CSV仍匯出所選區間全部資料。
