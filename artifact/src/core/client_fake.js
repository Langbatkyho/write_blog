// Client giả, xác định, cho test và chế độ xem thử. Cùng giao diện với client
// gọi Claude thật (ART-3):
//   describe(stageId, modelConfig) -> {provider, apiCapable}
//   call({prompt, stageId, modelConfig, signal, onText}) -> Promise<{text, modelApplied, tierApplied, truncated}>
// Lỗi được ném dưới dạng {code, message}, giống lỗi của capability `sample`.

const EDITOR_STAGES = new Set(["editor_agent", "breath_editor"]);

/** Phản hồi mặc định, cùng tinh thần build_dry_run_response của engine. */
export function fakeStageResponse(stageId) {
  const artifact = EDITOR_STAGES.has(stageId)
    ? `## Edited Blog\n\n[FAKE] Bài đã biên tập cho stage \`${stageId}\`.\n\n## Edit Log\n\n- [FAKE] Ghi lại chỉnh sửa tối thiểu.`
    : `[FAKE] Phản hồi giả cho stage \`${stageId}\`.`;
  return `## Artifact\n\n${artifact}\n\n## Handoff\n\n[FAKE HANDOFF] Tóm tắt ngắn của \`${stageId}\` cho stage sau.`;
}

/**
 * @param options.responses  {stageId: text} thay cho phản hồi mặc định
 * @param options.failures   {stageId: {code, message}} để giả lập lỗi
 * @param options.truncated  danh sách stageId trả về truncated: true
 * @param options.downgrade  danh sách stageId mà model "bị hạ hạng" (không có modelApplied)
 * @param options.apiCapable mặc định false: client giả không gọi API
 */
export function createFakeClient({
  responses = {},
  failures = {},
  truncated = [],
  downgrade = [],
  apiCapable = false,
  provider = "fake",
} = {}) {
  const calls = [];
  return {
    calls,
    describe() {
      return { provider, apiCapable };
    },
    async call({ prompt, stageId, modelConfig, signal, onText }) {
      calls.push({ stageId, prompt, modelConfig });
      if (signal && signal.aborted) throw { code: "cancelled", message: "Đã dừng." };
      if (failures[stageId]) throw failures[stageId];
      const text = Object.prototype.hasOwnProperty.call(responses, stageId) ? responses[stageId] : fakeStageResponse(stageId);
      if (onText) onText({ text, delta: text });
      return {
        text,
        modelApplied: downgrade.includes(stageId) ? null : modelConfig.model,
        tierApplied: modelConfig.model_tier,
        truncated: truncated.includes(stageId),
      };
    },
  };
}
