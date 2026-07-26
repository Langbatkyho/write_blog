import sys
from pathlib import Path
import json
import uuid
import datetime as dt
import shutil
import os
import yaml
from html import escape
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.voice_lab.models import StyleProfile, VoiceDNA, EvidenceClaim
from engine.voice_lab.analyzer import analyze_samples
from engine.voice_lab.compiler import compile_style
from engine.voice_lab.interview import generate_interview, calibrate_ab, DIMENSION_VI
from engine.voice_lab.overrides import merge_overrides

from engine.style_manager import (
    list_styles,
    get_style_detail,
    save_style_file,
    create_style,
    rename_style,
    delete_style,
    validate_style_contract,
)
from engine.workflow import run_workflow
from engine.utils import resolve_path, read_text, write_text

try:
    from code_editor import code_editor
    HAS_CODE_EDITOR = True
except ImportError:
    HAS_CODE_EDITOR = False

st.set_page_config(
    page_title="Antigravity Mindful Writing OS",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load CSS
css_path = ROOT / "ui" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{read_text(css_path)}</style>", unsafe_allow_html=True)

# Session State Init
if "mode" not in st.session_state:
    st.session_state.mode = "deep"
if "selected_style_slug" not in st.session_state:
    st.session_state.selected_style_slug = "reflective"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

# Voice Lab Session State
if "vl_step" not in st.session_state:
    st.session_state.vl_step = 1
if "vl_samples" not in st.session_state:
    st.session_state.vl_samples = [""]
if "vl_dna" not in st.session_state:
    st.session_state.vl_dna = None
if "vl_claims" not in st.session_state:
    st.session_state.vl_claims = []
if "vl_interview" not in st.session_state:
    st.session_state.vl_interview = []
if "vl_answers" not in st.session_state:
    st.session_state.vl_answers = {}
if "vl_calibration" not in st.session_state:
    st.session_state.vl_calibration = {} # dim -> (variant_a, variant_b, selected)
if "vl_compiled_ir" not in st.session_state:
    st.session_state.vl_compiled_ir = {}
if "vl_style_name" not in st.session_state:
    st.session_state.vl_style_name = ""
if "vl_style_slug" not in st.session_state:
    st.session_state.vl_style_slug = ""
# Dialogs
@st.dialog("🏷️ Đổi tên Style")
def show_rename_dialog(mode: str, old_slug: str, old_name: str, is_protected: bool):
    st.markdown(f"Đang đổi tên cho style: **{old_name}** (`{old_slug}`)")
    new_name = st.text_input("Tên hiển thị mới", value=old_name)
    new_slug = st.text_input(
        "Slug hệ thống mới (a-z, 0-9, dấu gạch ngang)",
        value=old_slug,
        disabled=is_protected,
        help="Không thể đổi slug của System Style bảo vệ." if is_protected else "2-50 ký tự hợp lệ cho tên folder.",
    )
    if st.button("💾 Lưu Đổi Tên", type="primary"):
        success, msg = rename_style(mode, old_slug, new_name, new_slug)
        if success:
            st.success("✅ Đổi tên thành công!")
            if st.session_state.get("selected_style_slug") == old_slug:
                st.session_state.selected_style_slug = new_slug
            st.rerun()
        else:
            st.error(f"❌ {msg}")

@st.dialog("🗑️ Xác nhận xóa Style")
def show_delete_dialog(mode: str, slug: str, name: str):
    st.warning(f"Bạn có chắc chắn muốn xóa vĩnh viễn style **{name}** (`{slug}`) không? Hành động này không thể khôi phục!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Hủy bỏ"):
            st.rerun()
    with col2:
        if st.button("🗑️ Xóa Vĩnh Viễn", type="primary"):
            success, msg = delete_style(mode, slug)
            if success:
                st.success("✅ Đã xóa style thành công!")
                if st.session_state.get("selected_style_slug") == slug:
                    st.session_state.selected_style_slug = "reflective"
                st.rerun()
            else:
                st.error(f"❌ {msg}")

# Sidebar
with st.sidebar:
    st.markdown("### 🧭 Ngăn Lựa chọn Chế độ")
    mode_choice = st.radio(
        "Chọn chế độ viết (Writing Mode):",
        options=["deep", "moment"],
        format_func=lambda x: "🌊 Deep Blog Mode (7 Agents)" if x == "deep" else "⚡ Moment Blog Mode (6 Agents)",
        index=0 if st.session_state.mode == "deep" else 1,
        key="mode_radio",
    )
    if mode_choice != st.session_state.mode:
        st.session_state.mode = mode_choice
        st.session_state.selected_style_slug = "reflective"
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Thông tin Chế độ")
    if st.session_state.mode == "deep":
        st.info(
            "**Deep Blog Mode**: Biến ghi chép thô thành bài chia sẻ sâu sắc qua 7 Agent chuyên biệt (Architect, Writer, Reader, Editor, Coach, Future, Reflection)."
        )
    else:
        st.info(
            "**Moment Blog Mode**: Ghi lại khoảnh khắc sống động qua giác quan với 6 Agent (Sensory, Inner Weather, Cosmic Signal, Moment Writer, Breath Editor, Gentle Witness)."
        )
    st.markdown("---")
    st.caption("✨ Antigravity Mindful Writing OS v5.0 Final")

# Header
st.title("✍️ Antigravity Mindful Writing OS")
st.markdown(f"**Trung tâm Quản trị & Nâng cấp Văn phong đa dạng** — Chế độ hiện tại: `{st.session_state.mode.upper()}`")

# Tabs
tab_gallery, tab_studio, tab_editor, tab_workbench = st.tabs([
    "📚 Style Gallery",
    "🎨 Style Studio",
    "💻 YAML Code Editor",
    "🧪 Live Workbench",
])

mode = st.session_state.mode
styles = list_styles(mode)

# ==============================================================================
# TAB 1: STYLE GALLERY
# ==============================================================================
with tab_gallery:
    st.subheader(f"📚 Bộ sưu tập Văn phong — Mode {mode.upper()}")
    st.markdown("Khám phá, chỉnh sửa hoặc quản lý các phong cách viết có sẵn trong hệ thống.")

    if not styles:
        st.info("Chưa có style nào trong chế độ này.")
    else:
        cols = st.columns(2)
        for idx, s in enumerate(styles):
            with cols[idx % 2]:
                is_prot = s.get("is_protected", False)
                badge_class = "badge-protected" if is_prot else "badge-custom"
                badge_text = "🔒 SYSTEM STYLE" if is_prot else "✨ CUSTOM STYLE"
                desc = escape(s.get("description", "Không có mô tả."))
                updated_at = s.get("updated_at", "")[:10]

                st.markdown(
                    f"""
                    <div class="style-card">
                        <div class="style-card-title">
                            <span>{escape(s.get('name'))} <code style="font-size:0.8rem; color:#38bdf8;">({s.get('slug')})</code></span>
                            <span class="{badge_class}">{badge_text}</span>
                        </div>
                        <div class="style-card-desc">{desc}</div>
                        <div class="style-card-meta">
                            <span>📅 Cập nhật: {updated_at}</span>
                            <span>⚙️ Mode: {s.get('mode', mode)}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                btn_cols = st.columns([1.2, 1.2, 1])
                with btn_cols[0]:
                    if st.button("✏️ Sửa Editor", key=f"edit_{s['slug']}"):
                        st.session_state.selected_style_slug = s["slug"]
                        st.toast(f"Đã chọn '{s['name']}' vào YAML Editor!", icon="✏️")
                with btn_cols[1]:
                    if st.button("🏷️ Đổi tên", key=f"rename_{s['slug']}"):
                        show_rename_dialog(mode, s["slug"], s.get("name", s["slug"]), is_prot)
                with btn_cols[2]:
                    if st.button(
                        "🗑️ Xóa",
                        key=f"del_{s['slug']}",
                        disabled=is_prot,
                        help="Không thể xóa System Style." if is_prot else "Xóa custom style này.",
                    ):
                        show_delete_dialog(mode, s["slug"], s.get("name", s["slug"]))

# ==============================================================================
# TAB 2: STYLE STUDIO (VOICE LAB WIZARD)
# ==============================================================================
with tab_studio:
    st.subheader("🎨 Voice Lab Studio (5-Step Wizard)")
    st.markdown("Xây dựng phong cách viết tự động qua ngôn ngữ tự nhiên và cấu hình AI.")

    step = st.session_state.vl_step
    
    # Progress Bar
    cols = st.columns(5)
    steps_labels = ["1. Samples", "2. Evidence", "3. Interview", "4. Calibration", "5. Publish"]
    for i, col in enumerate(cols):
        with col:
            if i + 1 == step:
                st.markdown(f"**👉 {steps_labels[i]}**")
            elif i + 1 < step:
                st.markdown(f"✅ <del>{steps_labels[i]}</del>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:gray;'>{steps_labels[i]}</span>", unsafe_allow_html=True)

    st.markdown("---")

    if step == 1:
        st.markdown("### Bước 1: Nhập bài viết mẫu")
        for i in range(len(st.session_state.vl_samples)):
            st.session_state.vl_samples[i] = st.text_area(f"Mẫu {i+1}", value=st.session_state.vl_samples[i], height=150, key=f"sample_{i}")
        
        if st.button("➕ Thêm Mẫu", key="add_sample"):
            st.session_state.vl_samples.append("")
            st.rerun()
            
        if st.button("🔍 Phân tích Mẫu (Analyze)", type="primary"):
            valid_samples = [s for s in st.session_state.vl_samples if s.strip()]
            if not valid_samples:
                st.error("Vui lòng nhập ít nhất 1 mẫu bài viết.")
            else:
                with st.spinner("Đang phân tích Voice DNA..."):
                    dna, claims = analyze_samples(valid_samples)
                    st.session_state.vl_dna = dna
                    st.session_state.vl_claims = claims
                    st.session_state.vl_step = 2
                    st.rerun()

    elif step == 2:
        st.markdown("### Bước 2: Xem xét Bằng chứng (Evidence Review)")
        st.write("**Voice DNA Trích xuất:**")
        if st.session_state.vl_dna:
            st.json(st.session_state.vl_dna.model_dump())
            
        st.write("**Các Bằng chứng (Claims):**")
        for claim in st.session_state.vl_claims:
            st.info(f"**Dimension:** {claim.dimension}\n\n**Claim:** {claim.claim}\n\n**Quote:** '{claim.quote}'\n\n**Confidence:** {claim.confidence:.2f}")

        col1, col2 = st.columns(2)
        if col1.button("⬅️ Quay lại", key="back_1"):
            st.session_state.vl_step = 1
            st.rerun()
        if col2.button("➡️ Tiếp tục (Interview)", type="primary"):
            profile = StyleProfile(slug="temp", mode=mode, dna=st.session_state.vl_dna, evidence=st.session_state.vl_claims)
            interview_qs = generate_interview(profile)
            st.session_state.vl_interview = interview_qs
            # If no interview questions, skip to calibration
            if not interview_qs:
                dim = "tone"
                var_a, var_b = calibrate_ab(dim, profile)
                st.session_state.vl_calibration = {"dimension": dim, "variant_a": var_a, "variant_b": var_b, "selected": None, "profile": profile}
                st.session_state.vl_step = 4
            else:
                st.session_state.vl_step = 3
            st.rerun()

    elif step == 3:
        st.markdown("### Bước 3: Phỏng vấn Bổ sung (Guided Interview)")
        for q in st.session_state.vl_interview:
            st.write(f"**{q.dimension}**: {q.question}")
            st.caption(f"Bối cảnh phân tích: {q.context}")
            st.session_state.vl_answers[q.id] = st.text_input("Câu trả lời của bạn", key=f"ans_{q.id}", value=st.session_state.vl_answers.get(q.id, ""))

        col1, col2 = st.columns(2)
        if col1.button("⬅️ Quay lại", key="back_2"):
            st.session_state.vl_step = 2
            st.rerun()
        if col2.button("➡️ Tiếp tục (Calibration)", type="primary"):
            # Use profile created in previous step or reconstruct
            profile = StyleProfile(slug="temp", mode=mode, dna=st.session_state.vl_dna, evidence=st.session_state.vl_claims)
            dim = "tone"
            var_a, var_b = calibrate_ab(dim, profile)
            st.session_state.vl_calibration = {"dimension": dim, "variant_a": var_a, "variant_b": var_b, "selected": None, "profile": profile}
            st.session_state.vl_step = 4
            st.rerun()

    elif step == 4:
        st.markdown("### Bước 4: Hiệu chỉnh (A/B Calibration)")
        calib = st.session_state.vl_calibration
        dim = calib.get("dimension", "")
        dim_vi = DIMENSION_VI.get(dim, dim)
        st.write(f"Vui lòng chọn biến thể phù hợp nhất cho **{dim_vi}** (Kiểm tra mù / Blind test):")
        
        c1, c2 = st.columns(2)
        with c1:
            st.info(calib["variant_a"])
            if st.button("Chọn Bản A"):
                st.session_state.vl_calibration["selected"] = "A"
        with c2:
            st.info(calib["variant_b"])
            if st.button("Chọn Bản B"):
                st.session_state.vl_calibration["selected"] = "B"
                
        if st.session_state.vl_calibration.get("selected"):
            st.success(f"Đã chọn Bản {st.session_state.vl_calibration['selected']}.")
            if st.button("➡️ Chuyển sang Compile & Review", type="primary"):
                profile = st.session_state.vl_calibration.get("profile") or StyleProfile(slug="temp", mode=mode, dna=st.session_state.vl_dna, evidence=st.session_state.vl_claims)
                profile.is_draft = False
                ir_dict = compile_style(profile, mode=mode)
                st.session_state.vl_compiled_ir = ir_dict
                st.session_state.vl_profile = profile
                st.session_state.vl_step = 5
                st.rerun()
        
        if st.button("⬅️ Quay lại", key="back_3"):
            st.session_state.vl_step = 3 if st.session_state.vl_interview else 2
            st.rerun()

    elif step == 5:
        st.markdown("### Bước 5: Review & Publish")
        
        st.subheader("🧬 Voice DNA & Profile Tổng Hợp")
        if getattr(st.session_state, 'vl_profile', None):
            st.json(st.session_state.vl_profile.model_dump())
        
        # Quota Estimator
        st.subheader("💰 Quota Estimator")
        total_chars = sum(len(str(v)) for agent in st.session_state.vl_compiled_ir.values() for v in agent.values())
        min_tokens = total_chars // 5
        max_tokens = total_chars // 3
        st.info(f"Ước tính Tokens cho toàn bộ Prompt: **~{min_tokens} - {max_tokens} tokens**")
        
        # Layer Inspector
        with st.expander("🔍 Advanced: Layer Inspector (IR vs YAML)", expanded=False):
            agent_keys = list(st.session_state.vl_compiled_ir.keys())
            if agent_keys:
                inspect_agent = st.selectbox("Chọn Agent", agent_keys)
                ir_data = st.session_state.vl_compiled_ir[inspect_agent]
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Canonical IR (Dict)**")
                    st.json(ir_data)
                with col_b:
                    st.markdown("**Effective YAML**")
                    st.code(yaml.safe_dump(ir_data, allow_unicode=True, sort_keys=False), language="yaml")
                    
        st.subheader("🚀 Đăng tải Style (Publish)")
        st.session_state.vl_style_name = st.text_input("Tên Style", value=st.session_state.vl_style_name)
        st.session_state.vl_style_slug = st.text_input("Slug Style", value=st.session_state.vl_style_slug)
        
        if st.button("🚀 Publish (Safety Pipeline)"):
            if not st.session_state.vl_style_name or not st.session_state.vl_style_slug:
                st.error("Vui lòng điền tên và slug.")
            else:
                slug = st.session_state.vl_style_slug
                try:
                    with st.spinner("Executing 4-Step Publish Pipeline..."):
                        # 1. Staging
                        staging_dir = resolve_path(f"skills/{mode}/{slug}.staging")
                        if staging_dir.exists():
                            shutil.rmtree(staging_dir)
                        staging_dir.mkdir(parents=True, exist_ok=True)
                        
                        # compiled_ir keys are now filenames (e.g. 'story_architect.yaml')
                        for filename, ir_data in st.session_state.vl_compiled_ir.items():
                            file_path = staging_dir / filename
                            # Write only the style_rules and prompt into the skill yaml
                            skill_content = {
                                "prompt": ir_data.get("prompt", ""),
                                "style_rules": ir_data.get("style_rules", []),
                                "output_contract": ir_data.get("output_contract", ""),
                                "handoff_contract": ir_data.get("handoff_contract", ""),
                                "context_policy": ir_data.get("context_policy", ""),
                                "voice_lab_generated": True,
                            }
                            write_text(file_path, yaml.safe_dump(skill_content, allow_unicode=True, sort_keys=False))
                            
                        meta = {
                            "name": st.session_state.vl_style_name,
                            "slug": slug,
                            "mode": mode,
                            "is_protected": False,
                            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()
                        }
                        write_text(staging_dir / "style_meta.yaml", yaml.safe_dump(meta, allow_unicode=True, sort_keys=False))

                        # 2. Validate — pass workflow_path directly so validator checks staging dir
                        flow_name = "write_moment_blog.yaml" if mode == "moment" else "write_blog.yaml"
                        workflow_path = resolve_path(f"flow/{flow_name}")
                        import yaml as _yaml
                        from pathlib import Path as _Path
                        if workflow_path.exists():
                            wf = _yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
                            missing = []
                            for step in wf.get("steps", []):
                                skill_filename = _Path(step["skill"]).name
                                if not (staging_dir / skill_filename).exists():
                                    missing.append(skill_filename)
                            if missing:
                                raise ValueError(f"Staging thiếu file skill bắt buộc: {missing}")
                        
                        runtime_dir = resolve_path(f"skills/{mode}/{slug}")
                        
                        # 3. Backup
                        backup_dir = resolve_path("profile_history")
                        backup_dir.mkdir(exist_ok=True)
                        if runtime_dir.exists():
                            backup_path = backup_dir / f"{slug}_{int(dt.datetime.now().timestamp())}.zip"
                            shutil.make_archive(str(backup_path).replace('.zip', ''), 'zip', str(runtime_dir))
                            
                        # 4. Atomic Replace (Tombstone pattern)
                        if runtime_dir.exists():
                            tombstone = runtime_dir.with_suffix('.old')
                            if tombstone.exists():
                                shutil.rmtree(tombstone)
                            os.rename(str(runtime_dir), str(tombstone))
                        os.rename(str(staging_dir), str(runtime_dir))
                        if 'tombstone' in locals() and tombstone.exists():
                            shutil.rmtree(tombstone)
                        
                    st.success(f"✅ Publish Pipeline Hoàn tất! Style '{st.session_state.vl_style_name}' đã sẵn sàng.")
                    # Reset wizard
                    st.session_state.vl_step = 1
                    st.session_state.selected_style_slug = slug
                    st.rerun()
                except Exception as e:
                    # Rollback
                    if 'tombstone' in locals() and tombstone.exists():
                        os.rename(str(tombstone), str(runtime_dir))
                    if 'staging_dir' in locals() and staging_dir.exists():
                        shutil.rmtree(staging_dir)
                    st.error(f"❌ Publish thất bại, đã Rollback. Lỗi: {str(e)}")

        if st.button("⬅️ Quay lại", key="back_4"):
            st.session_state.vl_step = 4
            st.rerun()

# ==============================================================================
# TAB 3: YAML CODE EDITOR
# ==============================================================================
with tab_editor:
    st.subheader("💻 Trình soạn thảo cấu hình Agent YAML")
    st.markdown("Chỉnh sửa trực tiếp lời nhắc hệ thống (prompts, supreme rules, guardrails) của từng Agent trong Style.")

    if not styles:
        st.warning("Không có style nào để chỉnh sửa.")
    else:
        avail_slugs = [s["slug"] for s in styles]
        curr_slug = st.session_state.get("selected_style_slug", "reflective")
        if curr_slug not in avail_slugs:
            curr_slug = avail_slugs[0]

        sel_col1, sel_col2 = st.columns([1, 2])
        with sel_col1:
            selected_slug = st.selectbox(
                "Chọn Style để chỉnh sửa:",
                options=avail_slugs,
                index=avail_slugs.index(curr_slug),
                key="editor_style_select",
            )
            st.session_state.selected_style_slug = selected_slug

        try:
            detail = get_style_detail(mode, selected_slug)
            files = detail.get("files", [])
            all_files = ["style_meta.yaml"] + files if "style_meta.yaml" not in files else files

            with sel_col2:
                selected_file = st.selectbox("Chọn file YAML:", options=all_files, key="editor_file_select")

            file_path = Path(detail["directory"]) / selected_file
            if file_path.exists():
                content = read_text(file_path)
            else:
                content = "# File not found"

            st.markdown(f"**Đang chỉnh sửa**: `skills/{mode}/{selected_slug}/{selected_file}`")

            # Code Editor Display
            if HAS_CODE_EDITOR:
                response_dict = code_editor(
                    content,
                    lang="yaml",
                    theme="cobalt",
                    height=[15, 30],
                    buttons=[
                        {
                            "name": "Save File",
                            "feather": "Save",
                            "primary": True,
                            "hasText": True,
                            "showWithIcon": True,
                            "commands": ["save-state"],
                        }
                    ],
                    key=f"ce_{selected_slug}_{selected_file}",
                )
                edited_content = response_dict.get("text", content)
                # Check if save button inside code_editor was clicked
                if response_dict.get("type") == "submit" and len(response_dict.get("text", "")) > 0:
                    succ, err, warn = save_style_file(mode, selected_slug, selected_file, edited_content)
                    if not succ:
                        st.error(f"❌ Lỗi Kiểm duyệt (Hard Check): {err}")
                    else:
                        if warn:
                            st.warning(f"⚠️ {warn}")
                        st.success(f"✅ Đã lưu file `{selected_file}` thành công!")
            else:
                edited_content = st.text_area("Nội dung file YAML (Monospace Fallback)", value=content, height=450)

            # Explicit Save Button (works for both editor and text_area fallback)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Lưu thay đổi vào File (Atomic Write + Validate)", type="primary"):
                succ, err, warn = save_style_file(mode, selected_slug, selected_file, edited_content)
                if not succ:
                    st.error(f"❌ Lỗi Kiểm duyệt Schema (Hard Check): {err}")
                else:
                    if warn:
                        st.warning(f"⚠️ {warn}")
                    st.success(f"✅ Đã lưu thay đổi vào file `{selected_file}` atomic thành công!")

        except Exception as e:
            st.error(f"Không thể tải style details: {str(e)}")

# ==============================================================================
# TAB 4: LIVE WORKBENCH (DRY-RUN CONTRACT TEST V1)
# ==============================================================================
with tab_workbench:
    st.subheader("🧪 Bàn Kiểm chứng Hợp đồng Định tuyến (Dry-Run Test V1)")
    st.markdown(
        "Chạy kiểm chứng định tuyến I/O mà **không tốn API quota**. Hệ thống sẽ kiểm tra xem style có đủ 100% file skill theo hợp đồng Flow và mô phỏng luồng chuyển giao dữ liệu chỉ trong 1-2 giây."
    )

    wb_c1, wb_c2 = st.columns(2)
    with wb_c1:
        wb_style = st.selectbox(
            "Chọn Style kiểm chứng:",
            options=[s["slug"] for s in styles],
            index=0,
            key="wb_style_select",
        )
    with wb_c2:
        default_sample = "examples/moment_blog_input_template.md" if mode == "moment" else "examples/blog_input_template.md"
        input_choice = st.radio("Nguồn văn bản nháp đầu vào:", options=["Mẫu chuẩn (template)", "Dán văn bản tùy chỉnh"], horizontal=True)

    if input_choice == "Dán văn bản tùy chỉnh":
        custom_input = st.text_area("Dán nội dung nháp vào đây:", value="Hôm nay trời mưa nhẹ bên khung cửa sổ quán cà phê quen thuộc...", height=120)

    if st.button("⚡ Chạy Kiểm chứng Dry-Run ngay", type="primary"):
        with st.spinner("Đang kiểm duyệt hợp đồng Flow và định tuyến mô phỏng..."):
            try:
                # Validate contract explicitly first
                validate_style_contract(mode, wb_style)

                # Prepare input
                if input_choice == "Dán văn bản tùy chỉnh":
                    tmp_in = ROOT / "runs" / "temp_dry_run_input.md"
                    tmp_in.parent.mkdir(parents=True, exist_ok=True)
                    write_text(tmp_in, custom_input)
                    input_file = tmp_in
                else:
                    input_file = resolve_path(default_sample)

                config_file = resolve_path("engine/config.example.yaml")
                run_dir = run_workflow(
                    config_path=config_file,
                    input_path=input_file,
                    dry_run=True,
                    style=wb_style,
                    mode=mode,
                )

                st.success(f"✅ Kiểm chứng hợp đồng thành công! Style `{wb_style}` hoàn toàn hợp lệ và định tuyến mượt mà.")

                # Show preview of run results
                meta_file = run_dir / "metadata.json"
                if meta_file.exists():
                    st.markdown("#### 📊 Run Metadata")
                    st.json(json.loads(read_text(meta_file)))

                st.markdown("#### 📑 Mô phỏng Kết quả Đầu ra (Dry-Run Artifacts)")
                out_files = [f.name for f in sorted(run_dir.iterdir()) if f.is_file() and f.name != "metadata.json"]
                out_tabs = st.tabs(out_files)
                for i, fname in enumerate(out_files):
                    with out_tabs[i]:
                        st.code(read_text(run_dir / fname), language="markdown" if fname.endswith(".md") else "text")

            except Exception as exc:
                st.error(f"❌ Kiểm chứng Hợp đồng Thất bại: {str(exc)}")
