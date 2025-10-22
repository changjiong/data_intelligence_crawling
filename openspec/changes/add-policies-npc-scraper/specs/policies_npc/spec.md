## MODIFIED Requirements
### Requirement: policies.npc crawl
Crawler MUST persist zxkc 政策正文与附件去重后的结果，并同步至 Google Workspace。

#### Scenario: Export to Google Docs
- **GIVEN** zxkc 政策包含正文与 pdf/doc 附件
- **WHEN** 运行 `python -m scrapers.policies_npc`
- **THEN** 在 Google Docs 新建文档包含标题、发布日期、来源链接与正文文本
- **AND** 附件上传至 Google Drive 并在文档末尾列出可访问的链接

#### Scenario: Repository deduplication
- **GIVEN** 已存在 `title + publish_date + site` 相同的政策记录
- **WHEN** 重新运行抓取任务
- **THEN** 本地存储不会新增重复记录
- **AND** 不会重复上传附件
