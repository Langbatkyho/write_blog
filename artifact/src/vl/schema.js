// Kiểm tra dữ liệu theo JSON Schema xuất từ Pydantic (bundle.voice_lab.schemas), fail-closed:
// gặp từ khóa schema chưa hỗ trợ thì báo lỗi thay vì bỏ qua. Trả giá trị đã điền mặc định
// theo thứ tự trường của schema, giống model_dump của Pydantic với các trường dùng ở đây.

const SUPPORTED = new Set([
  "$defs", "$ref", "additionalProperties", "anyOf", "const", "default", "enum", "format",
  "items", "maximum", "minimum", "properties", "required", "title", "type", "description",
]);

const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const DATE_TIME = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?$/i;

export class SchemaError extends Error {
  constructor(errors) {
    super(errors.join("; "));
    this.name = "SchemaError";
    this.errors = errors;
  }
}

function typeOk(type, value) {
  switch (type) {
    case "object": return isPlainObject(value);
    case "array": return Array.isArray(value);
    case "string": return typeof value === "string";
    case "number": return typeof value === "number" && Number.isFinite(value);
    case "integer": return Number.isInteger(value);
    case "boolean": return typeof value === "boolean";
    case "null": return value === null;
    default: throw new Error(`Kiểu schema chưa hỗ trợ: ${type}`);
  }
}

function emptyFor(schema, root) {
  const resolved = schema.$ref ? resolveRef(schema.$ref, root) : schema;
  if (resolved.type === "array") return [];
  if (resolved.type === "object" && !resolved.properties) return {};
  return undefined;
}

function resolveRef(ref, root) {
  const match = /^#\/\$defs\/(.+)$/.exec(ref);
  if (!match || !root.$defs?.[match[1]]) throw new Error(`$ref chưa hỗ trợ: ${ref}`);
  return root.$defs[match[1]];
}

function check(schema, value, path, root, errors) {
  for (const key of Object.keys(schema)) if (!SUPPORTED.has(key)) throw new Error(`Từ khóa schema chưa hỗ trợ: ${key}`);
  if (schema.$ref) return check(resolveRef(schema.$ref, root), value, path, root, errors);
  if (schema.anyOf) {
    for (const option of schema.anyOf) {
      const local = [];
      const result = check(option, value, path, root, local);
      if (!local.length) return result;
    }
    errors.push(`${path}: không khớp lựa chọn nào`);
    return value;
  }
  if (schema.type && !typeOk(schema.type, value)) {
    errors.push(`${path}: cần kiểu ${schema.type}`);
    return value;
  }
  if ("const" in schema && value !== schema.const) errors.push(`${path}: phải là ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.includes(value)) errors.push(`${path}: giá trị không hợp lệ`);
  if (typeof value === "number") {
    if ("minimum" in schema && value < schema.minimum) errors.push(`${path}: nhỏ hơn ${schema.minimum}`);
    if ("maximum" in schema && value > schema.maximum) errors.push(`${path}: lớn hơn ${schema.maximum}`);
  }
  if (schema.format) {
    if (schema.format !== "date-time") throw new Error(`format chưa hỗ trợ: ${schema.format}`);
    if (!DATE_TIME.test(value) || Number.isNaN(Date.parse(value))) errors.push(`${path}: không phải thời điểm hợp lệ`);
  }
  if (Array.isArray(value)) {
    return schema.items ? value.map((item, index) => check(schema.items, item, `${path}[${index}]`, root, errors)) : [...value];
  }
  if (isPlainObject(value) && (schema.properties || "additionalProperties" in schema)) {
    const properties = schema.properties || {};
    const out = {};
    for (const name of schema.required || []) if (!(name in value)) errors.push(`${path}.${name}: thiếu trường bắt buộc`);
    for (const [name, propSchema] of Object.entries(properties)) {
      if (name in value) out[name] = check(propSchema, value[name], `${path}.${name}`, root, errors);
      else if ("default" in propSchema) out[name] = structuredClone(propSchema.default);
      else {
        const empty = emptyFor(propSchema, root);
        if (empty !== undefined) out[name] = empty;
      }
    }
    for (const [name, item] of Object.entries(value)) {
      if (name in properties) continue;
      if (schema.additionalProperties === false) {
        errors.push(`${path}.${name}: trường không được phép`);
      } else if (isPlainObject(schema.additionalProperties)) {
        out[name] = check(schema.additionalProperties, item, `${path}.${name}`, root, errors);
      } else {
        out[name] = item;
      }
    }
    return out;
  }
  return value;
}

/** Kiểm tra `value` theo schema gốc; trả {ok, value, errors}. Không ném lỗi khi dữ liệu sai. */
export function validateSchema(schema, value) {
  const errors = [];
  const normalized = check(schema, value, "$", schema, errors);
  return errors.length ? { ok: false, value: null, errors } : { ok: true, value: normalized, errors: [] };
}

/** Như validateSchema nhưng ném SchemaError. */
export function parseWithSchema(schema, value) {
  const result = validateSchema(schema, value);
  if (!result.ok) throw new SchemaError(result.errors);
  return result.value;
}
