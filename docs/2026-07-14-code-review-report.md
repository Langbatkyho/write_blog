# Code Review Report — 2026-07-14 Editorial Workflow Redesign

**Reviewer:** Claude Opus 4.6 (Principal Code Reviewer)
**Subject:** Codex GPT 5.5 redesign of editorial workflow
**Date:** 2026-07-14

---

### 1. CHẤT LƯỢNG THIẾT KẾ SO VỚI MỤC ĐÍCH ĐẶT RA

**Đánh giá tổng: 9.2/10 — Xuất sắc.**

Mục đích cốt lõi của redesign là tách biệt vai trò các agent theo nguyên tắc *"mỗi agent bảo vệ một sự thật duy nhất"*. Codex GPT 5.5 đã thực thi nguyên tắc này một cách rất triệt để:

| Tiêu chí | Đánh giá |
| :--- | :--- |
| Tách `reader_experience` (chỉ ghi nhật ký) khỏi `editor_agent` (chỉ sửa tối thiểu) | ✅ Hoàn hảo. `reader_experience.yaml` có `forbidden_actions` và `forbidden_analysis` rõ ràng. |
| `future_self` không còn tạo `final_blog.md` → chỉ tạo `future_reflection.md` | ✅ Đúng. Output đổi thành `future_reflection.md`, rules ghi rõ *"Never produce final_blog.md"*. |
| `editor_agent` mới: tạo `edited_blog.md` + `edit_log.md` song song | ✅ Thiết kế `secondary_name` + `derive_artifact_file_contents()` xử lý tách file gọn gàng. |
| `coach_agent` đọc `edited_blog.md` thay vì `draft_blog.md` | ✅ `context_policy` trỏ artifact vào `editor_agent`. |
| `final_output` phân biệt AI draft / reflection / human final / production | ✅ 4 trường rõ ràng trong `write_blog.yaml`. |
| Learning loop hiểu workflow mới | ✅ `editorial_learning.yaml` đã có `editor_agent` trong tasks. `comparison_label` fallback tới `edited_blog.md`. |
| Contract tests bảo vệ thiết kế mới | ✅ 3 test cases mới trong `test_workflow_contract.py` kiểm tra order, blind review, secondary file. |

**Điểm mạnh nổi bật:**
- Skill YAML thiết kế ở tầm cao: `editor_agent.yaml` có `editing_priority`, `voice_protection`, `humanity_filter`, `minimal_edit_principle` — đây là thiết kế **prompt-architecture cấp production**, không phải prompt đơn giản.
- `writing_agent.yaml` v3.0 có `excluded_responsibilities` — ranh giới rõ, tránh việc agent tự mở rộng vai trò.

**Thiếu sót nhỏ:**
- `reflection_engine.yaml` vẫn còn cấu trúc YAML trùng key `sections` (L54-60 lặp lại L39-46 dưới `output.artifact.sections`). YAML spec cho phép nhưng gây nhầm lẫn về semantic (xem Refactor Vector #1).

---

### 2. 🔍 ĐỐI CHIẾU SỰ TUÂN THỦ (PLAN VS IMPLEMENTATION)

Plan tham chiếu: [2026-07-14-editorial-workflow-redesign.md](file:///D:/Nghiên cứu AI/write_blog/docs/2026-07-14-editorial-workflow-redesign.md)

| Mã Task | Tên Task (Trong PLAN) | Trạng thái | Ghi chú kỹ thuật nhanh |
| :--- | :--- | :--- | :--- |
| T1 | Thêm `editor_agent` sau `reader_experience` trong flow | ✅ Đạt | `write_blog.yaml` L66-78. Order: 7 steps đúng thứ tự. |
| T2 | `future_self` output → `future_reflection.md` | ✅ Đạt | `write_blog.yaml` L96, `future_self.yaml` L52. |
| T3 | `final_output` phân biệt AI draft / reflection / human / production | ✅ Đạt | `write_blog.yaml` L106-111, 4 trường tách biệt. |
| T4 | `context_policy`: reader chỉ nhận `draft_blog.md` (blind) | ✅ Đạt | `write_blog.yaml` L62-64. Handoffs rỗng, artifacts chỉ có `writing_agent`. |
| T5 | `context_policy`: editor nhận draft + reader report | ✅ Đạt | `write_blog.yaml` L71-78. Cả handoff lẫn artifact đầy đủ. |
| T6 | `context_policy`: coach nhận edited (không phải draft) | ✅ Đạt | `write_blog.yaml` L86-91. Artifact là `editor_agent`. |
| T7 | `context_policy`: future_self nhận edited + editor/coach/reflection handoffs | ✅ Đạt | `write_blog.yaml` L98-104. |
| T8 | Viết lại `writing_agent.yaml` thành ghost writer | ✅ Đạt | v3.0, có `excluded_responsibilities`, `draft_mindset`. |
| T9 | Viết lại `reader_experience.yaml` thành reader diary | ✅ Đạt | v3.0, có `forbidden_actions`, `forbidden_analysis`. |
| T10 | Thêm `editor_agent.yaml` | ✅ Đạt | v2.0, 177 dòng, thiết kế prompt-architecture hoàn chỉnh. |
| T11 | Viết lại `coach_agent.yaml` | ✅ Đạt | v2.0, focus vào blind spots, rules rõ: *"Never rewrite"*. |
| T12 | Viết lại `future_self.yaml` | ✅ Đạt | v2.0, output = reflection, rules rõ: *"Never produce final_blog.md"*. |
| T13 | Cập nhật `editorial_learning.yaml` | ✅ Đạt | v2.0, tasks bao gồm `editor_agent`. |
| T14 | Config per-stage cho `editor_agent` | ✅ Đạt | `config.example.yaml` L31-34. |
| T15 | Engine hỗ trợ `secondary_name` (tách `edit_log.md`) | ✅ Đạt | `derive_artifact_file_contents()` trong `workflow.py` L119-139. |
| T16 | Learning fallback: `final_blog.md` → `edited_blog.md` | ✅ Đạt | `run_learning_loop()` L313-329, fallback chain rõ ràng. |
| — | Sửa file ngoài plan | ⚠️ Không phát hiện | Agent không tự ý sửa file nào ngoài danh sách. |

**Kết luận:** 16/16 tasks đạt. Không sót, không sai lệch. Agent tuân thủ plan 100%.

---

### 3. ⚡ TỐI ƯU HÓA WORKFLOW & KIẾN TRÚC

- **Lỗi crash hệ thống / bảo mật nghiêm trọng:** Không phát hiện. Dry-run hoàn thành, tạo đủ 20 files đầu ra. 9/9 tests pass.

- **Lệch pha Data Contract:**
  - `editor_agent.yaml` khai báo `artifact.required_sections: ["### Edited Blog", "### Edit Log"]` nhưng `derive_artifact_file_contents()` regex tìm `## Edited Blog` (heading level 2, không phải 3). **Đây là lệch pha tiềm ẩn**: nếu LLM tuân thủ YAML và dùng `###`, regex sẽ vẫn match vì `re.search(r"(?ims)^##+\s*...", ...)` match cả `##` và `###`. Tuy nhiên, nếu LLM trả heading level 1 (`# Edited Blog`), regex sẽ match nhưng semantic sẽ sai. **Rủi ro thấp nhưng nên thống nhất.**

- **Trùng lặp / Thừa thãi:**
  - [reflection_engine.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/reflection_engine.yaml) L38-46 (`output.artifact.sections`) và L54-60 (`output.sections`) — **hai khối `sections` trùng nội dung**, key khác cấp nhưng dữ liệu giống hệt. Đây là dư thừa từ lần refactor trước (fix duplicate key `include` → `sections`) chưa dọn sạch.
  - [story_architect.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/story_architect.yaml) L40-47 (`output.artifact.sections`) và L56-63 (`output.sections`) — **tương tự**: hai khối `sections` cùng dữ liệu.

---

### 4. 🛠️ VECTOR TINH CHỈNH CODEBASE (REFACTOR VECTORS)

---

**Vector #1: Dọn `sections` trùng lặp trong skill YAML**

- **Vị trí:** [reflection_engine.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/reflection_engine.yaml) L54-60, [story_architect.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/story_architect.yaml) L56-63
- **Vấn đề:** `output.sections` lặp 100% nội dung của `output.artifact.sections`. Dữ liệu dư thừa, dễ lệch khi chỉ sửa một bên.
- **Giải pháp:** Xóa khối `output.sections` ở cả hai file. Chỉ giữ `output.artifact.sections`.

```diff
 # reflection_engine.yaml — xóa dòng 54-60
-  sections:
-    - emotional_truth
-    - hidden_tension
-    - premature_conclusions
-    - reflective_questions
-    - emerging_insight
-    - unresolved_space
```

---

**Vector #2: Thống nhất heading level trong `editor_agent` data contract**

- **Vị trí:** [editor_agent.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/editor_agent.yaml) L156-157, [workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/workflow.py) `extract_markdown_section()` L115
- **Vấn đề:** YAML khai báo `### Edited Blog` (h3) nhưng engine regex match `##+` (h2+). Nếu LLM trả đúng h3 thì OK, nhưng contract không rõ ràng.
- **Giải pháp:** Sửa YAML thành `## Edited Blog` và `## Edit Log` cho nhất quán với heading level mà engine regex expect, hoặc thêm ghi chú rõ ràng trong `build_step_prompt` rằng sub-sections dùng `##`.

```diff
 # editor_agent.yaml L155-157
    required_sections:
-     - "### Edited Blog"
-     - "### Edit Log"
+     - "## Edited Blog"
+     - "## Edit Log"
```

---

**Vector #3: `call_openai` gọi `get_api_key` lặp mỗi retry**

- **Vị trí:** [openai_client.py](file:///D:/Nghiên cứu AI/write_blog/engine/openai_client.py) `call_openai()` L105-114
- **Vấn đề:** `get_api_key(config)` được gọi bên trong vòng lặp retry. Mỗi lần retry đều gọi lại, kích hoạt lại `warnings.warn` nếu key hardcoded. API key không thay đổi giữa các lần retry.
- **Giải pháp:** Hoist `get_api_key` ra ngoài vòng lặp.

```diff
 def call_openai(...) -> str:
     options = get_openai_options(config, stage_id)
+    api_key = get_api_key(config)
     # ...
     for attempt in range(max_retries):
         request = urllib.request.Request(
             endpoint,
             # ...
             headers={
-                "Authorization": f"Bearer {get_api_key(config)}",
+                "Authorization": f"Bearer {api_key}",
                  "Content-Type": "application/json",
             },
```

---

**Vector #4: `derive_artifact_file_contents` thiếu warning khi fallback**

- **Vị trí:** [workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/workflow.py) `derive_artifact_file_contents()` L126-131
- **Vấn đề:** Hàm thử 3 tên heading cứng (`"Edited Blog"`, `"edited_blog"`, `"Edited Draft"`). Nếu LLM trả heading khác (ví dụ: `"Bài Đã Chỉnh Sửa"`), fallback trả toàn bộ artifact vào `edited_blog.md` và `edit_log.md` nhận string lỗi — không crash nhưng output sai lặng lẽ.
- **Giải pháp:** Log warning khi fallback xảy ra.

```python
# workflow.py, sau dòng 130
if edited_blog == artifact:
    import warnings
    warnings.warn(
        f"Could not split artifact into primary/secondary. "
        f"Falling back to full artifact for {primary_name}.",
        UserWarning, stacklevel=2,
    )
```

---

**Vector #5: Thiếu test cho `derive_artifact_file_contents` edge case**

- **Vị trí:** [test_handoff_parser.py](file:///D:/Nghiên cứu AI/write_blog/tests/test_handoff_parser.py)
- **Vấn đề:** Chỉ có happy-path test. Không có test cho trường hợp LLM không trả heading mong đợi.
- **Giải pháp:** Thêm 1 test case.

```python
def test_secondary_fallback_when_heading_missing(self) -> None:
    skill = {"output": {"name": "edited_blog.md", "secondary_name": "edit_log.md"}}
    artifact = "Just plain text without expected headings."
    contents = derive_artifact_file_contents(skill, artifact)
    self.assertEqual(contents["edited_blog.md"], artifact)
    self.assertIn("not found", contents["edit_log.md"])
```
