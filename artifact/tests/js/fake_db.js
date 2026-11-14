// db giả trong bộ nhớ, đủ cho repository: doc/collection, get/set/update/delete,
// orderBy/limit/where và quy tắc chẵn/lẻ phân đoạn của đường dẫn.
// Dùng chung cho test Node và (qua toString) cho test giao diện.

export function createFakeDb({ storage = null, failOn = null } = {}) {
  const store = storage || new Map();
  const segments = (path) => path.split("/").filter(Boolean);
  const check = (path, even) => {
    const count = segments(path).length;
    if (count === 0 || (count % 2 === 0) !== even) throw new TypeError(`Đường dẫn sai số phân đoạn: ${path}`);
  };
  const clone = (value) => (value === undefined ? undefined : JSON.parse(JSON.stringify(value)));
  const snapshot = (path) => {
    const value = store.get(path);
    return { id: segments(path).at(-1), exists: value !== undefined, data: () => clone(value), metadata: { fromCache: false, hasPendingWrites: false } };
  };
  const maybeFail = (op, path) => {
    if (failOn && failOn(op, path)) throw { code: "unavailable", message: `Lỗi giả khi ${op} ${path}` };
  };

  function doc(path) {
    check(path, true);
    return {
      id: segments(path).at(-1),
      path,
      async get() { maybeFail("get", path); return snapshot(path); },
      async set(data) { maybeFail("set", path); store.set(path, clone(data)); },
      async update(data) {
        maybeFail("update", path);
        if (!store.has(path)) throw { code: "invalid_argument", message: "update cần document đã tồn tại" };
        store.set(path, { ...store.get(path), ...clone(data) });
      },
      async delete() { maybeFail("delete", path); store.delete(path); },
      collection: (sub) => collection(`${path}/${sub}`),
    };
  }

  function query(path, { filters = [], order = null, max = null } = {}) {
    return {
      where: (field, op, value) => query(path, { filters: [...filters, [field, op, value]], order, max }),
      orderBy: (field, dir = "asc") => query(path, { filters, order: [field, dir], max }),
      limit: (n) => query(path, { filters, order, max: n }),
      async get() {
        maybeFail("query", path);
        const depth = segments(path).length + 1;
        let docs = [...store.keys()]
          .filter((key) => key.startsWith(path + "/") && segments(key).length === depth)
          .sort()
          .map(snapshot);
        for (const [field, op, value] of filters) {
          if (op !== "==") throw new Error("db giả chỉ hỗ trợ ==");
          docs = docs.filter((d) => d.data()[field] === value);
        }
        if (order) {
          const [field, dir] = order;
          docs.sort((a, b) => (a.data()[field] < b.data()[field] ? -1 : a.data()[field] > b.data()[field] ? 1 : 0) * (dir === "desc" ? -1 : 1));
        }
        if (max) docs = docs.slice(0, max);
        return { docs, size: docs.length, empty: docs.length === 0, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: false } };
      },
    };
  }

  function collection(path) {
    check(path, false);
    return { ...query(path), path, doc: (id) => doc(`${path}/${id}`) };
  }

  return { doc, collection, store };
}
