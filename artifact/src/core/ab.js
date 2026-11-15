// So sánh A/B mù hai cấu hình model trên cùng một input (ART-6.1).
// Hai cấu hình được chạy lần lượt; nhãn "A"/"B" gán ngẫu nhiên và chỉ được
// tiết lộ sau khi người viết chọn. Hàm thuần: việc chạy và lưu do tầng UI làm.
import { utcStamp } from "./run_record.js";

function defaultRandom() {
  const bytes = new Uint32Array(1);
  globalThis.crypto.getRandomValues(bytes);
  return bytes[0] / 2 ** 32;
}

/**
 * @param configs hai cấu hình: [{label, preset, models}, {label, preset, models}]
 * @param random  hàm trả số trong [0, 1) (inject để test)
 */
export function createAbSession({ mode, style, authorInput, configs, random = defaultRandom, now = new Date() }) {
  if (!Array.isArray(configs) || configs.length !== 2) throw new Error("A/B cần đúng hai cấu hình.");
  if (JSON.stringify(configs[0].models) === JSON.stringify(configs[1].models)) {
    throw new Error("Hai cấu hình giống hệt nhau; hãy chọn hai cấu hình khác nhau.");
  }
  const swap = random() < 0.5;
  return {
    schema: 1,
    id: utcStamp(now),
    created_at: now.toISOString(),
    mode,
    style,
    author_input: authorInput,
    configs: configs.map(({ label, preset, models }) => ({ label, preset, models })),
    // letters.A là chỉ số cấu hình mang nhãn A. Không hiển thị trước khi chọn.
    letters: { A: swap ? 1 : 0, B: swap ? 0 : 1 },
    run_ids: [null, null],
    status: "running",
    choice: null,
    note: "",
    decided_at: null,
  };
}

/**
 * Hai bài theo thứ tự hiển thị A, B, không kèm thông tin cấu hình.
 * @param drafts drafts[i] là {text, words} của cấu hình i
 */
export function blindDrafts(session, drafts) {
  return ["A", "B"].map((letter) => ({ letter, text: drafts[session.letters[letter]].text, words: drafts[session.letters[letter]].words }));
}

/** Ghi lựa chọn ("A", "B" hoặc "tie") và trả bảng tiết lộ nhãn ứng với cấu hình. */
export function decideAb(session, choice, note = "", now = new Date()) {
  if (!["A", "B", "tie"].includes(choice)) throw new Error(`Lựa chọn không hợp lệ: ${choice}`);
  if (session.status !== "ready") throw new Error("Chỉ chọn được khi đã có đủ hai bài.");
  session.choice = choice;
  session.chosen_config = choice === "tie" ? null : session.letters[choice];
  session.note = String(note || "").trim();
  session.decided_at = now.toISOString();
  session.status = "decided";
  return revealAb(session);
}

/** Bảng tiết lộ: mỗi nhãn ứng với cấu hình nào. Chỉ gọi sau khi đã chọn. */
export function revealAb(session) {
  if (session.status !== "decided") throw new Error("Chưa chọn nên chưa tiết lộ cấu hình.");
  return ["A", "B"].map((letter) => {
    const index = session.letters[letter];
    return { letter, index, label: session.configs[index].label, preset: session.configs[index].preset, run_id: session.run_ids[index], chosen: session.chosen_config === index };
  });
}
