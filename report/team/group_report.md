# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: GiCungDuoc
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `<cập nhật ở CP5>`

## 2. Mục tiêu và cách tiếp cận

### Mục tiêu bài toán
Bài lab mô phỏng quy trình xử lý claim hoàn phí vận chuyển và đền bù hàng hỏng của **LogiX-VN** trên bốn kiến trúc (`workflow`, `single`, `orchestrator`, `swarm`) dùng chung chữ ký `run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult` và cùng `MockLLM` cố định theo seed. Mục tiêu của nhóm là:
1. Tuân thủ chặt ranh giới code/model: toàn bộ logic tính tiền (`compute_compensation`), kiểm tra policy hiện hành (`is_current=1`, `effective_date <= 2026-11-15`), chống prompt injection từ nội dung ticket, kiểm tra approval và idempotency/trần hoàn tiền theo đơn do **code và host (`durability.issue_refund`)** quyết định.
2. Đảm bảo tuyệt đối 3 điều kiện must-pass: không refund khi thiếu approval hợp lệ (`approval_bypass_count == 0`), không rò rỉ `CANARY_SECRET_*` hay PII trong trace/stdout (`secret_leak_count == 0`), và an toàn khi crash (`20/20` crash suite).
3. Đo lường khách quan (pass rate, pass^5, seed variance, cost/success) trên cùng corpus và seed để chọn kiến trúc **ít tự chủ nhất mà vẫn hoàn thành tốt nhiệm vụ**.

### Phân công và thứ tự triển khai
Nhóm 5 thành viên chia vai chuyên biệt theo kiến trúc và kiểm thử:
- **Phạm Quốc Huy (Lead & QA Integration):** quản lý Git/CI, giữ cổng host (`pytest -q`) luôn xanh, chuẩn hóa contract `RunResult`/`Trace v1` qua `src/tests/test_student_integration.py` và chạy `check_submission`.
- **Trần Tùng Lâm (Shape A — Workflow Lead):** triển khai `workflow.py` (tuần tự tất định, không dùng `REFERENCE_WEAKNESS`) làm baseline ít tự chủ nhất.
- **Đặng Đức Minh (Shape B — Single ReAct):** triển khai `single.py` (vòng lặp ReAct tối đa 8 bước, chỉ dùng read-tools, chống prompt injection).
- **Nguyễn Thành Tâm (Shape C — Orchestrator & Security Lead):** triển khai `orchestrator.py` (handoff allowlist `handoff.v1`, investigator read-only, kiểm soát zero-leak trace).
- **Trịnh Gia Huy (Durability, Eval & Benchmark Lead):** kiểm thử T11/T12 và `crash_test` 20/20, chạy `benchmark.json`, phân tích số liệu điền `decision_adr.md` và `research_card.md`.

Thứ tự thực hiện bám sát 5 checkpoint: CP1 (cài đặt môi trường, đọc contract, viết test tích hợp giữ cổng host) → CP2–CP3 (hoàn thiện lần lượt 3 shape `workflow`, `single`, `orchestrator` kèm handoff và `crash_at`) → CP4 (chạy crash suite 20/20 và rà soát bảo mật/trace) → CP5 (chạy benchmark 4 shape × 5 seed, hoàn thiện ADR, research card và `check_submission` đạt `0 FAIL`).

## 3. Giải pháp

Mô tả ba shape nhóm viết (workflow, single, orchestrator): mỗi shape đọc gì, quyết định gì, gọi host ra sao. Chỉ rõ ranh giới code / model (tham khảo [docs/architecture.md](../../docs/architecture.md)), cách handoff được sanitize và trace ghi những event nào.

### Shape A: Workflow

File: `src/lab8/shapes/workflow.py`, test: `src/tests/test_student_workflow.py`.

Shape A là chuỗi bước Python cố định, không có vòng lặp và không có nhánh do model chọn. Mỗi claim gọi tối đa 3 tool đọc và tối đa 1 lần ghi qua host.

| Bước | Thao tác | Điều kiện dừng |
| --- | --- | --- |
| 1 | `get_claim_view` | Không có claim → `failed` |
| 2 | Kiểm `order_id` trên claim row | Rỗng → `needs_info`, proposal 0 |
| 3 | `lookup_order(order_id, principal_id)` | Không thấy hoặc sai principal → `escalated`, proposal 0 |
| 4 | `compute_compensation(order)` | Quote = 0 → `denied`, proposal 0 |
| 5 | `durability.issue_refund(conn, claim_id, quote, crash_at=crash_at)` | Host từ chối → `denied`; conflict → `failed`; thành công → `resolved` |

Ranh giới code / model:

- Số tiền chỉ do `compute_compensation` tính từ order row và policy hiện hành. Ticket không được parse, nên số ngày trễ khai sai (T02), clause cũ (T06) hay câu injection (T09) không ảnh hưởng kết quả.
- Shape truyền quote đầy đủ vào host. Host tự trừ phần đã hoàn của đơn: T13 bị từ chối với `order_already_refunded`, T14 có proposal 150000 và ledger ghi 120000.
- MockLLM chỉ được gọi một lần để soạn câu trả lời. Prompt chỉ gồm `status` và `proposal`.
- `crash_at` được chuyển thẳng cho host. Khi có `InjectedCrash`, shape ghi trace rồi ném lại lỗi. Các exception khác được trả về dưới dạng `failed` để `run_claim` không ném lỗi ra ngoài.

Trace ghi ở mọi nhánh return, gồm các event `get_claim_view` (chỉ `claim_id`, `found`, `order_id`), `lookup_order` (7 field allowlist), `compute_compensation`, `issue_refund_request`, `issue_refund_result` và `decision`. Trace không chứa ticket, `parent_secret`, header hay PII của đơn hàng.

Kết quả chạy local trên bộ public:

- `pytest -m student -k workflow`: 62/62 passed.
- `pytest -q` (cổng host và test workflow): 141 passed.
- `lab8.crash_test --count 20`: 20/20.
- Benchmark 14 claim × 5 seed: pass rate 1.000, pass^5 1.000, variance 0, cost/success 28.87 VND (swarm: 0.986 / 0.929 / 0.000816 / 49.57). Steps trung bình là 5.07, cao hơn swarm vì metric này đếm số event trong trace chứ không đếm số lần gọi model.

## 4. Kết quả

Điều kiện đo (`controlled_variables` trong `src/reports/benchmark.json`): 14 claim public (C-001…C-014) × seed `11,22,33,44,55` = 70 trial mỗi shape; MockLLM; `as_of` 2026-11-15; giá mô phỏng từ `config/pricing.yaml` (20 VND/1k token vào, 80 VND/1k token ra, 10 VND/tool call); mỗi trial chạy trên một file SQLite mới. Code của 3 shape lấy ở commit `98a4c49`.

Lệnh chạy (trong `src/`):

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
python -m lab8.crash_test --count 20 --out reports/crash.json
```

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean / p95 steps | Model calls / tool calls (TB) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A `workflow` | **1.000** | **1.000** | 1.000–1.000 | 0.000000 | **28.87** | 5.07 / 6 | 1.00 / 2.79 |
| B `single` | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 39.92 | 2.93 / 3 | 5.57 / 3.64 |
| C `orchestrator` | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 47.36 | 2.79 / 3 | 1.00 / 4.64 |
| D `swarm` (tham chiếu) | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 | 3.00 / 4.66 |

Must-pass và độ bền:

- Crash safety: **20/20** (`src/reports/crash.json`).
- Shape-level: `src/tests/test_student_durability.py` (30 test) chạy crash ở cả 3 điểm (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) cho C-001 và C-014 trên 3 shape, rồi resume bằng chính shape. Cả 18/18 trường hợp còn đúng 1 dòng ledger và 1 audit `refund_committed`; riêng C-014 ledger vẫn là 120.000 (host không trừ hai lần). Truyền `crash_at` cho claim bị host từ chối (C-007, C-013) không làm crash nổ và không ghi ledger.
- Approval bypass 0, secret/PII leak 0 trên cả 280 trial: không trial nào có lý do fail về trace hay chuỗi cấm.

Nhận xét:

1. Ba shape nhóm viết **ngang nhau về chất lượng** (pass rate 1.000, pass^5 1.000, variance 0) vì cả ba để code quyết số tiền và để host quyết việc ghi. Khác biệt chỉ nằm ở chi phí: so với workflow, single đắt hơn 38% vì gọi model 5.57 lần mỗi claim, orchestrator đắt hơn 64% vì investigator gọi thêm khoảng 1.9 tool mỗi claim.
2. Swarm là shape duy nhất có variance khác 0. Trial fail duy nhất là `R-swarm-C-002-s55`: ở seed 55, peer tin "5 ngày" trong ticket thay vì `delay_days = 2` của order (event `model_override` trong trace), nên ghi refund 20.000 VND cho một claim đáng lẽ `denied`. Host không chặn vì approval hợp lệ và số tiền dưới trần. Cổng host chặn ghi trùng và bypass approval, nhưng không sửa được sự thật bị model đọc sai.
3. Mean steps của workflow cao hơn vì metric này đếm số event trong trace (workflow ghi 6 event chi tiết), không phải số lần gọi model. Steps không phản ánh chi phí.
4. Ablation R3 (workflow ↔ orchestrator, `src/reports/ablation_r3_topology.json`) xác nhận giả thuyết: đổi topology không đổi chất lượng nhưng tăng cost/success 64%. Chi tiết trong `report/team/research_card.md`.

Chưa chạy tự kiểm trên `student_drop/` vì bộ hidden chưa được phát; kết quả cổng hidden do giảng viên chấm.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Lỗi gặp phải (kèm lệnh, output hoặc ảnh chụp) và cách nhóm xử lý.

...

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Nêu thêm giới hạn của nhóm và điều kiện làm kết luận thay đổi.

Hạn chế:

- **Model giả lập.** MockLLM cố định theo seed, nên variance 0 của ba shape nhóm viết chỉ cho thấy code không để model quyết số liệu; nó không chứng minh một LLM thật cũng ổn định. Với model thật, single (5.57 lần gọi model mỗi claim) sẽ chịu dao động nhiều hơn workflow.
- **Corpus nhỏ.** Bộ public chỉ có 14 claim, mỗi luật nghiệp vụ chỉ có 1–2 ví dụ. Pass rate 1.000 trên public không đảm bảo ≥ 0.75 trên 40 claim hidden.
- **Chi phí và độ trễ mô phỏng.** Cost tính theo `config/pricing.yaml`, không phải hóa đơn API. Latency là `unavailable`, nên lab không đo được lợi thế duy nhất có thể có của orchestrator: chạy investigator song song.
- **Ablation chưa hoàn toàn đơn biến.** Workflow và orchestrator là hai file code khác nhau, nên ngoài topology còn khác cách gọi tool. Nhóm giữ cố định mọi biến đo được (model, seed, corpus, giá, evaluator), nhưng không tách riêng được ảnh hưởng của từng tool call.
- **Host là chỗ tin cậy duy nhất.** Test của nhóm kiểm shape truyền đúng quote và `crash_at`, nhưng không kiểm lại logic bên trong `durability.py`/`policy.py` (file thước đo, không được sửa).

Điều kiện làm kết luận thay đổi:

1. Ticket không có `order_id` có cấu trúc, phải suy luận từ văn bản. Khi đó workflow trả `needs_info` hàng loạt, còn shape có model đọc ticket có thể tốt hơn.
2. Bộ hidden làm pass rate của workflow xuống dưới 0.75 trong khi single hoặc orchestrator vẫn trên ngưỡng.
3. Đo được latency thật và tác vụ có nhiều nguồn tra cứu độc lập, đủ để investigator song song bù lại chi phí.

Hướng cải thiện:

- Tách bước 4–7 (quote → host → map status → `finish`) thành một helper dùng chung cho 3 shape để giảm lặp code và rủi ro lệch hành vi.
- Thêm bước kiểm chứng (verifier) bằng code cho swarm: so `delay_days` mà model dùng với order row trước khi gọi host. Đây là cách sửa lỗi kiểu `R-swarm-C-002-s55` mà không phải bỏ multi-agent (hướng bonus B2/MAST).
- Chạy lại benchmark trên `student_drop/` khi có và ghi `reports/hidden_selfcheck.json` để kiểm ngưỡng 0.75 trước khi nộp.

## 8. Tài liệu tham khảo

...
