// Port của difflib (CPython 3.13) phần engine dùng cho báo cáo offline:
// SequenceMatcher (không có isjunk, autojunk mặc định bật) và unified_diff.
// Phải khớp từng byte với Python, nên giữ nguyên thuật toán và heuristic
// "popular elements" (phần tử xuất hiện > 1% khi chuỗi b dài từ 200 phần tử).

export class SequenceMatcher {
  /** @param a, b mảng phần tử so sánh được bằng === (dòng, hoặc ký tự theo code point) */
  constructor(a, b, { autojunk = true } = {}) {
    this.a = a;
    this.b = b;
    this.autojunk = autojunk;
    this.matchingBlocks = null;
    this.chainB();
  }

  chainB() {
    const b2j = new Map();
    this.b.forEach((element, index) => {
      if (!b2j.has(element)) b2j.set(element, []);
      b2j.get(element).push(index);
    });
    // isjunk = None nên không có phần tử junk; chỉ bỏ phần tử "popular".
    this.bpopular = new Set();
    const n = this.b.length;
    if (this.autojunk && n >= 200) {
      const ntest = Math.floor(n / 100) + 1;
      for (const [element, indices] of b2j) if (indices.length > ntest) this.bpopular.add(element);
      for (const element of this.bpopular) b2j.delete(element);
    }
    this.b2j = b2j;
  }

  findLongestMatch(alo, ahi, blo, bhi) {
    const { a, b, b2j } = this;
    let besti = alo;
    let bestj = blo;
    let bestsize = 0;
    let j2len = new Map();
    for (let i = alo; i < ahi; i += 1) {
      const newj2len = new Map();
      for (const j of b2j.get(a[i]) || []) {
        if (j < blo) continue;
        if (j >= bhi) break;
        const k = (j2len.get(j - 1) || 0) + 1;
        newj2len.set(j, k);
        if (k > bestsize) {
          besti = i - k + 1;
          bestj = j - k + 1;
          bestsize = k;
        }
      }
      j2len = newj2len;
    }
    // Mở rộng bằng phần tử không junk (gồm cả phần tử popular đã bị loại khỏi b2j).
    while (besti > alo && bestj > blo && a[besti - 1] === b[bestj - 1]) {
      besti -= 1;
      bestj -= 1;
      bestsize += 1;
    }
    while (besti + bestsize < ahi && bestj + bestsize < bhi && a[besti + bestsize] === b[bestj + bestsize]) {
      bestsize += 1;
    }
    // Không có junk (isjunk = None) nên bước "hút junk hai bên" của CPython không làm gì.
    return [besti, bestj, bestsize];
  }

  getMatchingBlocks() {
    if (this.matchingBlocks) return this.matchingBlocks;
    const la = this.a.length;
    const lb = this.b.length;
    const queue = [[0, la, 0, lb]];
    const blocks = [];
    while (queue.length) {
      const [alo, ahi, blo, bhi] = queue.pop();
      const [i, j, k] = this.findLongestMatch(alo, ahi, blo, bhi);
      if (k) {
        blocks.push([i, j, k]);
        if (alo < i && blo < j) queue.push([alo, i, blo, j]);
        if (i + k < ahi && j + k < bhi) queue.push([i + k, ahi, j + k, bhi]);
      }
    }
    blocks.sort((x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2]);
    let [i1, j1, k1] = [0, 0, 0];
    const nonAdjacent = [];
    for (const [i2, j2, k2] of blocks) {
      if (i1 + k1 === i2 && j1 + k1 === j2) {
        k1 += k2;
      } else {
        if (k1) nonAdjacent.push([i1, j1, k1]);
        [i1, j1, k1] = [i2, j2, k2];
      }
    }
    if (k1) nonAdjacent.push([i1, j1, k1]);
    nonAdjacent.push([la, lb, 0]);
    this.matchingBlocks = nonAdjacent;
    return nonAdjacent;
  }

  getOpcodes() {
    let i = 0;
    let j = 0;
    const answer = [];
    for (const [ai, bj, size] of this.getMatchingBlocks()) {
      let tag = "";
      if (i < ai && j < bj) tag = "replace";
      else if (i < ai) tag = "delete";
      else if (j < bj) tag = "insert";
      if (tag) answer.push([tag, i, ai, j, bj]);
      i = ai + size;
      j = bj + size;
      if (size) answer.push(["equal", ai, i, bj, j]);
    }
    return answer;
  }

  getGroupedOpcodes(n = 3) {
    let codes = this.getOpcodes();
    if (!codes.length) codes = [["equal", 0, 1, 0, 1]];
    if (codes[0][0] === "equal") {
      const [tag, i1, i2, j1, j2] = codes[0];
      codes[0] = [tag, Math.max(i1, i2 - n), i2, Math.max(j1, j2 - n), j2];
    }
    const last = codes.length - 1;
    if (codes[last][0] === "equal") {
      const [tag, i1, i2, j1, j2] = codes[last];
      codes[last] = [tag, i1, Math.min(i2, i1 + n), j1, Math.min(j2, j1 + n)];
    }
    const nn = n + n;
    const groups = [];
    let group = [];
    for (let [tag, i1, i2, j1, j2] of codes) {
      if (tag === "equal" && i2 - i1 > nn) {
        group.push([tag, i1, Math.min(i2, i1 + n), j1, Math.min(j2, j1 + n)]);
        groups.push(group);
        group = [];
        i1 = Math.max(i1, i2 - n);
        j1 = Math.max(j1, j2 - n);
      }
      group.push([tag, i1, i2, j1, j2]);
    }
    if (group.length && !(group.length === 1 && group[0][0] === "equal")) groups.push(group);
    return groups;
  }

  ratio() {
    const matches = this.getMatchingBlocks().reduce((sum, block) => sum + block[2], 0);
    const length = this.a.length + this.b.length;
    return length ? (2.0 * matches) / length : 1.0;
  }
}

function formatRangeUnified(start, stop) {
  let beginning = start + 1;
  const length = stop - start;
  if (length === 1) return `${beginning}`;
  if (!length) beginning -= 1;
  return `${beginning},${length}`;
}

/** difflib.unified_diff, trả mảng dòng. */
export function unifiedDiff(a, b, { fromfile = "", tofile = "", n = 3, lineterm = "\n" } = {}) {
  const out = [];
  let started = false;
  for (const group of new SequenceMatcher(a, b).getGroupedOpcodes(n)) {
    if (!started) {
      started = true;
      out.push(`--- ${fromfile}${lineterm}`, `+++ ${tofile}${lineterm}`);
    }
    const first = group[0];
    const last = group[group.length - 1];
    out.push(`@@ -${formatRangeUnified(first[1], last[2])} +${formatRangeUnified(first[3], last[4])} @@${lineterm}`);
    for (const [tag, i1, i2, j1, j2] of group) {
      if (tag === "equal") {
        for (const line of a.slice(i1, i2)) out.push(" " + line);
        continue;
      }
      if (tag === "replace" || tag === "delete") for (const line of a.slice(i1, i2)) out.push("-" + line);
      if (tag === "replace" || tag === "insert") for (const line of b.slice(j1, j2)) out.push("+" + line);
    }
  }
  return out;
}
