# Phân tích Workflow & Bài học Rút ra (Lessons Learned)

## Bài học 1: Tối ưu Token phải bắt đầu từ Kiến trúc Context

Việc chọn các mô hình giá rẻ giúp giảm chi phí, nhưng nguồn gốc lớn nhất của lãng phí là **sự lặp lại Context**. Ở thiết kế cũ, mỗi bước đều mang theo toàn bộ output của tất cả các bước trước đó. Các agent cuối chuỗi phải đọc lại hàng loạt thông tin mà chúng không hề cần.

**Giải pháp:**
- Giữ bản đầy đủ (Artifact) để con người review và dùng cho quá trình Learning.
- Chỉ truyền bản tóm tắt ngắn gọn (Handoff) cho máy thực thi.
- Khai báo luồng di chuyển context minh bạch ngay trong file YAML của workflow.

## Bài học 2: Output Debug và Context Thực thi phải tách biệt

Ban đầu, một file output gánh hai nhiệm vụ:
1. Cho con người đọc, gỡ lỗi.
2. Làm dữ liệu đầu vào cho máy ở bước sau.

Hai nhiệm vụ này yêu cầu độ lớn và độ chính xác khác nhau. Tách bạch `Artifact` và `Handoff` giúp hệ thống dễ dàng tối ưu lượng token mà không làm mất tính khả quan (observability).

## Bài học 3: File cấu hình Flow phải nắm giữ Context Policy

Đưa logic `context_policy` vào file `flow/write_blog.yaml` giúp workflow dễ dàng được kiểm tra trực quan. Người bảo trì tương lai có thể thấy rõ tại sao `future_self` nhận được bản nháp nhưng chỉ cần bản tóm tắt handoff từ các tác nhân khác. Việc giấu các quyết định này trong mã Python là một thực hành xấu (anti-pattern).

## Bài học 4: Learning Loop cần toàn bộ Bằng Chứng, không phải Handoff

Bản Handoff sinh ra để máy thực thi nhanh và rẻ, nhưng để học từ `production_blog.md` của con người, hệ thống cần toàn bộ bản `Artifact`. Nếu chỉ so sánh Handoff với bài đăng thực tế, AI có thể bỏ sót những chỉnh sửa quan trọng từ con người.
Việc tổ chức lại thư mục output với `step_outputs.json` đa tầng giúp duy trì bằng chứng nguyên vẹn phục vụ cho quá trình này.

## Bài học 5: Đừng để một Agent ôm đồm nhiều việc chỉ vì nó làm được

Ban đầu `writing_agent` vừa viết, vừa chỉnh văn phong; `reader_experience` vừa đóng vai độc giả, vừa đóng vai người bắt lỗi. Điều này khiến ranh giới trách nhiệm bị mờ nhạt, và prompt trở nên cực kỳ phức tạp.

**Quy tắc Vàng:** "Mỗi agent chỉ bảo vệ một chân lý và không trả lời thay câu hỏi của agent khác".
- Độc giả (Reader) chỉ nói cảm nhận lần đọc đầu.
- Biên tập (Editor) mới đưa ra chỉnh sửa.
- Việc xuất bản cuối cùng (`final_blog.md`) phải được trả về tay con người.

## Bài học 6: Code Dependency Injection (DI) hiệu quả hơn Fallback ngầm

Trong quá trình thiết lập Bridge để sử dụng Model Quota nội bộ (Antigravity), chúng ta từng mắc sai lầm chèn logic ghi file trực tiếp vào trong `openai_client.py` thông qua `try...except RuntimeError`. Điều này làm phá vỡ ranh giới module và gây rủi ro bảo mật rò rỉ key.

**Giải pháp tốt nhất:** Thiết lập TypeAlias `LlmClient` chuẩn và thực hiện Dependency Injection ở cấp cao nhất của hệ thống (`run_workflow.py`), thay vì vá lỗi ở tầng thấp.

## Bài học 7: Kiểm soát chi phí phải đi theo nhiều lớp (Layered)

Dự án hiện có 3 lớp kiểm soát chi phí:
1. Lựa chọn model theo từng giai đoạn (vd: xài model nhỏ cho bước tóm tắt).
2. Nén ngữ cảnh bằng Handoff Layer.
3. Chạy Offline Learning không cần gọi API.

Sự kết hợp nhiều lớp giúp hệ thống mạnh mẽ hơn nhiều so với việc chỉ dựa vào một thủ thuật cắt giảm token duy nhất. Đề xuất tương lai: Đo lường Token Telemetry trước khi gửi API request.

## Bài học 8: Router Pattern thay thế Hardcode Conditional Logic

Ban đầu, tham số `--client` chỉ hoạt động như một fallback đơn giản giữa OpenAI và Antigravity, được quyết định ở tầng ứng dụng (CLI) và cố định xuyên suốt workflow. Tuy nhiên, việc tối ưu chi phí và chất lượng thực tế yêu cầu từng stage sử dụng model (hoặc client) chuyên biệt. Thay vì thay đổi hàm thực thi LLM, sử dụng mô hình Router (với Dependency Injection) và Dictionary Map `--client-map` giúp tách bạch cấu hình khỏi logic workflow. `LlmClient` closure do Router trả về vẫn tuân thủ hoàn toàn signature cũ, đảm bảo tính đóng gói và mở rộng trong tương lai.

## Bài học 9: Hiểu đúng bản chất của Prompt Caching API

Việc tối ưu hóa token không chỉ đơn thuần là rút gọn (compression) văn bản, mà còn là nghệ thuật lợi dụng bộ nhớ đệm (Caching).
- **Tránh sai lầm "Đứt chuỗi"**: Các LLM API như Anthropic và OpenAI sử dụng **Prefix Hashing** phi trạng thái (stateless) cho Caching. Nếu một stage bất kỳ làm thay đổi prefix, cache của riêng stage đó sẽ miss, nhưng nó hoàn toàn không làm "đứt chuỗi" hay phá hỏng cache của các stage sau (những stage tiếp tục dùng chung prefix ban đầu).
- **Tối ưu vị trí dữ liệu**: 
  - Dữ liệu dài và tĩnh (như `author_input`) bắt buộc phải đẩy lên đầu file (Static Prefix) để API nhận dạng được và cache lại. Nếu đặt sai vị trí (ví dụ: ở giữa hoặc cuối prompt), phần dữ liệu này sẽ không bao giờ được cache.
  - Các chỉ thị mang tính tuân thủ cao (Skill YAML, định dạng đầu ra) nên đặt ở đuôi (Dynamic Suffix) để lợi dụng Recency Bias, giúp LLM không bị lạc lối sau khi đọc hàng ngàn token ngữ cảnh.

## Bài học 10: Kiến trúc Đa Phong Cách (Multi-Style) không nên làm phình to Engine
Ban đầu, để hỗ trợ nhiều phong cách viết (như `reflective` hay `provocative`), có nguy cơ phải viết thêm hàng loạt cấu trúc điều kiện `if/else` trong code. Việc định tuyến dựa trên Path resolution (`Path(step["skill"]).parent / style / Path(step["skill"]).name`) cho phép Engine hỗ trợ không giới hạn số lượng phong cách mà code lõi không thay đổi. YAML trở thành API Configuration của từng phong cách.

## Bài học 11: Lập kế hoạch Multi-Agent cần sự tuần tự chặt chẽ
Khi sử dụng cấu trúc Đa tác tử (Multi-Agent), việc thiết lập các Task song song dễ gây ra **Race Condition** (Tình trạng tương tranh) trên các file mã nguồn dùng chung hoặc unit tests chung. Thay vì phân công Agent 1 và Agent 2 chạy song song, việc yêu cầu Agent 1 hoàn tất Refactoring nền tảng (Thư mục, Engine, Test) rồi mới để Agent 2 vào làm nhiệm vụ Prompt Engineering (Tạo YAML mới) đảm bảo hệ thống không bị lỗi gãy đổ cục bộ. Ground Truth (`STYLE_BRIEF.md`) luôn phải được định nghĩa trước khi Agent làm nội dung nhảy vào thao tác.

## Bài học 12: Kiến trúc Dual Modes đòi hỏi định tuyến (Routing) linh hoạt từ lõi Engine
Ban đầu, khi chuyển từ một workflow duy nhất sang Hệ Hai Chế Độ Viết (`deep` và `moment`), phản xạ đầu tiên là sao chép toàn bộ file `flow/write_blog.yaml` thành `flow/write_deep_blog.yaml` dẫn đến tỷ lệ duplicate code lên tới 95%. Hệ thống tốt không nhân bản cấu trúc cố định, mà nên dựa vào cơ chế định tuyến động (`resolve_workflow_file` và `resolve_step_skill_path`) của Engine để tự phân giải đúng Context Policy và Skill YAML theo các cờ `--mode` và `--style`.

## Bài học 13: Phân tách triệt để không gian Tri Thức Học Tập (Learning Knowledge Space)
Tri thức để biên tập một "khoảnh khắc" (ngắn, trực giác, giữ nguyên năng lượng hiện tại) hoàn toàn khác với tri thức biên tập một bài "phản tư" (dài, tìm kiếm mâu thuẫn, chuyển hóa nhận thức). Nếu để chung vào một file `editorial_learning_report.md`, AI sẽ sớm bị "ô nhiễm chéo" quy tắc và sinh ra các mẫu câu khuyên nhủ triết lý hóa trong các bài viết khoảnh khắc. Việc phân tách luồng xuất ra file (`deep_blog_patterns.md` vs `moment_blog_patterns.md`) và tách biệt thư mục `learning/<mode>/` là bắt buộc để duy trì tính toàn vẹn của từng chế độ viết.

## Bài học 14: Lỗi Phá Vỡ Hợp Đồng Flow do Lệch Định Danh (Slug vs Filename Mapping)
Trong quá trình triển khai Trình quản lý giọng văn **Guided Style Voice Lab V1**, khi người dùng nhấn xuất bản (Publish) phong cách `va-natural`, hệ thống lập tức báo lỗi và tự động hoàn tác (Rollback):  
`Lỗi: Style 'va-natural.staging' vi phạm hợp đồng Flow. Thiếu các file skill bắt buộc: ['sensory_capture.yaml', 'cosmic_signal_reader.yaml'...]`.

**Nguyên nhân gốc rễ (Root Cause):**  
Khi biên dịch Canonical IR (tri thức nguyên bản) thành Effective YAML (kỹ năng thi hành), module `compiler.py` đã đặt tên file xuất ra dựa trực tiếp trên các định danh nội bộ (slug) viết tắt của Agent (ví dụ: `architect.yaml`, `writer.yaml`, `sensory.yaml`, `cosmic_signal.yaml`). Trong khi đó, hợp đồng quy trình `flow/*.yaml` lại yêu cầu chính xác tên đầy đủ (`story_architect.yaml`, `writing_agent.yaml`, `sensory_capture.yaml`, `cosmic_signal_reader.yaml`). Sự lệch pha danh pháp này khiến hàm kiểm duyệt `validate_style_contract` đánh giá folder staging thiếu file bắt buộc.

**Bài học & Giải pháp:**  
Trong kiến trúc động sinh mã (Code Generation / Compiler Engine), **danh pháp định danh (Naming Convention)** chính là hợp đồng giao tiếp quan trọng nhất giữa các module. Cần thiết lập một bảng tra cứu định danh cứng (`AGENT_FILENAME_MAP`) làm cầu nối trung gian giữa slug nội bộ và tên file hợp đồng trên đĩa, tuyệt đối không suy đoán hay giả định tên file.

## Bài học 15: Cơ Chế Fail-Fast và Quản Trị Giao Dịch Nguyên Tử (Atomic Rollback)
Trước đây, khi thiếu file hoặc sai tên style, engine có thói quen "silent fallback" âm thầm chuyển về mặc định (`reflective`). Điều này cực kỳ nguy hiểm trong môi trường Production vì người dùng hoặc AI tưởng rằng style mới đang hoạt động trong khi thực chất đang chạy code cũ.

**Quy tắc Giao dịch An toàn (Safe Transactional I/O):**
1. **Fail-Fast**: Phát hiện thiếu sót là từ chối thi hành và báo lỗi rõ ràng ngay tại cửa ngõ, tuyệt đối không tự động vá lỗi ngầm.
2. **Staging -> Validate -> Backup -> Replace**: Mọi thao tác xuất bản hoặc chèn đè hệ thống nhiều file (như phong cách mới) phải được thực hiện trên không gian tạm (`.staging`), gọi validator kiểm tra hợp đồng, sao lưu thư mục cũ, và cuối cùng dùng tráo đổi nguyên tử (`os.replace`). Nếu sai ở bất kỳ khâu nào, kích hoạt Rollback (`shutil.rmtree`) trả nguyên trạng hệ thống trong 0.1 giây.

## Bài học 16: Tranh Luận Kiến Trúc và Vai Trò Phản Biện Độc Lập (Claude Opus vs GPT-5.6 Sol vs Gemini)
Nhìn lại toàn bộ lịch sử tiến hóa dự án (từ script monolith 892 dòng -> Handoff Layer -> Editorial Redesign -> Client Routing -> Multi-Style -> Dual Modes -> Voice Lab V1), giá trị lớn nhất giữ cho kiến trúc luôn sạch sẽ chính là **sự tranh luận và phản biện chéo không khoan nhượng giữa các AI Agentic Models**:
- **Khắc phục tư duy nhân bản (Duplication Trap):** Khi GPT-5.6 Sol lập kế hoạch Dual Modes, ý tưởng đầu tiên là copy flow file thành `write_deep_blog.yaml` và hardcode whitelist. Chính **Claude Opus 4.6** qua bước Audit nghiêm ngặt đã chỉ ra việc nhân bản này tạo ra 95% nợ kỹ thuật (technical debt), thúc đẩy **Gemini 3.1 Pro** và **Gemini 3.6 Flash** tái cấu trúc theo hướng định tuyến động (`resolve_workflow_file`, `resolve_step_skill_path`).
- **Bảo vệ ranh giới module (Module Boundary Hygiene):** Khi tích hợp Antigravity Bridge, việc vá lỗi ngầm qua `try...except` trong client cũ đã bị bác bỏ hoàn toàn để thay bằng mô hình **Dependency Injection (`LlmClient`)** chuẩn hóa từ CLI entrypoint.

## Bài học 17: `runs/` là dữ liệu nghiệp vụ, không phải sandbox

Fixture trong `examples/` từng bị dùng để tạo nhiều dry-run có cùng chủ đề trong `runs/`. Test/dry-run từ nay phải dùng output root tạm; workflow thật chỉ tạo run mới collision-safe; run đã hoàn tất mặc định chỉ đọc. `runs/temp_llm/` chỉ là ngoại lệ tương thích có giới hạn cho file bridge của lần chạy hiện tại.

## Bài học 18: RULES và SKILL phải tách vai trò

- `.agents/AGENTS.md` là policy bắt buộc về dữ liệu, API, thao tác phá hủy, test và tiêu chí hoàn tất.
- `agentic-workflow-architect/SKILL.md` hướng dẫn quyết định kiến trúc theo contract → engine → prompt → integration → verification.
- RULES có hiệu lực cao hơn SKILL khi liên quan đến an toàn dữ liệu và I/O.

## Bài học 19: Refactor theo Gate để hệ thống luôn dùng được

P0 chỉ tách module và giữ facade tương thích; P1 siết contract; P2 xử lý audit hardening. Mỗi phase phải regression xanh trước khi chuyển tiếp. Vì vậy dừng do quota tại checkpoint không làm workflow rơi vào trạng thái sửa dở.

## Bài học 20: Refactor theo trách nhiệm, không theo số dòng

- UI tách state, view và controller.
- Workflow tách execution, persistence, context, resolution, artifacts và learning.
- Interview giữ facade; routing, profile patch và calibration thành domain module riêng.

Module mới chỉ hợp lệ khi có consumer thực tế và regression test.

## Bài học 21: Heuristic và rollback cần nói đúng giới hạn

- Token estimator chỉ là guardrail offline, không phải số token chính xác của Gemini.
- Xác nhận A/B trực tiếp có thể nâng confidence tới `0.95`, nhưng phải lưu before/after và provenance.
- Transaction phải xử lý cả rollback failure, bảo toàn tombstone và trả đường dẫn phục hồi thủ công.

---

# 5. Đánh Giá & Đề Xuất Tổng Hợp Thành Skill Kiến Trúc Sư (`agentic-workflow-architect`)

### 5.1. Có thể tổng hợp các bài học này thành Skill không?
**CÓ, HOÀN TOÀN KHẢ THI VÀ CỰC KỲ CẦN THIẾT!**  
21 bài học trên không chỉ là kinh nghiệm riêng của dự án viết blog, mà thực chất là **bộ quy chuẩn kiến trúc nền tảng (Architectural Design Patterns & Guardrails)** cho bất kỳ hệ thống AI Agentic đa tác tử (Multi-Agent Systems), AI Workflows, hoặc hệ thống sinh nội dung phức tạp nào.

Nếu không được đóng gói thành một Skill độc lập, trong các dự án sau (hoặc các giai đoạn mở rộng tiếp theo), các AI Agent thế hệ mới sẽ tiếp tục lặp lại những sai lầm kinh điển: viết script monolith, để bùng nổ token ngữ cảnh, dùng conditional hardcode, nhân bản code lặp, hoặc để các agent dẫm chân lên vai trò của nhau.

### 5.2. Trạng thái triển khai Skill: `agentic-workflow-architect`

Skill đã được triển khai tại `.agents/agentic-workflow-architect/SKILL.md` và được `.agents/AGENTS.md` bắt buộc kích hoạt khi thay đổi workflow, engine, prompt contract, schema, provider, learning, compiler, archive, publisher hoặc rollback.

#### **Khung Nội Dung Cốt Lõi Của Skill (`SKILL.md`):**

```yaml
---
name: agentic-workflow-architect
description: >
  Bộ quy chuẩn kiến trúc và thực hành tốt nhất cho việc thiết kế, tái cấu trúc, 
  và bảo trì các hệ thống AI Agentic Workflows, Multi-Agent Collaboration, và Code Engine.
  Sử dụng skill này khi cần lập kế hoạch thêm agent mới, xây dựng pipeline, tối ưu token, hoặc quản trị I/O an toàn.
---
```

1. **Trụ Cột 1: Vệ Sinh Token & Kiến Trúc Ngữ Cảnh (Token & Context Hygiene)**
   - **Quy tắc Tách biệt Đầu ra (Dual-Output Rule)**: Mọi Agent bắt buộc sinh 2 luồng: `Artifact` (bản đầy đủ cho human audit & learning loop) và `Handoff` (bản nén 120-250 từ cho agent tiếp theo).
   - **Tối ưu Caching (Prompt Caching Mechanics)**: Đẩy tĩnh lên trên (Static Prefix), để lệnh và YAML xuống dưới (Dynamic Suffix - Recency Bias). Không sợ "đứt chuỗi" cache khi stage giữa thay đổi prompt.
   - **Phân tách Không gian Tri thức (Knowledge Space Isolation)**: Các chế độ/domain khác nhau (như Deep vs Moment) buộc phải có báo cáo học tập và folder lưu trữ riêng biệt.

2. **Trụ Cột 2: Ranh Giới Trách Nhiệm Đại Lý (Agent Boundary Isolation)**
   - **Quy tắc Vàng**: "Mỗi agent bảo vệ một chân lý duy nhất và không trả lời thay câu hỏi của agent khác".
   - **Độc lập chức năng**: Người viết nháp (Writer), Người đọc mù (Reader), Người biên tập (Editor), Người phản biện (Coach) không được kiêm nhiệm hoặc gộp chung prompt. Quyền xuất bản bản cuối cùng luôn thuộc về con người hoặc explicit check.

3. **Trụ Cột 3: Định Tuyến Động & Bơm Phụ Thuộc (Dynamic Routing & Dependency Injection)**
   - **Chống Hardcode (No Whitelist Hardcoding)**: Sử dụng Path resolution và cấu trúc quy ước (`skills/<mode>/<style>/`) để mở rộng vô hạn thay vì viết `if/else`.
   - **Dependency Injection**: Luôn truyền `LlmClient` hoặc `Router` từ tầng CLI/Entrypoint xuống Engine; không chèn logic kết nối ngoại lệ vào tầng low-level client.

4. **Trụ Cột 4: Hợp Đồng Nghiêm Ngặt & Giao Dịch An Toàn (Contract-First & Safe I/O)**
   - **Chống Silent Fallback (Fail-Fast Rule)**: Thiếu file skill hay sai hợp đồng phải dừng và báo lỗi ngay lập tức, không tự động fallback về style mặc định.
   - **Bảng Ánh Xạ Danh Pháp (Explicit Filename Mapping)**: Luôn dùng `AGENT_FILENAME_MAP` khi biên dịch hoặc sinh mã động để đảm bảo khớp 100% với Flow contract.
   - **Quy trình Xuất bản 4 Bước (Safety Pipeline)**: `Staging` -> `Contract Validation` -> `Backup` -> `Atomic Replace (os.replace) / Rollback (shutil.rmtree)`.

5. **Trụ Cột 5: Điều Phối Multi-Agent Tuần Tự (Sequential Multi-Agent Governance)**
   - Trong một đợt nâng cấp phức tạp, bắt buộc Agent 1 hoàn tất Refactoring nền tảng (Thư mục, Engine, Contract test) trước khi Agent 2 làm nhiệm vụ Prompt Engineering hoặc tạo YAML mới, loại bỏ hoàn toàn rủi ro Race Condition trên test suites và file dùng chung.

### 5.3. Thành phần đã triển khai

- `SKILL.md`: trigger, quy trình, bất biến và tiêu chí bàn giao.
- `references/architecture-invariants.md`: contract, module boundary, provider, I/O và compatibility.
- `references/workflow-design-patterns.md`: Artifact/Handoff, context policy và orchestration.
- `references/refactor-checklist.md`: discovery, change design, verification và cleanup.


## [2026-07-31 16:05] Phân tích quy trình triển khai Web App & Deploy

**1. Bài học về Quản lý State trong Streamlit:**
- Khi ghép 2 luồng chức năng (Voice Lab và Blog Workflow) vào chung 1 web app, biến st.session_state dễ bị rò rỉ và ô nhiễm chéo. Giải pháp là định nghĩa rõ các khóa khởi tạo ban đầu (init states) và xây dựng hàm clear cache (
eset_blog_workflow_state).

**2. Bài học về cấu hình biến môi trường trên Cloud:**
- Khi user copy/paste API key lên các nền tảng như Render, rất dễ dính dấu ngoặc kép (", ') hoặc các biến null/rỗng. Luồng nạp biến môi trường bắt buộc phải có cơ chế strip() loại bỏ dấu ngoặc kép thay vì chỉ bỏ khoảng trắng, nếu không API provider (Gemini/OpenAI) sẽ từ chối.
- Logging của hệ thống khi chạy trên cloud cần in ra 1 phần mã hash của key (4 ký tự đầu/cuối) để dễ dàng debug xem server có thực sự nhận đúng key hay không.

**3. Bài học về Handoff giữa các Models:**
- Khi làm việc với nhiều Agentic LLMs (Opus -> Gemini), các Agent có khả năng tự review code và đề xuất Refactoring rất tốt. Tuy nhiên cần có một Agent quản lý tổng thể (như phiên Antigravity hiện tại) đứng ra xác nhận và thực thi đồng bộ, tránh đụng độ version.
## Bài học 22: Lưu trữ trên Render và Auto-deploy Loop với Git
Khi đẩy dữ liệu (Git Sync) từ Render runtime ngược lại repo GitHub, nếu branch được đẩy là `main` (hoặc branch đang liên kết deploy), Render sẽ lập tức trigger một quá trình auto-deploy mới. Quá trình này sẽ làm chết ứng dụng đang chạy (kill session của người dùng giữa chừng). Việc trỏ sang nhánh phụ (ví dụ `data`) khắc phục được vòng lặp deploy nhưng lại làm mất khả năng đồng bộ dữ liệu vào codebase chính cho lần khởi động sau.

**Giải pháp tối ưu:** Luôn tách biệt mã nguồn (chỉ định từ GitHub → Render) và dữ liệu (app runtime → Database/Supabase). Sử dụng DB ngoài (Supabase) kết hợp cơ chế restore lúc khởi động giúp luồng triển khai gọn gàng và không bao giờ gặp lỗi mất dữ liệu khi mất ổ cứng tạm trên Render.
