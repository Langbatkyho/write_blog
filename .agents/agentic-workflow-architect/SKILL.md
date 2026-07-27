---
name: agentic-workflow-architect
description: Thiết kế, đánh giá và refactor kiến trúc workflow AI/agentic của dự án write_blog theo contract-first, ranh giới agent rõ ràng, context tiết kiệm token và I/O an toàn. Dùng khi thêm hoặc sửa workflow/agent, engine/orchestrator, prompt contract, Pydantic schema, Canonical IR, provider/routing, context policy, learning loop, compiler, archive, publisher, rollback hoặc tích hợp UI liên quan.
---

# Agentic Workflow Architect

Thiết kế thay đổi kiến trúc nhỏ, có thể kiểm chứng và không phá vỡ contract hiện hành.

## Quy trình

1. Đọc `.agents/AGENTS.md`, `docs/current_architecture.md` và `docs/workflow_analysis.md`.
2. Đọc [architecture-invariants.md](references/architecture-invariants.md) cho mọi tác vụ.
3. Phân loại thay đổi: contract, orchestration, prompt/agent, provider, persistence/publish, UI.
4. Xác định source of truth, consumer và backward-compatibility trước khi sửa mã.
5. Lập kế hoạch theo thứ tự: contract → engine → prompt → integration → verification.
6. Thực hiện thay đổi nhỏ nhất đáp ứng contract; không tạo abstraction chưa có consumer.
7. Kiểm tra import/reference, test cô lập, API boundary, I/O và regression trước khi báo hoàn tất.

## Chọn reference

- Khi thiết kế workflow, agent, handoff hoặc context policy: đọc [workflow-design-patterns.md](references/workflow-design-patterns.md).
- Khi review/refactor module hoặc orchestrator: đọc [refactor-checklist.md](references/refactor-checklist.md).
- Khi thay đổi nhiều nhóm trên: đọc cả hai.

## Bất biến

- Dùng schema/contract làm nguồn chân lý; không để prompt hoặc UI định nghĩa contract song song.
- Mỗi agent bảo vệ một trách nhiệm và không trả lời thay vai trò khác.
- Tách artifact đầy đủ cho audit/learning khỏi handoff gọn cho downstream context.
- Dùng dependency injection tại biên; không vá provider fallback trong low-level module.
- Voice Lab giữ Gemini-only cho đến khi người dùng phê duyệt provider khác. Inject callable để test không đồng nghĩa mở multi-provider.
- Fail-closed khi contract sai; không silent fallback.
- Publish nhiều file phải theo transaction có staging, validation và rollback.
- Không ghi test/dry-run vào `runs/`; tuân thủ toàn bộ quy tắc I/O trong `.agents/AGENTS.md`.

## Tiêu chí bàn giao

- Contract, consumer và test nhất quán.
- Không có dead architecture hoặc duplicate source of truth.
- Không phát sinh API hay artifact ngoài dự kiến.
- UI được render/kiểm chứng nếu có thay đổi.
- Báo cáo nêu thay đổi, bằng chứng kiểm thử và rủi ro còn lại.
