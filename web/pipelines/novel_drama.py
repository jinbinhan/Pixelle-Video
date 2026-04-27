# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Novel Drama Pipeline UI.

Phase 1 MVP: input a novel excerpt and generate a reviewable script package.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from loguru import logger

from pixelle_video.models.novel_drama import NovelDramaPackage
from web.i18n import get_language, tr
from web.pipelines.base import PipelineUI, register_pipeline_ui
from web.utils.async_helpers import run_async


class NovelDramaPipelineUI(PipelineUI):
    """UI for the novel-to-short-drama script package MVP."""

    name = "novel_drama"
    icon = "Novel"

    @property
    def display_name(self):
        return tr("pipeline.novel_drama.name", fallback="Novel Drama")

    @property
    def description(self):
        return tr(
            "pipeline.novel_drama.description",
            fallback="Adapt a novel excerpt into a reviewable short-drama script package.",
        )

    def render(self, pixelle_video: Any):
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.markdown(f"**{tr('novel_drama.input.title', fallback='Novel Input')}**")
            st.info(
                tr(
                    "novel_drama.mvp_hint",
                    fallback="Phase 1 only generates a script package. It does not call ComfyUI yet.",
                )
            )

            novel_text = st.text_area(
                tr("novel_drama.input.text", fallback="Novel excerpt"),
                height=360,
                placeholder=tr(
                    "novel_drama.input.placeholder",
                    fallback="Paste 1000-3000 characters from a novel chapter...",
                ),
                key="novel_drama_text",
            )

            param_col1, param_col2 = st.columns(2)
            with param_col1:
                target_duration_seconds = st.slider(
                    tr("novel_drama.duration", fallback="Target duration"),
                    min_value=30,
                    max_value=120,
                    value=60,
                    step=15,
                    key="novel_drama_duration",
                )
                episode_number = st.number_input(
                    tr("novel_drama.episode", fallback="Episode"),
                    min_value=1,
                    value=1,
                    step=1,
                    key="novel_drama_episode",
                )
            with param_col2:
                target_shots = st.slider(
                    tr("novel_drama.shots", fallback="Target shots"),
                    min_value=4,
                    max_value=16,
                    value=8,
                    step=1,
                    key="novel_drama_shots",
                )
                current_language = get_language()
                default_language = "zh-CN" if current_language == "zh_CN" else "en-US"
                language = st.selectbox(
                    tr("novel_drama.language", fallback="Output language"),
                    ["zh-CN", "en-US"],
                    index=0 if default_language == "zh-CN" else 1,
                    key="novel_drama_language",
                )

            adaptation_style = st.text_input(
                tr("novel_drama.style", fallback="Adaptation style"),
                value=tr(
                    "novel_drama.style.default",
                    fallback="vertical short drama with strong hook, emotional conflict, and cliffhanger",
                ),
                key="novel_drama_style",
            )

            audience = st.text_input(
                tr("novel_drama.audience", fallback="Audience"),
                value=tr("novel_drama.audience.default", fallback="short-video viewers"),
                key="novel_drama_audience",
            )

            generate_clicked = st.button(
                tr("novel_drama.generate", fallback="Generate script package"),
                type="primary",
                use_container_width=True,
                key="novel_drama_generate",
            )

        with right_col:
            st.markdown(f"**{tr('novel_drama.output.title', fallback='Script Package')}**")

            if generate_clicked:
                if not novel_text.strip():
                    st.warning(tr("novel_drama.empty_warning", fallback="Please paste a novel excerpt first."))
                    return

                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(event):
                    progress_bar.progress(min(max(event.progress, 0.0), 1.0))
                    status_text.text(tr(event.event_type, fallback=event.event_type))

                try:
                    with st.spinner(tr("novel_drama.generating", fallback="Generating script package...")):
                        package = run_async(
                            pixelle_video.pipelines["novel_drama"](
                                novel_text,
                                progress_callback=progress_callback,
                                target_duration_seconds=target_duration_seconds,
                                target_shots=target_shots,
                                language=language,
                                adaptation_style=adaptation_style,
                                audience=audience,
                                episode_number=int(episode_number),
                            )
                        )

                    package_data = package.model_dump(mode="json")
                    st.session_state["novel_drama_package"] = package_data
                    st.session_state["novel_drama_package_original"] = package_data
                    st.session_state["novel_drama_json_editor"] = self._format_package_json(package_data)
                    progress_bar.progress(1.0)
                    status_text.text(tr("novel_drama.complete", fallback="Script package generated."))
                    st.success(tr("novel_drama.success", fallback="Script package generated successfully."))

                except Exception as e:
                    logger.exception(e)
                    progress_bar.empty()
                    status_text.empty()
                    st.error(tr("status.error", fallback="Error: {error}", error=str(e)))

            package_data = st.session_state.get("novel_drama_package")
            if not package_data:
                st.caption(
                    tr(
                        "novel_drama.output.empty",
                        fallback="Generate a package to review characters, scenes, shots, dialogue, and visual prompts.",
                    )
                )
                return

            package_data = self._render_review_tools(package_data)
            self._render_shot_video_tools(pixelle_video, package_data)
            self._render_shot_image_tools(pixelle_video, package_data)
            self._render_package(package_data)

    def _render_review_tools(self, package_data: dict) -> dict:
        """Render JSON editing, validation, and local draft save controls."""

        if st.session_state.pop("novel_drama_reset_editor_requested", False):
            original_package = st.session_state.get("novel_drama_package_original", package_data)
            st.session_state["novel_drama_json_editor"] = self._format_package_json(original_package)
        elif "novel_drama_json_editor" not in st.session_state:
            st.session_state["novel_drama_json_editor"] = self._format_package_json(package_data)

        with st.expander(tr("novel_drama.section.review_editor", fallback="Review / Edit JSON"), expanded=False):
            st.caption(
                tr(
                    "novel_drama.review_hint",
                    fallback="Edit the script package JSON, then apply it. The structure will be validated before use.",
                )
            )
            editor_text = st.text_area(
                tr("novel_drama.editor.label", fallback="Editable script package JSON"),
                height=360,
                key="novel_drama_json_editor",
            )

            action_col1, action_col2, action_col3 = st.columns(3)

            with action_col1:
                if st.button(
                    tr("novel_drama.editor.apply", fallback="Apply edits"),
                    use_container_width=True,
                    key="novel_drama_apply_edits",
                ):
                    try:
                        validated_data = self._validate_package_json(editor_text)
                        st.session_state["novel_drama_package"] = validated_data
                        st.success(tr("novel_drama.editor.apply_success", fallback="Edits applied."))
                    except Exception as e:
                        st.error(tr("novel_drama.editor.apply_failed", fallback="Invalid JSON: {error}", error=str(e)))

            with action_col2:
                if st.button(
                    tr("novel_drama.editor.reset", fallback="Reset to generated"),
                    use_container_width=True,
                    key="novel_drama_reset_edits",
                ):
                    original_package = st.session_state.get("novel_drama_package_original", package_data)
                    st.session_state["novel_drama_package"] = original_package
                    st.session_state["novel_drama_reset_editor_requested"] = True
                    st.info(tr("novel_drama.editor.reset_success", fallback="Restored generated package."))
                    st.rerun()

            with action_col3:
                if st.button(
                    tr("novel_drama.editor.save_draft", fallback="Save draft"),
                    use_container_width=True,
                    key="novel_drama_save_draft",
                ):
                    try:
                        validated_data = self._validate_package_json(editor_text)
                        st.session_state["novel_drama_package"] = validated_data
                        draft_path = self._save_package_draft(validated_data)
                        st.success(
                            tr(
                                "novel_drama.editor.save_success",
                                fallback="Draft saved: {path}",
                                path=str(draft_path),
                            )
                        )
                    except Exception as e:
                        st.error(tr("novel_drama.editor.save_failed", fallback="Save failed: {error}", error=str(e)))

        return st.session_state.get("novel_drama_package", package_data)

    def _render_shot_video_tools(self, pixelle_video: Any, package_data: dict):
        """Render one-shot LTX video generation controls for the reviewed package."""

        shots = package_data.get("shots", [])
        if not shots:
            return

        if "novel_drama_shot_videos" not in st.session_state:
            st.session_state["novel_drama_shot_videos"] = {}

        with st.expander(tr("novel_drama.section.shot_video", fallback="Single Shot Video"), expanded=True):
            st.caption(
                tr(
                    "novel_drama.shot_video.hint",
                    fallback="Main path: generate one LTX 2.3 text-to-video clip from a reviewed shot prompt.",
                )
            )

            shot_options = [shot.get("shot_id", f"shot_{index + 1}") for index, shot in enumerate(shots)]
            shot_labels = {
                shot.get("shot_id", f"shot_{index + 1}"): (
                    f"{shot.get('order', index + 1)}. {shot.get('shot_id', '')} - "
                    f"{shot.get('shot_type', '')} - {shot.get('dialogue_or_narration', '')[:28]}"
                )
                for index, shot in enumerate(shots)
            }
            selected_shot_id = st.selectbox(
                tr("novel_drama.shot_video.select_shot", fallback="Select shot"),
                shot_options,
                format_func=lambda shot_id: shot_labels.get(shot_id, shot_id),
                key="novel_drama_video_selected_shot",
            )
            selected_shot = next(shot for shot in shots if shot.get("shot_id") == selected_shot_id)

            workflow_options = self._get_video_workflow_options(pixelle_video)
            workflow_choice = st.selectbox(
                tr("novel_drama.shot_video.workflow", fallback="Video workflow"),
                workflow_options,
                format_func=lambda value: tr("novel_drama.shot_video.default_workflow", fallback="Configured default") if value is None else value,
                key="novel_drama_video_workflow",
            )

            size_col1, size_col2, size_col3 = st.columns(3)
            with size_col1:
                width = st.number_input(
                    tr("novel_drama.shot_video.width", fallback="Width"),
                    min_value=512,
                    max_value=1280,
                    value=960,
                    step=32,
                    key="novel_drama_video_width",
                )
            with size_col2:
                height = st.number_input(
                    tr("novel_drama.shot_video.height", fallback="Height"),
                    min_value=320,
                    max_value=1024,
                    value=544,
                    step=32,
                    key="novel_drama_video_height",
                )
            with size_col3:
                duration_seconds = st.slider(
                    tr("novel_drama.shot_video.duration", fallback="Duration"),
                    min_value=3.0,
                    max_value=8.0,
                    value=min(max(float(selected_shot.get("duration_seconds", 5)), 3.0), 8.0),
                    step=0.5,
                    key="novel_drama_video_duration",
                )

            prompt_override = st.text_area(
                tr("novel_drama.shot_video.prompt", fallback="Shot video prompt"),
                value=selected_shot.get("visual_prompt_en", ""),
                height=120,
                key=f"novel_drama_video_prompt_{selected_shot_id}",
            )

            generate_video_clicked = st.button(
                tr("novel_drama.shot_video.generate", fallback="Generate selected shot video"),
                type="primary",
                use_container_width=True,
                key="novel_drama_generate_shot_video",
            )

            if generate_video_clicked:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(event):
                    progress_bar.progress(min(max(event.progress, 0.0), 1.0))
                    status_text.text(tr(event.event_type, fallback=event.event_type))

                try:
                    with st.spinner(tr("novel_drama.shot_video.generating", fallback="Generating shot video...")):
                        result = run_async(
                            pixelle_video.pipelines["novel_drama"].generate_shot_video(
                                package_data,
                                selected_shot_id,
                                progress_callback=progress_callback,
                                prompt_override=prompt_override,
                                workflow=workflow_choice,
                                width=int(width),
                                height=int(height),
                                duration_seconds=float(duration_seconds),
                            )
                        )

                    shot_videos = st.session_state["novel_drama_shot_videos"]
                    shot_videos[selected_shot_id] = result.model_dump(mode="json")
                    progress_bar.progress(1.0)
                    status_text.text(tr("novel_drama.shot_video.complete", fallback="Shot video generated."))
                    st.success(tr("novel_drama.shot_video.success", fallback="Shot video generated successfully."))

                except Exception as e:
                    logger.exception(e)
                    progress_bar.empty()
                    status_text.empty()
                    st.error(tr("status.error", fallback="Error: {error}", error=str(e)))

            shot_video = st.session_state.get("novel_drama_shot_videos", {}).get(selected_shot_id)
            if shot_video:
                video_path = shot_video.get("video_path")
                st.caption(video_path)
                if video_path and Path(video_path).exists():
                    st.video(video_path)
                meta = (
                    f"{shot_video.get('width')}x{shot_video.get('height')}, "
                    f"{shot_video.get('frame_count')} frames @ {shot_video.get('fps')}fps"
                )
                st.caption(meta)
                with st.expander(tr("novel_drama.shot_video.used_prompt", fallback="Used prompt"), expanded=False):
                    st.code(shot_video.get("prompt", ""), language="text")

    def _render_shot_image_tools(self, pixelle_video: Any, package_data: dict):
        """Render one-shot image generation controls for the reviewed package."""

        shots = package_data.get("shots", [])
        if not shots:
            return

        if "novel_drama_shot_images" not in st.session_state:
            st.session_state["novel_drama_shot_images"] = {}

        with st.expander(tr("novel_drama.section.shot_image", fallback="Single Shot Image"), expanded=False):
            st.caption(
                tr(
                    "novel_drama.shot_image.hint",
                    fallback="Generate one reviewed shot image first. This keeps ComfyUI failures small and easy to retry.",
                )
            )

            shot_options = [shot.get("shot_id", f"shot_{index + 1}") for index, shot in enumerate(shots)]
            shot_labels = {
                shot.get("shot_id", f"shot_{index + 1}"): (
                    f"{shot.get('order', index + 1)}. {shot.get('shot_id', '')} - "
                    f"{shot.get('shot_type', '')} - {shot.get('dialogue_or_narration', '')[:28]}"
                )
                for index, shot in enumerate(shots)
            }
            selected_shot_id = st.selectbox(
                tr("novel_drama.shot_image.select_shot", fallback="Select shot"),
                shot_options,
                format_func=lambda shot_id: shot_labels.get(shot_id, shot_id),
                key="novel_drama_image_selected_shot",
            )
            selected_shot = next(shot for shot in shots if shot.get("shot_id") == selected_shot_id)

            workflow_options = self._get_image_workflow_options(pixelle_video)
            workflow_choice = st.selectbox(
                tr("novel_drama.shot_image.workflow", fallback="Image workflow"),
                workflow_options,
                format_func=lambda value: tr("novel_drama.shot_image.default_workflow", fallback="Configured default") if value is None else value,
                key="novel_drama_image_workflow",
            )

            size_col1, size_col2 = st.columns(2)
            with size_col1:
                width = st.number_input(
                    tr("novel_drama.shot_image.width", fallback="Width"),
                    min_value=512,
                    max_value=1536,
                    value=768,
                    step=64,
                    key="novel_drama_image_width",
                )
            with size_col2:
                height = st.number_input(
                    tr("novel_drama.shot_image.height", fallback="Height"),
                    min_value=512,
                    max_value=1536,
                    value=1024,
                    step=64,
                    key="novel_drama_image_height",
                )

            prompt_override = st.text_area(
                tr("novel_drama.shot_image.prompt", fallback="Shot image prompt"),
                value=selected_shot.get("visual_prompt_en", ""),
                height=120,
                key=f"novel_drama_shot_prompt_{selected_shot_id}",
            )

            generate_image_clicked = st.button(
                tr("novel_drama.shot_image.generate", fallback="Generate selected shot image"),
                type="primary",
                use_container_width=True,
                key="novel_drama_generate_shot_image",
            )

            if generate_image_clicked:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(event):
                    progress_bar.progress(min(max(event.progress, 0.0), 1.0))
                    status_text.text(tr(event.event_type, fallback=event.event_type))

                try:
                    with st.spinner(tr("novel_drama.shot_image.generating", fallback="Generating shot image...")):
                        result = run_async(
                            pixelle_video.pipelines["novel_drama"].generate_shot_image(
                                package_data,
                                selected_shot_id,
                                progress_callback=progress_callback,
                                prompt_override=prompt_override,
                                workflow=workflow_choice,
                                width=int(width),
                                height=int(height),
                            )
                        )

                    shot_images = st.session_state["novel_drama_shot_images"]
                    shot_images[selected_shot_id] = result.model_dump(mode="json")
                    progress_bar.progress(1.0)
                    status_text.text(tr("novel_drama.shot_image.complete", fallback="Shot image generated."))
                    st.success(tr("novel_drama.shot_image.success", fallback="Shot image generated successfully."))

                except Exception as e:
                    logger.exception(e)
                    progress_bar.empty()
                    status_text.empty()
                    st.error(tr("status.error", fallback="Error: {error}", error=str(e)))

            shot_image = st.session_state.get("novel_drama_shot_images", {}).get(selected_shot_id)
            if shot_image:
                image_path = shot_image.get("image_path")
                st.caption(image_path)
                if image_path and Path(image_path).exists():
                    st.image(image_path, use_container_width=True)
                with st.expander(tr("novel_drama.shot_image.used_prompt", fallback="Used prompt"), expanded=False):
                    st.code(shot_image.get("prompt", ""), language="text")

    def _render_package(self, package_data: dict):
        """Render generated package in a readable review layout."""

        st.subheader(package_data.get("episode_title", "Untitled"))
        st.caption(package_data.get("logline", ""))

        meta_col1, meta_col2, meta_col3 = st.columns(3)
        meta_col1.metric(tr("novel_drama.metric.duration", fallback="Duration"), package_data.get("target_duration_seconds"))
        meta_col2.metric(tr("novel_drama.metric.shots", fallback="Shots"), len(package_data.get("shots", [])))
        meta_col3.metric(tr("novel_drama.metric.characters", fallback="Characters"), len(package_data.get("characters", [])))

        with st.expander(tr("novel_drama.section.overview", fallback="Overview"), expanded=True):
            source_anchors = package_data.get("source_anchors", [])
            if source_anchors:
                st.markdown("**Source anchors:**")
                for anchor in source_anchors:
                    st.markdown(f"- {anchor}")
            st.markdown(f"**Hook:** {package_data.get('hook', '')}")
            st.markdown(f"**Summary:** {package_data.get('summary', '')}")
            st.markdown(f"**Ending hook:** {package_data.get('ending_hook', '')}")

        with st.expander(tr("novel_drama.section.characters", fallback="Characters"), expanded=True):
            for character in package_data.get("characters", []):
                st.markdown(f"**{character.get('character_id')} - {character.get('name')}**")
                st.write(character.get("appearance", ""))
                st.caption(character.get("visual_prompt_en", ""))

        with st.expander(tr("novel_drama.section.shots", fallback="Shots"), expanded=True):
            for shot in package_data.get("shots", []):
                st.markdown(
                    f"**{shot.get('order')}. {shot.get('shot_id')} - {shot.get('shot_type')} - "
                    f"{shot.get('duration_seconds')}s**"
                )
                st.write(shot.get("dialogue_or_narration", ""))
                st.caption(shot.get("visual_prompt_en", ""))

        json_text = json.dumps(package_data, ensure_ascii=False, indent=2)
        with st.expander(tr("novel_drama.section.json", fallback="Raw JSON"), expanded=False):
            st.code(json_text, language="json")
            st.download_button(
                tr("novel_drama.download", fallback="Download JSON"),
                data=json_text.encode("utf-8"),
                file_name="novel_drama_package.json",
                mime="application/json",
                use_container_width=True,
            )

    def _format_package_json(self, package_data: dict) -> str:
        """Format a package for review/editing."""

        return json.dumps(package_data, ensure_ascii=False, indent=2)

    def _validate_package_json(self, json_text: str) -> dict:
        """Validate edited JSON against the script package model."""

        parsed = json.loads(json_text)
        package = NovelDramaPackage.model_validate(parsed)
        return package.model_dump(mode="json")

    def _save_package_draft(self, package_data: dict) -> Path:
        """Save a reviewed script package draft under the runtime output directory."""

        drafts_dir = Path("output") / "novel_drama_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        episode_number = package_data.get("episode_number", 1)
        title = self._safe_filename(package_data.get("episode_title", "untitled"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_path = drafts_dir / f"episode_{episode_number}_{title}_{timestamp}.json"
        draft_path.write_text(self._format_package_json(package_data), encoding="utf-8")
        return draft_path

    def _safe_filename(self, value: str) -> str:
        """Convert a title into a portable filename fragment."""

        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value).strip())
        return safe.strip("_")[:40] or "untitled"

    def _get_image_workflow_options(self, pixelle_video: Any) -> list[str | None]:
        """Return image workflows for the single-shot generator."""

        workflows: list[str | None] = [None]
        try:
            for workflow in pixelle_video.media.list_workflows():
                key = workflow.get("key", "")
                name = workflow.get("name", "")
                if key and name.startswith("image_"):
                    workflows.append(key)
        except Exception as e:
            logger.warning(f"Failed to list image workflows: {e}")
        return workflows

    def _get_video_workflow_options(self, pixelle_video: Any) -> list[str | None]:
        """Return video workflows for the single-shot LTX generator."""

        workflows: list[str | None] = [None]
        try:
            for workflow in pixelle_video.media.list_workflows():
                key = workflow.get("key", "")
                name = workflow.get("name", "")
                if key and name.startswith("video_"):
                    workflows.append(key)
        except Exception as e:
            logger.warning(f"Failed to list video workflows: {e}")
        return workflows


register_pipeline_ui(NovelDramaPipelineUI)
