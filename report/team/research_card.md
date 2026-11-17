# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R3 · Architecture choices |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | AgentArch: A Comprehensive Benchmark to Evaluate Agent Architectures in Enterprise (ServiceNow), AACL 2026, arXiv:2509.10769 — benchmark học thuật (thư viện tham khảo của lab, slide 43) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Không có kiến trúc agent nào tốt nhất cho mọi trường hợp: hiệu quả phụ thuộc vào tổ hợp model × topology × tác vụ, và multi-agent không thắng single agent một cách nhất quán |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Các LLM thương mại trên một số workflow doanh nghiệp do tác giả dựng; không phải MockLLM, không có cổng host ghi tiền và không đo tác vụ claim hoàn tiền, nên chỉ dùng như giả thuyết cho lab |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Đổi topology A `workflow` → C `orchestrator` (thêm lớp investigator chỉ đọc): pass rate và pass^5 giữ nguyên 1.000 vì tiền vẫn do `compute_compensation` và host quyết; cost/success tăng khoảng +50–70% vì investigator gọi thêm tool (lookup_policy, compute_compensation riêng) |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định: MockLLM, tools, seed 11/22/33/44/55, 14 claim `data/public_claims.jsonl`, `config/pricing.yaml`, `as_of` 2026-11-15, evaluator `lab8.benchmark`, SQLite mới mỗi trial. Biến duy nhất thay đổi: topology (workflow ↔ orchestrator) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: topology nhiều tầng hơn làm tăng chi phí mà không tăng chất lượng (hoặc lộ secret qua handoff). Đo bằng pass rate, pass^5, seed variance, cost/success, mean tool calls và số trial leak/bypass |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r3_topology.json` (chạy trong `src/`)
- Run id / file report: `src/reports/ablation_r3_topology.json` (140 trial); ví dụ R-workflow-C-014-s11 và R-orchestrator-C-014-s11. Số liệu trùng khớp với `src/reports/benchmark.json`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng.** Pass rate 1.000 → 1.000, pass^5 1.000 → 1.000, variance 0 → 0, leak/bypass 0 → 0. Cost/success 28.87 → 47.36 VND (+64%, nằm trong khoảng dự đoán). Mean model calls bằng nhau (1.0), mean tool calls 2.79 → 4.64, tức chênh lệch chi phí gần như hoàn toàn đến từ tool call của lớp investigator. Với tác vụ tuần tự có luật cố định, thêm tầng điều phối chỉ làm tăng cost, khớp với claim của AgentArch là không có topology nào thắng mặc định
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. MockLLM cố định theo seed nên variance 0 không chứng minh model thật ổn định; corpus chỉ 14 claim public; giá là mô phỏng.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
