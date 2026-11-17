# Bonus report: B7

- Topic + nguồn (tên, năm, slide): B7 — Kiểm toán grader; *Rethinking Evaluation of MAS Efficiency* (EMNLP 2026, slide 44, 59).
- CLAIM của nguồn (1 câu): Nếu thước đo đánh giá sai (tính lỗi hạ tầng vào quyết định của agent, hoặc đếm sai chi phí) thì mọi so sánh kiến trúc đều bị lệch theo ngay cả khi hệ thống chạy đúng.
- BOUNDARY (model / dataset / setup): Kiểm định dựa trên bộ fixture metamorphic tổng hợp (`src/grader_audit/fixtures/*.json`), 3 hàm `summarize` mẫu (`grader_a`, `grader_b`, `grader_c`) và `lab8.compensation.quote` với policy `POL-2026-11` tại `as_of = 2026-11-15`.
- HYPOTHESIS trên LogiX: Áp dụng các quan hệ metamorphic (`infra_errors_do_not_move_pass_rate`, `duplicated_list_keeps_rates_doubles_totals`, `delay_days_2_vs_3`, và quan hệ đề xuất `permutation_invariance`) sẽ tách biệt chính xác grader đúng khỏi grader lỗi hành vi mà không cần biết trước đáp án tuyệt đối.
- Biến cố định / biến thay đổi: Cố định tập fixture đầu vào và hàm `lab8.metrics.summarize` nền; biến duy nhất thay đổi là bản cài đặt `grader_a` / `grader_b` / `grader_c` và phép biến đổi metamorphic trên đầu vào.
- Lệnh tái lập (copy-paste được): `cd src && python -m bonus.grader_audit_runner --out reports/bonus_grader_audit.json && python -m pytest -q tests/test_bonus_grader_audit.py`
- File report + run id: `src/reports/bonus_grader_audit.json` (topic `B7`, không dùng `--extra-shape`).

## Kết quả

Bảng kiểm toán trích xuất từ `src/reports/bonus_grader_audit.json`:

| Grader | `metamorphic_infra` | `metamorphic_duplicate` (cost & rate) | `permutation_invariance` (mới) | Kết luận hành vi |
| --- | --- | --- | --- | --- |
| `grader_a` | Đạt (`12→12`, `0.75→0.75`) | **Lệch** (`total_cost`: `283.5→473.0` thay vì `567.0`; `cost/success`: `31.5→26.28`) | **Lệch** (`283.5→283.0`) | Cộng thêm `cost_estimate` một lần cho mỗi `claim_id` đầu tiên gặp phải (đếm trùng & phụ thuộc thứ tự). |
| `grader_b` | Đạt (`12→12`, `0.75→0.75`) | Đạt (`total_cost`: `189.5→379.0`; `cost/success`: `21.06→21.06`) | Đạt (`diffs = {}`) | Đúng chuẩn: gán `passed=None` cho `infra_error=True` và giữ nguyên tổng hợp. |
| `grader_c` | **Lệch** (`graded`: `12→16`; `pass_rate`: `0.75→0.5625`) | Đạt (`total_cost`: `189.5→379.0`; `cost/success`: `21.06→21.06`) | Đạt (`diffs = {}`) | Đếm trial `infra_error=True` thành `passed=False`, làm phồng mẫu số và tụt `pass_rate`. |

- **Quan hệ `delay_days_2_vs_3` (`lab8.compensation.quote`):** Đạt — `delay_days=2` trả `0` VND, `delay_days=3` trả `35000` VND (`shipping_fee_vnd`).
- **Quan hệ mới `permutation_invariance`:** Hoán vị ngẫu nhiên danh sách trial (`seed=42`) không chỉ chứng minh `grader_b` bất biến thứ tự mà còn **bắt trực tiếp lỗi phụ thuộc thứ tự của `grader_a`** (cũng như lỗi `p95_steps` không sắp xếp trong test minh họa) — điều mà `metamorphic_infra` và `metamorphic_duplicate` chưa tách riêng được.
- **Ghi nhận thêm trên `lab8.metrics.summarize`:** Ở `metamorphic_duplicate`, `pass_5` giảm `0.6667 → 0.0` ở cả 3 grader do `metrics.py` kiểm tra `len(claim_rows) == len(seeds)` (khi nhân đôi list, số dòng mỗi claim là 4 khác số seed duy nhất là 2).

## Kết luận

- **Ủng hộ mạnh mẽ CLAIM của EMNLP 2026:** Một lỗi nhỏ ở tầng tổng hợp thước đo (`grader_a` cộng trùng cost theo `claim_id`, `grader_c` gộp lỗi hạ tầng vào `pass_rate`) làm sai lệch kết luận hiệu quả/chi phí mà smoke test thông thường (`test_grader_audit_smoke.py`) không hề phát hiện.
- **Trả lời câu hỏi B7:**
  - *Một lỗi thước đo có thể lọt qua mọi quan hệ đã viết không?* **Có** — ví dụ lỗi nhân toàn bộ `cost_estimate` với cùng một hằng số `k`, hoặc lỗi hoán đổi nhãn giữa hai shape có cùng kích thước, sẽ lọt qua `infra`, `duplicate` và `permutation_invariance`. Cần bổ sung thêm quan hệ **cost scaling** (`cost * k → total_cost * k`) và **shape-renaming invariance**.
  - *Vì sao quan hệ metamorphic hữu ích khi không có đáp án tuyệt đối?* Vì ta không cần gán nhãn tay hay biết trước `pass_rate`/`cost` đúng tuyệt đối, chỉ cần kiểm tra tính bất biến hoặc tỷ lệ biến thiên bắt buộc khi biến đổi đầu vào.
- **Điều kiện đảo ngược kết luận:** Nếu bộ dữ liệu không có `infra_error=True` thì `grader_c` cho kết quả giống `grader_b`; nếu mỗi `claim_id` chỉ có đúng 1 trial thì `grader_a` không bị lệch thứ tự nhưng vẫn sai gấp đôi chi phí.

## Giới hạn

- Fixture kiểm toán là dữ liệu tổng hợp quy mô nhỏ (12–16 trials), chưa bao phủ trường hợp `successes == 0` (`cost_per_success_vnd = null`).
- `MockLLM` không phải model sản xuất và latency của lab là `unavailable`, nên kiểm toán ở đây tập trung vào tính đúng đắn của bộ tổng hợp điểm và luật nghiệp vụ `compensation.quote`.
