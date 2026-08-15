"""Frozen Answer Generation Runtime V1 public interface."""

from .runtime import generate_answer
from .schema import VERSION

__all__ = ["VERSION", "generate_answer"]
