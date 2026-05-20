#!/usr/bin/env python3
"""
orc-local: Công cụ OCR tự động cho đề thi FPT University

Tự động quét ảnh đề thi trắc nghiệm, trích xuất câu hỏi bằng EasyOCR,
và xuất file questions.json chuẩn hóa.

Sử dụng:
    python ocr_local.py "D:\\path\\to\\exam\\folder"
    python ocr_local.py "D:\\path\\to\\folder" --force --raw
"""

import os
import re
import sys
import json
import argparse
import time
from pathlib import Path

# Supported image extensions
IMAGE_EXTENSIONS = {'.webp', '.jpg', '.jpeg', '.png', '.bmp'}

# Noise patterns to filter from OCR output
NOISE_PATTERNS = [
    r'^kizspy',
    r'^question:?\s*\d*$',
    r'^\(?\s*choose\s*$',
    r'^\s*answer\s*\)?\s*$',
    r'^fuo$',
    r'^fuoverflow',
    r'^zoom$',
    r'^close$',
    r'^100%$',
    r'^\s*[\'\"`_\.\-\|]\s*$',
    r'^\(choose\s+\d*\s*answer',
    r'^fuoverflowcom$',
    r'^fuoverflow\.com$',
]

NOISE_COMPILED = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]

# Pattern to detect numbered image files (exam question images)
NUMBERED_IMAGE_RE = re.compile(r'^(\d+)_.*\.(' + '|'.join(ext.lstrip('.') for ext in IMAGE_EXTENSIONS) + r')$', re.IGNORECASE)


def find_exam_folders(root_path):
    """
    Đệ quy tìm tất cả thư mục chứa ảnh đề thi.
    Một thư mục là "exam folder" nếu chứa ít nhất 1 file ảnh có tên dạng N_xxx.ext
    """
    exam_folders = []
    root = Path(root_path)

    if not root.is_dir():
        print(f"❌ Đường dẫn không tồn tại hoặc không phải thư mục: {root_path}")
        return exam_folders

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]

        has_numbered_images = False
        for fname in filenames:
            if NUMBERED_IMAGE_RE.match(fname):
                has_numbered_images = True
                break

        if has_numbered_images:
            exam_folders.append(Path(dirpath))

    # Sort for consistent ordering
    exam_folders.sort(key=lambda p: str(p).lower())
    return exam_folders


def get_sorted_images(folder_path):
    """
    Lấy danh sách file ảnh trong thư mục, sắp xếp theo số thứ tự.
    """
    folder = Path(folder_path)
    images = []

    for f in folder.iterdir():
        match = NUMBERED_IMAGE_RE.match(f.name)
        if match:
            num = int(match.group(1))
            images.append((num, f))

    images.sort(key=lambda x: x[0])
    return images


def ocr_folder(folder_path, reader):
    """
    OCR tất cả ảnh trong 1 thư mục đề thi.
    Trả về dict {image_filename: [list of text lines]}
    """
    images = get_sorted_images(folder_path)
    results = {}

    for idx, (num, img_path) in enumerate(images, 1):
        print(f"    [{idx}/{len(images)}] OCR: {img_path.name}...", end='', flush=True)
        try:
            ocr_results = reader.readtext(str(img_path))
            # Sort by vertical position (y-min), then horizontal (x-min) for reading order
            ocr_results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            lines = [text for _, text, _ in ocr_results]
            results[img_path.name] = lines
            print(f" ✅ ({len(lines)} dòng)")
        except Exception as e:
            print(f" ❌ Lỗi: {e}")
            results[img_path.name] = []

    return results


def is_noise(line):
    """Kiểm tra xem dòng text có phải là noise (watermark, UI element, etc.) không."""
    stripped = line.strip()
    if not stripped:
        return True
    for pattern in NOISE_COMPILED:
        if pattern.search(stripped):
            return True
    return False


def clean_line(line):
    """Xóa ký tự pipe `|` và các ký tự noise rời rạc khỏi dòng text."""
    # Remove stray pipe chars (from red divider line being OCR'd)
    cleaned = line.replace('|', '').strip()
    # Remove trailing underscores, dots
    cleaned = cleaned.rstrip('._')
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def filter_noise(lines):
    """Lọc bỏ noise lines và làm sạch text, trả về danh sách dòng sạch."""
    result = []
    for line in lines:
        if is_noise(line):
            continue
        cleaned = clean_line(line)
        if cleaned and len(cleaned) > 1:  # Skip single-char remnants
            result.append(cleaned)
    return result


def detect_option_letter(line):
    """
    Kiểm tra xem dòng có bắt đầu bằng ký hiệu option (A., B., C., D., ...) không.
    Trả về (letter, clean_text) nếu có, None nếu không.
    """
    match = re.match(r'^([A-Za-z])[\.\)]\s*(.*)', line)
    if match:
        letter = match.group(1).upper()
        text = match.group(2).strip()
        if letter in 'ABCDEFGH' and text:
            return (letter, text)
    return None


def parse_single_image(lines, image_name):
    """
    Phân tích danh sách dòng text từ 1 ảnh thành 1 câu hỏi.
    Trả về dict hoặc None nếu không parse được.
    """
    # Filter noise
    clean_lines = filter_noise(lines)
    if not clean_lines:
        return None

    # Extract question number from image name
    match = re.match(r'^(\d+)_', image_name)
    q_num = match.group(1) + '_' if match else image_name

    # Strategy 1: Try to detect letter-prefixed options (A., B., C., D.)
    question_parts = []
    options = []
    found_first_option = False

    for line in clean_lines:
        opt = detect_option_letter(line)
        if opt:
            found_first_option = True
            options.append(opt[1])
        elif found_first_option:
            # After options started, non-letter lines might be continuation of last option
            if options:
                options[-1] = options[-1] + ' ' + line
        else:
            question_parts.append(line)

    # If we found letter-prefixed options with at least 2 options
    if len(options) >= 2:
        question_text = ' '.join(question_parts).strip()
        # Clean up question text
        question_text = re.sub(r'\s+', ' ', question_text)
        # Clean up options
        clean_options = [re.sub(r'\s+', ' ', opt).strip().rstrip('._') for opt in options]

        q_type = 'singlechoice'
        return {
            'questionType': q_num,
            'questionText': question_text,
            'type': q_type,
            'options': clean_options
        }

    # Strategy 2: Heuristic - no letter prefixes detected
    # The question is typically the first part, then options follow
    # Try to find if it's a True/False question
    tf_check = [l.lower().strip() for l in clean_lines]
    if 'true' in tf_check and 'false' in tf_check:
        true_idx = min(tf_check.index('true'), tf_check.index('false'))
        question_text = ' '.join(clean_lines[:true_idx]).strip()
        question_text = re.sub(r'\s+', ' ', question_text)
        return {
            'questionType': q_num,
            'questionText': question_text,
            'type': 'singlechoice',
            'options': ['True', 'False']
        }

    # Strategy 3: Split by position - question = first line(s) ending with ?, options = rest
    question_parts = []
    option_start = -1

    for i, line in enumerate(clean_lines):
        question_parts.append(line)
        # Check if accumulated text forms a question (ends with ?)
        combined = ' '.join(question_parts)
        if combined.strip().endswith('?') or combined.strip().endswith(':'):
            option_start = i + 1
            break

    if option_start > 0 and option_start < len(clean_lines):
        question_text = ' '.join(clean_lines[:option_start]).strip()
        question_text = re.sub(r'\s+', ' ', question_text)

        # Remaining lines are options - try to group them sensibly
        remaining = clean_lines[option_start:]
        options = merge_option_lines(remaining)

        if len(options) >= 2:
            return {
                'questionType': q_num,
                'questionText': question_text,
                'type': 'singlechoice',
                'options': options
            }

    # Strategy 4: Fallback - just split everything
    if len(clean_lines) >= 2:
        question_text = clean_lines[0]
        question_text = re.sub(r'\s+', ' ', question_text)
        options = merge_option_lines(clean_lines[1:])

        return {
            'questionType': q_num,
            'questionText': question_text,
            'type': 'singlechoice',
            'options': options if len(options) >= 2 else clean_lines[1:]
        }

    return None


def merge_option_lines(lines):
    """
    Ghép các dòng rời rạc thành các options hoàn chỉnh.
    Heuristic: dòng ngắn (<30 ký tự) và không bắt đầu bằng chữ hoa
    có thể là phần tiếp nối của dòng trước.
    """
    if not lines:
        return []

    options = []
    current = lines[0]

    for line in lines[1:]:
        stripped = line.strip()
        # Nếu dòng này trông giống phần tiếp nối (bắt đầu bằng chữ thường, hoặc
        # bắt đầu bằng "and", "or", "with", etc.)
        continuation_words = {'and', 'or', 'with', 'of', 'for', 'the', 'to', 'in', 'on',
                              'that', 'which', 'is', 'are', 'was', 'were', 'not', 'but'}
        first_word = stripped.split()[0].lower() if stripped.split() else ''

        if (first_word in continuation_words or
            (len(stripped) < 20 and not stripped[0].isupper() if stripped else False)):
            current = current + ' ' + stripped
        else:
            options.append(re.sub(r'\s+', ' ', current).strip().rstrip('._'))
            current = stripped

    if current:
        options.append(re.sub(r'\s+', ' ', current).strip().rstrip('._'))

    return options


def process_exam_folder(folder_path, reader, force=False, save_raw=False):
    """
    Xử lý 1 thư mục đề thi: OCR → Parse → Save JSON.
    """
    folder = Path(folder_path)
    output_file = folder / 'questions.json'
    raw_file = folder / 'raw_ocr.txt'

    # Check if already processed
    if output_file.exists() and not force:
        print(f"  ⏭️  Đã có questions.json (dùng --force để ghi đè)")
        return 0

    # Step 1: OCR all images
    print(f"  📸 Đang OCR ảnh...")
    ocr_results = ocr_folder(folder_path, reader)

    if not ocr_results:
        print(f"  ⚠️  Không tìm thấy ảnh nào")
        return 0

    # Save raw OCR output if requested
    if save_raw:
        with open(raw_file, 'w', encoding='utf-8') as f:
            for img_name, lines in ocr_results.items():
                f.write(f"=== IMAGE: {img_name} ===\n")
                for line in lines:
                    f.write(f"{line}\n")
                f.write("\n")
        print(f"  📝 Raw OCR lưu tại: {raw_file.name}")

    # Step 2: Parse questions
    print(f"  🧠 Đang phân tích câu hỏi...")
    questions = []
    for img_name, lines in ocr_results.items():
        q = parse_single_image(lines, img_name)
        if q:
            questions.append(q)
        else:
            print(f"    ⚠️  Không parse được: {img_name}")

    # Step 3: Save JSON
    if questions:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"  ✅ Đã lưu {len(questions)} câu hỏi → {output_file.name}")
    else:
        print(f"  ⚠️  Không trích xuất được câu hỏi nào")

    return len(questions)


def main():
    parser = argparse.ArgumentParser(
        description='🔍 orc-local: OCR tự động đề thi FPT University',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python ocr_local.py "D:\\TaiLieu\\SWD392"           # Quét tất cả đề trong SWD392
  python ocr_local.py "D:\\TaiLieu"                    # Quét tất cả môn, tất cả kì
  python ocr_local.py "D:\\TaiLieu\\SWD392\\FE\\SWD392_SU25_FE"  # 1 đề cụ thể
  python ocr_local.py "D:\\TaiLieu" --force --raw      # Ghi đè + lưu raw OCR
        """
    )
    parser.add_argument('folder', help='Đường dẫn thư mục chứa ảnh đề thi (hỗ trợ đệ quy)')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Ghi đè questions.json nếu đã tồn tại')
    parser.add_argument('--raw', '-r', action='store_true',
                        help='Lưu thêm file raw_ocr.txt cho việc review')

    args = parser.parse_args()
    folder = args.folder

    # Banner
    print("=" * 60)
    print("🔍 orc-local: OCR Tự Động Đề Thi FPT University")
    print("=" * 60)
    print(f"📂 Thư mục: {folder}")
    print()

    # Step 1: Find all exam folders
    print("🔎 Đang tìm kiếm thư mục đề thi...")
    exam_folders = find_exam_folders(folder)

    if not exam_folders:
        print("❌ Không tìm thấy thư mục đề thi nào!")
        print("   Hãy chắc chắn thư mục chứa ảnh có tên dạng: 1_xxx.webp, 2_xxx.png, ...")
        sys.exit(1)

    print(f"✅ Tìm thấy {len(exam_folders)} bộ đề:\n")
    for i, ef in enumerate(exam_folders, 1):
        img_count = len(get_sorted_images(ef))
        print(f"   {i}. {ef.name} ({img_count} ảnh)")
    print()

    # Step 2: Initialize EasyOCR
    print("⏳ Đang khởi tạo EasyOCR (lần đầu có thể mất 1-2 phút)...")
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False)
        print("✅ EasyOCR đã sẵn sàng!\n")
    except ImportError:
        print("❌ Chưa cài EasyOCR! Chạy: pip install easyocr")
        sys.exit(1)

    # Step 3: Process each folder
    start_time = time.time()
    total_questions = 0

    for i, ef in enumerate(exam_folders, 1):
        print(f"{'─' * 50}")
        print(f"📋 [{i}/{len(exam_folders)}] {ef}")
        total_questions += process_exam_folder(ef, reader, args.force, args.raw)
        print()

    # Summary
    elapsed = time.time() - start_time
    print("=" * 60)
    print(f"🎉 HOÀN THÀNH!")
    print(f"   📊 {len(exam_folders)} bộ đề | {total_questions} câu hỏi")
    print(f"   ⏱️  Thời gian: {elapsed:.1f} giây")
    print("=" * 60)


if __name__ == '__main__':
    main()
