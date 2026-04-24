# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Prompt builder for adapting novel excerpts into reviewable short-drama packages.
"""

from pixelle_video.models.novel_drama import NovelDramaRequest, NovelSourceFacts


NOVEL_SOURCE_FACTS_PROMPT = """# Role
You are a careful story analyst.

# Task
Extract only explicit facts from the novel excerpt. This is grounding data for a later adaptation step.

# Rules
1. Do not invent names, relationships, occupations, locations, events, or genre tropes.
2. If a field is not explicit in the excerpt, return an empty list for that field.
3. Use exact character names, locations, objects, time markers, and short phrases when possible.
4. `source_summary` must describe only what is present in the excerpt.
5. Do not output a JSON schema. Fill the JSON object with facts from the excerpt.

# Novel Excerpt
```
{novel_text}
```

Only output this JSON object shape. No markdown. No explanations.

{{
  "source_summary": "",
  "character_names": [],
  "locations": [],
  "important_objects": [],
  "time_markers": [],
  "key_events": [],
  "conflicts_or_questions": [],
  "direct_quotes_or_phrases": []
}}
"""


NOVEL_DRAMA_SCRIPT_PACKAGE_PROMPT = """# Role
You are a professional vertical short-drama screenwriter and visual director.
You adapt novel excerpts into short, dramatic, reviewable episode plans.

# Task
Adapt the provided novel excerpt into a structured short-drama script package.
This is an MVP script package only. Do not generate video files. Do not mention ComfyUI.

# Output Language
Use this language for all human-readable script text: {language}
Keep `visual_prompt_en` and `negative_prompt_en` in English for future image/video generation.

# Target
- Episode number: {episode_number}
- Target duration: about {target_duration_seconds} seconds
- Target shot count: about {target_shots} shots
- Audience: {audience}
- Adaptation style: {adaptation_style}

# Novel Excerpt
```
{novel_text}
```

# Source Facts To Preserve
The following facts were extracted from the excerpt and are the hard source boundary.
Do not contradict them or replace them with another story.

```json
{source_facts_json}
```

# Adaptation Rules
1. Preserve the core conflict, relationship tension, and emotional truth of the excerpt.
2. Do not replace the source plot with a generic trope. If names, objects, locations, or events appear in the source facts, use them exactly.
3. Copy the most important source facts into `source_anchors`: character names, locations, objects, secrets, suspicious sounds, and important time markers.
4. Every character, scene, and shot must be consistent with the source facts and `source_anchors`.
5. Do not introduce unrelated divorce contracts, weddings, CEOs, hospitals, pregnancies, revenge plots, or modern romance tropes unless they are explicitly in the excerpt.
6. Do not summarize like an essay. Rewrite it as a watchable short-drama episode.
7. The first shot must create a strong hook within 3 seconds.
8. Each shot needs visible action, camera language, emotion, and either dialogue or narration.
9. Keep dialogue short and performable.
10. Use stable character IDs like C1, C2 and stable scene IDs like S1, S2.
11. Every shot must reference existing character IDs and scene IDs.
12. Add continuity notes for character appearance, wardrobe, props, and locations.
13. End with a cliffhanger or curiosity gap.
14. If the excerpt does not provide a character appearance, infer a restrained appearance that does not contradict the text.

# Structure Requirements
Create:
- episode title
- logline
- source anchors from the original excerpt
- opening hook
- summary
- genre
- character cards
- scenes
- ordered shots
- ending hook
- continuity notes

Only output JSON that matches the requested schema. No markdown. No explanations.
"""


def build_novel_source_facts_prompt(novel_text: str) -> str:
    """Build the prompt for extracting source facts from the original excerpt."""

    return NOVEL_SOURCE_FACTS_PROMPT.format(novel_text=novel_text)


def build_novel_drama_prompt(request: NovelDramaRequest, source_facts: NovelSourceFacts) -> str:
    """Build the prompt for novel-to-short-drama script package generation."""

    return NOVEL_DRAMA_SCRIPT_PACKAGE_PROMPT.format(
        novel_text=request.novel_text,
        source_facts_json=source_facts.model_dump_json(indent=2),
        target_duration_seconds=request.target_duration_seconds,
        target_shots=request.target_shots,
        language=request.language,
        audience=request.audience,
        adaptation_style=request.adaptation_style,
        episode_number=request.episode_number,
    )


__all__ = ["build_novel_source_facts_prompt", "build_novel_drama_prompt"]
