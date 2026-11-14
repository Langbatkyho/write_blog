// Port của engine/parser.py::build_context_package: chỉ đưa vào prompt những
// handoff và artifact mà `context_policy` của stage cho phép, theo thứ tự khai báo.

export function buildContextPackage(step, artifacts, handoffs) {
  const policy = (step && step.context_policy) || {};
  const pick = (names, source) => {
    const selected = {};
    for (const name of names || []) {
      if (Object.prototype.hasOwnProperty.call(source, name)) selected[name] = source[name];
    }
    return selected;
  };
  return {
    handoffs: pick(policy.handoffs, handoffs),
    artifacts: pick(policy.artifacts, artifacts),
  };
}
