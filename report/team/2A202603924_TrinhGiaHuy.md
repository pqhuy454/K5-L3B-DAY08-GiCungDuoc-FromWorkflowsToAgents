# Báo cáo cá nhân — 2A202603924_TrinhGiaHuy

## 1. Thông tin thành viên

- Họ tên: Trịnh Gia Huy
- MSSV: 2A202603924
- Email: trgyahuy1710@gmail.com
- GitHub: TrGiaHuy1710-valid

## 2. Phần việc phụ trách

Durability, Eval & Benchmark Lead:

- Độ bền khi ghi tiền: retry (T11), crash/resume (T12) trên cả 3 shape nhóm viết, crash suite 20 điểm.
- Bằng chứng đo: `src/reports/crash.json`, `src/reports/benchmark.json`, `src/reports/ablation_r3_topology.json`.
- Hồ sơ quyết định: `report/team/decision_adr.md`, `report/team/research_card.md`.
- Phần 4 (Kết quả) và Phần 7 (Hạn chế và hướng cải thiện) trong `report/team/group_report.md`.

## 3. Đóng góp cụ thể

- Viết `src/tests/test_student_durability.py` (30 test, chạy trên `workflow`, `single`, `orchestrator`) để phủ những gì T11/T12 của ma trận public chưa kiểm:
  - `test_crash_then_resume_pays_exactly_once`: crash ở cả 3 điểm (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) cho C-001 và C-014, rồi resume **bằng chính shape**. Kết quả phải còn 1 dòng ledger, 1 audit `refund_committed`, `proposal_amount` là quote đầy đủ. Ca C-014 bắt lỗi shape tự trừ phần đã hoàn: nếu trừ, ledger sẽ khác 120.000.
  - `test_crash_at_cannot_bypass_host_denial`: truyền `crash_at` cho claim bị host từ chối (C-007 approval hỏng, C-013 đơn đã hoàn đủ). Kết quả phải là `denied`, không crash, không ghi ledger. Đường crash không được là cửa vòng qua approval.
  - `test_conflicting_committed_amount_reports_failed_and_keeps_old_row`: ledger đã có số khác quote. Shape phải trả `failed`, proposal vẫn là quote, và dòng cũ giữ nguyên.
  - `test_retry_across_seeds_is_still_one_refund`: chạy cùng claim với 5 seed trên một store. Seed không được làm đổi idempotency key.
- Chạy crash suite (20/20), benchmark 4 shape × 5 seed và ablation R3 (workflow ↔ orchestrator), đối chiếu số liệu giữa hai file report.
- Đọc trace `R-swarm-C-002-s55` để xác định nguyên nhân trial fail duy nhất của swarm: event `model_override` thay `delay_days` 2 bằng 5 lấy từ ticket.
- Quyết định kỹ thuật đề xuất cho nhóm: chọn **workflow**. Ba shape nhóm viết ngang nhau về pass rate, pass^5 và variance, nên chọn shape ít tự chủ nhất và rẻ nhất (28.87 VND/success, so với 39.92 của single và 47.36 của orchestrator).

Commit: [`c416c60`](https://github.com/pqhuy454/K5-L3B-DAY08-GiCungDuoc-FromWorkflowsToAgents/commit/c416c60052e4baea2f1a7fcf14b76a5846b3e2e5) — `test(durability): shape-level crash/retry tests; eval: benchmark, crash, ADR, research card` (merge vào `main` qua PR #3).

## 4. Bằng chứng

- `python -m pytest -q tests/test_student_durability.py -o addopts=`: 30 passed.
- `python -m pytest -q -m student -o addopts=`: 248 passed (4 shape × 62).
- `python -m lab8.crash_test --count 20 --out reports/crash.json`: `crash_safety 20/20`.
- `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`:

  | Shape | Pass | Pass^5 | Variance | Cost/success (VND) |
  | --- | --- | --- | --- | --- |
  | workflow | 1.000 | 1.000 | 0 | 28.87 |
  | single | 1.000 | 1.000 | 0 | 39.92 |
  | orchestrator | 1.000 | 1.000 | 0 | 47.36 |
  | swarm | 0.986 | 0.929 | 0.000816 | 49.57 |

- Run id dẫn chứng: `R-workflow-C-002-s55` (workflow bỏ qua số ngày khai trong ticket), `R-workflow-C-014-s11` (proposal 150.000, ledger 120.000), `R-swarm-C-002-s55` (swarm fail do tin ticket).

## 5. Công cụ AI đã dùng

Dùng Claude Code để đọc contract, gợi ý các ca test durability, tổng hợp số liệu từ `benchmark.json` và viết nháp ADR, research card, Phần 4 và Phần 7 của báo cáo nhóm. Cách tự kiểm tra:

- Mọi con số trong báo cáo đều lấy từ `src/reports/*.json` do công cụ của lab sinh ra, không sửa tay file JSON.
- Chạy lại test durability, ma trận student, cổng host và `check_submission`.
- Đọc trực tiếp trace `R-swarm-C-002-s55` để kiểm lời giải thích về lỗi seed 55.
- Kiểm lại nguồn AgentArch trong research card với thư viện tham khảo của lab.

## 6. Tự đánh giá

- Làm được: phủ thêm các điểm crash và ca biên durability ở mức shape, có bằng chứng số liệu cho quyết định chọn workflow, ablation có lệnh chạy lại được.
- Chưa làm được: chưa tự kiểm trên `student_drop/` vì bộ hidden chưa phát; latency không đo được với MockLLM.
- Bài học: cổng host chặn được ghi trùng và bypass approval, nhưng không sửa được dữ kiện mà model đọc sai. Vì vậy càng ít để model quyết thì kết quả càng ổn định.
