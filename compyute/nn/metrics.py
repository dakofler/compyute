"""Evaluation metrics module"""

from abc import ABC, abstractmethod
from typing import Literal

from ..base_tensor import Tensor
from .functional.metrics import accuracy_score, r2_score

__all__ = ["Accuracy", "R2"]


class Metric(ABC):
    """Metric base class."""

    __slots__ = ()

    @abstractmethod
    def __call__(self, y: Tensor, t: Tensor) -> Tensor: ...


class Accuracy(Metric):
    """Computes the accuracy score."""

    __slots__ = ()

    def __call__(self, y_pred: Tensor, y_true: Tensor) -> Tensor:
        """Computes the accuracy score.

        Parameters
        ----------
        y_pred : Tensor
            A model's predictions.
        y_true : Tensor
            Target values.

        Returns
        -------
        Tensor
            Accuracy value.
        """
        return accuracy_score(y_pred, y_true)


class R2(Metric):
    """Computes the coefficient of determination (R2 score)."""

    __slots__ = ()

    def __call__(self, y_pred: Tensor, y_true: Tensor, eps: float = 1e-8) -> Tensor:
        """Computes the coefficient of determination (R2 score).

        Parameters
        ----------
        y_pred : Tensor
            A model's predictions.
        y_true : Tensor
            Target values.
        eps: float, optional
            Constant for numerical stability, by default 1e-8.

        Returns
        -------
        Tensor
            R2 score.
        """
        return r2_score(y_pred, y_true, eps)


_MetricLike = Metric | Literal["accuracy", "r2"]
METRICS = {"accuracy": Accuracy, "r2": R2}


def get_metric_function(metric: _MetricLike) -> Metric:
    """Returns an instance of a metric function."""
    if isinstance(metric, Metric):
        return metric
    if metric not in METRICS:
        raise ValueError(f"Unknown metric function: {metric}.")
    return METRICS[metric]()