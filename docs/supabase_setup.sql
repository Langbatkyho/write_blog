-- Supabase Setup Script cho Write Blog
-- Copy và dán toàn bộ đoạn mã này vào mục "SQL Editor" trên Supabase Dashboard và bấm "Run"

-- 1. Tạo bảng lưu trữ style files
CREATE TABLE IF NOT EXISTS style_files (
  id BIGSERIAL PRIMARY KEY,
  mode TEXT NOT NULL,          -- 'deep' hoặc 'moment'
  slug TEXT NOT NULL,          -- 'reflective', 'va-natural', v.v.
  filename TEXT NOT NULL,      -- 'sensory_capture.yaml', 'style_meta.yaml', v.v.
  content TEXT NOT NULL,       -- Nội dung YAML
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(mode, slug, filename)
);

-- 2. Cho phép truy cập ẩn danh (hoặc dùng service_key thì không bắt buộc, nhưng nên bật RLS nếu public)
-- Mặc định không có Row Level Security (RLS) để đơn giản cho ứng dụng nội bộ.
-- Nếu bạn muốn bảo mật hơn, có thể bật RLS và cấu hình Policy.
-- ALTER TABLE style_files ENABLE ROW LEVEL SECURITY;

-- 3. Tạo function cập nhật updated_at tự động khi sửa
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Gắn trigger vào bảng
DROP TRIGGER IF EXISTS trigger_style_files_updated_at ON style_files;
CREATE TRIGGER trigger_style_files_updated_at
BEFORE UPDATE ON style_files
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Hoàn tất!
