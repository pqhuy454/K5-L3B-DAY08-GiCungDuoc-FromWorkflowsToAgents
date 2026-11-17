# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 98a4c49 (code 3 shape lúc chạy `reports/benchmark.json` và `reports/crash.json`)
- Run id dẫn chứng: R-workflow-C-002-s55, R-workflow-C-014-s11 (workflow pass); R-swarm-C-002-s55 (swarm fail, đối chứng) — `src/reports/benchmark.json`
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (70 trial = 14 claim public × seed 11,22,33,44,55)
- Cost per success (mô phỏng, VND): 28.87 (single 39.92, orchestrator 47.36, swarm 49.57)
- Crash safety: 20/20 (src/reports/crash.json); shape-level 18/18 crash+resume trong src/tests/test_student_durability.py
- Secret leak / approval bypass: 0 / 0 (70/70 trial `ok`, grader quét trace và mọi file `<run_id>*`; không có trial nào refund khi `approval_ok` false)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng corpus public (14 claim), cùng 5 seed, cùng MockLLM và cùng `config/pricing.yaml`, ba shape nhóm viết đều đạt pass rate 1.000, pass^5 1.000 và variance 0. Chất lượng không phân biệt được ba shape, nên nhóm chọn theo nguyên tắc của lab: shape **ít tự chủ nhất** mà vẫn làm được việc. Workflow vừa ít tự chủ nhất vừa rẻ nhất: 28.87 VND mỗi lần thành công, so với 39.92 của single (+38%) và 47.36 của orchestrator (+64%). Workflow trung bình chỉ gọi model 1 lần mỗi claim (single gọi 5.57 lần) và gọi tool 2.79 lần (orchestrator gọi 4.64 lần). Bài toán là một chuỗi tuần tự với luật cố định: đọc claim → tra đơn → tính quote → gọi host. Không có bước nào cần model chọn đường đi, nên mỗi lần gọi model thêm chỉ làm tăng chi phí và tạo thêm chỗ cho prompt injection. Swarm là bằng chứng ngược lại: ở seed 55, run `R-swarm-C-002-s55` tin con số "5 ngày" trong ticket thay vì `delay_days = 2` của đơn, nên ghi refund 20.000 VND cho một claim đáng lẽ phải `denied`. Kết quả là swarm có pass^5 0.929 và variance 0.000816. Host không chặn được lỗi này vì approval vẫn hợp lệ và số tiền vẫn nằm dưới trần. Vậy cổng host chặn được ghi trùng và bypass approval, nhưng không chặn được việc model đọc sai sự thật.

## Có đáng đổi lấy multi-agent không

Không. Trên bộ public, orchestrator và single không pass nhiều hơn workflow, nhưng tốn hơn 38–64% chi phí mỗi lần thành công. Swarm vừa pass ít hơn (0.986) vừa đắt nhất. Giả sử multi-agent pass nhỉnh hơn vài điểm phần trăm nhưng cost và variance cao hơn, nhóm vẫn giữ workflow nếu workflow còn trên ngưỡng 0.75 và variance bằng 0: claim hoàn tiền là thao tác ghi tiền, nên tính ổn định (pass^5) quan trọng hơn vài điểm pass rate. Quyết định sẽ đảo lại khi gặp một trong ba điều kiện sau:

1. Ticket thiếu `order_id` có cấu trúc, phải suy luận từ văn bản tự do. Khi đó workflow chỉ trả `needs_info` hàng loạt, còn agent có thể hỏi lại hoặc tra thêm.
2. Bộ hidden có loại claim mới mà chuỗi bước cố định không phủ, làm pass rate của workflow xuống dưới 0.75 trong khi single hoặc orchestrator vẫn trên ngưỡng.
3. Có nhiều nguồn cần tra song song, đủ độc lập để investigator chạy song song và bù được chi phí bằng độ trễ thấp hơn. Latency của MockLLM là `unavailable`, nên lab này không đo được điều kiện này.

## Trace và bằng chứng

Trace của workflow ghi các event `get_claim_view` (chỉ `claim_id`, `found`, `order_id`), `lookup_order` (7 field allowlist: `order_id`, `status`, `delay_days`, `shipping_fee_vnd`, `paid_vnd`, `damage_verified`, `carrier`), `compute_compensation` (số tiền, lý do, clause), `issue_refund_request`, `issue_refund_result` và `decision`. Trace cố ý **không** ghi ticket, vì ticket là dữ liệu người dùng và có thể chứa PII hoặc câu injection. Trace cũng không ghi claim row thô (có `parent_secret`), header, cùng SĐT, địa chỉ, tên hàng và internal note của order row. Mọi trace nằm trong `src/traces/<run_id>.json`, đúng chỗ grader quét. Benchmark ghi nhận 0 trial bị `missing_trace`, `stale_trace`, `invalid_trace` hay `trace_run_id_mismatch`, và 0 trial chứa chuỗi cấm. Nếu trace nằm ngoài chỗ scanner quét được, nhóm không chứng minh được hệ thống sạch. Vì vậy shape không ghi file phụ nào khác và không `print` dữ liệu claim ra stdout.

## Giới hạn

MockLLM không phải model sản xuất: hành vi được cố định theo seed, nên variance 0 của ba shape nhóm viết phản ánh việc code không để model quyết số liệu, chứ không chứng minh model thật cũng ổn định. Latency để `unavailable`. Cost là giá mô phỏng trong `config/pricing.yaml`, không phải hóa đơn API. Corpus public chỉ có 14 claim, nên khoảng tin cậy của pass rate còn rộng; kết luận cuối cùng phụ thuộc cổng hidden (40 claim × 5 seed). Không sửa JSON cho đủ 0.75.
