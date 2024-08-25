"""Neural network loss functions."""

import math

from ...preprocessing.basic import one_hot_encode
from ...tensor_ops.transforming import clip, log, mean
from ...tensor_ops.transforming import sum as cpsum
from ...tensors import Tensor
from .activations import softmax
from .functions import Function, FunctionCache, PseudoCache

__all__ = ["mean_squared_error", "cross_entropy", "binary_cross_entropy"]


class FMeanSquaredError(Function):
    """Computes the mean squared error loss."""

    @staticmethod
    def forward(cache: FunctionCache, y_pred: Tensor, y_true: Tensor) -> Tensor:
        dif = y_pred - y_true
        cache.y_pred, cache.dif = y_pred, dif
        return mean(dif**2)

    @staticmethod
    def backward(cache: FunctionCache) -> Tensor:
        return cache.dif * 2 / float(cache.y_pred.size)


def mean_squared_error(y_pred: Tensor, y_true: Tensor) -> Tensor:
    """Computes the mean squared error loss.

    Parameters
    ----------
    y_pred : Tensor
        Model predictions.
    y_true : Tensor
        Target values.

    Returns
    -------
    Tensor
        Mean squared error loss.

    See Also
    --------
    :class:`compyute.nn.MeanSquaredError`
    """
    return FMeanSquaredError.forward(PseudoCache(), y_pred, y_true)


class FCrossEntropy(Function):
    """Computes the cross entropy loss."""

    @staticmethod
    def forward(cache: FunctionCache, y_pred: Tensor, y_true: Tensor) -> Tensor:
        probs = softmax(y_pred)
        y_true = one_hot_encode(y_true, y_pred.shape[-1]).to_float()
        y = mean(cpsum(-log(probs) * y_true, axis=-1))

        cache.y_true, cache.probs = y_true, probs
        return y

    @staticmethod
    def backward(cache: FunctionCache) -> Tensor:
        y_true, probs = cache.y_true, cache.probs
        return (probs - y_true) / float(math.prod(y_true.shape[:-1]))


def cross_entropy(y_pred: Tensor, y_true: Tensor) -> Tensor:
    """Computes the cross entropy loss.

    Parameters
    ----------
    y_pred : Tensor
        Model logits.
    y_true : Tensor
        Target class labels, must be of type ``int``.

    Returns
    -------
    Tensor
        Cross entropy loss.

    See Also
    --------
    :class:`compyute.nn.CrossEntropy`
    """
    return FCrossEntropy.forward(PseudoCache(), y_pred, y_true)


class FBinaryCrossEntropy(Function):
    """Computes the binary cross entropy loss."""

    @staticmethod
    def forward(cache: FunctionCache, y_pred: Tensor, y_true: Tensor) -> Tensor:
        clip_value = 100
        log_y_pred = clip(log(y_pred), -clip_value, clip_value)
        log_one_minus_y_pred = clip(log(1 - y_pred), -clip_value, clip_value)
        y = -mean(y_true * log_y_pred + (1 - y_true) * log_one_minus_y_pred)

        cache.y_pred, cache.y_true = y_pred, y_true
        return y

    @staticmethod
    def backward(cache: FunctionCache) -> Tensor:
        y_pred, y_true = cache.y_pred, cache.y_true
        return (-y_true / y_pred + (1 - y_true) / (1 - y_pred)) / float(y_pred.size)


def binary_cross_entropy(y_pred: Tensor, y_true: Tensor) -> Tensor:
    """Computes the binary cross entropy loss.

    Parameters
    ----------
    y_pred : Tensor
        Normalized model outputs.
    y_true : Tensor
        Binary target class labels, must be either ``0`` or ``1``.

    Returns
    -------
    Tensor
        Cross entropy loss.

    See Also
    --------
    :class:`compyute.nn.BinaryCrossEntropy`
    """
    return FBinaryCrossEntropy.forward(PseudoCache(), y_pred, y_true)
