# Bóc tách văn bản hành chính — PyQt5

Ứng dụng desktop bóc tách metadata từ PDF văn bản hành chính Việt Nam.
Gọi VLM qua endpoint OpenAI-compatible (vLLM), hậu xử lý sửa lỗi tiếng Việt,
xuất TSV + Excel.

## Cài đặt

```bash
pip install -r requirements.txt
```

Nếu chỉ chạy OCR mà **không** dùng bước sửa lỗi, bỏ `torch`, `transformers`,
`sentencepiece` khỏi `requirements.txt` và đặt `use_correction: false`
trong `config.json`. Riêng phần OCR chỉ cần PyQt5, PyMuPDF, Pillow,
openai, openpyxl.

## Chạy

```bash
python app.py
```

## Luồng sử dụng

1. `Chọn…` → chọn file PDF hoặc thư mục. Dòng ước lượng hiện số file,
   tổng số trang sẽ OCR, và thời gian dự kiến.
2. Đổi `Chiến lược trang` nếu cần — ước lượng cập nhật lại ngay.
3. `Kết nối server API` → lấy tên model từ endpoint, điền vào panel cài đặt.
4. `Bắt đầu`. Nếu vượt `page_estimate_warn_threshold` trang, app hỏi xác nhận.
5. Theo dõi tab `Console`, xem bảng ở tab `Kết quả`.
6. Xong → Excel tự tạo, popup hiện nút `Mở file kết quả`.

## Ba chiến lược trang

| Giá trị | Nhãn | Trang được OCR |
|---|---|---|
| `first` | đầu | chỉ trang 1 |
| `first_last` | đầu + cuối | trang 1 và trang cuối |
| `full` | full | mọi trang |

`first_last` là mặc định và phù hợp nhất với văn bản hành chính Việt Nam:
số hiệu, cơ quan ban hành, tiêu đề, ngày đều ở trang 1, còn người chịu
trách nhiệm thi hành ở trang cuối.

`full` không có trần số trang. Với thư mục lớn hãy xem dòng ước lượng
trước khi chạy.

## Cấu hình

`config.json` là cấu hình tĩnh, chỉ đọc trong app. Muốn đổi thì sửa file
rồi khởi động lại. Riêng `page_strategy` đổi được ngay trong UI.

Hai khoá quan trọng:

`field_page_preference` — khi nhiều trang cùng trả về giá trị cho một
trường, `first` lấy trang sớm nhất, `last` lấy trang muộn nhất. `full_name`
đặt `last` để không lấy tên xuất hiện trong phần căn cứ ở trang 1.

`correction_policy` — `correct` đưa qua model sửa lỗi, `protect` mask danh
từ riêng trước khi sửa rồi khôi phục, `skip` giữ nguyên tuyệt đối. Mã định
danh, ngày và tên người phải để `skip`.

## Metadata

Tab `Metadata` nạp `data_fields.json` thành bảng ba cột. Nút `Sửa` cho
phép chỉnh cột `Mô tả` — đây là văn bản đi vào prompt nên nó ảnh hưởng
trực tiếp đến chất lượng trích xuất.

`Lưu` ghi thẳng vào `data_fields.json` và tạo bản sao lưu `.bak` có
timestamp. Không sửa được khi đang chạy hoặc tạm dừng: prompt đã dựng từ
mô tả cũ, đổi giữa batch sẽ làm kết quả không đồng nhất.

## Đầu ra

Trong `output_dir`:

- `ket_qua_<timestamp>.tsv` — ghi liên tục sau từng file, đây là nguồn sự thật
- `ket_qua_<timestamp>.jsonl` — đầy đủ gồm provenance và audit sửa lỗi
- `ket_qua_<timestamp>.xlsx` — tạo tự động khi xong

TSV được ghi ngay sau mỗi file nên crash giữa batch không mất dữ liệu đã
xử lý. Excel là bản phái sinh, tên có timestamp nên không bao giờ đụng file
đang mở trong Excel.

Cột `document_number` và `issue_date` được set `number_format = "@"` để
Excel không diễn giải `08/2024` hay `12/03/2024` thành ngày tháng.

Mọi giá trị chuẩn hoá Unicode NFC. Không có bước này, chuỗi dạng tổ hợp
và dạng dựng sẵn hiển thị giống nhau nhưng không so sánh bằng nhau —
filter trong Excel sẽ không tìm được chữ có dấu.

## Tạm dừng và kết thúc

`Tạm dừng` dừng ở mức **file**, không giữa file. File đang xử lý chạy hết
rồi mới dừng, vì các request cho trang của nó đã gửi lên server. Sẽ có độ
trễ 2–5 giây trước khi trạng thái đổi thật.

Khi đã tạm dừng, `Kết thúc` chốt batch với những file đã xong, xuất Excel,
hiện popup như bình thường.

Nếu 3 file lỗi liên tiếp (`consecutive_error_limit`), worker tự tạm dừng
và ghi log đỏ. Thường là server chết — khởi động lại rồi bấm `Tiếp tục`.

## Cấu trúc

| File | Vai trò |
|---|---|
| `pipeline.py` | Logic thuần, không phụ thuộc PyQt. Import được từ dòng lệnh để test. |
| `workers.py` | `ConnectWorker`, `OcrWorker`, `EstimateWorker`. Chỉ giao tiếp qua signal. |
| `app.py` | UI, máy trạng thái, metadata editor, popup. |
| `config.json` | Cấu hình tĩnh. |
| `data_fields.json` | Định nghĩa trường trích xuất. |

## Giấy phép của model sửa lỗi

`protonx-models/protonx-legal-tc` dùng ProtonX Text Correction Model
License **v1.3-NC** — Non-Commercial. Rà soát pháp lý trước khi dùng
trong hệ thống có yếu tố thương mại. Đặt `use_correction: false` để tắt.
