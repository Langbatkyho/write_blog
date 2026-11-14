// Kiểm tra bundle.json khi tải (fail-closed) và tra cứu style/model trong bundle.
// Bundle do artifact/build_bundle.py sinh; đây chỉ kiểm tra hình dạng mà core cần.

export const SUPPORTED_BUNDLE_FORMAT = 1;
export const MODES = ["deep", "moment"];

export class BundleContractError extends Error {
  constructor(message) {
    super(message);
    this.name = "BundleContractError";
  }
}

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

function ensure(condition, message) {
  if (!condition) throw new BundleContractError(message);
}

function checkModelEntry(where, entry) {
  ensure(isObject(entry), `${where}: thiếu cấu hình model.`);
  for (const key of ["model", "effort", "model_tier"]) {
    ensure(typeof entry[key] === "string" && entry[key], `${where}: thiếu ${key}.`);
  }
}

/** Ném BundleContractError nếu bundle không đủ cho core; trả lại chính bundle. */
export function validateBundle(bundle) {
  ensure(isObject(bundle), "Bundle không phải object.");
  ensure(bundle.bundle_format === SUPPORTED_BUNDLE_FORMAT, `bundle_format ${bundle.bundle_format} không được hỗ trợ.`);
  ensure(typeof bundle.content_hash === "string" && bundle.content_hash, "Bundle thiếu content_hash.");
  ensure(isObject(bundle.workflows) && isObject(bundle.styles) && isObject(bundle.models), "Bundle thiếu workflows/styles/models.");
  ensure(isObject(bundle.models.stages) && isObject(bundle.models.learning), "Bundle thiếu models.stages/learning.");

  for (const mode of MODES) {
    const workflow = bundle.workflows[mode];
    ensure(isObject(workflow) && isObject(workflow.definition), `Thiếu workflow mode ${mode}.`);
    const steps = workflow.definition.steps;
    ensure(Array.isArray(steps) && steps.length > 0, `Workflow ${mode} không có step.`);
    const ids = steps.map((step) => step.id);
    ensure(JSON.stringify(ids) === JSON.stringify(workflow.stage_ids), `Workflow ${mode}: stage_ids lệch với steps.`);
    for (const id of ids) {
      ensure(typeof workflow.stage_files?.[id] === "string", `Workflow ${mode}: thiếu file skill cho stage ${id}.`);
      checkModelEntry(`models.stages.${id}`, bundle.models.stages[id]);
    }
    const styles = bundle.styles[mode];
    ensure(isObject(styles) && Object.keys(styles).length > 0, `Mode ${mode} không có style.`);
    for (const [slug, style] of Object.entries(styles)) {
      ensure(isObject(style.meta) && isObject(style.files), `Style ${mode}/${slug} thiếu meta/files.`);
      for (const id of ids) {
        const file = style.files[workflow.stage_files[id]];
        ensure(
          isObject(file) && isObject(file.data) && typeof file.yaml === "string",
          `Style ${mode}/${slug} thiếu skill ${workflow.stage_files[id]}.`,
        );
      }
    }
  }
  return bundle;
}

/** Tương đương resolve_style_by_slug_or_alias: slug trực tiếp, rồi alias trong previous_slugs. */
export function resolveStyle(bundle, mode, slugOrAlias) {
  const styles = bundle.styles[mode] || {};
  if (Object.prototype.hasOwnProperty.call(styles, slugOrAlias)) return slugOrAlias;
  for (const [slug, style] of Object.entries(styles)) {
    if ((style.meta.previous_slugs || []).includes(slugOrAlias)) return slug;
  }
  return null;
}

/** Danh sách style của mode, để hiển thị lựa chọn. */
export function listStyles(bundle, mode) {
  return Object.entries(bundle.styles[mode] || {}).map(([slug, style]) => ({
    slug,
    name: style.meta.name || slug,
    description: style.meta.description || "",
    system: style.system === true,
  }));
}

/** Cấu hình model của một stage workflow: {model, effort, model_tier}. */
export function modelConfigForStage(bundle, stageId) {
  const entry = bundle.models.stages[stageId];
  if (!entry) throw new BundleContractError(`Không có cấu hình model cho stage ${stageId}.`);
  return { ...entry };
}
