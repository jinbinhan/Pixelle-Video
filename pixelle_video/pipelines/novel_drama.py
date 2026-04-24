# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Novel Drama Pipeline.

Phase 1 MVP: generate a reviewable script package from a novel excerpt.
This pipeline deliberately stops before ComfyUI, TTS, or video composition.
"""

import json
import re
from typing import Optional, Callable

from loguru import logger

from pixelle_video.models.novel_drama import NovelDramaPackage, NovelDramaRequest, NovelSourceFacts
from pixelle_video.models.progress import ProgressEvent
from pixelle_video.pipelines.base import BasePipeline
from pixelle_video.prompts.novel_drama import build_novel_drama_prompt, build_novel_source_facts_prompt


class NovelDramaPipeline(BasePipeline):
    """Generate a structured short-drama script package from novel text."""

    async def __call__(
        self,
        text: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        **kwargs
    ) -> NovelDramaPackage:
        """
        Adapt novel text into a reviewable short-drama package.

        Args:
            text: Novel excerpt.
            progress_callback: Optional progress callback.
            **kwargs: NovelDramaRequest fields except `novel_text`.

        Returns:
            NovelDramaPackage.
        """

        self._report_progress(progress_callback, "novel_drama_preparing", 0.05)

        request = NovelDramaRequest(
            novel_text=text,
            target_duration_seconds=kwargs.get("target_duration_seconds", 60),
            target_shots=kwargs.get("target_shots", 8),
            language=kwargs.get("language", "zh-CN"),
            audience=kwargs.get("audience", "short-video viewers"),
            adaptation_style=kwargs.get(
                "adaptation_style",
                "vertical short drama with strong hook and cliffhanger",
            ),
            episode_number=kwargs.get("episode_number", 1),
        )

        logger.info(
            "Generating novel drama script package "
            f"(episode={request.episode_number}, duration={request.target_duration_seconds}s, "
            f"shots={request.target_shots})"
        )

        self._report_progress(progress_callback, "novel_drama_extracting_source_facts", 0.15)

        source_facts = await self._extract_grounded_source_facts(request, kwargs)
        source_markers = self._collect_source_markers(request.novel_text, source_facts)
        logger.info(f"Extracted novel source markers: {source_markers}")

        prompt = build_novel_drama_prompt(request, source_facts)

        self._report_progress(progress_callback, "novel_drama_generating_script_package", 0.25)

        package = await self.core.llm(
            prompt=prompt,
            response_type=NovelDramaPackage,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 8192),
        )

        missing_markers = self._find_missing_source_markers(package, source_markers)
        if missing_markers:
            logger.warning(f"Novel drama package missed source markers, retrying: {missing_markers}")
            self._report_progress(progress_callback, "novel_drama_retrying_source_fidelity", 0.7)
            retry_prompt = self._build_source_fidelity_retry_prompt(prompt, missing_markers)
            package = await self.core.llm(
                prompt=retry_prompt,
                response_type=NovelDramaPackage,
                temperature=kwargs.get("retry_temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 8192),
            )
            missing_markers = self._find_missing_source_markers(package, source_markers)

        if missing_markers:
            raise ValueError(
                "剧本包与小说原文锚点不一致，缺少关键原文元素："
                + "、".join(missing_markers)
                + "。建议缩短原文片段，或换更强的剧本/理解模型后重试。"
            )

        self._report_progress(progress_callback, "novel_drama_script_package_complete", 1.0)
        logger.info(f"Generated novel drama package: {package.episode_title}")

        return package

    async def _extract_grounded_source_facts(self, request: NovelDramaRequest, kwargs: dict) -> NovelSourceFacts:
        """Extract source facts, falling back to local rules when the LLM drifts."""

        rule_based_facts = self._build_rule_based_source_facts(request.novel_text)
        if not kwargs.get("use_llm_source_facts", False):
            return rule_based_facts

        try:
            source_facts_raw = await self.core.llm(
                prompt=build_novel_source_facts_prompt(request.novel_text),
                temperature=kwargs.get("source_temperature", 0.1),
                max_tokens=kwargs.get("source_max_tokens", 2048),
            )
            llm_facts = self._parse_source_facts(source_facts_raw)
        except Exception as e:
            logger.warning(f"Novel source fact extraction fell back to local rules: {e}")
            return rule_based_facts

        return self._merge_grounded_source_facts(request.novel_text, rule_based_facts, llm_facts)

    def _collect_source_markers(self, novel_text: str, source_facts: NovelSourceFacts) -> list[str]:
        """Collect source markers that should survive the adaptation step."""

        normalized_source = self._normalize_text(novel_text)
        candidates: list[str] = []

        for values in (
            source_facts.character_names,
            source_facts.locations,
            source_facts.important_objects,
            source_facts.time_markers,
        ):
            candidates.extend(values)

        markers: list[str] = []
        for candidate in candidates:
            marker = candidate.strip()
            if not marker or len(marker) < 2:
                continue
            if self._normalize_text(marker) not in normalized_source:
                continue
            normalized_marker = self._normalize_text(marker)
            if any(normalized_marker in self._normalize_text(existing) for existing in markers):
                continue
            markers = [
                existing
                for existing in markers
                if self._normalize_text(existing) not in normalized_marker
            ]
            if marker not in markers:
                markers.append(marker)

        return markers[:12]

    def _build_rule_based_source_facts(self, novel_text: str) -> NovelSourceFacts:
        """Build conservative source facts directly from the excerpt text."""

        return NovelSourceFacts(
            source_summary=novel_text[:240],
            character_names=self._extract_chinese_names(novel_text),
            locations=self._extract_terms(
                novel_text,
                ["老宅", "门口", "二楼", "楼上", "房间", "客厅", "卧室", "走廊", "门外", "屋里", "医院", "学校", "公司"],
            ),
            important_objects=self._extract_terms(
                novel_text,
                ["怀表", "照片", "信", "钥匙", "手机", "戒指", "玉佩", "合同", "日记", "录音", "项链", "血迹", "刀", "伞"],
            ),
            time_markers=self._extract_time_markers(novel_text),
            key_events=[],
            conflicts_or_questions=[],
            direct_quotes_or_phrases=self._extract_short_phrases(novel_text),
        )

    def _merge_grounded_source_facts(
        self,
        novel_text: str,
        rule_based_facts: NovelSourceFacts,
        llm_facts: NovelSourceFacts,
    ) -> NovelSourceFacts:
        """Merge only LLM facts that can be grounded in the source text."""

        normalized_source = self._normalize_text(novel_text)

        def grounded(values: list[str]) -> list[str]:
            result: list[str] = []
            for value in values:
                item = value.strip()
                if len(item) < 2:
                    continue
                if self._normalize_text(item) not in normalized_source:
                    continue
                if item not in result:
                    result.append(item)
            return result

        return NovelSourceFacts(
            source_summary=rule_based_facts.source_summary,
            character_names=self._merge_unique(rule_based_facts.character_names, grounded(llm_facts.character_names)),
            locations=self._merge_unique(rule_based_facts.locations, grounded(llm_facts.locations)),
            important_objects=self._merge_unique(rule_based_facts.important_objects, grounded(llm_facts.important_objects)),
            time_markers=self._merge_unique(rule_based_facts.time_markers, grounded(llm_facts.time_markers)),
            key_events=grounded(llm_facts.key_events),
            conflicts_or_questions=grounded(llm_facts.conflicts_or_questions),
            direct_quotes_or_phrases=self._merge_unique(
                rule_based_facts.direct_quotes_or_phrases,
                grounded(llm_facts.direct_quotes_or_phrases),
            ),
        )

    def _extract_chinese_names(self, text: str) -> list[str]:
        """Extract likely Chinese personal names with a conservative surname list."""

        surnames = "赵钱孙李周吴郑王冯陈蒋沈韩杨朱秦许何吕施张孔曹严华金魏陶姜谢邹苏潘范彭郎鲁韦昌马苗方俞任袁柳史唐薛雷贺倪汤罗郝安常乐傅齐康伍余顾孟黄穆萧尹姚邵汪毛戴宋庞熊纪舒屈项祝董梁杜阮蓝季贾路江童颜郭梅盛林钟徐邱骆高夏蔡田胡凌霍虞万文寇欧陆刘叶程"
        pattern = rf"([{surnames}][\u4e00-\u9fff]{{1,2}})"
        return self._merge_unique([], re.findall(pattern, text))

    def _extract_terms(self, text: str, terms: list[str]) -> list[str]:
        """Extract known useful source terms that appear in the excerpt."""

        return [term for term in terms if term in text]

    def _extract_time_markers(self, text: str) -> list[str]:
        """Extract common Chinese time markers."""

        patterns = [
            r"[一二三四五六七八九十两0-9]+年前",
            r"午夜[一二三四五六七八九十0-9]+点(?:整)?",
            r"[一二三四五六七八九十0-9]+点(?:整)?",
            r"雨夜|深夜|午夜|清晨|黄昏|傍晚|凌晨",
        ]
        markers: list[str] = []
        for pattern in patterns:
            markers.extend(re.findall(pattern, text))
        return self._merge_unique([], markers)

    def _extract_short_phrases(self, text: str) -> list[str]:
        """Extract short quoted phrases from Chinese dialogue punctuation."""

        phrases = re.findall(r"[：:][“\"]?([^。！？\n]{2,24})[。！？\"]?", text)
        return self._merge_unique([], [phrase.strip() for phrase in phrases if phrase.strip()])

    def _merge_unique(self, *groups: list[str]) -> list[str]:
        """Merge string lists while preserving order."""

        merged: list[str] = []
        for group in groups:
            for value in group:
                if value and value not in merged:
                    merged.append(value)
        return merged

    def _parse_source_facts(self, content: str) -> NovelSourceFacts:
        """Parse source facts from a raw LLM JSON response."""

        data = self._extract_json_object(content)
        if self._looks_like_json_schema(data):
            raise ValueError(
                "LLM returned a JSON schema instead of extracted source facts. "
                "Please retry, or use a model with better JSON instruction following."
            )
        return NovelSourceFacts.model_validate(data)

    def _extract_json_object(self, content: str) -> dict:
        """Extract the first JSON object from raw LLM text."""

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(content[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Failed to parse source facts JSON: {content[:200]}...")

    def _looks_like_json_schema(self, data: dict) -> bool:
        """Detect when a model echoed a JSON schema instead of filling the object."""

        return "properties" in data and "source_summary" not in data

    def _find_missing_source_markers(self, package: NovelDramaPackage, markers: list[str]) -> list[str]:
        """Return source markers missing from the generated script package."""

        if not markers:
            return []

        package_text = self._normalize_text(json.dumps(package.model_dump(mode="json"), ensure_ascii=False))
        return [marker for marker in markers if self._normalize_text(marker) not in package_text]

    def _build_source_fidelity_retry_prompt(self, prompt: str, missing_markers: list[str]) -> str:
        """Build a stricter retry prompt when the first draft drifts from the source."""

        return (
            prompt
            + "\n\n# Source Fidelity Retry\n"
            + "The previous draft drifted away from the original excerpt. Regenerate from scratch.\n"
            + "The output must include and preserve these exact source markers: "
            + ", ".join(missing_markers)
            + "\nDo not introduce a different story, different names, or unrelated short-drama tropes.\n"
            + "Only output JSON that matches the requested schema."
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for simple source-marker checks."""

        return "".join(str(text).lower().split())
