// Cấu hình model theo từng bước cho riêng người dùng (ART-6.1).
// Mặc định là bảng `claude:` trong repo (phương án Cân bằng, có trong bundle.models).
// Người dùng lưu phần ghi đè; cấu hình hiệu lực = mặc định + ghi đè hợp lệ.
// Chỉ chấp nhận model và effort có trong bundle.model_catalog (đúng những gì build chấp nhận).

export const MODEL_GROUPS = ["stages", "learning", "voice_lab"];

// Các bước tạo và biên tập bài: giữ model mạnh ở preset "Nhanh".
const WRITER_STAGES = new Set(["writing_agent", "editor_agent", "moment_writer", "breath_editor"]);

export const PRESETS = [
  { id: "balanced", label: "Cân bằng (mặc định)", description: "Bảng model trong repo." },
  { id: "max", label: "Chất lượng tối đa", description: "Mọi bước dùng model mạnh nhất, effort high." },
  { id: "fast", label: "Nhanh", description: "Sonnet 5.5 cho mọi bước; bước viết và biên tập dùng Opus 5.5, effort medium." },
  { id: "opus-medium", label: "Mốc Opus 5.5 · medium", description: "Mọi bước Opus 5.5, effort medium; mốc so sánh A/B của ART-6.2." },
];

const clone = (value) => JSON.parse(JSON.stringify(value));

function modelForTier(bundle, tier) {
  const entry = Object.entries(bundle.model_catalog.models).find(([, value]) => value === tier);
  if (!entry) throw new Error(`Không có model hạng ${tier} trong danh mục.`);
  return entry[0];
}

function entry(bundle, model, effort) {
  return { model, effort, model_tier: bundle.model_catalog.models[model] };
}

/** Bảng model đầy đủ (cùng dạng bundle.models) của một preset. */
export function presetModels(bundle, presetId) {
  const models = clone(bundle.models);
  if (presetId === "balanced") return models;
  const strongest = modelForTier(bundle, "complex");
  const everyday = modelForTier(bundle, "default");
  for (const group of MODEL_GROUPS) {
    for (const stage of Object.keys(models[group])) {
      if (presetId === "max") models[group][stage] = entry(bundle, strongest, "high");
      else if (presetId === "opus-medium") models[group][stage] = entry(bundle, strongest, "medium");
      else if (presetId === "fast") {
        models[group][stage] = WRITER_STAGES.has(stage) ? entry(bundle, strongest, "medium") : entry(bundle, everyday, "medium");
      } else throw new Error(`Preset không tồn tại: ${presetId}`);
    }
  }
  return models;
}

/** Phần ghi đè so với mặc định: chỉ các bước khác bảng trong repo. */
export function overridesFrom(bundle, models) {
  const overrides = {};
  for (const group of MODEL_GROUPS) {
    for (const [stage, value] of Object.entries(models[group] || {})) {
      const base = bundle.models[group][stage];
      if (base && (base.model !== value.model || base.effort !== value.effort)) {
        overrides[group] = overrides[group] || {};
        overrides[group][stage] = { model: value.model, effort: value.effort };
      }
    }
  }
  return overrides;
}

/** Bỏ các ghi đè không hợp lệ (bước lạ, model chưa kiểm chứng, effort sai). */
export function cleanOverrides(bundle, overrides) {
  const clean = {};
  const dropped = [];
  for (const [group, stages] of Object.entries(overrides || {})) {
    for (const [stage, value] of Object.entries(stages || {})) {
      const where = `${group}.${stage}`;
      const valid =
        MODEL_GROUPS.includes(group) &&
        bundle.models[group]?.[stage] &&
        value &&
        Object.prototype.hasOwnProperty.call(bundle.model_catalog.models, value.model) &&
        bundle.model_catalog.efforts.includes(value.effort);
      if (!valid) {
        dropped.push(where);
        continue;
      }
      clean[group] = clean[group] || {};
      clean[group][stage] = { model: value.model, effort: value.effort };
    }
  }
  return { overrides: clean, dropped };
}

/** Bảng model hiệu lực = mặc định + ghi đè hợp lệ; kèm model_tier từ danh mục. */
export function effectiveModels(bundle, settings) {
  const models = clone(bundle.models);
  const { overrides } = cleanOverrides(bundle, settings?.overrides);
  for (const [group, stages] of Object.entries(overrides)) {
    for (const [stage, value] of Object.entries(stages)) models[group][stage] = entry(bundle, value.model, value.effort);
  }
  return models;
}

/** Danh sách "nhóm.bước" khác mặc định. */
export function changedStages(bundle, settings) {
  const { overrides } = cleanOverrides(bundle, settings?.overrides);
  return Object.entries(overrides).flatMap(([group, stages]) => Object.keys(stages).map((stage) => `${group}.${stage}`));
}

/** Cài đặt ứng với một preset. */
export function settingsForPreset(bundle, presetId) {
  return { schema: 1, preset: presetId, overrides: overridesFrom(bundle, presetModels(bundle, presetId)) };
}

/** Preset nào khớp đúng bảng hiệu lực, hoặc "custom". */
export function matchingPreset(bundle, settings) {
  const current = JSON.stringify(effectiveModels(bundle, settings));
  const found = PRESETS.find((preset) => JSON.stringify(presetModels(bundle, preset.id)) === current);
  return found ? found.id : "custom";
}

/** Bundle dùng bảng model khác (các phần còn lại dùng chung tham chiếu). */
export function withModels(bundle, models) {
  return { ...bundle, models };
}

/** Tóm tắt để ghi vào bản ghi run: preset và các bước đã đổi. */
export function modelProfile(bundle, settings) {
  return { preset: matchingPreset(bundle, settings), changed: changedStages(bundle, settings) };
}
