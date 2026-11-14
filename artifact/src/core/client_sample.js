// Client gọi Claude qua capability `sample` của Artifact, cùng giao diện với
// client_fake.js. Hàm `sample` được truyền vào (lấy bằng claude.use("sample")
// ở tầng UI), nên module này không chạm window.claude và test được bằng Node.

export const MAX_PROMPT_BYTES = 262144;

// Lỗi xảy ra sau khi Claude đã thật sự xử lý yêu cầu. Các mã còn lại (không
// cho phép, quá giới hạn, request sai...) bị chặn trước khi tới Claude.
const REACHED_CLAUDE = new Set(["refused", "empty_completion"]);

function normalizeError(error) {
  const code = (error && error.code) || "upstream_error";
  const text = error && typeof error.text === "string" && error.text ? error.text : null;
  return {
    code,
    message: (error && error.message) || String(error),
    text,
    // Có chữ trả về một phần nghĩa là lời gọi đã tới Claude.
    apiCalled: REACHED_CLAUDE.has(code) || Boolean(text),
  };
}

export function createSampleClient(sample) {
  if (typeof sample !== "function") throw new Error("Cần hàm sample của Artifact.");
  return {
    describe() {
      return { provider: "claude-sample", apiCapable: true };
    },
    async call({ prompt, modelConfig, signal, onText }) {
      const bytes = new TextEncoder().encode(prompt).length;
      if (bytes > MAX_PROMPT_BYTES) {
        throw { code: "prompt_too_large", message: `Prompt ${bytes} byte vượt giới hạn ${MAX_PROMPT_BYTES}.`, apiCalled: false };
      }
      try {
        const result = await sample(prompt, {
          model: modelConfig.model,
          modelTier: modelConfig.model_tier,
          effort: modelConfig.effort,
          cache: false,
          signal,
          onText: onText ? ({ text }) => onText({ text }) : undefined,
        });
        return {
          text: result.text,
          modelApplied: result.modelApplied || null,
          tierApplied: result.modelTierApplied || null,
          truncated: Boolean(result.truncated),
        };
      } catch (error) {
        throw normalizeError(error);
      }
    },
  };
}
