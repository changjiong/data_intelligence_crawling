## 1. 抓取与解析
- [x] 1.1 建立 `zxkc` 列表分页迭代器，支持 `since`、`max_pages`
- [x] 1.2 完成列表页解析：提取标题、详情链接、发布日期、站点元数据
- [x] 1.3 完成详情页解析：正文 HTML、纯文本摘要、附件链接（pdf/doc）
- [x] 1.4 附件下载保存到本地缓存目录，并在模型中记录

## 2. 数据持久化与去重
- [x] 2.1 扩展 `Policy` 模型/存储，增加 Google Docs id、附件列表
- [x] 2.2 实现去重逻辑（title + publish_date + site）；支持增量抓取

## 3. Google Docs 集成
- [x] 3.1 封装 Google Docs 客户端（服务账户凭据从 `.env` 读取）
- [x] 3.2 将政策正文、元数据写入 Docs；上传附件至 Drive 并附链接
- [x] 3.3 失败重试与错误记录

## 4. CLI 与 Pipeline
- [x] 4.1 增加独立 CLI (`python -m scrapers.policies_npc`) 入口
- [x] 4.2 在 `pipeline.py` 注册真实执行流程与 `--dry-run` 展示

## 5. 测试与验证
- [x] 5.1 添加 HTML fixture 与解析单元测试
- [x] 5.2 为 Google 集成编写模拟测试
- [x] 5.3 `openspec validate add-policies-npc-scraper --strict`
- [x] 5.4 `pytest`
