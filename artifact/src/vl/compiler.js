// Port của compiler.py và overrides.py: hàm tất định chồng hồ sơ giọng văn lên base template
// đầy đủ của một style hệ thống, giữ nguyên các trường bất biến. Base skill và base_hash lấy
// từ bundle (Python tính sẵn base_hash vì JSON làm mất dạng số thực như 3.0).
import { pyCasefold, pyCompare, pyFormatFixed, pyStrip, pyTruthy } from "../core/pycompat.js";
import { clone } from "./models.js";

const isDict = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const has = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/** So sánh bằng nhau kiểu Python cho dữ liệu JSON (dict không phụ thuộc thứ tự key). */
export function pyEquals(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((item, i) => pyEquals(item, b[i]));
  }
  if (isDict(a) && isDict(b)) {
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every((key) => has(b, key) && pyEquals(a[key], b[key]));
  }
  return false;
}

export function getAffectedAgents(changedDimensions, mode, vl) {
  const required = vl.required_agents[mode] || [];
  const affected = new Set(changedDimensions.flatMap((dimension) => vl.dimension_agents[dimension] || []));
  return required.filter((agent) => affected.has(agent));
}

function baseSkill(bundle, mode, baseStyleSlug, filename) {
  const file = bundle.styles[mode]?.[baseStyleSlug]?.files?.[filename];
  if (!file) throw new Error(`Base skill không tồn tại: mode=${mode}, style=${baseStyleSlug}, file=${filename}`);
  return file;
}

/** _rules_for_dimension: rule cho một chiều; báo lỗi nếu cùng một rule nằm ở cả do và avoid. */
export function rulesForDimension(dimension, profile) {
  if (!pyStrip(profile.description)) return [];
  const fold = (items) => new Set(items.filter((item) => pyStrip(item)).map((item) => pyCasefold(pyStrip(item))));
  const avoid = fold(profile.avoid);
  const duplicated = [...fold(profile.do)].filter((item) => avoid.has(item));
  if (duplicated.length) {
    throw new Error(`Dimension '${dimension}' có rule đồng thời trong do và avoid: ` + duplicated.sort(pyCompare).join(", "));
  }
  const rules = [`Mô tả: ${profile.description}`, `Cường độ mục tiêu: ${pyFormatFixed(profile.strength, 2)}`];
  for (const item of profile.do) if (pyStrip(item)) rules.push(`Nên: ${item}`);
  for (const item of profile.avoid) if (pyStrip(item)) rules.push(`Tránh: ${item}`);
  for (const item of profile.examples.slice(0, 2)) if (pyStrip(item)) rules.push(`Ví dụ tham chiếu: ${item}`);
  return rules;
}

function invariantSnapshot(base, { filename, workflowOrder, agentId }, vl) {
  const snapshot = {};
  for (const key of vl.skill_level_invariants) if (has(base, key)) snapshot[key] = clone(base[key]);
  // dict.update của Python: key đã có giữ vị trí, key mới thêm vào cuối.
  snapshot.agent_id = agentId;
  snapshot.filename = filename;
  snapshot.workflow_order = workflowOrder;
  return snapshot;
}

function contractObject(value) {
  if (value === null || value === undefined) return null;
  if (isDict(value)) return clone(value);
  return { reference: clone(value) };
}

/** compile_style: Canonical IR cho từng agent bị ảnh hưởng (mặc định: mọi agent của mode). */
export function compileStyle(profile, mode, changedDimensions = null, { bundle }) {
  const vl = bundle.voice_lab;
  if (!has(vl.required_agents, mode)) throw new Error(`Mode không hợp lệ: ${mode}`);
  if (profile.mode !== mode) throw new Error(`Profile mode '${profile.mode}' không khớp compile mode '${mode}'.`);
  const filenameMap = vl.agent_filename_map[mode];
  const required = vl.required_agents[mode];
  const warnings = [];
  let agents;
  if (changedDimensions === null || changedDimensions === undefined) {
    agents = required;
  } else {
    const unknown = [...new Set(changedDimensions)].filter((item) => !vl.dimensions.includes(item)).sort(pyCompare);
    if (unknown.length) warnings.push("Dimension không được map: " + unknown.join(", "));
    agents = getAffectedAgents(changedDimensions, mode, vl);
  }

  const artifacts = {};
  for (const agentSlug of agents) {
    const filename = filenameMap[agentSlug];
    const file = baseSkill(bundle, mode, profile.base_style_slug, filename);
    const base = file.data;
    const workflowOrder = required.indexOf(agentSlug) + 1;
    const agentId = pyTruthy(base.name) ? String(base.name) : agentSlug;
    const overlays = {};
    if (profile.dna) {
      for (const dimension of vl.dimensions) {
        if (!vl.dimension_agents[dimension].includes(agentSlug)) continue;
        const rules = rulesForDimension(dimension, profile.dna[dimension]);
        if (rules.length) overlays[dimension] = rules;
      }
    }
    const effective = clone(base);
    if (Object.keys(overlays).length) {
      effective.voice_lab_style = { schema_version: 2, profile_revision: profile.revision, dimensions: overlays };
    } else {
      delete effective.voice_lab_style;
    }
    const invariants = invariantSnapshot(base, { filename, workflowOrder, agentId }, vl);
    for (const [key, expected] of Object.entries(invariants)) {
      if (has(effective, key) && has(base, key) && !pyEquals(effective[key], expected)) throw new Error(`Compiler đã thay đổi invariant '${key}'.`);
    }
    const output = base.output;
    artifacts[filename] = {
      id: `${mode}:${profile.base_style_slug}:${agentSlug}`,
      schema_version: 2,
      agent_id: agentId,
      filename,
      workflow_order: workflowOrder,
      output_contract: contractObject(has(base, "output_contract") ? base.output_contract : base.output),
      handoff_contract: contractObject(has(base, "handoff_contract") ? base.handoff_contract : isDict(output) ? output.handoff ?? null : null),
      context_policy: contractObject(base.context_policy),
      base_style_slug: profile.base_style_slug,
      base_hash: file.base_hash,
      invariants,
      style_overlays: overlays,
      effective_skill: effective,
    };
  }
  return { artifacts, warnings };
}

// --- overrides.py ------------------------------------------------------------

const CANONICAL_FIELDS = [
  "id", "schema_version", "agent_id", "filename", "workflow_order", "output_contract", "handoff_contract",
  "context_policy", "base_style_slug", "base_hash", "invariants", "style_overlays", "effective_skill",
];

/** merge_overrides: gộp ba chiều tất định; thay đổi mơ hồ được giữ lại thành conflict. */
export function mergeOverrides(baseIr, currentIr, overridesIr, { bundle }) {
  const ids = new Set([baseIr.id, currentIr.id, overridesIr.id]);
  if (ids.size !== 1 || ids.has(undefined) || ids.has(null)) throw new Error("Cannot merge IRs with mismatched IDs");
  const invariantKeys = new Set(bundle.voice_lab.ir_level_invariants);
  const merged = { ...currentIr };
  const conflicts = [];
  const keys = [...new Set([...Object.keys(baseIr), ...Object.keys(currentIr), ...Object.keys(overridesIr)])].sort(pyCompare);
  const get = (object, key) => (has(object, key) ? object[key] : null);
  for (const key of keys) {
    const base = get(baseIr, key);
    const current = get(currentIr, key);
    const override = get(overridesIr, key);
    const conflict = (reason) => conflicts.push({ key, base_value: base, current_value: current, override_value: override, reason });
    if (invariantKeys.has(key)) {
      if (!pyEquals(override, base) || !pyEquals(current, base)) conflict("invariant_modified");
      continue;
    }
    if (pyEquals(current, override)) continue;
    if (pyEquals(current, base) && !pyEquals(override, base)) merged[key] = override;
    else if (pyEquals(override, base) && !pyEquals(current, base)) merged[key] = current;
    else conflict("both_sides_changed");
  }
  return { merged_ir: merged, conflicts };
}

function validateCanonicalIr(value) {
  const extra = Object.keys(value).filter((key) => !CANONICAL_FIELDS.includes(key));
  const problems = extra.map((key) => `trường lạ ${key}`);
  for (const key of ["id", "agent_id", "filename", "base_style_slug", "base_hash"]) if (typeof value[key] !== "string") problems.push(`${key} phải là chuỗi`);
  if (!Number.isInteger(value.workflow_order)) problems.push("workflow_order phải là số nguyên");
  if (has(value, "schema_version") && value.schema_version !== 2) problems.push("schema_version phải là 2");
  for (const key of ["invariants", "effective_skill"]) if (!isDict(value[key])) problems.push(`${key} phải là object`);
  if (!isDict(value.style_overlays) || !Object.values(value.style_overlays).every((rules) => Array.isArray(rules) && rules.every((r) => typeof r === "string"))) {
    problems.push("style_overlays phải là object của danh sách chuỗi");
  }
  for (const key of ["output_contract", "handoff_contract", "context_policy"]) if (has(value, key) && value[key] !== null && !isDict(value[key])) problems.push(`${key} phải là object hoặc null`);
  if (problems.length) throw new Error("Canonical IR không hợp lệ: " + problems.join("; "));
  return Object.fromEntries(CANONICAL_FIELDS.map((key) => [key, key === "schema_version" ? 2 : has(value, key) ? value[key] : null]));
}

/** apply_conflict_resolutions: áp lựa chọn của người dùng rồi kiểm tra lại IR và invariant. */
export function applyConflictResolutions(result, resolutions) {
  const unresolved = new Set(result.conflicts.map((item) => item.key));
  const invariantConflicts = result.conflicts.filter((item) => item.reason === "invariant_modified").map((item) => item.key);
  if (invariantConflicts.length) throw new Error("Không thể resolve thay đổi invariant: " + invariantConflicts.sort(pyCompare).join(", "));
  const missing = [...unresolved].filter((key) => !has(resolutions, key)).sort(pyCompare);
  const unknown = Object.keys(resolutions).filter((key) => !unresolved.has(key)).sort(pyCompare);
  if (missing.length) throw new Error("Thiếu lựa chọn cho conflict: " + missing.join(", "));
  if (unknown.length) throw new Error("Resolution không khớp conflict: " + unknown.join(", "));
  const artifact = validateCanonicalIr({ ...result.merged_ir, ...resolutions });
  for (const [key, expected] of Object.entries(artifact.invariants)) {
    if (has(artifact.effective_skill, key) && !pyEquals(artifact.effective_skill[key], expected)) throw new Error(`Resolution làm thay đổi invariant '${key}'.`);
  }
  return artifact;
}
