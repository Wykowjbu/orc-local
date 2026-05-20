# 🔍 orc-local

Công cụ OCR tự động cho đề thi trắc nghiệm FPT University.

Chỉ cần truyền vào **đường dẫn thư mục** chứa ảnh đề thi → tool tự động quét, trích xuất câu hỏi, và xuất file `questions.json` chuẩn hóa.

---

## 📋 Yêu cầu hệ thống

- **Python** 3.10 trở lên
- **pip** (Python package manager)

---

## 🚀 Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/Wykowjbu/orc-local.git
cd orc-local
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Lưu ý:** Lần đầu chạy EasyOCR sẽ tự tải model (~100MB). Cần kết nối internet.

---

## 📖 Cách sử dụng

### Cú pháp cơ bản

```bash
python ocr_local.py "<đường_dẫn_thư_mục>"
```

### Ví dụ

```bash
# OCR 1 đề cụ thể
python ocr_local.py "D:\TaiLieu\SWD392\FE\SWD392_SU25_FE"

# OCR tất cả đề trong 1 môn
python ocr_local.py "D:\TaiLieu\SWD392"

# OCR tất cả môn, tất cả kì (đệ quy)
python ocr_local.py "D:\TaiLieu"

# Ghi đè file cũ + lưu raw OCR text
python ocr_local.py "D:\TaiLieu" --force --raw
```

### Tùy chọn CLI

| Tùy chọn | Viết tắt | Mô tả |
|-----------|----------|-------|
| `--force` | `-f` | Ghi đè `questions.json` nếu đã tồn tại |
| `--raw` | `-r` | Lưu thêm file `raw_ocr.txt` (văn bản thô từ OCR) |

---

## 📂 Cấu trúc thư mục đầu vào

Tool hỗ trợ **độ sâu thư mục bất kỳ**. Nó tự đệ quy tìm các thư mục chứa ảnh đề thi.

```
TàiLiệu/                              ← Truyền folder này cũng OK
├── Kì_Summer_2025/
│   ├── SWD392/
│   │   ├── FE/
│   │   │   ├── SWD392_SU25_FE/        ← ✅ Phát hiện → OCR
│   │   │   │   ├── 1_xxx.webp
│   │   │   │   ├── 2_xxx.webp
│   │   │   │   └── ...
│   │   │   └── SWD392_FA24_FE/        ← ✅ Phát hiện → OCR
│   │   └── PE/
│   │       └── SWD392_SU25_PE_1/      ← ✅ Phát hiện → OCR
│   └── PRN231/
│       └── FE/
│           └── PRN231_SU25_FE/        ← ✅ Phát hiện → OCR
```

**Cách nhận diện đề thi:** Bất kỳ thư mục nào chứa file ảnh có tên bắt đầu bằng **số + underscore** (ví dụ `1_xxx.webp`, `2_xxx.jpg`, `10_xxx.png`) đều được coi là 1 bộ đề.

### Định dạng ảnh hỗ trợ

`.webp`, `.jpg`, `.jpeg`, `.png`, `.bmp`

---

## 📄 Cấu trúc JSON đầu ra

Mỗi bộ đề sẽ có 1 file `questions.json` được tạo trong cùng thư mục:

```json
[
  {
    "questionType": "1_",
    "questionText": "What is the main function of the COMET methodology in Software Architecture Design?",
    "type": "singlechoice",
    "options": [
      "Focusing on object-oriented methods for modularity",
      "Simplifying data storage",
      "Testing the performance of the system",
      "Automating the coding process"
    ]
  },
  {
    "questionType": "2_",
    "questionText": "What is the primary purpose of software modeling?",
    "type": "singlechoice",
    "options": [
      "To create visually appealing user interface",
      "To write code and implement software functionality",
      "To document, analyze, and design software systems",
      "To perform software testing and quality assurance"
    ]
  }
]
```

### Giải thích các trường

| Trường | Mô tả |
|--------|-------|
| `questionType` | Số thứ tự câu hỏi (lấy từ tên ảnh, ví dụ `"1_"`, `"2_"`) |
| `questionText` | Nội dung câu hỏi |
| `type` | Loại câu hỏi: `"singlechoice"` hoặc `"multiplechoice"` |
| `options` | Danh sách các phương án trả lời |

---

## 🖥️ Demo output

```
============================================================
🔍 orc-local: OCR Tự Động Đề Thi FPT University
============================================================
📂 Thư mục: D:\TaiLieu\SWD392

🔎 Đang tìm kiếm thư mục đề thi...
✅ Tìm thấy 3 bộ đề:

   1. SWD392_FA24_FE (60 ảnh)
   2. SWD392_FA24_FE_BLOCK_5 (60 ảnh)
   3. SWD392_SU25_FE (60 ảnh)

⏳ Đang khởi tạo EasyOCR (lần đầu có thể mất 1-2 phút)...
✅ EasyOCR đã sẵn sàng!

──────────────────────────────────────────────────
📋 [1/3] SWD392_FA24_FE
  📸 Đang OCR ảnh...
    [1/60] OCR: 1_SWD392_-_FA_2024_-_FE_3001.webp... ✅ (8 dòng)
    [2/60] OCR: 2_SWD392_-_FA_2024_-_FE_3001.webp... ✅ (10 dòng)
    ...
  🧠 Đang phân tích câu hỏi...
  ✅ Đã lưu 60 câu hỏi → questions.json

============================================================
🎉 HOÀN THÀNH!
   📊 3 bộ đề | 180 câu hỏi
   ⏱️  Thời gian: 245.3 giây
============================================================
```

---

## ❓ FAQ / Khắc phục sự cố

### Q: Lần đầu chạy rất lâu?
**A:** EasyOCR cần tải model (~100MB) lần đầu. Các lần sau sẽ nhanh hơn nhiều.

### Q: OCR sai một số câu hỏi?
**A:** Đây là hạn chế của OCR tự động. Bạn có thể:
1. Dùng flag `--raw` để lưu văn bản thô
2. Mở `questions.json` và sửa thủ công các câu bị sai

### Q: Muốn chạy lại 1 bộ đề?
**A:** Dùng flag `--force` để ghi đè file cũ:
```bash
python ocr_local.py "D:\path\to\exam" --force
```

### Q: Máy không có GPU?
**A:** Tool mặc định chạy trên CPU, không cần GPU. Tuy nhiên tốc độ sẽ chậm hơn (~5 giây/ảnh).

### Q: Hỗ trợ đề thi PE (Practical Exam)?
**A:** Đề PE thường là dạng bài tập thực hành (không phải trắc nghiệm), nên kết quả OCR có thể không cấu trúc tốt. Tool hoạt động tốt nhất với đề FE (Final Exam) dạng trắc nghiệm.

---

## 📝 License

MIT License
