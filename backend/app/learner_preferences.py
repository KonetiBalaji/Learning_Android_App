from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Interest = Literal['sports', 'music', 'art', 'nature', 'space', 'games']


class InterestPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    interests: list[Interest] = Field(max_length=3)

    @field_validator('interests')
    @classmethod
    def unique_interests(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Choose each interest only once')
        return values
