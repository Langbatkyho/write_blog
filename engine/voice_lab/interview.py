from typing import List, Tuple
from engine.voice_lab.models import StyleProfile, InterviewQuestion
from engine.gemini_client import call_gemini
import random
import uuid
import json

DIMENSION_VI = {
    "tone": "Giọng điệu (Tone)",
    "vocabulary": "Từ vựng (Vocabulary)",
    "sentence_structure": "Cấu trúc câu (Sentence Structure)",
    "rhythm": "Nhịp điệu (Rhythm)",
    "formatting": "Định dạng (Formatting)",
    "humor": "Sự hài hước (Humor)",
    "sensory_density": "Mật độ giác quan (Sensory Density)",
    "emoji": "Biểu tượng cảm xúc (Emoji)",
    "metaphor_density": "Mật độ ẩn dụ (Metaphor Density)",
    "emotional_depth": "Chiều sâu cảm xúc (Emotional Depth)",
    "pacing": "Nhịp độ (Pacing)",
    "perspective": "Góc nhìn / Ngôi kể (Perspective)"
}

def generate_interview(profile: StyleProfile) -> List[InterviewQuestion]:
    """
    Generates guided interview questions for dimensions with low confidence or missing DNA.
    Always generates at least a few questions to let user refine their profile.
    """
    questions = []
    if not profile.dna:
        return questions
        
    dimensions = [
        "tone", "vocabulary", "sentence_structure", "rhythm", "formatting",
        "humor", "sensory_density", "emoji", "metaphor_density", 
        "emotional_depth", "pacing", "perspective"
    ]
    
    # Build a set of dimensions that already have strong evidence
    strong_dims = set()
    for ev in profile.evidence:
        if ev.confidence >= 0.8:
            strong_dims.add(ev.dimension)
    
    for dim in dimensions:
        val = getattr(profile.dna, dim, "")
        # Ask a question if:
        #  - dimension value is empty or short, OR
        #  - dimension has no strong evidence claim backing it
        if not val or len(val) < 15 or dim not in strong_dims:
            dim_vi = DIMENSION_VI.get(dim, dim)
            questions.append(
                InterviewQuestion(
                    id=str(uuid.uuid4()),
                    dimension=dim_vi,
                    question=f"Bạn có thể mô tả chi tiết hơn về {dim_vi.lower()} mà bạn mong muốn trong bài viết không? Ví dụ cụ thể hoặc sở thích xưng hô sẽ rất hữu ích.",
                    context=f"Hệ thống đã phân tích sơ bộ {dim_vi.lower()} là: '{val if val else 'Chưa có thông tin rõ ràng'}'. Cần thêm sự xác nhận từ bạn để làm sắc nét phong cách."
                )
            )
            
    return questions

def calibrate_ab(dimension: str, profile: StyleProfile) -> Tuple[str, str]:
    """
    Generates two contrasting variants (A and B) for a specific dimension to calibrate the profile.
    Uses LLM to generate contextual text in Vietnamese.
    """
    dna_desc = getattr(profile.dna, dimension, "") if profile.dna else ""
    dim_vi = DIMENSION_VI.get(dimension, dimension)
    
    prompt = f"""
You are an expert writing assistant. We are calibrating a user's writing style for the dimension: '{dimension}' ({dim_vi}).
The user's current DNA for this dimension is described as: "{dna_desc}".

QUAN TRỌNG: Bạn PHẢI viết cả 2 đoạn văn mẫu (Variant 1 và Variant 2) hoàn toàn bằng TIẾNG VIỆT tự nhiên, trôi chảy, giàu cảm xúc. Không sử dụng tiếng Anh.
Please write TWO short paragraphs in VIETNAMESE (about 100-150 words each) on a neutral mindful topic (e.g., "Ý nghĩa của sự tĩnh lặng trong cuộc sống hiện đại" or "Lợi ích của việc sống chánh niệm mỗi ngày").
Variant 1 MUST strongly emphasize and exaggerate the trait described in the DNA ("{dna_desc}").
Variant 2 MUST deliberately tone down or contrast the trait to provide a clear, calm alternative.

Output ONLY valid raw JSON with two keys: "variant_1" and "variant_2". Do NOT wrap in markdown like ```json.
{{
  "variant_1": "...",
  "variant_2": "..."
}}
"""
    try:
        response = call_gemini(prompt, stage_id="voice_lab_calibrate")
        
        response = response.strip()
        if response.startswith("```json"): response = response[7:]
        elif response.startswith("```"): response = response[3:]
        if response.endswith("```"): response = response[:-3]
        
        data = json.loads(response.strip())
        variant_1 = data.get("variant_1", f"[Bản A - Đậm chất {dim_vi}]\n\nTrong quá trình viết chánh niệm, yếu tố {dim_vi.lower()} đóng vai trò như một mỏ neo cảm xúc. Khi ta dồn tâm sức để làm nổi bật nét văn phong này, từng câu chữ sẽ bừng lên sức sống mãnh liệt và chạm sâu vào tâm khảm người đọc.")
        variant_2 = data.get("variant_2", f"[Bản B - Tiết chế {dim_vi}]\n\nViết chánh niệm không nhất thiết phải phô diễn hay nhấn mạnh quá mức vào kỹ thuật. Bằng cách tiết chế nhẹ nhàng {dim_vi.lower()}, ta tạo ra một không gian văn bản tĩnh lặng, thảnh thơi, nhường chỗ cho thông điệp tự nhiên được cất tiếng.")
    except Exception as e:
        print(f"LLM generation failed for calibration: {e}")
        # Fallback to stub in Vietnamese
        variant_1 = (
            f"[Bản A - Đậm chất {dim_vi}]\n\n"
            f"Trong quá trình viết chánh niệm, yếu tố {dim_vi.lower()} đóng vai trò như một mỏ neo cảm xúc. "
            f"Khi ta dồn tâm sức để làm nổi bật nét văn phong này, từng câu chữ sẽ bừng lên sức sống mãnh liệt và chạm sâu vào tâm khảm người đọc."
        )
        variant_2 = (
            f"[Bản B - Tiết chế {dim_vi}]\n\n"
            f"Viết chánh niệm không nhất thiết phải phô diễn hay nhấn mạnh quá mức vào kỹ thuật. Bằng cách tiết chế nhẹ nhàng {dim_vi.lower()}, "
            f"ta tạo ra một không gian văn bản tĩnh lặng, thảnh thơi, nhường chỗ cho thông điệp tự nhiên được cất tiếng."
        )
    
    variants = [variant_1, variant_2]
    # Randomize to ensure blind selection
    random.shuffle(variants)
    
    return variants[0], variants[1]
