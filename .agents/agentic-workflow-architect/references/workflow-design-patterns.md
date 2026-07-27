# Workflow Design Patterns

## Ranh giới agent

- Mỗi agent bảo vệ một chân lý hoặc một quyết định.
- Reader mô tả trải nghiệm đọc; editor đề xuất chỉnh sửa; writer tạo bản nháp; publisher không sáng tác.
- Không gộp vai trò chỉ để giảm số stage nếu làm prompt mơ hồ hoặc output khó kiểm chứng.

## Context và token

- Lưu `Artifact` đầy đủ cho human audit và learning.
- Truyền `Handoff` ngắn, có cấu trúc cho downstream agent.
- Khai báo context policy trong flow/config thay vì hardcode trong Python.
- Learning loop dùng bằng chứng đầy đủ, không chỉ handoff.
- Tách knowledge space theo mode/domain để tránh nhiễm chéo.

## Prompt và cache

- Đặt context dài, ổn định ở phần đầu; đặt nhiệm vụ và output contract gần cuối.
- Không tối ưu cache bằng cách nhân bản prompt hoặc phá ranh giới agent.
- Đo token/context trước khi tối ưu model.

## Routing và mở rộng

- Dùng convention/path resolution và registry thay cho chuỗi `if/else`.
- Định tuyến provider/model ở biên thông qua dependency injection.
- Không copy workflow gần giống nhau nếu khác biệt có thể biểu diễn bằng mode, policy hoặc config.

## Trình tự triển khai

1. Chốt schema, invariant và filename mapping.
2. Viết validator và contract test.
3. Thay engine/persistence.
4. Viết hoặc sửa prompt/agent.
5. Tích hợp UI.
6. Chạy regression và audit artifact.

Khi dùng nhiều agent, không cho các agent sửa song song contract hoặc file tích hợp chung.
