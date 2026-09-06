# ERPNext Vietnam Localization

**ERPNext Vietnam** (`erpnext_vietnam`) là lớp bản địa hóa và tuân thủ Việt Nam dành cho **Frappe + ERPNext v16**, tích hợp tùy chọn với **HRMS v16**. Ứng dụng không fork và không sửa core Frappe/ERPNext/HRMS; toàn bộ dữ liệu pháp lý, mapping, bằng chứng và tích hợp bên ngoài nằm trong app riêng.

Phiên bản hiện tại: **0.1.0-rc1 — Engineering Release Candidate**.

> **Lưu ý pháp lý:** RC này xác nhận các gate kỹ thuật P0 → P5, không thay thế ý kiến của kế toán trưởng, chuyên gia thuế, chuyên gia BHXH hoặc tư vấn pháp lý. Trước khi dùng để kê khai/gửi dữ liệu thật, doanh nghiệp phải rà soát cấu hình, mapping tài khoản, phân loại thuế và hợp đồng kỹ thuật của nhà cung cấp.

## Mục tiêu thiết kế

- Giữ nguyên ERPNext làm transaction/GL engine và HRMS làm payroll engine.
- Quy tắc pháp lý có `effective_from/effective_to`, nguồn văn bản và dấu vết kiểm toán; không rải hằng số pháp luật trong code.
- Không tự suy diễn thuế suất/phân loại pháp lý cho Item hay giao dịch.
- Không tự bật cổng gửi dữ liệu ra cơ quan nhà nước/nhà cung cấp.
- Adapter hóa đơn điện tử/BHXH/thuế phải provider-neutral, versioned và có certification gate riêng.
- Dữ liệu lịch sử không bị ghi đè khi văn bản mới có hiệu lực.

## Phạm vi 0.1.0-rc1

| Phase | Chức năng chính |
|---|---|
| P0 | Foundation, legal-rule registry, setup snapshot, business profile |
| P1 | TT99 account catalog, COA semantic mapping, VAT classification/reconciliation |
| P2 | PIT, BHXH/BHYT/BHTN, payroll evidence/reconciliation |
| P3 | Tax/BHXH declaration canonical model, review export, TT89 reporting taxonomy |
| P4 | E-invoice canonical lifecycle, gateway, idempotency, evidence archive, adapter certification |
| P5 | Operator UX, Health, Release Doctor, clean-install/migrate release gates |

## Yêu cầu hệ thống

Baseline đã kiểm thử cho RC1:

- Frappe **16.17.0**.
- ERPNext **16.16.0**.
- HRMS **16.5.4** là tùy chọn; chỉ cần khi dùng các chức năng payroll phụ thuộc HRMS.
- MariaDB là database được dùng cho clean-install certification gate của RC1.
- Quyền `System Manager` để chạy Setup/Health và cấu hình localization.

## Cài đặt

### Cài mới RC1

Trong thư mục Frappe Bench:

```bash
bench get-app https://github.com/n8n2erpnext/erpnext-vietnam --branch v0.1.0-rc1
bench --site your-site install-app erpnext_vietnam
bench --site your-site migrate
bench build --app erpnext_vietnam
```

Sau đó đăng nhập ERPNext bằng tài khoản có quyền System Manager.

### Nâng cấp một site đã có app

Luôn backup trước khi nâng cấp:

```bash
bench --site your-site backup --with-files
cd apps/erpnext_vietnam
git fetch --tags origin
git checkout v0.1.0-rc1
cd ../..
bench --site your-site migrate
bench build --app erpnext_vietnam
```

## Hướng dẫn sử dụng

### 1. Mở Vietnam Localization

Vào **ERPNext → Global Defaults / Cài đặt chung → Vietnam Localization**. App thêm một khu vực riêng vào Global Defaults bằng Custom Fields; không sửa file core ERPNext.

Bạn có hai lối vào:

- **Setup**: cấu hình localization cho Company.
- **Health**: xem trạng thái sẵn sàng và các cảnh báo vận hành.

Có thể mở trực tiếp route Desk `/app/vn-setup-wizard` và `/app/vn-localization-health` nếu cần.

### 2. Chạy Setup Wizard

Chọn:

1. **Company**.
2. **Business Domain**: preset nghiệp vụ; chỉ là gợi ý cấu hình, không quyết định nghĩa vụ pháp lý.
3. **Accounting Regime**: `TT99_2025`, `TT133_2016` hoặc `CUSTOM_REVIEW_REQUIRED`.
4. **VAT Method**: `DEDUCTION`, `DIRECT` hoặc `NOT_CONFIGURED`.
5. Tùy chọn bật chuẩn bị **PIT Payroll**, **BHXH/BHYT/BHTN**, **E-Invoice**.

Bấm **Preview** trước để xem planned changes, warning và `snapshot_hash`. Chỉ khi đã rà soát mới bấm **Apply Setup**. Apply Setup không tự bật gửi dữ liệu ra ngoài; Compliance Gateway vẫn disabled cho đến khi được cấu hình riêng.

### 3. Kế toán và VAT

- `VN Statutory Account` cung cấp catalog tham chiếu TT99; RC1 chứa **184 mã tài khoản**, trong đó **71 tài khoản cấp 1**.
- `VN COA Mapping` ánh xạ semantic statutory role sang Account thật của từng Company.
- Mapping tài khoản là explicit/reviewable; app không tự tạo hoặc đổi tên tài khoản ERPNext dựa trên suy đoán.
- VAT phân biệt `NON_TAXABLE`, 0%, 5%, 10% và diện giảm tạm thời 8%; 0% không đồng nghĩa với không chịu thuế.
- Phân loại VAT cho Item/giao dịch cần kế toán xác nhận; preset domain không tự gán nghĩa vụ thuế.

### 4. Payroll, PIT và bảo hiểm bắt buộc

Khi HRMS có mặt và các tính năng tương ứng được bật, app cung cấp rule/evidence layer cho PIT và BHXH/BHYT/BHTN. Mỗi phép tính phải gắn với rule set và nguồn pháp lý có hiệu lực tại thời điểm tính; không dùng một mức đóng duy nhất cho mọi trường hợp.

RC1 chứa baseline 2026 cho mức giảm trừ gia cảnh, biểu thuế PIT lũy tiến, tỷ lệ BHXH/BHYT/BHTN thông thường, mức tham chiếu và lương tối thiểu vùng. Doanh nghiệp vẫn phải rà soát đối tượng tham gia, tiền lương làm căn cứ đóng, khoản miễn/giảm và trường hợp đặc thù trước khi dùng trên payroll thật.

### 5. Kê khai thuế/BHXH

P3 chuẩn hóa dữ liệu sang canonical model trước khi export. Tax declaration baseline dùng **Thông tư 89/2026/TT-BTC**; mẫu VAT 01/GTGT và các reporting bucket được tách khỏi tax-treatment semantics để tránh việc “ô báo cáo” tự biến thành “nghĩa vụ thuế”.

Các export trong RC1 là deterministic/human-review artifacts. Việc gửi chính thức phải qua adapter đã được kiểm chứng riêng với schema và hợp đồng kỹ thuật hiện hành.

### 6. Hóa đơn điện tử

P4 cung cấp `VN E-Invoice`, profile, lifecycle, idempotency, gateway contract, evidence archive và adapter-certification gate. Baseline pháp lý hiện hành là Nghị định 254/2026/NĐ-CP + Thông tư 91/2026/TT-BTC.

**RC1 không tuyên bố có adapter nhà cung cấp thật nào production-certified** nếu chưa pin và review tài liệu kỹ thuật chính thức của provider/cơ quan thuế. Không suy ra XML/API machine schema chỉ từ PDF pháp luật.

### 7. Health và Release Doctor

Trang **Vietnam Localization Health** là read-only. Nó kiểm tra Company setup, accounting/VAT mapping readiness, payroll/e-invoice readiness, gateway state, certification pins và statutory artifact state nhưng không sửa dữ liệu.

Release Doctor có thể chạy từ bench:

```bash
bench --site your-site execute erpnext_vietnam.diagnostics.release_doctor.run
```

Kết quả `PASS` là gate kỹ thuật tương thích/cấu hình, không phải chứng nhận tuân thủ pháp lý cho dữ liệu doanh nghiệp.

## Cơ sở pháp lý và nguồn chính thức

Danh mục dưới đây là baseline pháp lý mà RC1 đang dùng/đối chiếu. Nguồn ưu tiên: **Quốc hội/UBTVQH → Chính phủ → Bộ Tài chính → cơ quan chuyên ngành → tài liệu kỹ thuật provider**. Khi văn bản được sửa đổi, app phải thêm rule/version mới thay vì ghi đè lịch sử.

### Kế toán doanh nghiệp

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật Kế toán 88/2015/QH13 | Nguyên tắc chứng từ, sổ sách, lưu trữ và trách nhiệm kế toán | https://vanban.chinhphu.vn/default.aspx?docid=183198&pageid=27160 |
| **Thông tư 99/2025/TT-BTC** | Chế độ kế toán doanh nghiệp từ 01/01/2026; nguồn Appendix II cho catalog tài khoản | https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-doanh-nghiep |

Catalog TT99 trong app được đối chiếu từ Công Báo chính thức và lưu SHA-256 nguồn trong tài liệu `docs/P1_TT99_CATALOG.md`.

### Thuế giá trị gia tăng (VAT)

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật 48/2024/QH15 | Khung VAT từ 01/07/2025 | https://vanban.chinhphu.vn/?docid=212476&pageid=27160 |
| Luật 149/2025/QH15 | Sửa đổi Luật VAT, hiệu lực 01/01/2026 | https://vanban.chinhphu.vn/?classid=1&docid=216588&pageid=27160&typegroupid=3 |
| Luật 09/2026/QH16 | Lớp sửa đổi thuế năm 2026 | https://vanban.chinhphu.vn/?docid=218095&pageid=27160 |
| Nghị định 181/2025/NĐ-CP | Hướng dẫn Luật VAT | https://vanban.chinhphu.vn/?docid=214336&pageid=27160 |
| Nghị định 359/2025/NĐ-CP | Sửa đổi NĐ 181 | https://vanban.chinhphu.vn/?classid=1&docid=216388&pageid=27160 |
| Nghị định 144/2026/NĐ-CP | Tiếp tục sửa đổi NĐ 181/NĐ 359 | https://vanban.chinhphu.vn/?docid=218020&pageid=27160 |
| **Thông tư 69/2025/TT-BTC** | Chi tiết Luật VAT và NĐ 181 | https://vanban.chinhphu.vn/?docid=214417&pageid=27160 |
| Nghị quyết 204/2025/QH15 | Chính sách giảm VAT | https://vanban.chinhphu.vn/?classid=1&docid=214209&pageid=27160 |
| Nghị định 174/2025/NĐ-CP | Triển khai giảm VAT theo NQ 204, đến 31/12/2026 | https://vanban.chinhphu.vn/?docid=214310&pageid=27160 |

### Thuế thu nhập cá nhân (PIT)

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật 109/2025/QH15 | Khung PIT mới; quy định lương/tiền công áp dụng cho kỳ tính thuế 2026 | https://vanban.chinhphu.vn/?docid=216495&pageid=27160 |
| Nghị quyết 110/2025/UBTVQH15 | Mức giảm trừ gia cảnh áp dụng từ 01/01/2026 | https://vanban.chinhphu.vn/?docid=215927&pageid=27160 |
| Luật 09/2026/QH16 | Sửa đổi bổ sung một số luật thuế, gồm PIT | https://vanban.chinhphu.vn/?docid=218095&pageid=27160 |

### Quản lý thuế và mẫu khai

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật Quản lý thuế 108/2025/QH15 | Khung quản lý thuế hiện hành từ 2026 | https://vanban.chinhphu.vn/?docid=216541&pageid=27160 |
| Nghị định 252/2026/NĐ-CP | Hướng dẫn Luật Quản lý thuế, hiệu lực 01/07/2026 | https://vanban.chinhphu.vn/?docid=218690&pageid=27160 |
| **Thông tư 89/2026/TT-BTC** | Tax declaration/forms/reporting taxonomy; baseline P3 | https://vanban.chinhphu.vn/?classid=1&docid=218974&orggroupid=4&pageid=27160 |

App pin bản PDF ký số của TT89 cùng SHA-256 trong `erpnext_vietnam/setup/p3_seed.py` để kiểm tra lineage của nguồn dùng khi xây adapter/reporting taxonomy.

### BHXH, BHYT, BHTN và tiền lương tối thiểu

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật BHXH 41/2024/QH15 | Khung BHXH bắt buộc, hiệu lực 01/07/2025 | https://vanban.chinhphu.vn/?docid=211199&pageid=27160 |
| Nghị định 158/2025/NĐ-CP | Chi tiết BHXH bắt buộc | https://vanban.chinhphu.vn/?classid=1&docid=214189&pageid=27160 |
| Nghị định 188/2025/NĐ-CP | Hướng dẫn BHYT | https://vanban.chinhphu.vn/?classid=1&docid=214515&pageid=27160 |
| Luật Việc làm 74/2025/QH15 | Cơ sở pháp lý BHTN từ 01/01/2026 | https://vanban.chinhphu.vn/?docid=214560&pageid=27160 |
| Nghị định 374/2025/NĐ-CP | Quy định chi tiết BHTN từ 01/01/2026 | https://vanban.chinhphu.vn/?docid=216493&pageid=27160 |
| Nghị định 293/2025/NĐ-CP | Lương tối thiểu vùng từ 01/01/2026 | https://vanban.chinhphu.vn/?docid=215832&pageid=27160 |
| Nghị định 58/2020/NĐ-CP | Mức đóng quỹ tai nạn lao động/bệnh nghề nghiệp, áp dụng cùng sửa đổi liên quan | https://vanban.chinhphu.vn/?docid=200108&pageid=27160 |
| Nghị định 161/2026/NĐ-CP | Mức lương cơ sở 2.530.000 đồng từ 01/07/2026; app dùng cho transition reference-level rule | https://vanban.chinhphu.vn/?classid=1&docid=218107&pageid=27160 |

### Hóa đơn/chứng từ điện tử

| Văn bản | Vai trò trong app | Nguồn chính thức |
|---|---|---|
| Luật Quản lý thuế 108/2025/QH15 | Luật nền cho quản lý thuế 2026 | https://vanban.chinhphu.vn/?docid=216541&pageid=27160 |
| Nghị định 254/2026/NĐ-CP | Khung hóa đơn điện tử/chứng từ điện tử từ 01/07/2026 | https://vanban.chinhphu.vn/?docid=218689&pageid=27160 |
| **Thông tư 91/2026/TT-BTC** | Quy định chi tiết hóa đơn điện tử/chứng từ điện tử | https://vanban.chinhphu.vn/?docid=219006&pageid=27160 |

Tài liệu provider, schema XML/API và quy trình truyền nhận phải được pin riêng theo phiên bản; không được coi một URL marketing hoặc tài liệu không định danh phiên bản là nguồn đủ để bật production adapter.

## Tài liệu kỹ thuật trong repo

- `PLAN.md` — trạng thái P0 → P5 và release gate.
- `ARCHITECTURE_V0.md` — kiến trúc tổng thể, ownership boundary và rule engine.
- `research/VIETNAM_LOCALIZATION_DEEP_RESEARCH.md` — nghiên cứu nền về kế toán, thuế, payroll, BHXH và e-invoice.
- `docs/P1_TT99_CATALOG.md` — lineage của Appendix II TT99 và catalog tài khoản.
- `docs/P2_PAYROLL_COMPLIANCE.md` — payroll/PIT/BHXH compliance model.
- `docs/P3_STATUTORY_DECLARATIONS.md` — declaration canonical model và TT89 baseline.
- `docs/P4_EINVOICE_GATEWAY.md` — e-invoice gateway/certification boundary.
- `docs/P5_RELEASE_HARDENING.md` — Health, Release Doctor và clean-install gate.
- `docs/RELEASE_0.1.0_RC1.md` — release note RC1.
- `CHANGELOG.md` — lịch sử phiên bản.

## Development topology

Source of truth là repo host-side:

```text
/home/ubuntu/n8n2erpnext/.erpnext-vietnam-localization
```

Checkout app trong LXD/Frappe Bench chỉ là runtime deployment copy. Mọi code/docs/test/commit phải bắt đầu từ repo source-of-truth, push GitHub, sau đó runtime mới fast-forward từ `origin/main` hoặc checkout release tag.

## Trạng thái release

P0 → P5 engineering gates đã hoàn thành. RC1 đã qua clean MariaDB install, ERPNext + `erpnext_vietnam` install, Release Doctor trước/sau migrate, 15/15 business-profile seed và configured-site regression. Chi tiết xem `docs/RELEASE_0.1.0_RC1.md`.

Repository: https://github.com/n8n2erpnext/erpnext-vietnam
