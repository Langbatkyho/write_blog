// Lưu lịch sử run vào capability `db` của Artifact. `db` được truyền vào (DI),
// nên module này không chạm window.claude và test được bằng db giả.
//
// Đường dẫn (theo quy tắc chẵn/lẻ phân đoạn của db):
//   data/users/<uid>/blog                       document của tác giả
//   data/users/<uid>/blog/runs/<runId>          một lần chạy
//   data/users/<uid>/blog/runs/<runId>/stages/<stageId>
//   data/users/<uid>/blog/runs/<runId>/production/current     bản cuối của người viết
//   data/users/<uid>/blog/runs/<runId>/learning/<learningId>  một vòng học
// Vùng data/users/<uid>/ là riêng tư với từng người xem, kể cả với chủ Artifact.
import { newRunId, serializeRunDoc, serializeStageDoc } from "./run_record.js";

export const MAX_DOC_BYTES = 256 * 1024;

export class RepositoryError extends Error {
  constructor(message, code = null) {
    super(message);
    this.name = "RepositoryError";
    this.code = code;
  }
}

function checkSize(what, doc) {
  const bytes = new TextEncoder().encode(JSON.stringify(doc)).length;
  if (bytes > MAX_DOC_BYTES) throw new RepositoryError(`${what} quá lớn để lưu (${bytes} byte > 256 KiB).`, "too_large");
}

/**
 * @param db      namespace `db` (claude.use("db")) hoặc db giả
 * @param userId  kết quả `await user.id()`; null nghĩa là không có vùng riêng
 */
export function createRunRepository({ db, userId, randomHex, clock = () => new Date() }) {
  if (!db || !userId) throw new RepositoryError("Không có vùng lưu trữ riêng cho tài khoản này.");
  const runs = db.doc(`data/users/${userId}/blog`).collection("runs");
  // Mọi lệnh ghi đi qua một hàng đợi: không bao giờ có hai lệnh ghi chồng nhau.
  let queue = Promise.resolve();
  const enqueue = (task) => {
    const next = queue.then(task, task);
    queue = next.catch(() => {});
    return next;
  };

  return {
    /** Tạo document cho run mới với Run ID chưa tồn tại; gán run.id. */
    createRun(run, extras = {}) {
      return enqueue(async () => {
        for (let attempt = 0; attempt < 5; attempt += 1) {
          const id = newRunId({ mode: run.mode, style: run.style, now: clock(), randomHex });
          const ref = runs.doc(id);
          if ((await ref.get()).exists) continue;
          run.id = id;
          const doc = serializeRunDoc(run, { ...extras, now: clock() });
          checkSize("Lần chạy", doc);
          await ref.set(doc);
          run.persisted = true;
          return id;
        }
        throw new RepositoryError("Không tạo được Run ID duy nhất sau 5 lần thử.", "id_collision");
      });
    },

    /** Lưu kết quả một stage rồi cập nhật document của run (checkpoint). */
    saveStage(run, stageId, extras = {}) {
      return enqueue(async () => {
        const result = run.results[stageId];
        if (!run.id || !result) throw new RepositoryError("Run chưa được tạo hoặc stage chưa có kết quả.");
        const stageDoc = serializeStageDoc(result);
        checkSize(`Bước ${stageId}`, stageDoc);
        await runs.doc(run.id).collection("stages").doc(stageId).set(stageDoc);
        await runs.doc(run.id).set(serializeRunDoc(run, { ...extras, now: clock() }));
      });
    },

    /** Cập nhật riêng document của run (ví dụ sau khi xóa các bước để chạy lại). */
    saveRun(run, extras = {}) {
      return enqueue(() => runs.doc(run.id).set(serializeRunDoc(run, { ...extras, now: clock() })));
    },

    /** Xóa document của các stage từ `index` trở đi, trước khi chạy lại. */
    deleteStagesFrom(run, index) {
      return enqueue(async () => {
        for (const id of run.stageIds.slice(index)) {
          await runs.doc(run.id).collection("stages").doc(id).delete();
        }
      });
    },

    /** Lưu bản cuối (production) của người viết cho run. */
    saveProduction(run, text) {
      return enqueue(async () => {
        const doc = { schema: 1, text, updated_at: clock().toISOString() };
        checkSize("Bản cuối", doc);
        await runs.doc(run.id).collection("production").doc("current").set(doc);
      });
    },

    /** Bản cuối đã lưu của run, hoặc null. */
    async loadProduction(runId) {
      const snapshot = await runs.doc(runId).collection("production").doc("current").get();
      return snapshot.exists ? snapshot.data().text : null;
    },

    /** Lưu kết quả một vòng học (báo cáo, gợi ý, telemetry). */
    saveLearning(run, session) {
      return enqueue(async () => {
        const doc = { schema: 1, ...session };
        checkSize("Kết quả học", doc);
        await runs.doc(run.id).collection("learning").doc(session.id).set(doc);
      });
    },

    /** Các vòng học của run, mới nhất trước. */
    async listLearning(runId, limit = 20) {
      const snapshot = await runs.doc(runId).collection("learning").orderBy("created_at", "desc").limit(limit).get();
      return snapshot.docs.map((doc) => {
        const { schema, ...session } = doc.data();
        return session;
      });
    },

    /** Các lần chạy gần nhất, mới nhất trước. */
    async listRuns(limit = 50) {
      const snapshot = await runs.orderBy("created_at", "desc").limit(limit).get();
      return snapshot.docs.map((doc) => doc.data());
    },

    /** {runDoc, stageDocs} của một lần chạy, hoặc null nếu không có. */
    async loadRun(id) {
      const snapshot = await runs.doc(id).get();
      if (!snapshot.exists) return null;
      const stages = await runs.doc(id).collection("stages").get();
      return { runDoc: snapshot.data(), stageDocs: stages.docs.map((doc) => doc.data()) };
    },
  };
}
