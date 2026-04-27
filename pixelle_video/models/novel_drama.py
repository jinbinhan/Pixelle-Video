# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
Domain models for the novel-to-short-drama MVP.

These models describe the reviewable script package only. They intentionally do
not depend on ComfyUI, TTS, or final video composition.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class NovelDramaRequest(BaseModel):
    """User request for adapting a novel excerpt into a short-drama package."""

    novel_text: str = Field(description="Original novel excerpt to adapt")
    target_duration_seconds: int = Field(default=60, ge=15, le=180)
    target_shots: int = Field(default=8, ge=3, le=20)
    language: str = Field(default="zh-CN", description="Output language, e.g. zh-CN or en-US")
    audience: str = Field(default="short-video viewers")
    adaptation_style: str = Field(default="vertical short drama with strong hook and cliffhanger")
    episode_number: int = Field(default=1, ge=1)


class NovelSourceFacts(BaseModel):
    """Grounding facts extracted from the original novel excerpt."""

    source_summary: str = Field(description="Brief factual summary of only what is explicit in the excerpt")
    character_names: List[str] = Field(default_factory=list, description="Exact character names in the excerpt")
    locations: List[str] = Field(default_factory=list, description="Exact locations or setting details in the excerpt")
    important_objects: List[str] = Field(default_factory=list, description="Important props, objects, or visible clues")
    time_markers: List[str] = Field(default_factory=list, description="Time markers explicitly present in the excerpt")
    key_events: List[str] = Field(default_factory=list, description="Explicit events from the excerpt")
    conflicts_or_questions: List[str] = Field(
        default_factory=list,
        description="Explicit conflicts, mysteries, or unanswered questions in the excerpt",
    )
    direct_quotes_or_phrases: List[str] = Field(
        default_factory=list,
        description="Short exact phrases from the excerpt that should be preserved",
    )


class CharacterCard(BaseModel):
    """Stable character card for continuity across shots."""

    character_id: str = Field(description="Stable ID, e.g. C1")
    name: str
    role: str = Field(description="Role in this episode, e.g. protagonist, antagonist")
    age_range: str
    personality: str
    appearance: str
    costume: str
    motivation: str
    continuity_notes: List[str] = Field(default_factory=list)
    visual_prompt_en: str = Field(description="English character prompt for later image/video generation")
    negative_prompt_en: str = Field(default="")


class DramaScene(BaseModel):
    """A dramatic scene grouping one or more shots."""

    scene_id: str = Field(description="Stable ID, e.g. S1")
    location: str
    time_of_day: str
    dramatic_purpose: str
    mood: str
    characters: List[str] = Field(description="Character IDs appearing in this scene")


class DramaShot(BaseModel):
    """Single short-drama shot."""

    shot_id: str = Field(description="Stable ID, e.g. SH1")
    scene_id: str
    order: int = Field(ge=1)
    duration_seconds: float = Field(ge=1, le=20)
    shot_type: str = Field(description="Camera framing, e.g. close-up, medium shot")
    camera_motion: str
    characters: List[str] = Field(description="Character IDs appearing in this shot")
    action: str
    dialogue_or_narration: str
    emotion: str
    visual_prompt_en: str = Field(description="English visual prompt for later image/video generation")
    sound_design: str = Field(default="")
    continuity_notes: List[str] = Field(default_factory=list)


class NovelDramaPackage(BaseModel):
    """Reviewable output of the novel-to-short-drama MVP."""

    episode_title: str
    episode_number: int = Field(ge=1)
    logline: str
    source_anchors: List[str] = Field(
        description="Concrete facts from the source excerpt that the adaptation must preserve"
    )
    hook: str = Field(description="Opening hook for the first 3 seconds")
    summary: str
    genre: str
    target_duration_seconds: int = Field(ge=15, le=180)
    language: str
    adaptation_notes: List[str] = Field(default_factory=list)
    characters: List[CharacterCard]
    scenes: List[DramaScene]
    shots: List[DramaShot]
    ending_hook: str
    continuity_notes: List[str] = Field(default_factory=list)
    status: Literal["script_package_only"] = "script_package_only"

    @model_validator(mode="after")
    def validate_references(self):
        character_ids = {character.character_id for character in self.characters}
        scene_ids = {scene.scene_id for scene in self.scenes}

        for scene in self.scenes:
            missing = set(scene.characters) - character_ids
            if missing:
                raise ValueError(f"Scene {scene.scene_id} references unknown characters: {sorted(missing)}")

        for shot in self.shots:
            if shot.scene_id not in scene_ids:
                raise ValueError(f"Shot {shot.shot_id} references unknown scene: {shot.scene_id}")
            missing = set(shot.characters) - character_ids
            if missing:
                raise ValueError(f"Shot {shot.shot_id} references unknown characters: {sorted(missing)}")

        return self


class NovelShotImageResult(BaseModel):
    """Generated image asset for one reviewed drama shot."""

    shot_id: str
    image_path: str
    prompt: str
    workflow: Optional[str] = None
    width: int
    height: int
    status: Literal["image_generated"] = "image_generated"


class NovelShotVideoResult(BaseModel):
    """Generated video asset for one reviewed drama shot."""

    shot_id: str
    video_path: str
    prompt: str
    workflow: Optional[str] = None
    width: int
    height: int
    duration_seconds: float
    frame_count: int
    fps: int
    status: Literal["video_generated"] = "video_generated"


__all__ = [
    "NovelDramaRequest",
    "NovelSourceFacts",
    "NovelDramaPackage",
    "NovelShotImageResult",
    "NovelShotVideoResult",
    "CharacterCard",
    "DramaScene",
    "DramaShot",
]
