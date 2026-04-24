# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Novel Drama Pipeline UI.

Phase 1 MVP: input a novel excerpt and generate a reviewable script package.
"""

import json
from typing import Any

import streamlit as st
from loguru import logger

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

                    st.session_state["novel_drama_package"] = package.model_dump(mode="json")
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

            self._render_package(package_data)

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


register_pipeline_ui(NovelDramaPipelineUI)
